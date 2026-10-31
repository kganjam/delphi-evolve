"""Aggregation and paired analysis of LazySP shards against the SAVED original episodes.

Comparator: artifacts/recovery/episodes.csv (original 700-episode benchmark recovered from actual
query histories; policy rows are never re-run here).  The panel is complete only if every
(variant, seed, k) shard exists; otherwise the output is labelled PARTIAL and no panel-level claim is made.

Pre-registered statistics (docs/lazysp.md):
  * resolved@B: fraction of the 100 episodes with a ledger certificate (open/blocked) using <= B assays.
    Unresolved/abstained episodes stay in the denominator.
  * RMST: restricted mean assays-to-certificate at tau=1000, unresolved counted as tau
    (lower is better; it is an upper-bound-censored mean, not an unbiased mean time).
  * paired difference (LazySP - comparator) of each statistic, 95% percentile interval from a
    paired seed-cluster bootstrap (resample the 20 seeds with replacement, 10,000 draws,
    numpy default_rng(20261031)).  This interval is descriptive: 20 clusters, one panel, no coverage claim.
  * discordant-pair counts (episodes resolved by exactly one policy) are reported raw.
"""
from __future__ import annotations

import csv
import gzip
import json
import math
from pathlib import Path

import numpy as np

KEY = ("family", "seed", "start", "target")
BUDGETS = (100, 250, 500, 750, 1000)
TAU = 1000
BOOT = 10_000
BOOT_SEED = 20261031
COMPARATORS = ("q2c", "directed", "random", "collective_shared", "collective_isolated", "greedy", "uncertainty")


def load_shards(outdir, variant):
    rows = {}
    for p in sorted((Path(outdir) / "shards").glob(f"lazysp_{variant}__seed*__ep*.json.gz")):
        with gzip.open(p, "rt") as f:
            d = json.load(f)
        r = d["row"]
        rows[(r["family"], r["seed"], r["start"], r["target"])] = (r, d["meta"], p.name)
    return rows


def load_recovery(path):
    out = {}
    with open(path) as f:
        for r in csv.DictReader(f):
            k = (r["family"], int(r["seed"]), r["start"], r["target"])
            out.setdefault(r["policy"], {})[k] = r
    return out


def cert_assays(r):
    """Assays to ledger certificate (int) or None if unresolved."""
    if r["status"] in ("open", "blocked"):
        return int(float(r["assays"]))
    return None


def stat_resolved(vals, B):
    return float(np.mean([(v is not None and v <= B) for v in vals]))


def stat_rmst(vals):
    return float(np.mean([TAU if v is None else min(v, TAU) for v in vals]))


def boot_pair(seeds, a, b, fn, rng):
    """a,b aligned lists; seeds aligned list; returns (point diff, lo, hi)."""
    seeds = np.asarray(seeds); useeds = np.unique(seeds)
    idx = {s: np.flatnonzero(seeds == s) for s in useeds}
    point = fn(a) - fn(b)
    d = np.empty(BOOT)
    for i in range(BOOT):
        pick = rng.choice(useeds, len(useeds), replace=True)
        ii = np.concatenate([idx[s] for s in pick])
        d[i] = fn([a[j] for j in ii]) - fn([b[j] for j in ii])
    return float(point), float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))


