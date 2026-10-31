#!/usr/bin/env python3
"""Acceptance driver for the Lean certificates (reads certificates, compiles, mutates, writes a receipt).

  python scripts/check_proofs.py                # verify committed certificates, write receipt
  python scripts/check_proofs.py --regenerate   # rebuild certificates + Lean files from the source CSV
  python scripts/check_proofs.py --fast         # skip Lean-source mutants

Exit status 0 only if: no generated-file drift; fresh kernel compile succeeds; axioms are a subset
of {propext, Classical.choice, Quot.sound}; every "reject" mutant fails in Lean and every
"accept" boundary control passes; Python mirror agrees with Lean on every instance mutant.
"""
from __future__ import annotations

import argparse
import re
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evolve import proof as P  # noqa: E402

ART = ROOT / "artifacts" / "proof"


def first_error(text: str) -> str:
    text = re.sub(r"/(tmp|var/tmp)/[^\s:]*/", "", text)
    for line in text.splitlines():
        if "error" in line:
            return line.strip()[:300]
    return text.strip().splitlines()[0][:300] if text.strip() else ""


def strip_lean_comments(src: str) -> str:
    src = re.sub(r"/-.*?-/", "", src, flags=re.S)
    return re.sub(r"--[^\n]*", "", src)


def forbidden_tokens(lean_dir: Path) -> list[str]:
    bad = []
    pat = re.compile(r"\b(sorry|admit|native_decide|axiom|unsafe|implemented_by|extern|opaque|Lean\.ofReduceBool)\b")
    for f in sorted(lean_dir.rglob("*.lean")):
        if ".lake" in f.parts:
            continue
        if f.name == "Audit.lean":
            continue
        for m in pat.finditer(strip_lean_comments(f.read_text())):
            bad.append(f"{f.relative_to(lean_dir)}: {m.group(1)}")
    return bad


def load_certs() -> list[dict]:
    certs = []
    for f in sorted(ART.glob("trpb_*.json")):
        certs.append(P.read_json(f))
    return certs


SWEEP_DELTAS = ["0", "0.001", "0.0025", "0.005", "0.0075", "0.01", "0.015"]
SWEEP_PAIRS = [("route", "VFVS", "AIKG"), ("blocked", "GCLS", "AIKG")]


