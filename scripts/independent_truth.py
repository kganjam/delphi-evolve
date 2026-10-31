#!/usr/bin/env python3
"""Independent recomputation of core's benchmark truth (forward admissible closure) from raw CSV.
Does NOT import evolve/. Rule (from core certificate): s_k = mu_k - mean(mu_k over stop rows);
s = mean(s1,s2) -> round(s*1e6); eps = ceil(kappa*sd_bin/2*1e6) with bins of min(InputCount_1,2) edges (20,50,200);
edge u->v admissible iff lo[v] >= hi[u]; only the 159,129 measured non-stop genotypes are vertices.
usage: independent_truth.py RAW_SUMMARY.csv DEMO.json START TARGET"""
import sys, json, math, collections
import numpy as np, pandas as pd
AA = "ACDEFGHIKLMNPQRSTVWY"
raw = pd.read_csv(sys.argv[1]); demo = json.load(open(sys.argv[2])); S, T = sys.argv[3], sys.argv[4]
stop = raw["# Stop"] > 0
bg1, bg2 = raw.loc[stop, "mu_1"].mean(), raw.loc[stop, "mu_2"].mean()
m = raw[~stop]
idx = lambda g: ((AA.index(g[0]) * 20 + AA.index(g[1])) * 20 + AA.index(g[2])) * 20 + AA.index(g[3])
I = np.array([idx(g) for g in m["AAs"]])
sc = np.rint(((m["mu_1"].to_numpy() - bg1) + (m["mu_2"].to_numpy() - bg2)) / 2 * 1e6).astype(np.int64)
cnt = np.minimum(m["InputCount_1"].to_numpy(), m["InputCount_2"].to_numpy())
sdb = np.array(demo["interval_model"]["sd_bins"].values(), dtype=float) if False else np.array(list(demo["interval_model"]["sd_bins"].values()))
b = (cnt >= 20).astype(int) + (cnt >= 50) + (cnt >= 200)
meas = np.zeros(160000, bool); meas[I] = True
S_ = np.zeros(160000, np.int64); S_[I] = sc; B = np.zeros(160000, int); B[I] = b
def closure(kappa):
    eps = np.ceil(kappa * sdb / 2 * 1e6).astype(np.int64)
    lo = S_ - eps[B]; hi = S_ + eps[B]
    s, t = idx(S), idx(T); seen = {s: None}; q = collections.deque([s])
    while q:
        u = q.popleft(); d = [u // 8000, (u // 400) % 20, (u // 20) % 20, u % 20]
        for p, w in enumerate((8000, 400, 20, 1)):
            for a in range(20):
                if a == d[p]: continue
                v = u + (a - d[p]) * w
                if meas[v] and v not in seen and lo[v] >= hi[u]:
                    seen[v] = u; q.append(v)
    depth = None
    if t in seen:
        depth = 0; x = t
        while seen[x] is not None: x = seen[x]; depth += 1
    return t in seen, len(seen), depth
res = []
for row in demo["kappa_sweep"]:
    o, n, dpt = closure(row["kappa"])
    res.append({"kappa": row["kappa"], "core": [row["open"], row["reachable_from_start"], row["shortest_route_edges"]], "independent": [o, n, dpt],
                "match": [o, n, dpt] == [row["open"], row["reachable_from_start"], row["shortest_route_edges"]]})
print(json.dumps(res, indent=1)); sys.exit(0 if all(r["match"] for r in res) else 1)
