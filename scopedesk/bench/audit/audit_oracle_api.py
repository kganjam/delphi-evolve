"""Run the SPEC.md oracle API against the Scope Desk key once scopedesk/oracles exists.
Expects oracles.linear.check(structured) -> {"verdict": ..., "admissible_unstable_modes": [...], ...} where the verdict vocabulary is mapped here:
unstable/linearly_unstable -> applies ; stable -> out_of_scope ; refusals are recorded, not scored. Usage: python3 -I audit_oracle_api.py ORACLE_CHECKOUT OUT.json [BENCHDIR]"""
import importlib, json, os, sys
root, out = sys.argv[1], sys.argv[2]; bench = sys.argv[3] if len(sys.argv) > 3 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, root)
try:
    lin = importlib.import_module("scopedesk.oracles.linear")
except Exception as e:
    print("scopedesk.oracles.linear not importable:", repr(e)); json.dump({"status": "oracle layer absent", "error": repr(e)}, open(out, "w")); sys.exit(2)
full = [json.loads(l) for l in open(f"{bench}/instances_full.jsonl")]; key = {json.loads(l)["id"]: json.loads(l) for l in open(f"{bench}/key.jsonl")}
rows = []
for it in full:
    if it["family"] != "turing_finite_domain": continue
    s = it["hidden"]["structured"]
    try: r = lin.check(s); v = r.get("verdict")
    except Exception as e: r, v = {"error": repr(e)}, "error"
    m = {"unstable": "applies", "linearly_unstable": "applies", "stable": "out_of_scope"}.get(v, "refused:" + str(v))
    rows.append({"id": it["id"], "bc": s["bc"], "key": key[it["id"]]["verdict"], "oracle": v, "mapped": m, "agree": m == key[it["id"]]["verdict"]})
res = {"n": len(rows), "agree": sum(r["agree"] for r in rows), "rows": rows, "note": "refusals (BC variants) are listed, judge them against the oracle's documented scope"}
json.dump(res, open(out, "w"), indent=1); print(res["agree"], "/", res["n"])
