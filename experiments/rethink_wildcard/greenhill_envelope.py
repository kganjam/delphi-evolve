"""Red-team of 'Claims-as-tests' on Thompson ch02-02: the original passage is a self-weight BUCKLING LIMIT
(upper bound), not a mean-allometry equality. Test the bound-shaped proposition on Tallo (CC-BY, Zenodo 6637599)
alongside the descriptive OLS slope. Descriptive probe only: neither confirms nor refutes Thompson's mechanics.

Greenhill (uniform cylinder, clamped base, own weight): H_cr = (7.8373 E I / (rho g A))^(1/3), I/A = d^2/16
  => H_cr = 0.7880 (E/(rho g))^(1/3) d^(2/3).  (Taper or branch mass change the constant; E, rho are inputs.)
Parameter grid is an ASSUMED sensitivity range for green wood, not a measured property of Tallo trees.
Usage: python3 -I greenhill_envelope.py Tallo.csv OUT.json"""
import csv, hashlib, json, sys
import numpy as np
path, out = sys.argv[1], sys.argv[2]
sha = hashlib.sha256(open(path, "rb").read()).hexdigest()
rows = list(csv.DictReader(open(path)))
n_raw = len(rows)
d_cm, h, div, ref = [], [], [], []
for r in rows:
    try:
        d = float(r["stem_diameter_cm"]); hh = float(r["height_m"])
    except ValueError:
        continue
    if r["height_outlier"] != "N" or d <= 0 or hh <= 0: continue
    d_cm.append(d); h.append(hh); div.append(r["division"]); ref.append(r["reference_id"])
d_m = np.array(d_cm) / 100.0; h = np.array(h); div = np.array(div); ref = np.array(ref)
g = 9.81
res = {"source": "Tallo.csv", "sha256": sha, "rows_raw": n_raw, "rows_used": int(len(h)),
       "filter": "height_outlier=='N', diameter>0, height>0 (same as director probe)"}
# 1. Bound-shaped test: share of trees above Greenhill H_cr for an assumed E (GPa) / rho (kg/m3) grid
grid = {}
for E in (3.0, 6.0, 10.0, 15.0):
    for rho in (600.0, 800.0, 1000.0):
        hc = 0.7880 * (E * 1e9 / (rho * g)) ** (1 / 3) * d_m ** (2 / 3)
        ratio = h / hc
        grid[f"E{E}GPa_rho{int(rho)}"] = {"frac_trees_above_Hcr": float((ratio > 1).mean()),
                                         "n_above": int((ratio > 1).sum()),
                                         "ratio_p50": float(np.percentile(ratio, 50)),
                                         "ratio_p99": float(np.percentile(ratio, 99)),
                                         "ratio_max": float(ratio.max())}
res["greenhill_bound_grid_assumed_E_rho"] = grid
# 2. Upper-envelope exponent: slope of per-bin q99 height vs bin-centre diameter (log-log), bins by log10 d
def env_slope(mask, q, min_n=300, nb=14):
    dm, hm = d_m[mask], h[mask]
    edges = np.logspace(np.log10(np.percentile(dm, 1)), np.log10(np.percentile(dm, 99.5)), nb + 1)
    xs, ys, ns = [], [], []
    for a, b in zip(edges[:-1], edges[1:]):
        s = (dm >= a) & (dm < b)
        if s.sum() >= min_n:
            xs.append(np.log10(np.sqrt(a * b))); ys.append(np.log10(np.percentile(hm[s], q))); ns.append(int(s.sum()))
    xs, ys = np.array(xs), np.array(ys)
    sl = np.polyfit(xs, ys, 1)[0]
    return {"slope": float(sl), "n_bins": len(xs), "n_min_bin": min(ns)}
allm = np.ones(len(h), bool)
res["upper_envelope_slope_log10h_on_log10d"] = {
    f"q{q}": {"all": env_slope(allm, q), "Angiosperm": env_slope(div == "Angiosperm", q),
              "Gymnosperm": env_slope(div == "Gymnosperm", q)} for q in (90, 99)}
# 3. OLS vs errors-in-variables (SMA) slope, pooled and by clade: OLS attenuates when d is noisy
def slopes(mask):
    x, y = np.log10(d_m[mask]), np.log10(h[mask])
    b = np.polyfit(x, y, 1)[0]; r = np.corrcoef(x, y)[0, 1]
    return {"n": int(mask.sum()), "ols": float(b), "pearson_r": float(r), "sma": float(b / abs(r))}
res["ols_vs_sma"] = {"all": slopes(allm), "Angiosperm": slopes(div == "Angiosperm"), "Gymnosperm": slopes(div == "Gymnosperm")}
# 4. Study mixture: per-study OLS slope spread (studies with >=500 trees)
sl = []
for r_ in np.unique(ref):
    m = ref == r_
    if m.sum() >= 500: sl.append(slopes(m)["ols"])
res["per_study_ols_slope"] = {"n_studies": len(sl), "p10_p50_p90": [float(np.percentile(sl, p)) for p in (10, 50, 90)]}
res["interpretation_limits"] = [
 "Greenhill constant assumes uniform cylinder; taper and branch mass change the limit (Thompson pp.19-20 discuss both).",
 "E and rho are an assumed grid, not measured on Tallo trees; the bound is only as good as that input.",
 "Tallo mixes studies and measurement protocols; heights saturate with diameter so a power law is only a local fit.",
 "Descriptive probe. Not a test of Thompson's mechanical argument and not a Lean-checked statement."]
json.dump(res, open(out, "w"), indent=1)
print(json.dumps(res, indent=1)[:6000])
