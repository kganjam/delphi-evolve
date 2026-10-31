"""Director feasibility probe: Delphi Thompson 1917 ch02-02 (d ∝ h^{3/2}, i.e. log h ~ (2/3) log d)
against the Tallo tree database (Jucker et al. 2022, CC-BY 4.0, doi 10.5281/zenodo.6637599).
Usage: python thompson_tallo_probe.py Tallo.csv out.json
Observed data: stem diameter and height measurements. The fitted slope is an OLS estimate on
log-log data (not corrected for measurement error); no confidence bounds are claimed."""
import sys, json, hashlib, numpy as np, pandas as pd
path, out = sys.argv[1], sys.argv[2]
sha = hashlib.sha256(open(path,'rb').read()).hexdigest()
d = pd.read_csv(path)
n_raw = len(d)
d = d[(d.height_outlier=='N') & (d.stem_diameter_cm>0) & (d.height_m>0)]
def slope(g): return float(np.polyfit(np.log(g.stem_diameter_cm), np.log(g.height_m), 1)[0])
res = {"source":"Tallo.csv","sha256":sha,"rows_raw":n_raw,"rows_used":len(d),
       "filter":"height_outlier=='N', diameter>0, height>0","prediction_delphi_thompson1917_ch02_02":2/3,
       "slope_log_h_on_log_d":{"all":slope(d)}}
for k,g in d.groupby('division'): res["slope_log_h_on_log_d"][k]={"n":len(g),"slope":slope(g)}
res["by_diameter_class_cm"]={f"{lo}-{hi}":{"n":int(len(g)),"slope":slope(g)} for lo,hi in [(1,5),(5,20),(20,60),(60,300)] for g in [d[(d.stem_diameter_cm>=lo)&(d.stem_diameter_cm<hi)]]}
st=[slope(g) for _,g in d.groupby('reference_id') if len(g)>=500 and g.stem_diameter_cm.nunique()>20]
res["per_study_slope_p10_p50_p90"]={"n_studies":len(st),"values":np.percentile(st,[10,50,90]).tolist()}
sp=[slope(g) for _,g in d.groupby('species') if len(g)>=500]
res["per_species_slope_p10_p50_p90"]={"n_species":len(sp),"values":np.percentile(sp,[10,50,90]).tolist()}
json.dump(res,open(out,'w'),indent=1)
print(json.dumps(res,indent=1))
