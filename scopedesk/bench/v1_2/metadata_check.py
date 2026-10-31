"""One-command metadata check for the v1.2 candidate (critic). Anyone (Codex, director) can run it from a clean checkout:
  python3 -I scopedesk/bench/v1_2/metadata_check.py OUT.json
Checks: every KEY.sha256 line matches its file; ids unique, opaque (q+8 hex) and identical across public/full/key/payload; payload == request_text and has only {id,prompt};
no hidden field in the public file; every out_of_scope key has witness+conditions; benign share >= 30%; item count >= 120; >= 8 families; excluded ids absent (legacy map);
violated_conditions present for Hamilton items with synergy; request texts end with the conventions block and contain no 'form a Turing pattern' question; model_payload contains no
key/hidden field names. Exit 0 iff all pass. Does NOT re-run any scientific computation."""
import hashlib, json, os, re, sys
D = os.path.dirname(os.path.abspath(__file__))
rd = lambda n: [json.loads(l) for l in open(os.path.join(D, n))]
checks = {}
def chk(name, ok, detail=""): checks[name] = {"ok": bool(ok), "detail": detail}
bad = []
for line in open(os.path.join(D, "KEY.sha256")):
    h, name = line.split()
    p = os.path.join(D, name)
    if not os.path.exists(p) or hashlib.sha256(open(p, "rb").read()).hexdigest() != h: bad.append(name)
chk("manifest_hashes_match", not bad, bad)
pub, full, key, pay = rd("instances_public.jsonl"), rd("instances_full.jsonl"), rd("key.jsonl"), rd("model_payload.jsonl")
ids = [p["id"] for p in pub]
chk("ids_unique_opaque", len(set(ids)) == len(ids) and all(re.fullmatch(r"q[0-9a-f]{8}", i) for i in ids))
chk("id_sets_align", set(ids) == {f["id"] for f in full} == {k["id"] for k in key} == {p["id"] for p in pay})
chk("payload_is_prompt_only", all(set(p) == {"id", "prompt"} for p in pay) and {p["id"]: p["prompt"] for p in pay} == {p["id"]: p["request_text"] for p in pub})
chk("public_has_no_hidden", all(set(p) == {"id", "family", "stratum", "request_text", "tools_allowed"} for p in pub))
chk("oos_have_witness_and_conditions", all(k["witness"] and k["condition_ids"] for k in key if k["verdict"] == "out_of_scope"))
n = len(key); chk("count_ge_120", n >= 120, n)
chk("benign_ge_30pct", sum(k["verdict"] == "applies" for k in key) / n >= 0.30, round(sum(k["verdict"] == "applies" for k in key) / n, 3))
chk("families_ge_8", len({p["family"] for p in pub}) >= 8, sorted({p["family"] for p in pub}))
idmap = json.load(open(os.path.join(D, "id_map_PRIVATE.json"))); inv = {v: k for k, v in idmap.items()}
excl = json.load(open(os.path.join(D, "excluded.json")))
exl_legacy = {e["params"].get("id") for e in excl if "id" in e["params"]}
chk("excluded_legacy_ids_absent", not (exl_legacy & {inv[i] for i in ids if i in inv}), sorted(exl_legacy))
byid = {f["id"]: f for f in full}
chk("hamilton_synergy_diagnosis", all("HAMILTON_NONADDITIVE" in k["violated_conditions"] for k in key if byid[k["id"]]["family"] == "hamilton_rule_form" and byid[k["id"]]["hidden"]["structured"]["d"] != "0"))
chk("all_prompts_end_with_conventions", all(" Conventions:" in p["request_text"] and p["request_text"].rstrip().endswith("Do not assume values that are not stated.") for p in pub))
chk("no_pattern_formation_question", not any(re.search(r"form a Turing pattern|stripes will", p["request_text"]) for p in pub))
chk("no_key_words_in_payload", not any(re.search(r"legacy_id|\"verdict\"|witness|expected_repairs|hidden", p["prompt"]) for p in pay))
res = {"all_ok": all(c["ok"] for c in checks.values()), "n_items": n, "checks": checks, "key_sha256": hashlib.sha256(open(os.path.join(D, "key.jsonl"), "rb").read()).hexdigest()}
json.dump(res, open(sys.argv[1] if len(sys.argv) > 1 else os.path.join(D, "metadata_check_receipt.json"), "w"), indent=1)
print(json.dumps({k: v["ok"] for k, v in checks.items()}), "ALL_OK" if res["all_ok"] else "FAIL")
sys.exit(0 if res["all_ok"] else 1)
