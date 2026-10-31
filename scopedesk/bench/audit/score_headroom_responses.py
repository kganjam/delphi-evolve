"""Critic's independent scoring of dx-guilds' unguarded-arm (arm U) per-item verdicts against the frozen v1.2 key. Models had NO code tool and one call per item with only the model-visible prompt:
a measure of judgement, not derivation. Copies of the response files are in headroom_unguarded/ (originals untracked in the guilds worktree). Different-family = gemini-3.8-flash;
claude = Sonnet 5.5 (same family as the key's author). Usage: python3 -I score_headroom_responses.py OUT.json"""
import json, hashlib, os, sys
from collections import Counter
from scipy.stats import beta
D = os.path.dirname(os.path.abspath(__file__)); B = os.path.join(D, "..", "v1_2")
cp = lambda k, n: [round(0.0 if k == 0 else float(beta.ppf(.025, k, n - k + 1)), 3), round(1.0 if k == n else float(beta.ppf(.975, k + 1, n - k)), 3)]
key = {json.loads(l)["id"]: json.loads(l)["verdict"] for l in open(os.path.join(B, "key.jsonl"))}
fam = {json.loads(l)["id"]: json.loads(l)["family"] for l in open(os.path.join(B, "instances_public.jsonl"))}
dev = set(json.load(open(os.path.join(B, "split.json")))["dev_families"])
res = {"key_sha256": hashlib.sha256(open(os.path.join(B, "key.jsonl"), "rb").read()).hexdigest(), "caveat": "arm U: single call per item, no tools; agreement with the key is item-level (items within a family are not independent; effective n = 8 families); not blinded to nothing - the models saw only the prompt; scored by the key's author"}
for m in ("claude", "gemini"):
    rows = [json.loads(l) for l in open(os.path.join(D, "headroom_unguarded", f"responses_{m}.jsonl"))]
    run = json.load(open(os.path.join(D, "headroom_unguarded", f"RUN_{m}.json")))
    assert set(r["id"] for r in rows) == set(key), "id sets differ"
    assert run["payload_sha256"] == "6c571db13a63d5dc8e8b5e5fadda601471f9a0a4fad6053f798395a48f78ee42"
    pred = {r["id"]: (r["verdict"] if r.get("ok") and r.get("verdict") in ("applies", "out_of_scope", "underdetermined") else None) for r in rows}
    def agg(ids):
        ans = [i for i in ids if pred[i] is not None]; ok = sum(pred[i] == key[i] for i in ans); n = len(ids)
        return {"N": n, "answered": len(ans), "agree": ok, "agree_over_N_cp95": [ok / n, cp(ok, n)], "selective_risk": (round(1 - ok / len(ans), 3) if ans else None)}
    ids = list(key); res[m] = {"served_model": rows[0].get("served_model"), "family_verified": rows[0].get("family_verified"), "tokens_total": run["tokens"], "overall": agg(ids),
        "heldout": agg([i for i in ids if fam[i] not in dev]), "dev": agg([i for i in ids if fam[i] in dev]), "by_family": {f: agg([i for i in ids if fam[i] == f]) for f in sorted(set(fam.values()))},
        "by_gold": {g: agg([i for i in ids if key[i] == g]) for g in ("applies", "out_of_scope", "underdetermined")},
        "confusion_gold_x_pred": {f"{key[i]}|{pred[i]}": c for (i, c) in [(i, 0) for i in ids]} if False else dict(Counter(f"{key[i]}|{pred[i]}" for i in ids)),
        "disagreements": [{"id": i, "family": fam[i], "gold": key[i], "pred": pred[i]} for i in ids if pred[i] != key[i]]}
both = [i for i in key]
res["models_disagree_with_each_other"] = sum(1 for i in key if {r["id"]: r["verdict"] for r in map(json.loads, open(os.path.join(D, "headroom_unguarded", "responses_claude.jsonl")))}[i] != {r["id"]: r["verdict"] for r in map(json.loads, open(os.path.join(D, "headroom_unguarded", "responses_gemini.jsonl")))}[i])
json.dump(res, open(sys.argv[1], "w"), indent=1)
for m in ("claude", "gemini"):
    o = res[m]["overall"]; print(m, res[m]["served_model"], "agree", o["agree"], "/", o["N"], o["agree_over_N_cp95"], "answered", o["answered"], "heldout", res[m]["heldout"]["agree"], "/", res[m]["heldout"]["N"])
    print("  by family:", {f: f'{v["agree"]}/{v["N"]}' for f, v in res[m]["by_family"].items()})
    print("  by gold:", {g: f'{v["agree"]}/{v["N"]}' for g, v in res[m]["by_gold"].items()})
print("models disagree with each other on", res["models_disagree_with_each_other"], "items")
