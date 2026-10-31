import hashlib, json, os, subprocess, sys, tempfile
ROOT = os.path.join(os.path.dirname(__file__), "..")
B = os.path.join(ROOT, "scopedesk", "bench", "v1_2")
rd = lambda n: [json.loads(l) for l in open(os.path.join(B, n))]

def test_counts_and_controls():
    pub, key = rd("instances_public.jsonl"), rd("key.jsonl")
    assert len(pub) == len(key) >= 120
    assert len({p["family"] for p in pub}) >= 8
    assert sum(k["verdict"] == "applies" for k in key) / len(key) >= 0.30

def test_every_out_of_scope_has_witness_and_conditions():
    for k in rd("key.jsonl"):
        if k["verdict"] == "out_of_scope":
            assert k["witness"] and k["condition_ids"]

def test_public_file_hides_everything():
    for p in rd("instances_public.jsonl"):
        assert set(p) == {"id", "family", "stratum", "request_text", "tools_allowed"}

def test_hashes_match_and_rebuild_is_deterministic():
    for line in open(os.path.join(B, "KEY.sha256")):
        h, name = line.split()
        assert hashlib.sha256(open(os.path.join(B, name), "rb").read()).hexdigest() == h, name
    with tempfile.TemporaryDirectory() as d:
        subprocess.run([sys.executable, "-I", os.path.join(B, "build.py"), d], check=True, capture_output=True, cwd=B)
        for n in ("key.jsonl", "instances_public.jsonl"):
            assert open(os.path.join(d, n), "rb").read() == open(os.path.join(B, n), "rb").read()

def test_independent_verification_recorded_all_agree():
    v = json.load(open(os.path.join(B, "key_verification.json")))
    assert v["disagreements"] == [] and all(r["n"] == r["agree"] for r in v["per_family"].values())


def test_ids_are_opaque_and_payload_is_request_text_only():
    pub = rd("instances_public.jsonl"); pay = {p["id"]: p for p in rd("model_payload.jsonl")}
    assert all(__import__("re").fullmatch(r"q[0-9a-f]{8}", p["id"]) for p in pub)
    assert all(set(pay[p["id"]]) == {"id", "prompt"} and pay[p["id"]]["prompt"] == p["request_text"] for p in pub)
    full = rd("instances_full.jsonl")
    assert all("legacy_id" in f["hidden"] for f in full)

def test_diagnosis_fields_complete_for_synergy_and_nonkpp():
    key = {k["id"]: k for k in rd("key.jsonl")}
    for f in rd("instances_full.jsonl"):
        s = f["hidden"]["structured"]
        if f["family"] == "hamilton_rule_form" and s["d"] != "0":
            assert "HAMILTON_NONADDITIVE" in key[f["id"]]["violated_conditions"]
