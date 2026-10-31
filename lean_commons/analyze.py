"""Aggregate preregistered runs into one table (descriptive; no p-values, R small)."""
import json, statistics, sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "artifacts/commons/runs")


def rows():
    out = []
    for d in sorted(ROOT.glob("*_r*/")):
        sp = d / "summary.json"
        if not sp.exists():
            continue
        s = json.loads(sp.read_text())
        att = [json.loads(l) for l in (d / "attempts.jsonl").read_text().splitlines() if l.strip()]
        ok_first = sum(1 for a in att if a["k"] == 0 and a["ok"])
        n_first = sum(1 for a in att if a["k"] == 0)
        fams = sorted({a.get("family", "") for a in att} - {""})
        accts = sorted({a["account"] for a in att})
        ver = all(a["family_verified"] for a in att) if att else None
        out.append({"run": d.name, "arm": d.name.split("_")[0], "n_proved": s["n_proved"], "n_targets": s["n_targets"],
                    "calls_used": s["calls_used"], "tokens": s["tokens_spent"], "wall_s": s["wall_s"],
                    "first_try_success": f"{ok_first}/{n_first}", "reuse": s["reuse"], "failed": s["failed_tasks"],
                    "accounts": accts, "families": fams, "all_family_verified": ver})
    return out


def main():
    R = rows()
    arms = {}
    for r in R:
        arms.setdefault(r["arm"], []).append(r)
    summ = {}
    for a, rs in sorted(arms.items()):
        f = lambda k: [x[k] for x in rs]
        summ[a] = {"runs": len(rs), "n_proved": f("n_proved"), "calls_used": f("calls_used"), "tokens": f("tokens"), "wall_s": f("wall_s"),
                   "median_calls": statistics.median(f("calls_used")), "median_tokens": statistics.median(f("tokens")),
                   "median_wall_s": statistics.median(f("wall_s")),
                   "lemma_uses": [x["reuse"]["total_lemma_uses"] for x in rs], "cross_agent_uses": [x["reuse"]["cross_agent_uses"] for x in rs]}
    print(json.dumps({"runs": R, "by_arm": summ}, indent=1))
    (ROOT / "TABLE.json").write_text(json.dumps({"runs": R, "by_arm": summ}, indent=1) + "\n")


if __name__ == "__main__":
    main()
