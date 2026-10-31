"""Assemble tasks/results/guilds.json from committed run artifacts (numbers only come from files)."""
import json, subprocess, statistics
from pathlib import Path

A = Path("artifacts/commons")


def table(root):
    p = root / "TABLE.json"
    return json.loads(p.read_text()) if p.exists() else None


def hetero():
    out = []
    for d in sorted((A / "runs_hetero").glob("*_r*/")):
        sp = d / "summary.json"
        if not sp.exists():
            continue
        s = json.loads(sp.read_text())
        att = [json.loads(l) for l in (d / "attempts.jsonl").read_text().splitlines() if l.strip()]
        fam = {}
        for a in att:
            f = fam.setdefault(a["family"], {"calls": 0, "compiled_ok": 0, "tokens": 0, "accounts": set(), "served": set(), "verified": True})
            f["calls"] += 1; f["compiled_ok"] += bool(a["ok"]); f["tokens"] += a["tokens"]
            f["accounts"].add(a["account"]); f["served"].add(a["served_model"]); f["verified"] &= bool(a["family_verified"])
        for f in fam.values():
            f["accounts"] = sorted(f["accounts"]); f["served"] = sorted(f["served"])
        out.append({"run": d.name, "n_proved": s["n_proved"], "n_targets": s["n_targets"], "calls_used": s["calls_used"],
                    "tokens": s["tokens_spent"], "wall_s": s["wall_s"], "reuse": s["reuse"], "failed": s["failed_tasks"], "by_family": fam})
    return out


def main():
    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    runs = json.loads((A / "runs/TABLE.json").read_text())
    det = json.loads((A / "deterministic.json").read_text())
    res = {"role": "guilds", "status": "completed_with_nulls", "commit_base": commit, "branch": "work/guilds",
           "same_model_runs": runs, "deterministic": {k: det[k] for k in ("n_proved", "n_targets", "tokens", "wall_s")},
           "deterministic_proved": [r["id"] for r in det["rows"] if r["proved"]], "heterogeneous_runs": hetero()}
    Path("artifacts/commons/RESULTS_NUMERIC.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({"hetero_runs": len(res["heterogeneous_runs"])}))


if __name__ == "__main__":
    main()
