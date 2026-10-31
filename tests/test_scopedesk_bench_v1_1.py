import hashlib, json, os, subprocess, sys, tempfile
ROOT = os.path.join(os.path.dirname(__file__), "..")
B = os.path.join(ROOT, "scopedesk", "bench", "v1_1")
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
