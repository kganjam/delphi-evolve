"""Real one-pass retrieval baseline for bench v1.2 (critic): TF-IDF nearest Delphi math claim (92 claims from planning/rethink/wildcard/delphi_math_claims_raw.json; title + statement + LaTeX math)
for each model_payload prompt STEM (text before ' Conventions:'). Policy R: if the retrieved claim is the one the family cites, answer 'applies' (the retrieved textbook statement says it applies; no scope reasoning),
else ABSTAIN. Reports retrieval top-1 accuracy, coverage, selective risk, false acceptance. Inputs: prompt text + the claim corpus only (no family metadata, no parameters).
Usage: python3 -I retrieval_baseline.py OUT.json"""
import json, os, sys
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
D = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(D, "..", "..", ".."))
claims = json.loads(json.load(open(os.path.join(ROOT, "planning/rethink/wildcard/delphi_math_claims_raw.json")))["search"]["result"]["content"][0]["text"])
cid = [c["claim"].rsplit("/", 1)[-1] for c in claims]
ctext = [f'{c["title"]}. {c["statement"]} {c["math"]}' for c in claims]
EXPECT = {"turing_finite_domain": {"turing-ddi"}, "turing_2d_rectangle": {"turing-ddi"}, "wavelength_formula_licence": {"turing-wavelength"}, "kimura_regime": {"kimura-fixation-probability", "kimura-fixation-time", "kimura-substitution-rate"},
          "hawk_dove_ess": {"maynardsmith-hawk-dove", "maynardsmith-ess"}, "greenhill_buckling": {"thompson1917-ch02-02", "thompson1917-ch02-03"}, "hamilton_rule_form": {"hamilton-rule"}, "fisher_kpp_speed": {"fisher-kpp-speed"}}
pub = [json.loads(l) for l in open(os.path.join(D, "instances_public.jsonl"))]; key = {json.loads(l)["id"]: json.loads(l)["verdict"] for l in open(os.path.join(D, "key.jsonl"))}
vec = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, stop_words="english"); X = vec.fit_transform(ctext)
rows = []
for p in pub:
    stem = p["request_text"].split(" Conventions:")[0]; sims = (vec.transform([stem]) @ X.T).toarray()[0]; top = cid[int(sims.argmax())]
    ok_ret = top in EXPECT[p["family"]]
    rows.append({"id": p["id"], "family": p["family"], "top1": top, "retrieval_correct": ok_ret, "pred": "applies" if ok_ret else None, "truth": key[p["id"]]})
N = len(rows); ans = [r for r in rows if r["pred"]]; err = sum(r["pred"] != r["truth"] for r in ans); fa = sum(r["pred"] == "applies" and r["truth"] != "applies" for r in rows)
res = {"N": N, "retrieval_top1_correct": sum(r["retrieval_correct"] for r in rows), "answered": len(ans), "coverage": round(len(ans) / N, 4), "errors_among_answered": err,
       "selective_risk": round(err / len(ans), 4) if ans else None, "false_acceptance": {"count": fa, "denominator": sum(r["truth"] != "applies" for r in rows)},
       "by_family_retrieval_correct": {f: [sum(r["retrieval_correct"] for r in rows if r["family"] == f), sum(r["family"] == f for r in rows)] for f in sorted(EXPECT)},
       "note": "retrieval locates the cited claim and asserts it applies; it cannot compute scope, so on this bench it behaves like always-applies restricted to retrieval successes. Expected-claim mapping is by the critic."}
json.dump({"summary": res, "rows": rows}, open(sys.argv[1], "w"), indent=1); print(res)