def analyze(outdir, variants, recovery_csv, comparator="q2c"):
    rec = load_recovery(recovery_csv)
    res = {"outdir": str(outdir), "comparator_artifact": str(recovery_csv), "primary_comparator": comparator,
           "tau": TAU, "bootstrap": {"draws": BOOT, "seed": BOOT_SEED, "unit": "seed cluster (20)"}, "variants": {}}
    for var in variants:
        sh = load_shards(outdir, var)
        keys = sorted(rec[comparator])
        have = [k for k in keys if k in sh]
        v = {"episodes_expected": len(keys), "episodes_present": len(have), "complete_panel": len(have) == len(keys) == 100,
             "extra_unexpected_shards": [list(k) for k in sh if k not in rec[comparator]]}
        v["status"] = "COMPLETE_100" if v["complete_panel"] else f"PARTIAL_{len(have)}_of_{len(keys)}"
        rows = [sh[k][0] for k in have]
        v["panel_sha256_values"] = sorted({sh[k][1]["panel_sha256"] for k in have})
        v["code_commits"] = sorted({str(sh[k][1]["code_commit"]) for k in have})
        v["baselines_sha256_values"] = sorted({sh[k][1]["baselines_sha256"] for k in have})
        v["status_counts"] = {s: sum(r["status"] == s for r in rows) for s in ("open", "blocked", "unresolved")}
        v["abstain_reasons"] = {}
        for r in rows:
            if r["abstain_reason"]:
                v["abstain_reasons"][r["abstain_reason"]] = v["abstain_reasons"].get(r["abstain_reason"], 0) + 1
        v["false_certificates"] = sum(r["certificate"] is not None and not r["correct"] for r in rows)
        v["full_data_verification_failures"] = sum(r["certificate"] is not None and not r["verified_by_full_data"] for r in rows)
        v["native_infeasible_before_ledger_certificate"] = sum(r["lazysp"]["native_infeasible_at"] is not None for r in rows)
        v["resolved_at"] = {str(B): stat_resolved([cert_assays(r) for r in rows], B) for B in BUDGETS}
        v["rmst_assays"] = stat_rmst([cert_assays(r) for r in rows]) if rows else None
        v["task_wall_s_sum"] = round(sum(sh[k][1]["task_wall_s"] for k in have), 1)
        v["paired"] = {}
        for cmp_ in COMPARATORS:
            if cmp_ not in rec:
                continue
            ok = [k for k in have if k in rec[cmp_]]
            a = [cert_assays(sh[k][0]) for k in ok]; b = [cert_assays(rec[cmp_][k]) for k in ok]
            sd = [k[1] for k in ok]
            p = {"n_pairs": len(ok)}
            if ok:
                rng = np.random.default_rng(BOOT_SEED)
                p["resolved_at_1000_lazysp"] = stat_resolved(a, 1000); p["resolved_at_1000_comparator"] = stat_resolved(b, 1000)
                p["resolved_diff_1000"] = dict(zip(("diff", "lo95", "hi95"), boot_pair(sd, a, b, lambda x: stat_resolved(x, 1000), rng)))
                p["rmst_lazysp"] = stat_rmst(a); p["rmst_comparator"] = stat_rmst(b)
                p["rmst_diff"] = dict(zip(("diff", "lo95", "hi95"), boot_pair(sd, a, b, stat_rmst, rng)))
                p["resolved_only_by_lazysp"] = sum(x is not None and y is None for x, y in zip(a, b))
                p["resolved_only_by_comparator"] = sum(x is None and y is not None for x, y in zip(a, b))
                p["both_resolved"] = sum(x is not None and y is not None for x, y in zip(a, b))
                p["neither_resolved"] = sum(x is None and y is None for x, y in zip(a, b))
                both = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
                if both:
                    p["both_resolved_lazysp_fewer"] = sum(x < y for x, y in both)
                    p["both_resolved_comparator_fewer"] = sum(x > y for x, y in both)
                    p["both_resolved_tied"] = sum(x == y for x, y in both)
                    p["both_resolved_median_diff_conditional"] = float(np.median([x - y for x, y in both]))
            v["paired"][cmp_] = p
        v["by_family"] = {}
        for fam in ("A", "B"):
            kk = [k for k in have if k[0] == fam]
            qk = [k for k in kk if k in rec[comparator]]
            v["by_family"][fam] = {"n": len(kk), "resolved_at_1000": stat_resolved([cert_assays(sh[k][0]) for k in kk], 1000) if kk else None,
                                   f"{comparator}_resolved_at_1000": stat_resolved([cert_assays(rec[comparator][k]) for k in qk], 1000) if qk else None}
        v["by_truth"] = {}
        for t in (True, False):
            kk = [k for k in have if sh[k][0]["truth_open"] == t]
            v["by_truth"]["open" if t else "closed"] = {"n": len(kk), "resolved_at_1000": stat_resolved([cert_assays(sh[k][0]) for k in kk], 1000) if kk else None,
                                                        f"{comparator}_resolved_at_1000": stat_resolved([cert_assays(rec[comparator][k]) for k in kk if k in rec[comparator]], 1000) if kk else None}
        res["variants"][var] = {"summary": v, "rows": [sh[k][0] | {"_shard": sh[k][2]} for k in have]}
    return res


