"""Pre-freeze validation of the target set: every reference proof compiles (axioms clean) and every
law mutant (false statement) is REJECTED when the reference proof is replayed against it.
Writes targets/VALIDATION.json. Reference proofs are held out from agents."""
from __future__ import annotations
import json, hashlib
from pathlib import Path
from . import lean_check as L

HERE = Path(__file__).parent


def main():
    T = L.load_targets(); defs = L.load_defs()
    ref = json.loads((HERE / "reference/proofs.json").read_text())
    lib, rows = [], []
    for t in T:
        src = L.assemble(defs, lib, "", t["id"], t["statement"], ref[t["id"]])
        r = L.check_source(src, [t["id"]], scan_text="", fidelity=(t["id"], t["statement"]))
        msrc = L.assemble(defs, lib, "", t["id"], t["mutant"], ref[t["id"]])
        m = L.check_source(msrc, [t["id"]], scan_text="")
        rows.append({"id": t["id"], "family": t["family"], "reference_compiles": r.ok,
                     "axioms": r.axioms.get(t["id"]), "mutant_rejected": (not m.ok),
                     "reference_seconds": round(r.seconds, 2)})
        if r.ok:
            lib.append({"name": t["id"], "source": f"theorem {t['id']} : {t['statement']} := {ref[t['id']].strip()}"})
    out = {"lean_version": L.lean_version(), "targets_sha256": hashlib.sha256((HERE / "targets/targets.json").read_bytes()).hexdigest(),
           "defs_sha256": hashlib.sha256((HERE / "targets/Defs.lean").read_bytes()).hexdigest(),
           "n_targets": len(T), "all_reference_compile": all(r["reference_compiles"] for r in rows),
           "all_mutants_rejected": all(r["mutant_rejected"] for r in rows), "rows": rows}
    (HERE / "targets/VALIDATION.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "rows"}, indent=1))
    for r in rows:
        print(r["id"], r["reference_compiles"], r["mutant_rejected"], r["axioms"])


if __name__ == "__main__":
    main()
