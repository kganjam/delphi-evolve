"""Stronger surface-leakage audit (critic). Question: can the verdict be predicted from request wording alone (no computation)?
Models: TF-IDF word 1-2gram logistic regression and char 3-5gram logistic regression, trained on all-but-one families and tested on the held-out family
(leave-one-family-out), plus the same with conventions boilerplate stripped. Baseline: majority class of the test family. Exact binomial intervals.
Also reports the most predictive tokens (to be read by a human). Usage: python3 -I leakage_audit.py BENCHDIR OUT.json"""
import json, sys
import numpy as np
from collections import Counter
from scipy.stats import beta
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
d, out = sys.argv[1:3]
pub = [json.loads(l) for l in open(f"{d}/instances_public.jsonl")]; key = {json.loads(l)["id"]: json.loads(l)["verdict"] for l in open(f"{d}/key.jsonl")}
y = np.array([key[p["id"]] for p in pub]); fam = np.array([p["family"] for p in pub])
def stem(t): return t.split(" Conventions:")[0]
cp = lambda k, n: [round(float(beta.ppf(.025, k, n - k + 1)) if k else 0.0, 3), round(float(beta.ppf(.975, k + 1, n - k)) if k < n else 1.0, 3)]
res = {"n": len(pub)}
for name, texts in (("full_text", [p["request_text"] for p in pub]), ("stem_only_no_conventions", [stem(p["request_text"]) for p in pub])):
    for vname, vec in (("word_1-2gram", lambda: TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)), ("char_3-5gram", lambda: TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=3, sublinear_tf=True))):
        correct = 0; maj = 0; per = {}
        for f in sorted(set(fam)):
            tr, te = fam != f, fam == f
            v = vec(); Xtr = v.fit_transform(np.array(texts, dtype=object)[tr]); Xte = v.transform(np.array(texts, dtype=object)[te])
            clf = LogisticRegression(max_iter=2000, C=1.0).fit(Xtr, y[tr]); pr = clf.predict(Xte)
            k = int((pr == y[te]).sum()); m = Counter(y[te]).most_common(1)[0][1]
            per[f] = {"acc": round(k / te.sum(), 3), "n": int(te.sum()), "majority": round(m / te.sum(), 3)}; correct += k; maj += m
        res[f"{name}|{vname}"] = {"leave_one_family_out_correct": correct, "n": len(pub), "acc": round(correct / len(pub), 4), "cp95": cp(correct, len(pub)),
                                  "majority_within_family_acc": round(maj / len(pub), 4), "per_family": per}
# most predictive tokens (full-data fit, for human reading only)
v = TfidfVectorizer(ngram_range=(1, 2), min_df=3, sublinear_tf=True); X = v.fit_transform([stem(p["request_text"]) for p in pub]); clf = LogisticRegression(max_iter=3000).fit(X, y)
names = np.array(v.get_feature_names_out()); top = {}
for i, c in enumerate(clf.classes_): top[c] = names[np.argsort(clf.coef_[i])[-12:][::-1]].tolist()
res["top_tokens_full_fit_stem_only"] = top
res["reading"] = "Accuracy near or below the within-family majority rate means wording does not transfer across families as a label cue; high within-family cues are possible and are listed for human review (top tokens)."
json.dump(res, open(out, "w"), indent=1)
for k, v_ in res.items():
    if "|" in k: print(k, v_["acc"], v_["cp95"], "majority", v_["majority_within_family_acc"])
print(top)
