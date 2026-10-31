#!/usr/bin/env python3
"""Independent audit of core's committed replay results (no evolve/ import).
usage: audit_episodes.py RAW_SUMMARY.csv artifacts/core/replay [kappa=2]
(1) recompute benchmark truth (forward admissible closure) for every unique (start,target) from the raw CSV and
    compare with truth_open / truth_closure_size in episodes.csv;
(2) recompute the family-'all' table at budget 1000 from episodes.csv and compare with table_primary.csv;
(3) check each open certificate's route (when stored) edge-by-edge against my own intervals;
(4) sanity: 'correct' flags agree with certificate vs truth, unresolved are censored, counts per policy are 100.
Exit 0 only if everything matches."""
import sys, json, collections, math
import numpy as np, pandas as pd
AA = "ACDEFGHIKLMNPQRSTVWY"
raw = pd.read_csv(sys.argv[1]); rd = sys.argv[2]; kappa = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0
ep = pd.read_csv(rd + "/episodes.csv"); prim = pd.read_csv(rd + "/table_primary.csv")
SD = [0.014953, 0.009995, 0.005851, 0.002992]  # frozen values from artifacts/core/audit.json (checked below)
au = json.load(open(rd.rsplit("/", 1)[0] + "/audit.json"))
assert au["noise_model_check"]["frozen"] == SD
stop = raw["# Stop"] > 0
bg1, bg2 = raw.loc[stop, "mu_1"].mean(), raw.loc[stop, "mu_2"].mean()
m = raw[~stop]
idx = lambda g: ((AA.index(g[0]) * 20 + AA.index(g[1])) * 20 + AA.index(g[2])) * 20 + AA.index(g[3])
I = np.array([idx(g) for g in m["AAs"]])
sc = np.rint(((m["mu_1"].to_numpy() - bg1) + (m["mu_2"].to_numpy() - bg2)) / 2 * 1e6).astype(np.int64)
cnt = np.minimum(m["InputCount_1"], m["InputCount_2"]).to_numpy()
b = (cnt >= 20).astype(int) + (cnt >= 50) + (cnt >= 200)
meas = np.zeros(160000, bool); meas[I] = True
s_ = np.zeros(160000, np.int64); s_[I] = sc; B = np.zeros(160000, int); B[I] = b
eps = np.ceil(kappa * np.array(SD) / 2 * 1e6).astype(np.int64)
lo = s_ - eps[B]; hi = s_ + eps[B]
W = (8000, 400, 20, 1)
def nbrs(u):
    d = [u // 8000, (u // 400) % 20, (u // 20) % 20, u % 20]
    for p, w in enumerate(W):
        for a in range(20):
            if a != d[p]: yield u + (a - d[p]) * w
def closure(s):
    seen = {s}; q = collections.deque([s])
    while q:
        u = q.popleft()
        for v in nbrs(u):
            if meas[v] and v not in seen and lo[v] >= hi[u]: seen.add(v); q.append(v)
    return seen
rep = {"checks": {}}
cache = {}; bad = []
for (st, tg), g in ep.groupby(["start", "target"]):
    c = closure(idx(st)) if st not in cache else cache[st]; cache[st] = c
    t_open = idx(tg) in c
    for r in g.itertuples():
        if bool(r.truth_open) != t_open or int(r.truth_closure_size) != len(c): bad.append((st, tg, r.policy, r.truth_open, t_open, r.truth_closure_size, len(c)))
rep["checks"]["truth_recomputed_pairs"] = {"unique_pairs": int(ep.groupby(["start", "target"]).ngroups), "unique_starts": len(cache), "mismatches": len(bad), "examples": bad[:3]}
# (2) primary table
mis = []
t = ep.assign(t=np.where(ep.certificate.notna(), ep.assays, np.inf))
for pol, g in t.groupby("policy"):
    row = prim[(prim.family == "all") & (prim.policy == pol) & (prim.budget == 1000)].iloc[0]
    cr = float((g.t <= 1000).mean()); rm = float(np.minimum(g.t, 1000).mean())
    if abs(cr - row.cert_rate) > 1e-9 or abs(rm - row.rmst_assays) > 1e-6 or int((g.t <= 1000).sum()) != int(row.certified): mis.append((pol, cr, row.cert_rate, rm, row.rmst_assays))
rep["checks"]["table_primary_all_1000_recomputed"] = {"policies": int(t.policy.nunique()), "mismatches": len(mis), "examples": mis[:3]}
# (3) routes
rbad = 0; nroute = 0
for r in ep[ep.certificate == "open"].itertuples():
    if isinstance(r.route, str):
        route = eval(r.route) if r.route.startswith("[") else None
        if route:
            nroute += 1
            for a, b2 in zip(route, route[1:]):
                ia, ib = idx(a), idx(b2)
                if not (meas[ia] and meas[ib] and lo[ib] >= hi[ia] and sum(x != y for x, y in zip(a, b2)) == 1): rbad += 1
rep["checks"]["open_routes_edge_check"] = {"routes_checked": nroute, "bad_edges": rbad}
# (4) sanity
issues = []
for r in ep.itertuples():
    if isinstance(r.certificate, str):
        want = (r.certificate == "open") == bool(r.truth_open)
        if bool(r.correct) != want: issues.append(("correct flag", r.policy, r.start, r.target))
    elif not bool(r.censored): issues.append(("uncertified but not censored", r.policy, r.start, r.target))
rep["checks"]["flags"] = {"issues": len(issues), "per_policy_counts": sorted(set(ep.groupby("policy").size()))}
rep["checks"]["false_certificates"] = int(((ep.certificate.notna()) & (ep.correct == False)).sum())  # noqa: E712
ok = bad == [] and mis == [] and rbad == 0 and issues == [] and rep["checks"]["false_certificates"] == 0 and rep["checks"]["flags"]["per_policy_counts"] == [100]
rep["ok"] = ok
print(json.dumps(rep, indent=1, default=str)); sys.exit(0 if ok else 1)