def run_sweep(csv_path, scope: bool) -> dict:
    """For each assumed delta: does a certificate exist, and does Lean accept it?"""
    obs, counts = P.load_trpb_observations(csv_path)
    source = dict(P.SOURCE_META, sha256=P.sha256_file(csv_path), counts=counts)
    rows = []
    with tempfile.TemporaryDirectory(prefix="darwin-sweep-") as td:
        for d in SWEEP_DELTAS:
            inst = P.Instance(obs, d)
            for kind, s, t in SWEEP_PAIRS:
                row = {"delta": d, "delta_status": "assumed", "kind": kind, "start": s, "target": t}
                try:
                    build = P.build_route_certificate if kind == "route" else P.build_blocked_certificate
                    cert = build(inst, s, t, source, label=f"sweep_{kind}_{d.replace('.', 'p')}_{s}_{t}")
                except P.CannotCertify as exc:
                    row.update(status="cannot_certify", reason=str(exc)[:200])
                    rows.append(row)
                    continue
                mf = Path(td) / (cert["label"] + ".lean")
                mf.write_text(P.render_lean(cert))
                res = P.lean_compile_file(mf, scope=scope)
                row.update(status="certified" if res["exit_code"] == 0 else "lean_rejected",
                           lean_exit_code=res["exit_code"], certificate_sha256=cert["certificate_sha256"],
                           route=cert.get("route"), closed_set=cert.get("closed_set"),
                           route_length=(len(cert["route"]) - 1) if cert.get("route") else None)
                rows.append(row)
                print(f"   sweep delta={d} {kind} {s}->{t}: {row['status']}", flush=True)
    return {"kind": "darwin-bridge-sensitivity-sweep/1", "source_sha256": source["sha256"],
            "note": "delta values are ASSUMED sensitivity bounds in growth-rate units (mu-bg), not confidence bounds. "
                    "Descriptive full-data certificates, not a prediction benchmark. cannot_certify means the finder "
                    "found nothing at that delta, not that the pair is biologically unconnected.",
            "rows": rows}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv")
    ap.add_argument("--regenerate", action="store_true")
    ap.add_argument("--fast", action="store_true")
    ap.add_argument("--sweep", action="store_true", help="write artifacts/proof/sensitivity_sweep.json (Lean-checks each certificate found)")
    ap.add_argument("--no-scope", action="store_true", help="do not wrap subprocesses in systemd-run")
    ap.add_argument("--out", default=str(ART / "receipt.json"))
    args = ap.parse_args()
    scope = not args.no_scope
    t0 = time.time()
    checks: list[dict] = []

    def record(name, ok, **info):
        checks.append({"check": name, "ok": bool(ok), **info})
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  {info.get('detail', '')}" if info.get("detail") else ""), flush=True)
        return ok

    csv_path = None
    try:
        csv_path = P.find_source_csv(args.csv)
    except FileNotFoundError:
        pass

    if args.regenerate:
        if csv_path is None:
            print("cannot regenerate: source CSV not found", file=sys.stderr)
            return 2
        certs = P.generate_all(csv_path)
        for c in certs:
            P.write_json(ART / f"{c['label']}.json", c)
        P.write_lean_tree(certs)
        print(f"regenerated {len(certs)} certificates from {csv_path}")
    certs = load_certs()
    record("certificates_present", len(certs) >= 3, detail=f"{len(certs)} certificates: " + ", ".join(c["label"] for c in certs))

    # 1. generated Lean files == render(certificate JSON)  (JSON is the runtime input of record)
    drift = []
    for c in certs:
        f = P.LEAN_DIR / "DarwinBridge" / "Certs" / (P.module_name(c).rsplit(".", 1)[1] + ".lean")
        if not f.exists() or f.read_text() != P.render_lean(c):
            drift.append(f.name)
        if P.certificate_digest(c) != c["certificate_sha256"]:
            drift.append(c["label"] + ".json digest")
    mods = [P.module_name(c) for c in certs]
    if (P.LEAN_DIR / "DarwinBridge" / "Audit.lean").read_text() != P.render_audit(mods):
        drift.append("Audit.lean")
    record("lean_files_match_certificate_json", not drift, detail=", ".join(drift))

    # 2. python mirror (differential only)
    mirror = {c["label"]: P.check_certificate_python(c) for c in certs}
    record("python_mirror_accepts_certificates", all(v[0] for v in mirror.values()),
           detail="; ".join(f"{k}: {v[1]}" for k, v in mirror.items()))

    # 3. source tie
    src_info = {"verified": False}
    if csv_path is not None:
        try:
            obs = P.load_trpb_observations(csv_path)[0]
            rows = 0
            for c in certs:
                rows += P.verify_against_source(c, csv_path, observations=obs)["rows_checked"]
            src_info = {"verified": True, "csv": str(csv_path), "sha256": P.sha256_file(csv_path), "rows_checked": rows}
            record("certificate_tied_to_source_csv", True, detail=f"sha256 {src_info['sha256'][:16]}…, {rows} rows re-read")
        except P.ProofInputError as exc:
            record("certificate_tied_to_source_csv", False, detail=str(exc))
    else:
        record("certificate_tied_to_source_csv", True, skipped=True,
               detail="SKIPPED: source CSV absent on this machine; hashes recorded in certificate only (not re-verified)")

    # 4. forbidden constructs
    bad = forbidden_tokens(P.LEAN_DIR)
    record("no_sorry_admit_native_decide_axiom_unsafe", not bad, detail="; ".join(bad))

    # 5. fresh kernel compile + axioms
    lean_ver = P.lean_version()
    with tempfile.TemporaryDirectory(prefix="darwin-lean-") as td:
        tree = P.copy_lean_tree(Path(td) / "lean")
        t1 = time.time()
        build = P.run_cmd([P.find_tool("lake"), "build"], cwd=tree, scope=scope)
        compile_exit = build["exit_code"]
        record("fresh_lake_build_original", compile_exit == 0, exit_code=compile_exit,
               detail=f"{time.time() - t1:.1f}s; {first_error(build['stdout'] + build['stderr']) if compile_exit else 'ok'}")
        axioms = {}
        if compile_exit == 0:
            audit = P.run_cmd([P.find_tool("lake"), "env", P.find_tool("lean"), "DarwinBridge/Audit.lean"], cwd=tree, scope=scope)
            axioms = P.parse_axiom_report(audit["stdout"] + audit["stderr"])
            expected = 14 + 2 * len(certs)
            ok = audit["exit_code"] == 0 and len(axioms) == expected and all(set(a) <= P.ALLOWED_AXIOMS for a in axioms.values())
            record("axiom_audit", ok, exit_code=audit["exit_code"],
                   detail=f"{len(axioms)}/{expected} theorems; axioms used: {sorted({a for v in axioms.values() for a in v})}")

        # 6. instance-level mutants against the freshly built library
        mut_rows = []
        for c in certs:
            for m in P.data_mutants(c):
                mf = Path(td) / f"{m['name']}.lean"
                mf.write_text(P.render_lean({**m["cert"], "label": m["name"]}))
                res = P.lean_compile_file(mf, project_dir=tree, scope=scope)
                lean_accept = res["exit_code"] == 0
                py_accept, py_reason = P.check_certificate_python({**m["cert"], "label": m["name"]})
                err = first_error(res["stdout"] + res["stderr"])
                row = {"name": m["name"], "expect": m["expect"], "lean_exit_code": res["exit_code"],
                       "lean_accepted": lean_accept, "python_mirror_accepted": py_accept, "python_reason": py_reason,
                       "why": m["why"], "lean_first_error": err}
                row["as_expected"] = lean_accept == (m["expect"] == "accept")
                # a rejection must come from the decision procedure, not from a syntax slip
                if m["expect"] == "reject":
                    row["rejected_by_decision"] = ("decide" in err or "false" in err or "Decidable" in err)
                    row["as_expected"] = row["as_expected"] and row["rejected_by_decision"]
                row["mirror_agrees"] = py_accept == lean_accept
                mut_rows.append(row)
                print(f"   mutant {m['name']}: expect={m['expect']} lean_exit={res['exit_code']} mirror={'acc' if py_accept else 'rej'}", flush=True)
        n_bad = [r["name"] for r in mut_rows if not r["as_expected"]]
        record("instance_mutants_as_expected", not n_bad and len(mut_rows) > 0, detail=f"{len(mut_rows)} mutants; unexpected: {n_bad}")
        record("python_mirror_agrees_with_lean_on_mutants", all(r["mirror_agrees"] for r in mut_rows),
               detail=str([r["name"] for r in mut_rows if not r["mirror_agrees"]]))

    # 7. Lean-source mutants (break the checker itself; the theorems must stop compiling)
    src_rows = []
    if not args.fast:
        for mut in P.SOURCE_MUTANTS:
            with tempfile.TemporaryDirectory(prefix="darwin-lean-mut-") as td2:
                tree2 = P.copy_lean_tree(Path(td2) / "lean")
                P.apply_source_mutant(tree2, mut)
                res = P.run_cmd([P.find_tool("lake"), "build"], cwd=tree2, scope=scope)
                err = first_error(res["stdout"] + res["stderr"])
                row = {"name": mut[0], "file": mut[1], "description": mut[4], "lean_exit_code": res["exit_code"],
                       "rejected": res["exit_code"] != 0, "first_error": err}
                src_rows.append(row)
                print(f"   source mutant {mut[0]}: exit={res['exit_code']}", flush=True)
        record("lean_source_mutants_all_rejected", bool(src_rows) and all(r["rejected"] for r in src_rows),
               detail=f"{sum(r['rejected'] for r in src_rows)}/{len(src_rows)} break compilation")

    if args.sweep:
        if csv_path is None:
            record("sensitivity_sweep", False, detail="source CSV required")
        else:
            sweep = run_sweep(csv_path, scope)
            P.write_json(ART / "sensitivity_sweep.json", sweep)
            record("sensitivity_sweep", all(r.get("lean_exit_code", 0) == 0 for r in sweep["rows"]),
                   detail=f"{len(sweep['rows'])} rows written to artifacts/proof/sensitivity_sweep.json")

    ok = all(c["ok"] for c in checks)
    canonical = next((r for r in mut_rows if r["name"].endswith("route_delta005__dominance_violated_by_one") or "dominance_violated_by_one" in r["name"]), None)
    open_edge = next((r for r in mut_rows if "open_cut_edge_equal" in r["name"]), None)
    now = datetime.now(timezone.utc)
    receipt = {
        "status": "completed" if ok else "failed",
        "kind": "darwin-bridge-proof-receipt/1",
        "generated_at_utc": now.isoformat(timespec="seconds"),
        "generated_at_seattle": now.astimezone(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d %H:%M:%S %Z"),
        "wall_seconds": round(time.time() - t0, 1),
        "command": "python scripts/check_proofs.py" + (" --fast" if args.fast else ""),
        "lean_version": lean_ver,
        "python_version": sys.version.split()[0],
        "compile_command": "lake build  (fresh copy of lean/, no cached .lake)",
        "compile_exit_code": compile_exit,
        "min_mutant_exit_code": min([r["lean_exit_code"] for r in mut_rows if r["expect"] == "reject"], default=None),
        "dominance_mutant_exit_code": canonical["lean_exit_code"] if canonical else None,
        "open_cut_edge_mutant_exit_code": open_edge["lean_exit_code"] if open_edge else None,
        "receipt_path": str(Path(args.out).relative_to(ROOT)) if Path(args.out).is_absolute() and ROOT in Path(args.out).parents else args.out,
        "certificates": [{"label": c["label"], "kind": c["kind"], "start": c["start"], "target": c["target"],
                          "delta_decimal": c["delta_decimal"], "delta_status": "assumed",
                          "certificate_sha256": c["certificate_sha256"], "source_sha256": c["source"]["sha256"],
                          "table_rows": len(c["table"]), "route": c.get("route"),
                          "closed_set": c.get("closed_set"), "crossing_edges_checked": c.get("crossing_edges_checked")} for c in certs],
        "source_tie": src_info,
        "axioms": axioms,
        "checks": checks,
        "instance_mutants": mut_rows,
        "source_mutants": src_rows,
        "limitations": [
            "Soundness is conditional on interval containment (assumed, not proved) and on the declared four-site graph.",
            "delta is an assumed sensitivity bound, not a confidence bound; two replicates cannot give simultaneous 95% intervals.",
            "Text->integer conversion and graph search are untrusted Python; Lean checks the resulting finite instance.",
            "Absence of a certified route / presence of a blocked certificate says nothing about sequence space beyond these four sites.",
        ],
    }
    P.write_json(args.out, receipt)
    print(f"receipt: {args.out}  status={receipt['status']}  wall={receipt['wall_seconds']}s")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
