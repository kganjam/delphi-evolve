#!/usr/bin/env python3
"""Assemble the final contract demo.json from saved artifacts (integrator-owned, no new science).

  python3 scripts/assemble_demo.py            # reads artifacts/demo.json (core), writes it in place
                                              # and copies it to site/data/demo.json

Refuses (nonzero exit) if receipts contradict each other. It never turns a missing result into a
pass: absent GPU/benchmark stay 'unavailable'.
"""
import hashlib, json, pathlib, shutil, sys

R = pathlib.Path(__file__).resolve().parents[1]
J = lambda p: json.load(open(R / p))
demo = J("artifacts/demo.json")
errs = []

# --- proof ------------------------------------------------------------------------------------
rc = J("artifacts/proof/receipt.json")
if rc.get("status") != "completed" or rc.get("compile_exit_code") != 0:
    errs.append("proof receipt not completed/compile exit != 0")
if rc.get("min_mutant_exit_code") in (None, 0) or rc.get("dominance_mutant_exit_code") in (None, 0) \
        or rc.get("open_cut_edge_mutant_exit_code") in (None, 0):
    errs.append("proof receipt: a required mutant was not rejected")
used = {a for v in rc.get("axioms", {}).values() for a in v}
if not used <= {"propext", "Quot.sound", "Classical.choice"}:
    errs.append(f"unexpected axioms in receipt: {sorted(used)}")
bad = [c["check"] for c in rc.get("checks", []) if not c.get("ok")]
if bad or not rc.get("checks"):
    errs.append(f"proof receipt has failing/absent checks: {bad}")
br = J("artifacts/integration/core_kappa2_route_lean.json")
core_cert = J("artifacts/core/certificates/route_VFVS_AIKG_kappa2.json")
if not br.get("ok"):
    errs.append("bridge receipt not ok")
if br.get("core_body_sha256") != core_cert.get("body_sha256"):
    errs.append("bridge receipt does not match core route certificate body hash")
if J("artifacts/integration/core_kappa2_route.input.json").get("body_sha256") != core_cert.get("body_sha256"):
    errs.append("stored bridge input differs from current core route certificate (core regenerated it): rerun scripts/bridge_core_cert.py")
demo["proof"] = {
    "status": "completed",
    "theorem": "DarwinBridge.routeCert_sound; DarwinBridge.blockedCert_sound (conditional on assumed interval containment)",
    "command": rc.get("command"),
    "exit_code": rc.get("compile_exit_code"),
    "mutation_exit_code": rc.get("min_mutant_exit_code"),
    "receipt": "artifacts/proof/receipt.json",
    "lean_version": rc.get("lean_version"),
    "wall_seconds": rc.get("wall_seconds"),
    "axioms_used": sorted(used),
    "scope": "Lean-checked: proof-worker route certificates, strong blocked certificates (all exits certified lower) and the admissible-cut certificate for core's HTGR>GTVN example "
             "('no certifiable route', weaker); plus the bridged core kappa=2 VFVS>AIKG ROUTE. "
             "NOT Lean-checked: the replay's individual episode decisions (they are sound by construction from revealed labels and re-verified against full data in Python). "
             "'Blocked' in core never means 'no true route' (planning/INTEGRATION-FINDINGS.md F1).",
    "bridged_core_route": {"receipt": "artifacts/integration/core_kappa2_route_lean.json",
                           "certificate": "artifacts/integration/core_kappa2_route_lean.certificate.json",
                           "lean_original_build_exit": br.get("lean_original_build_exit"),
                           "lean_mutant_swap_build_exit": br.get("lean_mutant_swap_build_exit"),
                           "intervals_recomputed_from_raw_csv_exact": f'{br.get("recompute_exact_matches")}/{br.get("nodes")}'},
    "assumption": "Interval containment is ASSUMED; two replicates do not give simultaneous confidence bands.",
}
for r in demo.get("routes", []):
    if r.get("id") == "certified-shortest" and br.get("ok"):
        r["lean_receipt"] = "artifacts/integration/core_kappa2_route_lean.json"
        r["lean_certificate_path"] = "artifacts/integration/core_kappa2_route_lean.certificate.json"

adm = J("artifacts/proof/core_kappa2_adm_cut_htgr_gtvn.json")
cut_files = sorted((R / "artifacts/core/certificates").glob("cut_*_kappa2.json"))
core_cut = json.load(open(cut_files[0])) if cut_files else None
def cut_content_matches(core_cut, adm):
    """Tie by CONTENT (body_sha256 includes the software-version block, so it is environment dependent)."""
    if not core_cut or adm.get("theorem") != "DarwinBridge.admCert_sound":
        return False
    if (core_cut["start"], core_cut["target"]) != (adm["start"], adm["target"]) or adm.get("unlisted_neighbours") != []:
        return False
    if sorted(core_cut["closed_set"]) != sorted(adm["closed_set"]) or adm.get("scale_exponent") != 6 or adm.get("delta_scaled") != 0:
        return False
    rows = {e["genotype"]: (e["r1"], e["r2"]) for e in adm["table"]}
    measured = {g: (v["lower"], v["upper"]) for g, v in core_cut["nodes"].items() if v["measured"]}
    return rows == {g: (min(v), max(v)) for g, v in measured.items()}
