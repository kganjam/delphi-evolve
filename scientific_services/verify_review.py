"""Independent checks of Gemini-review claims against the pinned CaltechDATA table and core's replay shards.
Does NOT import core's evolve package: reimplements the declared score/interval/edge rule from specs
(protocol.json) so it can disagree with it. Descriptive only; thresholds are the core's ASSUMED kappa=2.

  python -m scientific_services.verify_review <summary_AA.csv> <shards_dir> <out.json>
"""
import os
os.environ.setdefault("OMP_NUM_THREADS", "2"); os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
import glob, hashlib, json, sys
from pathlib import Path
import numpy as np, pandas as pd

AA = "ACDEFGHIKLMNPQRSTVWY"; N = 20 ** 4
EDGES = (20, 50, 200); SD = (0.014953, 0.009995, 0.005851, 0.002992); KAPPA = 2.0
SHA_EXPECT = "a631d8cf6c5b188a801555cc4117547a1bf8e294240e1757c2d2d78dcb25ee82"

def enc(g): return ((AA.index(g[0]) * 20 + AA.index(g[1])) * 20 + AA.index(g[2])) * 20 + AA.index(g[3])
def dec(i): return AA[i // 8000] + AA[(i // 400) % 20] + AA[(i // 20) % 20] + AA[i % 20]
POW = np.array([8000, 400, 20, 1])

def load(path):
    raw = Path(path).read_bytes(); sha = hashlib.sha256(raw).hexdigest()
    assert sha == SHA_EXPECT, "summary_AA.csv hash differs from the core protocol pin"
    d = pd.read_csv(path); stop = d["# Stop"] > 0
    bg = (d.loc[stop, "mu_1"].mean(), d.loc[stop, "mu_2"].mean()); ok = d[~stop]
    idx = np.array([enc(g) for g in ok["AAs"]])
    meas = np.zeros(N, bool); meas[idx] = True
    s1 = np.zeros(N, np.int64); s2 = np.zeros(N, np.int64); cm = np.zeros(N, np.int64)
    s1[idx] = np.round((ok["mu_1"].to_numpy() - bg[0]) * 1e6); s2[idx] = np.round((ok["mu_2"].to_numpy() - bg[1]) * 1e6)
    cm[idx] = np.minimum(ok["InputCount_1"], ok["InputCount_2"])
    s = np.round((s1 + s2) / 2).astype(np.int64) * meas
    return meas, s1, s2, s, cm, sha

def intervals(s, cm, kappa=KAPPA):
    sd = np.array(SD)[np.searchsorted(EDGES, cm, side="right")]
    e = np.ceil(kappa * sd / 2 * 1e6).astype(np.int64)
    return s - e, s + e

def neighbours(idx):
    d = np.stack([idx // 8000, (idx // 400) % 20, (idx // 20) % 20, idx % 20], -1)
    out = []
    for p in range(4):
        for k in range(1, 20):
            out.append(idx + (((d[:, p] + k) % 20) - d[:, p]) * POW[p])
    return np.stack(out, -1)

def edge_checks(meas, s1, s2, s, cm):
    Lo, Hi = intervals(s, cm)
    ids = np.flatnonzero(meas); n_adm = n_pairs = 0
    n_rep_contra_any = n_rep_contra_both = 0; margin_hist = []
    n_s_down = 0
    for a in range(0, len(ids), 20000):
        u = ids[a:a + 20000]; nb = neighbours(u); uu = np.repeat(u, 76); vv = nb.ravel()
        m = meas[vv]; uu, vv = uu[m], vv[m]
        n_pairs += len(uu)
        adm = Lo[vv] >= Hi[uu]
        ua, va = uu[adm], vv[adm]
        n_adm += len(ua)
        r1 = s1[va] < s1[ua]; r2 = s2[va] < s2[ua]
        n_rep_contra_any += int((r1 | r2).sum()); n_rep_contra_both += int((r1 & r2).sum())
        n_s_down += int((s[va] < s[ua]).sum())
    return {"directed_measured_pairs": n_pairs, "admissible_directed_edges_kappa2": n_adm,
            "admissible_edges_where_at_least_one_replicate_decreases": n_rep_contra_any,
            "admissible_edges_where_both_replicates_decrease": n_rep_contra_both,
            "admissible_edges_where_mean_decreases (should be 0)": n_s_down,
            "frac_admissible_with_replicate_reversal": round(n_rep_contra_any / max(n_adm, 1), 5)}

def bfs(meas, Lo, Hi, start):
    reached = np.zeros(N, bool); reached[start] = True; fr = np.array([start]); depth = 0
    while fr.size:
        nb = neighbours(fr); src = np.repeat(fr, 76); dst = nb.ravel()
        ok = meas[dst] & ~reached[dst] & (Lo[dst] >= Hi[src])
        new = np.unique(dst[ok]); reached[new] = True; fr = new; depth += 1
    return reached

def pair_base_rates(meas, s, cm):
    Lo, Hi = intervals(s, cm)
    r = bfs(meas, Lo, Hi, enc("VFVS"))
    ids = np.flatnonzero(meas); sc = s[ids]
    top = ids[np.argsort(-sc)[:1591]]            # top 1% of measured genotypes by mean score
    out = {"closure_size_from_VFVS": int(r.sum()), "frac_of_measured_reachable_from_VFVS": round(float(r.sum() / meas.sum()), 4),
           "top1pct_measured_by_mean_score_reachable_frac": round(float(r[top].mean()), 4),
           "published_targets_reachable": {g: bool(r[enc(g)]) for g in ("AIKG", "CLKG", "VLKG", "ALKG")}}
    # random start->target base rate (target higher mean score than start), 40 random starts
    rng = np.random.default_rng(1)
    starts = rng.choice(ids, 40, replace=False); fr = []
    for st in starts:
        rr = bfs(meas, Lo, Hi, int(st)); better = ids[s[ids] > s[st]]
        fr.append(float(rr[better].mean()) if len(better) else float("nan"))
    out["random_start_frac_of_better_genotypes_reachable_summary"] = {"n_starts": 40, "median": round(float(np.nanmedian(fr)), 4), "min": round(float(np.nanmin(fr)), 4), "max": round(float(np.nanmax(fr)), 4)}
    return out

def init_sample_noise(meas, s1, s2, cm):
    """How well could the replicate-difference SD by count bin be estimated from ONLY the 96 initial observations?"""
    ids = np.flatnonzero(meas); allsd = []
    d_all = (s1 - s2) / 1e6
    bins_all = np.searchsorted(EDGES, cm, side="right")
    glob = [float(np.std(d_all[ids][bins_all[ids] == b], ddof=1)) for b in range(4)]
    rows = []
    for seed in range(20):
        rng = np.random.default_rng(20261031 + seed); init = rng.choice(ids, 96, replace=False)
        b = bins_all[init]; est = []
        for k in range(4):
            x = d_all[init][b == k]
            est.append({"n": int(len(x)), "sd": round(float(np.std(x, ddof=1)), 5) if len(x) > 2 else None})
        rows.append(est)
    return {"sd_from_all_159129 (what the benchmark hardcodes, recomputed)": [round(g, 5) for g in glob],
            "hardcoded": list(SD),
            "per_seed_96_sample_bin_n_and_sd": rows,
            "bins_with_fewer_than_5_obs_in_96_sample_frac_of_seed_bins": round(float(np.mean([e["n"] < 5 for r in rows for e in r])), 3)}

def shard_checks(shards_dir):
    out = {"empty_rows_shards": 0, "populated_shards": 0}; detour = []; greedy_first = None
    for f in sorted(glob.glob(str(Path(shards_dir) / "*.json"))):
        d = json.loads(Path(f).read_text()); name = Path(f).name
        if d["rows"]: out["populated_shards"] += 1
        else: out["empty_rows_shards"] += 1
        for r in d["rows"]:
            if r["policy"] == "q2c" and r["truth_open"] and r.get("truth_shortest_route_len") is not None:
                h = sum(a != b for a, b in zip(r["start"], r["target"]))
                detour.append(r["truth_shortest_route_len"] - h)
        if name == "greedy__seed00.json":
            ql = d["qlogs"].get("B:VFVS>AIKG", [])
            greedy_first = [dec(q[2]) if isinstance(q[2], int) else q[2] for q in ql[:25]]
    out["q2c_truth_open_episodes_seeds_with_rows"] = len(detour)
    out["truth_shortest_route_len_minus_hamming_counts"] = {str(k): int(v) for k, v in zip(*np.unique(detour, return_counts=True))} if detour else {}
    out["greedy_seed00_B_VFVS>AIKG_first_25_queried_genotypes"] = greedy_first
    return out

def main(csv, shards, out):
    meas, s1, s2, s, cm, sha = load(csv)
    res = {"summary_AA_sha256": sha, "kappa": KAPPA, "edge_checks": edge_checks(meas, s1, s2, s, cm),
           "pair_base_rates": pair_base_rates(meas, s, cm), "noise_from_96_sample": init_sample_noise(meas, s1, s2, cm),
           "shard_checks": shard_checks(shards)}
    Path(out).write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1)[:6000])

if __name__ == "__main__":
    main(*sys.argv[1:4])