def write_outputs(res, out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    rows = []
    for var, d in res["variants"].items():
        rows += d["rows"]
    if rows:
        cols = [c for c in rows[0] if c not in ("lazysp",)] + ["lazysp_replans", "lazysp_expansions", "lazysp_search_wall_s", "lazysp_native_infeasible_at", "lazysp_fallback_queries"]
        with open(out / "episodes.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore"); w.writeheader()
            for r in rows:
                r = dict(r); L = r["lazysp"]
                r.update({"lazysp_replans": L["replans"], "lazysp_expansions": L["expansions"], "lazysp_search_wall_s": L["search_wall_s"],
                          "lazysp_native_infeasible_at": L["native_infeasible_at"], "lazysp_fallback_queries": L["fallback_queries"]})
                r["policy"] = "lazysp_" + r["variant"]
                if "route" in r:
                    r["route"] = str(r["route"])
                w.writerow(r)
    # combined view: saved original 700 episodes + these rows (same columns where available), for core-summary-style tooling
    try:
        import pandas as pd
        orig = pd.read_csv(res["comparator_artifact"])
        mine = pd.read_csv(out / "episodes.csv")
        orig["source"] = "saved_original_recovery"; mine["source"] = "lazysp_baseline"
        pd.concat([orig, mine], ignore_index=True).to_csv(out / "episodes_with_original.csv", index=False)
    except Exception as e:  # pragma: no cover
        (out / "combine_error.txt").write_text(repr(e))
    summ = {k: ({kk: vv for kk, vv in v.items() if kk != "rows"} if k == "variants" else v) for k, v in res.items()}
    summ["variants"] = {var: d["summary"] for var, d in res["variants"].items()}
    (out / "summary.json").write_text(json.dumps(summ, indent=1, default=str))
    with open(out / "table_paired.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["variant", "comparator", "n_pairs", "resolved@1000_lazysp", "resolved@1000_comparator", "diff", "lo95_cluster_boot", "hi95_cluster_boot",
                    "rmst_lazysp", "rmst_comparator", "rmst_diff", "rmst_lo95", "rmst_hi95", "only_lazysp", "only_comparator", "both", "neither", "panel_status"])
        for var, d in res["variants"].items():
            for c, p in d["summary"]["paired"].items():
                if p["n_pairs"]:
                    w.writerow([var, c, p["n_pairs"], p["resolved_at_1000_lazysp"], p["resolved_at_1000_comparator"], *[round(p["resolved_diff_1000"][x], 4) for x in ("diff", "lo95", "hi95")],
                                round(p["rmst_lazysp"], 1), round(p["rmst_comparator"], 1), *[round(p["rmst_diff"][x], 1) for x in ("diff", "lo95", "hi95")],
                                p["resolved_only_by_lazysp"], p["resolved_only_by_comparator"], p["both_resolved"], p["neither_resolved"], d["summary"]["status"]])
    with open(out / "table_primary.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["variant", "panel_status", "episodes", "open", "blocked", "unresolved", "false_certificates", "full_data_verification_failures"] + [f"resolved@{B}" for B in BUDGETS] + ["rmst_assays"])
        for var, d in res["variants"].items():
            s = d["summary"]
            w.writerow([var, s["status"], s["episodes_present"], s["status_counts"]["open"], s["status_counts"]["blocked"], s["status_counts"]["unresolved"],
                        s["false_certificates"], s["full_data_verification_failures"]] + [round(s["resolved_at"][str(B)], 3) for B in BUDGETS] + [None if s["rmst_assays"] is None else round(s["rmst_assays"], 1)])


def plot(res, recovery_csv, out):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    rec = load_recovery(recovery_csv)
    xs = np.arange(0, TAU + 1, 10)
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for pol in ("q2c", "directed", "random"):
        a = [cert_assays(r) for r in rec[pol].values()]
        ax.plot(xs, [stat_resolved(a, B) for B in xs], label=f"{pol} (saved original, n={len(a)})", lw=1.2)
    for var, d in res["variants"].items():
        a = [cert_assays(r) for r in d["rows"]]
        if a:
            ax.plot(xs, [stat_resolved(a, B) for B in xs], label=f"lazysp_{var} (n={len(a)}, {d['summary']['status']})", lw=2)
    ax.set_xlabel("additional assays"); ax.set_ylabel("fraction of episodes with ledger certificate"); ax.set_ylim(0, 1)
    ax.legend(fontsize=7); ax.grid(alpha=.3)
    ax.set_title("Certificate rate vs assays (unresolved stay in denominator)", fontsize=9)
    fig.tight_layout(); fig.savefig(Path(out) / "cert_vs_assays.png", dpi=140); plt.close(fig)


def exploratory(res, recovery_csv, comparator="q2c"):
    """POST HOC (written after seeing the preregistered results; not preregistered).

    Family B reuses 4 fixed published targets across the 20 seeds, so its 80 episodes are replicates of
    only 4 problems that differ in their random initial observations.  Seed clusters therefore overstate the
    effective number of independent problems.  This block (i) lists per-problem outcomes, (ii) repeats the
    paired bootstrap with PROBLEM clusters (20 family-A seeds + 4 family-B targets = 24 clusters), and
    (iii) gives paired resolved@B curves."""
    rec = load_recovery(recovery_csv)
    out = {"label": "POST HOC / exploratory; not preregistered", "problem_clusters": 24, "variants": {}}
    for var, d in res["variants"].items():
        rows = {(r["family"], r["seed"], r["start"], r["target"]): r for r in d["rows"]}
        keys = sorted(k for k in rows if k in rec[comparator])
        a = [cert_assays(rows[k]) for k in keys]; b = [cert_assays(rec[comparator][k]) for k in keys]
        cl = [("A", k[1]) if k[0] == "A" else ("B", k[3]) for k in keys]
        cid = {c: i for i, c in enumerate(sorted(set(cl)))}
        ci = np.array([cid[c] for c in cl])
        idx = {c: np.flatnonzero(ci == c) for c in range(len(cid))}
        rng = np.random.default_rng(BOOT_SEED)
        def bs(fn):
            pt = fn(a) - fn(b); dd = np.empty(BOOT)
            for i in range(BOOT):
                pick = rng.choice(len(cid), len(cid), replace=True)
                ii = np.concatenate([idx[c] for c in pick])
                dd[i] = fn([a[j] for j in ii]) - fn([b[j] for j in ii])
            return {"diff": float(pt), "lo95": float(np.percentile(dd, 2.5)), "hi95": float(np.percentile(dd, 97.5))}
        per = {}
        for fam, tg in sorted({(k[0], k[3]) if k[0] == "B" else (k[0], None) for k in keys}, key=str):
            kk = [k for k in keys if k[0] == fam and (tg is None or k[3] == tg)]
            xs = [cert_assays(rows[k]) for k in kk]; ys = [cert_assays(rec[comparator][k]) for k in kk]
            name = f"B:{tg}" if tg else "A:all20"
            f = lambda v: [x for x in v if x is not None]
            per[name] = {"n": len(kk), "lazysp_resolved": len(f(xs)), "comparator_resolved": len(f(ys)),
                         "lazysp_assays_median_resolved": float(np.median(f(xs))) if f(xs) else None, "lazysp_assays_min_max": [min(f(xs)), max(f(xs))] if f(xs) else None,
                         "comparator_assays_median_resolved": float(np.median(f(ys))) if f(ys) else None, "comparator_assays_min_max": [min(f(ys)), max(f(ys))] if f(ys) else None}
        out["variants"][var] = {
            "problem_cluster_bootstrap_resolved_at_1000_diff": bs(lambda x: stat_resolved(x, 1000)),
            "problem_cluster_bootstrap_rmst_diff": bs(stat_rmst),
            "paired_resolved_at_B": {str(B): [stat_resolved(a, B), stat_resolved(b, B)] for B in (100, 250, 500, 750, 800, 850, 900, 950, 1000)},
            "per_problem": per}
    return out


def cmd_analyze(a):
    res = analyze(a.dir, a.variants.split(","), a.recovery, a.comparator)
    write_outputs(res, a.out)
    ex = exploratory(res, a.recovery, a.comparator)
    (Path(a.out) / "exploratory_post_hoc.json").write_text(json.dumps(ex, indent=1))
    plot(res, a.recovery, a.out)
    for var, d in res["variants"].items():
        print(var, d["summary"]["status"], d["summary"]["status_counts"], "false_cert", d["summary"]["false_certificates"])
    return 0


def add_parser(sub):
    p = sub.add_parser("analyze", help="aggregate shards and compare with saved original episodes")
    p.add_argument("--dir", required=True); p.add_argument("--out", required=True)
    p.add_argument("--variants", default="alternate")
    p.add_argument("--recovery", default=str(Path(__file__).resolve().parents[2] / "artifacts" / "recovery" / "episodes.csv"))
    p.add_argument("--comparator", default="q2c")
    p.set_defaults(fn=cmd_analyze)
