"""Assemble the frozen Scope Desk bench. Usage: python3 -I build.py OUTDIR  (writes instances_full/public, key, excluded, split, KEY.sha256)."""
import hashlib, json, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collections import Counter
import common, conventions, fam_turing, fam_turing2d, fam_wavelength, fam_kimura, fam_hawkdove, fam_greenhill, fam_hamilton, fam_kpp

FAMS = [(fam_turing, 24), (fam_wavelength, 16), (fam_turing2d, 16), (fam_kimura, 16), (fam_hawkdove, 16),
        (fam_greenhill, 16), (fam_hamilton, 16), (fam_kpp, 16)]
DEV_FAMILIES = ["turing_finite_domain", "hawk_dove_ess"]          # prompt tuning allowed here only; all others are held out
SEED = 20261031

def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()

def build():
    allitems = []
    for i, (mod, n) in enumerate(FAMS):
        rng = random.Random(SEED + i)
        allitems += mod.make(rng, n, 1)
    # stable shuffle so position in the file is not label-bearing; ids stay family-prefixed
    random.Random(SEED).shuffle(allitems)
    for pub, full, key in allitems:      # v1.1: every request carries its declared target and conventions
        txt = pub['request_text'] + ' ' + conventions.CONV[pub['family']] + ' ' + conventions.COMMON
        pub['request_text'] = txt; full['request_text'] = txt
    return allitems

if __name__ == "__main__":
    out = sys.argv[1]
    items = build()
    pub = [p for p, _, _ in items]; full = [f for _, f, _ in items]; keys = [k for _, _, k in items]
    ids = [p["id"] for p in pub]; assert len(ids) == len(set(ids))
    w = lambda name, rows: open(f"{out}/{name}", "w").write("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
    w("instances_public.jsonl", pub); w("instances_full.jsonl", full); w("key.jsonl", keys)
    json.dump(common.EXCLUDED, open(f"{out}/excluded.json", "w"), indent=1)
    json.dump({'COMMON': conventions.COMMON, 'CONV': conventions.CONV}, open(f"{out}/conventions.json", "w"), indent=1)
    split = {"dev_families": DEV_FAMILIES, "heldout_families": sorted({p["family"] for p in pub} - set(DEV_FAMILIES)),
             "rule": "prompt/harness tuning only on dev families; report held-out families separately; headline numbers are family-clustered"}
    json.dump(split, open(f"{out}/split.json", "w"), indent=1)
    with open(f"{out}/KEY.sha256", "w") as f:
        src = os.path.dirname(os.path.abspath(__file__))
        for p in ("key.jsonl", "instances_public.jsonl", "instances_full.jsonl", "excluded.json", "split.json", "conventions.json"):
            f.write(f"{sha(f'{out}/{p}')}  {p}\n")
        for p in ("build.py", "common.py", "conventions.py") + tuple(f"{m.__name__}.py" for m, _ in FAMS):
            f.write(f"{sha(f'{src}/{p}')}  {p}\n")
    vc = Counter(k["verdict"] for k in keys); fc = Counter(p["family"] for p in pub)
    print("n", len(keys), dict(vc), "benign_frac", round(vc["applies"] / len(keys), 3), dict(fc), "excluded", len(common.EXCLUDED))
