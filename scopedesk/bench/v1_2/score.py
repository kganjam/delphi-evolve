"""Score baselines against the key with answer/abstain separation (critic). Statuses: answered | abstained (B0 parse failure / no answer). Reports coverage,
selective risk (undefined when nothing answered), false acceptance, false refusal, constant policies incl. always-abstain; exact Clopper-Pearson 95% intervals.
Utility is NOT computed here: costs must be preregistered by the arms owner. Usage: python3 -I score.py BENCHDIR OUT.json"""
import json, os, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scipy.stats import beta
import numpy as np
import baselines

def cp(k, n, a=0.05):
    if n == 0: return [None, None]
    return [round(0.0 if k == 0 else float(beta.ppf(a / 2, k, n - k + 1)), 4), round(1.0 if k == n else float(beta.ppf(1 - a / 2, k + 1, n - k)), 4)]

def summarize(rows):
    N = len(rows); ans = [r for r in rows if r["pred"] is not None]; A = len(ans); E = sum(r["pred"] != r["truth"] for r in ans)
    conf = Counter((r["truth"], r["pred"] if r["pred"] is not None else "ABSTAIN") for r in rows)
    fa = sum(r["pred"] == "applies" and r["truth"] != "applies" for r in rows); nonapp = sum(r["truth"] != "applies" for r in rows)
    app = [r for r in rows if r["truth"] == "applies"]; frej = sum(r["pred"] in ("out_of_scope", "underdetermined") for r in app); fabs = sum(r["pred"] is None for r in app)
    return {"N": N, "answered": A, "abstained": N - A, "coverage": round(A / N, 4), "coverage_cp95": cp(A, N),
            "errors_among_answered": E, "selective_risk": (round(E / A, 4) if A else None), "selective_risk_cp95": (cp(E, A) if A else None),
            "accuracy_over_all_N_counting_abstain_as_wrong": round((A - E) / N, 4),
            "false_acceptance(answered applies on gold out_of_scope/underdetermined)": {"count": fa, "denominator": nonapp},
            "false_refusal(gold applies answered out_of_scope/underdetermined)": {"count": frej, "denominator": len(app)}, "abstained_on_gold_applies": fabs,
            "confusion_truth_x_pred": {f"{a}|{b}": c for (a, b), c in sorted(conf.items())}}

def fmt_features(i, inst):
    t = inst["request_text"]; return [len(t), sum(c.isdigit() for c in t), t.count(","), i % 2]

def main(d, out):
    pub = [json.loads(l) for l in open(f"{d}/instances_public.jsonl")]; key = {json.loads(l)["id"]: json.loads(l) for l in open(f"{d}/key.jsonl")}
    full = {json.loads(l)["id"]: json.loads(l) for l in open(f"{d}/instances_full.jsonl")}
    dev = set(json.load(open(f"{d}/split.json"))["dev_families"])
    pols = {"B0_scope_gate(inputs: request text + family metadata; parse failure => abstain)": baselines.predict_B0, "constant_always_applies": lambda p: "applies",
            "constant_always_out_of_scope": lambda p: "out_of_scope", "constant_always_underdetermined(an ANSWER, not abstention)": lambda p: "underdetermined", "always_abstain": lambda p: None}
    res = {}
    for name, fn in pols.items():
        rows = [{"id": p["id"], "family": p["family"], "tset": full[p["id"]]["hidden"]["template_set"], "truth": key[p["id"]]["verdict"], "pred": fn(p)} for p in pub]
        res[name] = {"all": summarize(rows), "template_A": summarize([r for r in rows if r["tset"] == "A"]), "template_B": summarize([r for r in rows if r["tset"] == "B"]),
                     "heldout_families": summarize([r for r in rows if r["family"] not in dev]), "by_family": {f: summarize([r for r in rows if r["family"] == f]) for f in sorted({r["family"] for r in rows})}}
    X = np.array([fmt_features(i, p) for i, p in enumerate(pub)], float); y = np.array([key[p["id"]]["verdict"] for p in pub]); fam = np.array([p["family"] for p in pub])
    tr = np.isin(fam, list(dev)); te = ~tr; mu, sd = X[tr].mean(0), X[tr].std(0) + 1e-9
    cents = {c: ((X[tr][y[tr] == c] - mu) / sd).mean(0) for c in set(y[tr])}
    pred = np.array([min(cents, key=lambda c: np.linalg.norm((x - mu) / sd - cents[c])) for x in X[te]]); k = int((pred == y[te]).sum()); maj = Counter(y[te]).most_common(1)[0]
    res["format_only_nearest_centroid_trained_on_dev_tested_heldout"] = {"correct": k, "n": int(te.sum()), "acc": round(k / te.sum(), 4), "cp95": cp(k, int(te.sum())), "majority_class": str(maj[0]), "majority_rate": round(maj[1] / te.sum(), 4)}
    json.dump(res, open(out, "w"), indent=1)
    for n, v in res.items():
        if isinstance(v, dict) and "all" in v: print(n[:60], {a: v["all"][a] for a in ("N", "answered", "coverage", "selective_risk")}, "heldout cov", v["heldout_families"]["coverage"])
    print("format-only", res["format_only_nearest_centroid_trained_on_dev_tested_heldout"])

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
