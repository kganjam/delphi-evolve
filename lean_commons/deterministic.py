"""Arm D: ordinary deterministic tactics on the frozen library. No model, zero tokens.
For each target in the frozen order, try a fixed list of closing tactics (with `intros`/`unfold` of
the Scope definitions, and with previously certified targets as `grind` hints) and accept the first
that the kernel accepts. This is the floor any agent arm must beat."""
from __future__ import annotations
import json, sys, time
from pathlib import Path
from . import lean_check as L

UNF = "Scope.Model.modeTr Scope.Model.modeDet Scope.Model.trJ Scope.Model.detJ Scope.Model.S Scope.modeN Scope.modeM Scope.Hurwitz Scope.hamGain Scope.Favoured Scope.hdHH Scope.hdHD Scope.hdDH Scope.hdDD"


TRY_UNF = "; ".join(f"(try unfold {n})" for n in UNF.split())


def scripts(proved: list[str]) -> list[str]:
    hint = (" [" + ", ".join(proved) + "]") if proved else ""
    return ["by intros; grind", "by intros; omega", "by intros; simp_all", "by intros; decide",
            f"by intros; {TRY_UNF}; grind", f"by intros; {TRY_UNF}; omega",
            f"by intros; {TRY_UNF}; simp_all <;> grind",
            f"by intros; grind{hint}" if proved else "by intros; grind",
            f"by intros; {TRY_UNF}; grind{hint}" if proved else f"by intros; {TRY_UNF}; grind"]


def run(only: list[str] | None = None) -> dict:
    T = [t for t in L.load_targets() if not only or t["id"] in only]; defs = L.load_defs(); lib: list[dict] = []; rows = []
    t0 = time.time()
    for t in T:
        got = None; n = 0
        for sc in scripts([e["name"] for e in lib]):
            n += 1
            src = L.assemble(defs, lib, "", t["id"], t["statement"], sc)
            r = L.check_source(src, [t["id"]], scan_text="")
            if r.ok:
                got = sc; break
        rows.append({"id": t["id"], "proved": got is not None, "script": got, "tactic_attempts": n})
        if got:
            lib.append({"name": t["id"], "statement": t["statement"], "source": f"theorem {t['id']} : {t['statement']} := {got}"})
    out = {"arm": "deterministic", "n_targets": len(T), "n_proved": sum(r["proved"] for r in rows), "tokens": 0,
           "wall_s": round(time.time() - t0, 1), "rows": rows, "targets_sha256": __import__("hashlib").sha256((L.HERE / "targets/targets.json").read_bytes()).hexdigest()}
    return out


if __name__ == "__main__":
    o = run()
    if len(sys.argv) > 1:
        Path(sys.argv[1]).parent.mkdir(parents=True, exist_ok=True)
        Path(sys.argv[1]).write_text(json.dumps(o, indent=1) + "\n")
    print(json.dumps({k: v for k, v in o.items() if k != "rows"}, indent=1))
    print([r["id"] for r in o["rows"] if r["proved"]])
