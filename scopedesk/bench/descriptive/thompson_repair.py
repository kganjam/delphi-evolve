"""Thompson d ~ h^{3/2} 'repair artifact' (critic, 2026-10-31): request -> diagnosis -> four operationalisations kept separate with study-clustered bootstrap
-> missing mechanical inputs -> bound-shaped conditional test. Evidence kinds: 'observed' only for Tallo rows (Jucker et al. 2022, CC-BY 4.0, Zenodo 6637599);
everything else is 'assumed' or 'model-derived'. No invented bounds: intervals are percentile intervals of a study-cluster bootstrap and are DESCRIPTIVE.
Usage: python3 -I thompson_repair.py Tallo.csv OUT.json OUT_TABLE.csv"""
import csv, hashlib, json, sys
import numpy as np
path, out, table = sys.argv[1:4]
sha = hashlib.sha256(open(path, "rb").read()).hexdigest()
d_cm, h, div, ref = [], [], [], []
for r in csv.DictReader(open(path)):
    try: d = float(r["stem_diameter_cm"]); hh = float(r["height_m"])
    except ValueError: continue
    if r["height_outlier"] != "N" or d <= 0 or hh <= 0: continue
    d_cm.append(d); h.append(hh); div.append(r["division"]); ref.append(r["reference_id"])
D = np.array(d_cm) / 100.0; H = np.array(h); DIV = np.array(div); REF = np.array(ref)
G = 9.81
studies = np.unique(REF); idx_by = {s: np.where(REF == s)[0] for s in studies}
LX, LY = np.log10(D), np.log10(H)

def ols(ix): x, y = LX[ix], LY[ix]; return float(np.polyfit(x, y, 1)[0])
def sma(ix): x, y = LX[ix], LY[ix]; return float(np.polyfit(x, y, 1)[0] / abs(np.corrcoef(x, y)[0, 1]))
def env(ix, q=99, nb=14, min_n=200):
    dm, hm = D[ix], H[ix]
    edges = np.logspace(np.log10(np.percentile(dm, 1)), np.log10(np.percentile(dm, 99.5)), nb + 1)
    xs, ys = [], []
    for a, b in zip(edges[:-1], edges[1:]):
        s = (dm >= a) & (dm < b)
        if s.sum() >= min_n: xs.append(np.log10(np.sqrt(a * b))); ys.append(np.log10(np.percentile(hm[s], q)))
    return float(np.polyfit(xs, ys, 1)[0]) if len(xs) >= 5 else float("nan")
def frac_above(ix, E=10e9, rho=800.0):
    hc = 0.7880 * (E / (rho * G)) ** (1 / 3) * D[ix] ** (2 / 3); return float((H[ix] > hc).mean())

allix = np.arange(len(H))
stats = {"pooled_OLS_slope": ols, "pooled_SMA_slope": sma, "q99_envelope_slope": env, "frac_trees_above_Greenhill_E10GPa_rho800_uniform": frac_above}
point = {k: f(allix) for k, f in stats.items()}
rng = np.random.default_rng(7); B = 300; boot = {k: [] for k in stats}
for _ in range(B):
    pick = rng.choice(studies, size=len(studies), replace=True)
    ix = np.concatenate([idx_by[s] for s in pick])
    for k, f in stats.items():
        v = f(ix)
        if v == v: boot[k].append(v)
