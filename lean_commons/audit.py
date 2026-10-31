"""Post-hoc audit of accepted proofs (applies to the runs in artifacts/commons/runs*).

For every accepted attempt (one per certified target per run) we reconstruct the library the agent saw,
re-compile, and then
  (1) REUSE by proof-term constants: the target theorem's kernel term is inspected (`Expr.getUsedConstants`)
      and intersected with library theorem names (direct dependency, not text matching);
  (2) MUTANT REPLAY: the same helpers + proof are replayed against the paired FALSE mutant statement of the
      target; the replay must FAIL, otherwise the accepted proof is not evidence that the statement carried content.
Scoring rule: a target counts as *strictly certified* only if (original compiles, axioms clean) AND (mutant replay rejected).
This is an analysis layer; it does not change which targets the runner accepted.
"""
from __future__ import annotations

import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import lean_check as L
from .agent import parse_response

DEPS_CMD = '''
open Lean Elab Command in
elab "#deps " n:ident : command => do
  let env ← getEnv
  match env.find? n.getId with
  | some (.thmInfo t) => logInfo m!"DEPS {n.getId} {t.value.getUsedConstants.toList}"
  | some _ => logInfo m!"DEPS-NOT-A-THEOREM {n.getId}"
  | none => logInfo m!"DEPS-NONE {n.getId}"
'''


def _library_at(run_dir: Path, arm: str, agent: str, tid: str, ts: str) -> list[dict]:
    if arm == "shared":
        f = run_dir / "commons_shared.jsonl"
    elif arm == "private":
        f = run_dir / f"commons_{agent}.jsonl"
    else:
        return []
    if not f.exists():
        return []
    out = []
    for line in f.read_text().splitlines():
        if not line.strip():
            continue
        e = json.loads(line)
        if e.get("kind") != "lemma" or e.get("task") == tid or e.get("for_task") == tid:
            continue
        if e["ts_utc"] <= ts:
            out.append(e)
    return out


def audit_attempt(run_dir: Path, att: dict, targets: dict, defs: str) -> dict:
    tid, arm, agent = att["task"], att["arm"], att["agent"]
    helpers, proof, perr = parse_response(att["response"])
    lib = _library_at(run_dir, arm, agent, tid, att["ts_utc"])
    t = targets[tid]
    names = L.theorem_names(helpers)

    def build(stmt):
        return L.assemble(defs, lib, helpers, tid, stmt, proof)

    orig = build(t["statement"])
    r = L.check_source(orig + DEPS_CMD + f"\n#deps {tid}\n", names + [tid], scan_text=helpers + "\n" + proof,
                       fidelity=(tid, t["statement"]))
    rec = {"run": run_dir.name, "arm": arm, "agent": agent, "task": tid, "reconstructed_ok": r.ok,
           "helper_structure_error": L.helper_structure_error(helpers)}
    if r.ok:
        out = r.raw
        m = re.search(r"DEPS \S+ \[(.*?)\]", out, re.S)
        rec["deps_extracted"] = bool(m)
        used = [x.strip() for x in m.group(1).split(",")] if m and m.group(1).strip() else []
        libnames = {e["name"]: e["author"] for e in lib}
        rec["library_deps"] = sorted({u for u in used if u in libnames})
        rec["library_deps_authors"] = {u: libnames[u] for u in rec["library_deps"]}
        rec["cross_agent_deps"] = sorted(u for u in rec["library_deps"] if libnames[u] != agent)
        rec["helper_deps"] = sorted({u for u in used if u in names})
    mut = L.check_source(build(t["mutant"]), names + [tid], scan_text="")
    rec["mutant_rejected"] = (not mut.ok)
    rec["strictly_certified"] = bool(r.ok and rec["mutant_rejected"] and not rec["helper_structure_error"])
    return rec


def audit_run(run_dir: Path, targets: dict, defs: str) -> list[dict]:
    att = [json.loads(l) for l in (run_dir / "attempts.jsonl").read_text().splitlines() if l.strip()]
    return [audit_attempt(run_dir, a, targets, defs) for a in att if a.get("ok")]


def main(root: str, pattern: str = "*_r*/"):
    targets = {t["id"]: t for t in L.load_targets()}
    defs = L.load_defs()
    dirs = sorted(d for d in Path(root).glob(pattern) if (d / "attempts.jsonl").exists())
    with ThreadPoolExecutor(max_workers=2) as ex:
        res = list(ex.map(lambda d: audit_run(d, targets, defs), dirs))
    rows = [r for rs in res for r in rs]
    summ = {}
    for r in rows:
        s = summ.setdefault(r["run"], {"certified": 0, "strict": 0, "unreconstructed": 0, "mutant_accepted": 0, "lib_dep_uses": 0, "cross_agent_dep_uses": 0})
        s["certified"] += 1
        s["strict"] += r["strictly_certified"]
        s["unreconstructed"] += (not r["reconstructed_ok"])
        s["mutant_accepted"] += (not r["mutant_rejected"])
        s["lib_dep_uses"] += len(r.get("library_deps", []))
        s["cross_agent_dep_uses"] += len(r.get("cross_agent_deps", []))
    out = {"root": root, "per_run": summ, "rows": rows}
    Path(root, f"AUDIT_{pattern.replace('*','x').replace('/','')}.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "artifacts/commons/runs", sys.argv[2] if len(sys.argv) > 2 else "*_r*/")
