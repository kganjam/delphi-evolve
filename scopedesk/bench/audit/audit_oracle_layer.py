"""Audit (critic, 2026-10-31) of the Scope Desk oracle layer scopedesk/oracles (rethink-nca, read-only import) against the frozen/draft bench key.
Compares oracles.linear.check(structured)['scope_verdict'] and condition_ids with the key for the turing_finite_domain and turing_2d_rectangle families,
and oracles.gate.wavelength_licence(structured) with the wavelength family. Disagreements are listed, not 'fixed'. Usage: python3 -I audit_oracle_layer.py ORACLE_CHECKOUT BENCH_V_DIR OUT.json"""
import json, sys
root, bench, out = sys.argv[1:4]
sys.path.insert(0, root)
from scopedesk.oracles import linear, gate
full = [json.loads(l) for l in open(f"{bench}/instances_full.jsonl")]; key = {json.loads(l)["id"]: json.loads(l) for l in open(f"{bench}/key.jsonl")}
rows = []
for it in full:
    fam = it["family"]; s = it["hidden"]["structured"]; k = key[it["id"]]
    try:
        if fam in ("turing_finite_domain", "turing_2d_rectangle"):
            r = linear.check(s); v = r["scope_verdict"]; c = r.get("condition_ids", [])
        elif fam == "wavelength_formula_licence":
            r = gate.wavelength_licence(s); v = r.get("verdict") or r.get("scope_verdict"); c = r.get("condition_ids", [])
        else: continue
    except Exception as e:
        v, c, r = "error:" + repr(e)[:80], [], {}
    rows.append({"id": it["id"], "family": fam, "key": k["verdict"], "oracle": v, "key_cond": k["condition_ids"], "oracle_cond": c, "agree": v == k["verdict"], "cond_agree": sorted(c) == sorted(k["condition_ids"])})
res = {"bench_dir": bench, "n": len(rows), "agree": sum(r["agree"] for r in rows), "cond_agree": sum(r["cond_agree"] for r in rows),
       "by_family": {f: [sum(r["agree"] for r in rows if r["family"] == f), sum(r["family"] == f for r in rows)] for f in sorted({r["family"] for r in rows})},
       "disagreements": [r for r in rows if not r["agree"]], "cond_disagreements": [r for r in rows if r["agree"] and not r["cond_agree"]][:20]}
json.dump(res, open(out, "w"), indent=1)
print({k: v for k, v in res.items() if k not in ("disagreements", "cond_disagreements")}); [print(r) for r in res["disagreements"][:15]]
print("cond disagreements:", len(res["cond_disagreements"]))