ci = {k: [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))] for k, v in boot.items()}
by_div = {dv: {"n": int((DIV == dv).sum()), "OLS": ols(np.where(DIV == dv)[0]), "SMA": sma(np.where(DIV == dv)[0])} for dv in ("Angiosperm", "Gymnosperm")}
# sensitivity of the bound-shaped statistic to the ASSUMED inputs (not measured on these trees)
grid = {f"E{E/1e9:g}GPa_rho{int(r)}": frac_above(allix, E, r) for E in (3e9, 6e9, 10e9, 15e9) for r in (600.0, 800.0, 1000.0)}
# Thompson's own numbers as an illustration: Kew flagstaff 221 ft tall, 21 in base diameter, 'could not by theory exceed ~300 ft'
FT, IN = 0.3048, 0.0254
kew = {"height_m": 221 * FT, "base_diameter_m": 21 * IN, "stated_limit_m": 300 * FT}
kew["implied_E_over_rho_g_m3_uniform_formula"] = (kew["stated_limit_m"] / (0.7880 * kew["base_diameter_m"] ** (2 / 3))) ** 3
kew["E_GPa_if_rho_800"] = kew["implied_E_over_rho_g_m3_uniform_formula"] * 800 * G / 1e9
res = {
 "request": "Test Thompson's d ~ h^{3/2} on Tallo.",
 "diagnosis": {
   "source": "Thompson, On Growth and Form (1917), ch. II 'On Magnitude', pp. 19-20 (Gutenberg 55264; critic read the first 100,000 characters via a tool summary, primary read the passage directly)",
   "what_the_source_says": "Greenhill's result that the diameter of a homogeneous body must increase as the 3/2 power of the height, derived under stated assumptions (trunk tapers uniformly; branch cross-section follows a definite law such as Ruskin's constant area), applied to the Kew flagstaff (about 221 ft, 21 in base), which 'could not possibly, by theory, have grown to more than about 300 ft'. It is a limiting-height (self-weight buckling) argument.",
   "mismatch": "A pooled regression of log height on log diameter over living trees tests a mean allometric relation, a different proposition from an upper limit under uniform taper and a stated branch law."},
 "evidence_kinds": {"tallo_rows": "observed", "slopes_and_fractions": "observed-derived (descriptive)", "bound_test_inputs_E_rho": "assumed", "Greenhill_constant": "model-derived"},
 "data": {"file": "Tallo.csv", "sha256": sha, "licence": "CC-BY 4.0 (Zenodo record 6637599)", "rows_used": int(len(H)), "filter": "height_outlier=='N', diameter>0, height>0", "n_studies": int(len(studies))},
 "operationalisations": {
   "1_pooled_OLS": {"quantity": "slope of log10 h on log10 d (claim implies 2/3 = 0.667 if read as mean allometry)", "point": point["pooled_OLS_slope"], "study_cluster_bootstrap_95": ci["pooled_OLS_slope"], "reading": "tests mean allometry; OLS attenuates when diameter is noisy"},
   "2_pooled_SMA": {"point": point["pooled_SMA_slope"], "study_cluster_bootstrap_95": ci["pooled_SMA_slope"], "reading": "errors-in-variables slope; shows the verdict depends on the estimator"},
   "3_q99_upper_envelope": {"point": point["q99_envelope_slope"], "study_cluster_bootstrap_95": ci["q99_envelope_slope"], "reading": "closest observational proxy for an upper limit, but still not a buckling bound"},
   "4_bound_shaped_conditional": {"statement": "For each tree, height <= Greenhill H_cr = 0.788 (E/(rho g))^(1/3) d^(2/3) (UNIFORM cylinder) given E and rho",
        "fraction_above_at_E10GPa_rho800": point["frac_trees_above_Greenhill_E10GPa_rho800_uniform"], "study_cluster_bootstrap_95": ci["frac_trees_above_Greenhill_E10GPa_rho800_uniform"],
        "sensitivity_grid_assumed_inputs": grid, "reading": "conditional on ASSUMED E, rho and a uniform cylinder; taper/branch mass change the limit (Thompson's own assumptions); not a refutation or confirmation"}},
 "by_clade": by_div,
 "thompson_own_numbers_illustration": kew | {"note": "model-derived: with the uniform Greenhill formula, a 300 ft limit at 21 in base diameter implies E/(rho g) of this size; compare green-wood E of order 5-15 GPa; taper and branch law (not modelled here) change this"},
 "missing_mechanical_inputs": [
   {"input": "wood density rho (green)", "candidate_source": "Global Wood Density Database v2 (Zanne et al.; Zenodo 10.5281/zenodo.18262736, CC-BY 4.0 per the Zenodo API; v1 at Dryad 10.5061/dryad.234 licence NOT verified)", "caveat": "basic (dry) density, not green density; species-level join to Tallo species is not done here"},
   {"input": "Young's modulus E (green wood)", "candidate_source": "USDA Forest Products Laboratory Wood Handbook FPL-GTR-190 (2010), species property tables; availability found, licence/public-domain status not verified here", "caveat": "values are for small clear specimens, not living stems"},
   {"input": "taper profile", "candidate_source": "none identified for Tallo; crown radius is present, taper is not", "caveat": "Thompson's argument assumes uniform taper"},
   {"input": "branch/crown mass (branch-area law)", "candidate_source": "none identified in Tallo (crown radius only)", "caveat": "changes the loading in the buckling problem"}],
 "conditional_statement": "IF E, rho, taper and branch mass for a tree are supplied, THEN the tapered-column Rayleigh-Ritz buckling height (scopedesk/bench/fam_greenhill.py) can be compared with its measured height. WITHOUT those inputs the Tallo data cannot test Thompson's mechanical claim; descriptive slopes are reported separately and do not decide it.",
 "limitations": ["bootstrap resamples studies (B=300), percentile intervals, descriptive only", "Tallo mixes protocols; heights saturate with diameter so a power law is a local fit", "Tallo's own 2022 paper already compares the H-D exponent with 2/3 using mixed-effects models (primary's read); this is a reproduction"]}
json.dump(res, open(out, "w"), indent=1)
with open(table, "w", newline="") as f:
    w = csv.writer(f); w.writerow(["operationalisation", "quantity", "point", "ci_low", "ci_high", "evidence_kind", "tests_buckling_claim"])
    for name, key, kind, tests in (("pooled OLS", "pooled_OLS_slope", "observed-derived", "no (mean allometry)"), ("pooled SMA", "pooled_SMA_slope", "observed-derived", "no (mean allometry)"),
                                  ("q99 envelope", "q99_envelope_slope", "observed-derived", "no (upper-percentile proxy)"), ("fraction above uniform Greenhill bound (assumed E=10GPa, rho=800)", "frac_trees_above_Greenhill_E10GPa_rho800_uniform", "observed + assumed inputs", "only conditionally (uniform cylinder, assumed E, rho)")):
        w.writerow([name, key, round(point[key], 4), round(ci[key][0], 4), round(ci[key][1], 4), kind, tests])
print(json.dumps({k: res["operationalisations"][k].get("point", res["operationalisations"][k].get("fraction_above_at_E10GPa_rho800")) for k in res["operationalisations"]}), ci)
