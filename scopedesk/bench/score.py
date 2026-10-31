"""Score baselines against the key. Exact Clopper-Pearson 95% intervals; family-clustered view reported separately. Usage: python3 -I score.py BENCHDIR OUT.json"""
import json, os, sys
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scipy.stats import beta
import baselines

def cp(k, n, a=0.05):
    if n == 0: return [None, None]
    return [0.0 if k == 0 else float(beta.ppf(a / 2, k, n - k + 1)), 1.0 if k == n else float(beta.ppf(1 - a / 2, k + 1, n - k))]

def acc(rows):
    k = sum(r["ok"] for r in rows); n = len(rows)
    return {"correct": k, "n": n, "acc": round(k / n, 4) if n else None, "cp95": [None if x is None else round(x, 4) for x in cp(k, n)]}

def fmt_features(i, inst):
    t = inst["request_text"]
    return [len(t), sum(c.isdigit() for c in t), t.count(","), i % 2]

def main(d, out):
    pub = [json.loads(l) for l in open(f"{d}/instances_public.jsonl")]; key = {json.loads(l)["id"]: json.loads(l) for l in open(f"{d}/key.jsonl")}
    full = {json.loads(l)["id"]: json.loads(l) for l in open(f"{d}/instances_full.jsonl")}
    split = json.load(open(f"{d}/split.json")); dev = set(split["dev_families"])
    res = {}
    for name, fn in (("B0_scope_gate", baselines.predict_B0), ("R_retrieval_always_applies", baselines.predict_R)):
        rows = []
        for p in pub:
            pred = fn(p); k = key[p["id"]]
            rows.append({"id": p["id"], "family": p["family"], "tset": full[p["id"]]["hidden"]["template_set"], "ok": pred == k["verdict"], "pred": pred, "truth": k["verdict"]})
        res[name] = {"all": acc(rows), "template_A": acc([r for r in rows if r["tset"] == "A"]), "template_B": acc([r for r in rows if r["tset"] == "B"]),
                     "by_family": {f: acc([r for r in rows if r["family"] == f]) for f in sorted({r["family"] for r in rows})},
                     "by_truth": {v: acc([r for r in rows if r["truth"] == v]) for v in ("applies", "out_of_scope", "underdetermined")},
                     "false_alarm_rate_on_applies": {"false_alarms": sum(r["pred"] != "applies" for r in rows if r["truth"] == "applies"), "n": sum(r["truth"] == "applies" for r in rows)}}
    # format-only: train on dev families (nearest-centroid on length/digits), test on held-out; compare with majority class of held-out
    import numpy as np
    X = np.array([fmt_features(i, p) for i, p in enumerate(pub)], float); y = np.array([key[p["id"]]["verdict"] for p in pub]); fam = np.array([p["family"] for p in pub])
    tr = np.isin(fam, list(dev)); te = ~tr
    mu, sd = X[tr].mean(0), X[tr].std(0) + 1e-9
    cents = {c: ((X[tr][y[tr] == c] - mu) / sd).mean(0) for c in set(y[tr])}
    pred = np.array([min(cents, key=lambda c: np.linalg.norm((x - mu) / sd - cents[c])) for x in X[te]])
    maj = Counter(y[te]).most_common(1)[0]
    res["FMT_format_only_trained_on_dev_tested_heldout"] = {"acc": acc([{"ok": bool(a == b)} for a, b in zip(pred, y[te])]),
                                                           "majority_class_rate_heldout": {"class": maj[0], "rate": round(maj[1] / te.sum(), 4)},
                                                           "note": "must not clearly exceed majority rate; interval shown for the classifier accuracy"}
    json.dump(res, open(out, "w"), indent=1)
    for k, v in res.items():
        print(k, {a: b for a, b in v.items() if a in ("all", "template_A", "template_B", "acc", "majority_class_rate_heldout")})

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