adm_ok = cut_content_matches(core_cut, adm)
checks = {c["check"]: c["ok"] for c in rc.get("checks", [])}
if not adm_ok:
    print("note: core cut is not the one Lean-checked by proof (regenerated?); blocked route stays lean_checked=false")
for r in demo.get("routes", []):
    if str(r.get("status", "")).startswith("blocked") or r.get("verdict") == "no_route_certifiable":
        if r.get("verdict") == "no_route_certifiable":
            r["status"] = r["core_status"]  # idempotent re-run: restore original, rewrite below
        r["core_status"] = r["status"]
        r["verdict"] = "no_route_certifiable"
        r["status"] = "no route certifiable at this bound (" + r["core_status"].split("(", 1)[-1].rstrip(")") + "); an actual ascending route may still exist"
        r["semantics"] = ("'blocked' here means NO ROUTE CAN BE CERTIFIED in the measured subgraph under the assumed kappa "
                          "(intervals that overlap count as not admitted). It does NOT exclude a true non-decreasing path: the strong no-path theorem "
                          "(blocked_cut_sound) needs every exit certified lower. Lean separates the two (artifacts/proof/CORRESPONDENCE.md, "
                          "DarwinBridge/Distinction.lean). 'nodes' lists the start/target endpoints, not a path.")
        r["lean_checked"] = bool(adm_ok and checks.get("python_mirror_accepts_certificates") and rc.get("compile_exit_code") == 0)
        if r["lean_checked"]:
            r["lean_theorem"] = "DarwinBridge.admCert_sound (no certifiable route; weaker than blocked_cut_sound)"
            r["lean_certificate_path"] = "artifacts/proof/core_kappa2_adm_cut_htgr_gtvn.json"

# --- make every route endpoint a real node (core lists the blocked example's endpoints without nodes) ---
sys.path.insert(0, str(R))
have = {n["id"] for n in demo["nodes"]}
missing = sorted({g for r in demo.get("routes", []) for g in r.get("nodes", [])} - have)
if missing:
    from evolve import data as _data
    from evolve.demo import _node
    _L = _data.load(); _Lo, _Hi = _L.intervals()
    for g in missing:
        demo["nodes"].append(_node(_L, _data.encode(g), _Lo, _Hi))

# --- claims -----------------------------------------------------------------------------------
cl = J("artifacts/evidence/demo_claims.json")["claims"]
demo["claims"] = cl
demo["claims_status"] = "Delphi records queried live 2026-10-31 (local and network kept separate); relation is motivation/context only; nanopub drafts are unsigned and unpublished"

from evolve.release_evidence import claim_block, compute_block, lazysp_block, scale_block
try:
    demo["operational_claims"] = claim_block(R)
    lazysp = lazysp_block(R)
    scale = scale_block(R)
except (ValueError, OSError, KeyError) as error:
    errs.append(f"claim-runtime integration: {error}")

# --- compute (GPU) ----------------------------------------------------------------------------
try:
    demo["compute"] = compute_block(R)
except (ValueError, OSError, KeyError) as error:
    errs.append(f"GPU integration: {error}")

if errs:
    print(json.dumps({"ok": False, "errors": errs}, indent=1)); sys.exit(1)
out = json.dumps(demo, indent=1)
(R / "artifacts/demo.json").write_text(out)
(R / "site/data").mkdir(parents=True, exist_ok=True)
(R / "site/data/demo.json").write_text(out)
if lazysp.get("status") == "completed":
    (R / "site/data/lazysp.json").write_text(json.dumps(lazysp, indent=1))
if scale.get("status") == "completed":
    (R / "site/data/scale.json").write_text(json.dumps(scale, indent=1))
if demo.get("operational_claims", {}).get("status") == "recorded":
    destination = R / "site/claims"
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("index.html", "receipt.js", "bench.js"):
        shutil.copyfile(R / "claim_runtime/demo" / name, destination / name)
if (R / "artifacts/turing_scope/results.json").exists():
    destination = R / "site/turing"
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("index.html", "data.js"):
        shutil.copyfile(R / "turing_scope/site" / name, destination / name)
for relative in ("deck.html", "deck.pdf", "video/darwins-bridge-walkthrough.mp4"):
    source = R / "presentation" / relative
    if source.exists():
        destination = R / "site/presentation" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
print(json.dumps({"ok": True, "sha256": hashlib.sha256(out.encode()).hexdigest(), "proof": demo["proof"]["status"],
                  "compute": demo["compute"]["status"], "benchmark": demo["benchmark"]["status"]}))
