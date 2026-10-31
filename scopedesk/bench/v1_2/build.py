"""Assemble the frozen Scope Desk bench. Usage: python3 -I build.py OUTDIR  (writes instances_full/public, key, excluded, split, KEY.sha256)."""
import hashlib, json, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collections import Counter
import common, conventions, fam_turing, fam_turing2d, fam_wavelength, fam_kimura, fam_hawkdove, fam_greenhill, fam_hamilton, fam_kpp

FAMS = [(fam_turing, 24), (fam_wavelength, 16), (fam_turing2d, 16), (fam_kimura, 16), (fam_hawkdove, 16),
        (fam_greenhill, 16), (fam_hamilton, 16), (fam_kpp, 16)]
DEV_FAMILIES = ["turing_finite_domain", "hawk_dove_ess"]          # prompt tuning allowed here only; all others are held out
SEED = 20261031
DROP_IDS = {"wl-0010": "near-tie between adjacent admissible modes (n=9 vs n=8, growth rates differ by 0.3%) whose wavelengths fall on opposite sides of the 10% criterion; blinded audit flagged it", "ts-0007": "false-premise Turing item: the requester's claim that the inequality holds is false, no mode grows; the verdict depends on whether the question 'does the condition give the right answer' is read as existence of a mode (out_of_scope) or as correctness of the condition (applies). Blinded payload-only audit read applies, key says out_of_scope: genuine convention ambiguity.", "ts-0017": "false-premise Turing item (same pattern as qd03269c6).", "t2-0010": "false-premise Turing 2-D item (same pattern as qd03269c6).", "wl-0001": "wavelength item where 'fastest-growing' read as max real part of the eigenvalues vs most negative determinant flips the verdict (blinded audit flag); convention not pinned in the text.", "gh-0016": "uniform column with density unlisted: relabelled applies on the argument that the printed 0.788 coefficient and the exact value 0.78828 agree to 0.04%, but the literal printed coefficient and the exact constant give opposite buckling predictions at specific densities (Codex witness rho=822.256954 kg/m3 for gh-0016); neither the exact-constant convention nor a constrained completion was declared, so the item is excluded", "gh-0004": "uniform column with density unlisted: relabelled applies on the argument that the printed 0.788 coefficient and the exact value 0.78828 agree to 0.04%, but the literal printed coefficient and the exact constant give opposite buckling predictions at specific densities (Codex witness rho=822.256954 kg/m3 for gh-0016); neither the exact-constant convention nor a constrained completion was declared, so the item is excluded", "gh-0012": "uniform column with density unlisted: relabelled applies on the argument that the printed 0.788 coefficient and the exact value 0.78828 agree to 0.04%, but the literal printed coefficient and the exact constant give opposite buckling predictions at specific densities (Codex witness rho=822.256954 kg/m3 for gh-0016); neither the exact-constant convention nor a constrained completion was declared, so the item is excluded", "ts-0016": "exact marginal admissible mode: Dirichlet, det(J-qD)=0 at q=1/4, so the linearisation is inconclusive and the key's strict-growth convention (out_of_scope) is a convention choice; dx-collab's reviewed service returns 'unresolved'. Excluded (same family of defect as det J=0). A scan of all Turing 1-D/2-D items found two further items with a marginal mode (t2-0008, t2-0014) whose verdict 'applies' rests on a different, strictly growing mode, so they are retained."}

def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()

def build():
    allitems = []
    for i, (mod, n) in enumerate(FAMS):
        rng = random.Random(SEED + i)
        allitems += mod.make(rng, n, 1)
    # stable shuffle so position in the file is not label-bearing; ids stay family-prefixed
    random.Random(SEED).shuffle(allitems)
    for pub, full, key in allitems:
        if pub['id'] in DROP_IDS: common.exclude(pub['family'], DROP_IDS[pub['id']], {'id': pub['id']})
    allitems = [t for t in allitems if t[0]['id'] not in DROP_IDS]
    import hashlib as _h
    idmap = {}
    for pub, full, key in allitems:      # v1.2: opaque public ids independent of generator order and label
        old = pub['id']; new = 'q' + _h.sha256(f'{SEED}:{old}'.encode()).hexdigest()[:8]
        assert new not in idmap.values(); idmap[old] = new
        pub['id'] = new; full['id'] = new; key['id'] = new; full['hidden']['legacy_id'] = old
    common.IDMAP = idmap
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
    w("model_payload.jsonl", [{'id': p['id'], 'prompt': p['request_text']} for p in pub])   # the EXACT text a model receives; nothing else
    json.dump(common.EXCLUDED, open(f"{out}/excluded.json", "w"), indent=1)
    json.dump({'COMMON': conventions.COMMON, 'CONV': conventions.CONV}, open(f"{out}/conventions.json", "w"), indent=1)
    split = {"dev_families": DEV_FAMILIES, "heldout_families": sorted({p["family"] for p in pub} - set(DEV_FAMILIES)),
             "rule": "prompt/harness tuning only on dev families; report held-out families separately; headline numbers are family-clustered"}
    split['mechanism_groups'] = {'linear_reaction_diffusion_stability': ['turing_finite_domain', 'turing_2d_rectangle', 'wavelength_formula_licence']}
    split['grouping_note'] = 'The 1-D Turing, 2-D Turing and wavelength families share the same Jacobian/mode mathematics. Report the 8-family analysis AND the 6-group analysis (these three merged); dev=turing_finite_domain, hawk_dove_ess means the other two reaction-diffusion families are within-mechanism transfer, not unseen-mechanism generalisation.'
    json.dump(split, open(f"{out}/split.json", "w"), indent=1)
    json.dump(common.IDMAP, open(f"{out}/id_map_PRIVATE.json", "w"), indent=1)
    with open(f"{out}/KEY.sha256", "w") as f:
        src = os.path.dirname(os.path.abspath(__file__))
        for p in ("key.jsonl", "instances_public.jsonl", "instances_full.jsonl", "excluded.json", "split.json", "conventions.json", "id_map_PRIVATE.json", "model_payload.jsonl"):
            f.write(f"{sha(f'{out}/{p}')}  {p}\n")
        for p in ("build.py", "common.py", "conventions.py") + tuple(f"{m.__name__}.py" for m, _ in FAMS):
            f.write(f"{sha(f'{src}/{p}')}  {p}\n")
    vc = Counter(k["verdict"] for k in keys); fc = Counter(p["family"] for p in pub)
    print("n", len(keys), dict(vc), "benign_frac", round(vc["applies"] / len(keys), 3), dict(fc), "excluded", len(common.EXCLUDED))
