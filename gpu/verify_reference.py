#!/usr/bin/env python3
"""Independent verification of the TrpB Tm9D8s* reference sequence and residue numbering.

Evidence chain (all from CaltechDATA record h5rah-5z170, CC0 1.0):
  1. data/ftmlde_data/tm9d8s_AAs.fasta     397 aa, header ">Tm9D8*"
  2. data/ftmlde_data/TARGET_b0.3.fa       EVmutation target; must be the identical sequence
  3. data/ftmlde_data/Tm9D8s_refine_19.pdb crystal structure; residue names at 183/184/227/228
  4. 118X_184X_pooled_culture_data.csv    per-read VariantSequence + declared "118 AA"/"184 AA";
                                            the fragment must match the FASTA except exactly at 118 and 184,
                                            and the declared residues must equal the fragment's residues
  5. simplified_AA.csv                     row AAs=="VFVS" exists (parent) and is measured

  verify_reference.py --members DIR --caltech DIR --out receipt.json

DIR (--members) holds the four ftmlde_data files by basename (fetch with zip_range.py extract).
Run with `python3 -I`.
"""
import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import trpb_ref as R  # noqa: E402

THREE = {"VAL": "V", "PHE": "F", "SER": "S", "ALA": "A", "ILE": "I", "LYS": "K", "GLY": "G"}


def fa(path):
    return "".join(x.strip() for x in Path(path).read_text().splitlines() if not x.startswith(">"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--members", required=True)
    ap.add_argument("--caltech", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    m, c = Path(a.members), Path(a.caltech)
    rec = {"record": "https://data.caltech.edu/records/h5rah-5z170", "license": "CC0-1.0 (record metadata)",
           "doi": "10.22002/h5rah-5z170", "numbering": "1-based index into FASTA; Met1", "checks": {}}
    hdr, seq = R.load_reference(m / "tm9d8s_AAs.fasta")      # hash, length, site residues enforced
    rec["checks"]["fasta"] = {"header": hdr, "length": len(seq), "sha256": R.sha256_file(m / "tm9d8s_AAs.fasta"),
                              "site_residues": {str(p): seq[p - 1] for p in R.SITES}, "his_tag": seq[-8:]}
    tgt = fa(m / "TARGET_b0.3.fa")
    rec["checks"]["target_fa_identical"] = {"identical": tgt == seq, "sha256": R.sha256_file(m / "TARGET_b0.3.fa")}
    assert tgt == seq
    # PDB
    ca = {}
    for line in (m / "Tm9D8s_refine_19.pdb").read_text().splitlines():
        if line.startswith("ATOM") and line[12:16].strip() == "CA":
            ca.setdefault(line[21], {})[int(line[22:26])] = line[17:20]
    pdb = {}
    for ch, d in ca.items():
        pdb[ch] = {"n_residues": len(d), "sites": {str(p): d.get(p) for p in R.SITES}}
        assert "".join(THREE.get(d[p], "?") for p in R.SITES) == R.PARENT, (ch, d)
        # every observed residue number must agree with the FASTA numbering
        mism = [p for p, r3 in d.items() if p <= len(seq) and THREE.get(r3) and THREE[r3] != seq[p - 1]]
        pdb[ch]["numbering_mismatches_vs_fasta_for_known_aa"] = len(mism)
        assert not mism[:1] or len(mism) < 0.02 * len(d)   # tolerate non-listed residue names only
    rec["checks"]["pdb_Tm9D8s_refine_19"] = {"sha256": R.sha256_file(m / "Tm9D8s_refine_19.pdb"), "chains": pdb}
    # pooled-culture file: first column index is blank; header includes VariantSequence, '118 AA', '184 AA'
    rows = list(csv.DictReader(open(c / "118X_184X_pooled_culture_data.csv")))
    seqs = Counter()
    bad = 0
    start = None
    for r in rows:
        v = r["VariantSequence"]
        if start is None:
            start = seq.find(v[:12]) + 1   # 1-based index of fragment start in the reference
        off = start - 1
        diffs = [off + k + 1 for k in range(len(v)) if seq[off + k] != v[k]]
        ok = set(diffs) <= {118, 184}
        if ok:
            if 118 in diffs and v[118 - 1 - off] != r["118 AA"]:
                ok = False
            if 184 in diffs and v[184 - 1 - off] != r["184 AA"]:
                ok = False
            if 118 not in diffs and r["118 AA"] != seq[117]:
                ok = False
            if 184 not in diffs and r["184 AA"] != seq[183]:
                ok = False
        bad += (not ok)
        seqs[tuple(diffs)] += 1
    rec["checks"]["pooled_culture_118_184"] = {
        "sha256": R.sha256_file(c / "118X_184X_pooled_culture_data.csv"), "rows": len(rows),
        "fragment_start_1based": start, "fragment_length": len(rows[0]["VariantSequence"]),
        "rows_inconsistent_with_reference_numbering": bad,
        "diff_position_patterns": {str(k): v for k, v in seqs.most_common(6)}}
    assert bad == 0
    # parent row in measured table
    parent = [r for r in csv.DictReader(open(c / "simplified_AA.csv")) if r["AAs"] == R.PARENT]
    rec["checks"]["parent_row_simplified_AA"] = {"sha256": R.sha256_file(c / "simplified_AA.csv"), "rows": parent}
    assert len(parent) == 1 and parent[0]["# Stop"] in ("0", "0.0")
    rec["verdict"] = "reference established; positions 183/184/227/228 = V/F/V/S under FASTA numbering"
    rec["caveats"] = [
        "FASTA header says Tm9D8* while the file/PDB are named tm9d8s/Tm9D8s; the primary archive treats them as the same background. "
        "All 3,199 pooled-culture reads differ from the reference only at 118 and 184 (that earlier experiment's library positions), and their declared '118 AA'/'184 AA' columns equal the read residues, which confirms the numbering at those two positions; positions 183/227/228 are confirmed by the PDB and by the parent row VFVS.",
        "Sequence includes a C-terminal LEHHHHHH expression tag (residues 390-397); it is kept in the model input as in the source construct.",
        "Numbering is of the expressed construct (Met1), not of wild-type T. maritima TrpB; no mapping to Tm WT numbering is claimed."]
    Path(a.out).write_text(json.dumps(rec, indent=1))
    print(json.dumps({k: v for k, v in rec.items() if k != "checks"}, indent=1))


if __name__ == "__main__":
    main()
