"""Aggregate replay shards into CSV tables, paired comparisons, plots and query logs.

Everything reported is computed from the saved shards.  Bootstrap intervals resample
SEEDS (clusters; each seed holds 1 family-A pair + 4 family-B pairs) and are descriptive
resampling summaries, not coverage claims.
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path

import numpy as np
import pandas as pd

BUDGETS = (100, 250, 500, 1000)
ORDER = ["random", "greedy", "uncertainty", "directed", "q2c_nomodel", "q2c", "collective_shared", "collective_shared_rr", "collective_isolated", "collective_shared_c", "collective_isolated_c"]
LABEL = {"random": "random frontier", "greedy": "greedy walk", "uncertainty": "GP uncertainty", "directed": "directed best-first",
         "q2c": "query-to-certify (single)", "q2c_nomodel": "query-to-certify, no learned model", "collective_shared": "collective, shared", "collective_shared_rr": "collective, shared + round-robin", "collective_isolated": "collective, isolated", "collective_shared_c": "collective, shared (no GP)", "collective_isolated_c": "collective, isolated (no GP)"}
COLOR = {"random": "#52514e", "greedy": "#eda100", "uncertainty": "#e87ba4", "directed": "#2a78d6", "q2c": "#eb6834", "q2c_nomodel": "#e34948",
         "collective_shared": "#1baf7a", "collective_isolated": "#6250d6", "collective_shared_rr": "#008300", "collective_shared_c": "#199e70", "collective_isolated_c": "#9085e9"}
STYLE = {"random": ":", "greedy": ":", "uncertainty": "-.", "directed": "--", "q2c": "-", "q2c_nomodel": "-.", "collective_shared": "-", "collective_isolated": "--", "collective_shared_rr": "-.", "collective_shared_c": "-", "collective_isolated_c": "--"}


def load_rows(d: Path):
    rows, q = [], {}
    for p in sorted((d / "shards").glob("*.json")):
        j = json.loads(p.read_text())
        rows += j["rows"]
        pol = p.name.split("__")[0]
        for k, v in j["qlogs"].items():
            q[(pol, p.stem.split("seed")[1], k)] = v
    df = pd.DataFrame(rows)
    return df, q


def cert_time(df):
    t = df["assays"].astype(float).where(df["certificate"].notna(), np.inf)
    return t


def table_primary(df):
    out = []
    df = df.assign(t=cert_time(df))
    for fam, sub0 in [("A", df[df.family == "A"]), ("B", df[df.family == "B"]), ("all", df)]:
        for pol in ORDER:
            s = sub0[sub0.policy == pol]
            if s.empty:
                continue
            for b in BUDGETS:
                cert = s.t <= b
                row = {"family": fam, "policy": pol, "budget": b, "episodes": len(s), "certified": int(cert.sum()),
                       "cert_rate": cert.mean(), "abstain_censored": int((~cert).sum()),
                       "false_certificates": int((cert & (s.correct == False)).sum()),  # noqa: E712
                       "full_data_verification_failures": int((cert & (s.verified_by_full_data == False)).sum()),  # noqa: E712
                       "rmst_assays": np.minimum(s.t, b).mean(),
                       "median_assays_or_censored": ("censored>%d" % b) if (s.t.median() > b) else float(s.t.median())}
                for tr in ("open", "blocked"):
                    st = s[s.truth_open == (tr == "open")]
                    row[f"cert_rate_truth_{tr}"] = float((st.t <= b).mean()) if len(st) else np.nan
                    row[f"n_truth_{tr}"] = len(st)
                out.append(row)
    return pd.DataFrame(out)


def boot_ci(vals_by_seed: np.ndarray, rng, n=4000):
    k = len(vals_by_seed)
    idx = rng.integers(0, k, (n, k))
    m = vals_by_seed[idx].mean(1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def paired(df, a, b, metric, budget, fam=None):
    """Mean over seeds of (metric_a - metric_b), episodes matched on (family,start,target,seed)."""
    d = df.assign(t=cert_time(df))
    if fam:
        d = d[d.family == fam]
    key = ["family", "seed", "start", "target"]
    A = d[d.policy == a].set_index(key); B = d[d.policy == b].set_index(key)
    j = A.join(B, lsuffix="_a", rsuffix="_b", how="inner")
    if metric == "cert":
        diff = (j.t_a <= budget).astype(float) - (j.t_b <= budget).astype(float)
    else:  # restricted-mean assays: lower is better
        diff = np.minimum(j.t_a, budget) - np.minimum(j.t_b, budget)
    per_seed = diff.groupby(level="seed").mean().to_numpy()
    wins = int((diff > 0).sum()) if metric == "cert" else int((diff < 0).sum())
    losses = int((diff < 0).sum()) if metric == "cert" else int((diff > 0).sum())
    return diff, per_seed, wins, losses, int((diff == 0).sum())


def table_paired(df):
    rng = np.random.default_rng(7)
    pairs = [("directed", "random"), ("q2c", "random"), ("q2c", "directed"), ("q2c", "q2c_nomodel"), ("q2c_nomodel", "directed"), ("collective_shared", "directed"),
             ("collective_shared", "q2c"), ("collective_shared", "collective_isolated"), ("collective_shared_c", "collective_isolated_c"), ("collective_shared_c", "q2c_nomodel"), ("collective_isolated_c", "q2c_nomodel"), ("q2c_nomodel", "q2c"), ("collective_isolated", "q2c"),
             ("collective_shared_rr", "collective_isolated"), ("collective_shared_rr", "collective_shared"), ("collective_isolated", "directed"),
             ("uncertainty", "random"), ("greedy", "random")]
    rows = []
    for a, b in pairs:
        if not ((df.policy == a).any() and (df.policy == b).any()):
            continue
        for fam in ("A", "B", None):
            for budget in BUDGETS:
                for metric in ("cert", "rmst"):
                    diff, ps, w, l, t = paired(df, a, b, metric, budget, fam)
                    lo, hi = boot_ci(ps, rng)
                    rows.append({"a": a, "b": b, "family": fam or "all", "budget": budget, "metric": "cert_rate_diff(a-b)" if metric == "cert" else "rmst_assays_diff(a-b; negative=a better)",
                                 "mean_diff": float(diff.mean()), "seed_cluster_bootstrap_2.5": lo, "seed_cluster_bootstrap_97.5": hi,
                                 "episodes": len(diff), "a_better": w, "b_better": l, "tied": t})
    return pd.DataFrame(rows)


MAIN = ["random", "greedy", "uncertainty", "directed", "q2c", "q2c_nomodel", "collective_shared", "collective_isolated"]
ABLATION = ["directed", "q2c", "q2c_nomodel", "collective_shared", "collective_shared_rr", "collective_isolated", "collective_shared_c", "collective_isolated_c"]


def plots(df, outdir: Path):
    _plots(df, outdir, MAIN, "cert_vs_assays.png", "outcomes_at_budget.png")
    _plots(df, outdir, ABLATION, "ablation_cert_vs_assays.png", "ablation_outcomes_at_budget.png")


def _plots(df, outdir: Path, ORDER, curve_name, bar_name):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": "#52514e", "axes.labelcolor": "#0b0b0b", "text.color": "#0b0b0b"})
    d = df.assign(t=cert_time(df)); xs = np.arange(0, 1001, 5)
    fig, axs = plt.subplots(1, 3, figsize=(13, 5.0), sharey=True)
    for ax, (fam, title) in zip(axs, [("A", "A: seeded-initial pairs (20)"), ("B", "B: parent VFVS → published top variants (80)"), (None, "All 100 episodes")]):
        s = d if fam is None else d[d.family == fam]
        for pol in ORDER:
            sp = s[s.policy == pol]
            if sp.empty:
                continue
            y = [(sp.t <= x).mean() for x in xs]
            ax.plot(xs, y, color=COLOR[pol], ls=STYLE[pol], lw=2, label=LABEL[pol])
        ax.set_title(title, loc="left", fontsize=10); ax.set_xlabel("assays beyond the 96 initial observations")
        ax.set_xlim(0, 1000); ax.set_ylim(0, 1.0); ax.grid(axis="y", color="#e6e5e1", lw=0.6)
    axs[0].set_ylabel("fraction of episodes with a sound certificate\n(remainder = unresolved, right-censored at 1000)")
    h, l = axs[0].get_legend_handles_labels()
    fig.legend(h, l, frameon=False, fontsize=8.5, loc="lower center", ncol=4)
    fig.suptitle("Retrospective replay on measured TrpB: certificate (open or blocked) vs assays, matched budget", x=0.01, ha="left", fontsize=11)
    fig.tight_layout(rect=(0, 0.12, 1, 1)); fig.savefig(outdir / curve_name, dpi=150); plt.close(fig)

    # outcome decomposition at the full budget
    fig, axs = plt.subplots(1, 2, figsize=(11, 0.55 * len(ORDER) + 1.6), sharey=True)
    for ax, fam in zip(axs, ["A", "B"]):
        s = d[d.family == fam]; y = np.arange(len(ORDER))[::-1]
        for yy, pol in zip(y, ORDER):
            sp = s[s.policy == pol]
            if sp.empty:
                continue
            n = len(sp); o = ((sp.certificate == "open")).sum() / n; bl = (sp.certificate == "blocked").sum() / n; un = 1 - o - bl
            ax.barh(yy, o, color="#2a78d6", edgecolor="white", lw=1.5, height=0.62)
            ax.barh(yy, bl, left=o, color="#eb6834", edgecolor="white", lw=1.5, height=0.62)
            ax.barh(yy, un, left=o + bl, color="#d9d8d3", edgecolor="white", lw=1.5, height=0.62)
        ax.set_yticks(y); ax.set_yticklabels([LABEL[p] for p in ORDER]); ax.set_xlim(0, 1); ax.set_xlabel("fraction of episodes at 1000 assays")
        ax.set_title({"A": "A: seeded-initial pairs", "B": "B: published-parent pairs"}[fam], loc="left", fontsize=10)
    from matplotlib.patches import Patch
    fig.legend(handles=[Patch(color="#2a78d6", label="open certificate"), Patch(color="#eb6834", label="blocked (cut) certificate"), Patch(color="#d9d8d3", label="unresolved / abstain (right-censored)")], frameon=False, fontsize=8.5, loc="lower center", ncol=3)
    fig.tight_layout(rect=(0, 0.07, 1, 1)); fig.savefig(outdir / bar_name, dpi=150); plt.close(fig)


def write_logs(q, outdir: Path):
    outdir.mkdir(parents=True, exist_ok=True)
    from . import data
    by_pol = {}
    for (pol, seed, pair), rows in q.items():
        by_pol.setdefault(pol, []).append((seed, pair, rows))
    sizes = {}
    for pol, items in by_pol.items():
        p = outdir / f"queries__{pol}.tsv.gz"
        with gzip.open(p, "wt") as f:
            f.write("seed\tpair\tn\tactor\tgenotype\tlower_micro\tupper_micro\tscore_micro\twhy\n")
            for seed, pair, rows in sorted(items):
                for n, actor, node, rec, why in rows:
                    lo, hi, s = ("", "", "") if rec is None else rec
                    f.write(f"{seed}\t{pair}\t{n}\t{actor}\t{data.decode(node)}\t{lo}\t{hi}\t{s}\t{why}\n" if rec else f"{seed}\t{pair}\t{n}\t{actor}\t{data.decode(node)}\t\t\t\tABSENT:{why}\n")
        sizes[pol] = p.stat().st_size
    return sizes


def run(replay_dir: Path, out: Path, logs: bool = True):
    df, q = load_rows(replay_dir)
    df.to_csv(replay_dir / "episodes.csv", index=False)
    prim = table_primary(df); prim.to_csv(replay_dir / "table_primary.csv", index=False)
    pr = table_paired(df); pr.to_csv(replay_dir / "table_paired.csv", index=False)
    plots(df, replay_dir)
    sizes = write_logs(q, replay_dir / "queries") if logs else {}
    seeds = sorted(df.seed.unique().tolist())
    summ = {"episodes": int(len(df)), "policies": [p for p in ORDER if (df.policy == p).any()], "seeds": len(seeds),
            "primary_at_1000_family_all": {r.policy: {"cert_rate": r.cert_rate, "false_certificates": int(r.false_certificates), "abstain": int(r.abstain_censored),
                                                       "rmst_assays": r.rmst_assays} for r in prim[(prim.family == "all") & (prim.budget == 1000)].itertuples()},
            "any_false_certificate": bool((prim.false_certificates > 0).any()), "any_full_data_verification_failure": bool((prim.full_data_verification_failures > 0).any()),
            "truth_open_fraction": {f: float(df[(df.family == f) & (df.policy == "random")].truth_open.mean()) for f in ("A", "B")},
            "query_log_bytes": sizes}
    (replay_dir / "summary.json").write_text(json.dumps(summ, indent=1, default=float))
    print(prim[(prim.budget == 1000)][["family", "policy", "cert_rate", "abstain_censored", "false_certificates", "rmst_assays"]].to_string())
