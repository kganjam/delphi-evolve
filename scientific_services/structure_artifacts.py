"""Turn the downloaded OpenFold2 result into small tracked artifacts and compare with the public crystal.

Writes: trpb_VFVS_openfold2.pdb, trpb_VFVS_openfold2_metrics.json
Inputs (scratch, untracked): /tmp/_of2_result.json (parsed result), /tmp/res_xtal/Tm9D8s_refine_19.pdb
The crystal comparison is descriptive: Calpha RMSD after Kabsch superposition on residues present in both.
"""
import hashlib, json, sys
from pathlib import Path
import numpy as np
from .common import now_utc, now_seattle, sha256_bytes, write_json

OUT = Path("artifacts/services/nebius")
SITES = (183, 184, 227, 228)
THREE = {"ALA":"A","ARG":"R","ASN":"N","ASP":"D","CYS":"C","GLN":"Q","GLU":"E","GLY":"G","HIS":"H","ILE":"I","LEU":"L","LYS":"K","MET":"M","PHE":"F","PRO":"P","SER":"S","THR":"T","TRP":"W","TYR":"Y","VAL":"V"}

def ca_atoms(pdb_text, chain=None):
    out = {}
    for l in pdb_text.splitlines():
        if l.startswith("ATOM") and l[12:16].strip() == "CA" and (chain is None or l[21] == chain) and l[16] in " A":
            out[int(l[22:26])] = (THREE.get(l[17:20], "?"), np.array([float(l[30:38]), float(l[38:46]), float(l[46:54])]), float(l[60:66]))
    return out

def kabsch(P, Q):
    Pc, Qc = P - P.mean(0), Q - Q.mean(0)
    U, S, Vt = np.linalg.svd(Pc.T @ Qc)
    d = np.sign(np.linalg.det(U @ Vt)); D = np.diag([1, 1, d])
    R = U @ D @ Vt
    return R, P.mean(0), Q.mean(0)

def rmsd(A, B):
    return float(np.sqrt(((A - B) ** 2).sum(1).mean()))

def main(G="VFVS"):
    res = json.load(open(f"/tmp/_of2_result_{G}.json"))
    s = res["structures_in_ranked_order"][0]
    pdb = s["structure"]
    pdb_bytes = pdb.encode()
    (OUT / f"trpb_{G}_openfold2.pdb").write_bytes(pdb_bytes)
    seq = json.load(open(OUT / f"structure_parent_{G}.json"))["sequence"]
    pred = ca_atoms(pdb)
    pred_seq = "".join(pred[i][0] for i in sorted(pred))
    assert pred_seq == seq, "predicted residue sequence != submitted sequence"
    pl = np.array(s["plddt"])
    pae = np.array(s["predicted_aligned_error"])
    xt_text = Path("/tmp/res_xtal/Tm9D8s_refine_19.pdb").read_text()
    xt_sha = sha256_bytes(Path("/tmp/res_xtal/Tm9D8s_refine_19.pdb").read_bytes())
    comp = {}
    for ch in ("A", "B"):
        x = ca_atoms(xt_text, ch)
        common = sorted(set(x) & set(pred))
        P = np.array([pred[i][1] for i in common]); Q = np.array([x[i][1] for i in common])
        R, pc, qc = kabsch(P, Q)
        Pa = (P - pc) @ R + qc
        dist = np.linalg.norm(Pa - Q, axis=1)
        hi = np.array([pl[i - 1] >= 70 for i in common])
        mism = sum(1 for i in common if x[i][0] != pred[i][0])
        sites = {}
        for p in SITES:
            if p in x:
                k = common.index(p)
                sites[str(p)] = {"crystal_resname": x[p][0], "displacement_A_after_global_superposition": round(float(dist[k]), 2),
                                 "pred_plddt": round(float(pl[p - 1]), 1)}
        def pair(coords_get):
            return {f"{a}-{b}": round(float(np.linalg.norm(coords_get(a) - coords_get(b))), 2) for i, a in enumerate(SITES) for b in SITES[i + 1:]}
        comp[ch] = {"n_common_residues": len(common), "residue_identity_mismatches": mism,
                    "ca_rmsd_all_A": round(rmsd(Pa, Q), 2),
                    "ca_rmsd_plddt_ge_70_A": round(rmsd(Pa[hi], Q[hi]), 2) if hi.sum() >= 10 else None,
                    "n_plddt_ge_70_in_common": int(hi.sum()),
                    "median_ca_displacement_A": round(float(np.median(dist)), 2),
                    "frac_ca_within_4A": round(float((dist < 4).mean()), 3),
                    "sites": sites,
                    "site_site_ca_distance_crystal_A": pair(lambda a: x[a][1]),
                    "site_site_ca_distance_predicted_A": pair(lambda a: pred[a][1])}
    metrics = {
        "generated_t_utc": now_utc(), "generated_t_seattle": now_seattle(),
        "epistemic_status": "PREDICTED structure (model output). Not an observation; not a fitness or function measurement.",
        "provider": "Nebius Scientific AI (MCP https://forge.nebius.cloud/mcp)", "tool": "infer_openfold2_native",
        "model": "OpenFold2 model_3_ptm / finetuning_no_templ_ptm_1 (selected_models=[1]), relax_prediction=false",
        "runtime_origin_reported": s.get("runtime_origin"),
        "operation_id": json.load(open(OUT / f"structure_parent_{G}.json"))["operation_id"],
        "idempotency_key": json.load(open(OUT / f"structure_parent_{G}.json"))["idempotency_key"],
        "seed": "not exposed by this tool; deterministic seed unknown/unspecified (no seed field in schema)",
        "msa": "single-sequence DUMMY MSA only: no external MSA, no templates, no relaxation (tool description). Not an alphafold-style MSA prediction.",
        "sequence_name": f"Tm9D8s* TrpB construct, genotype {G} at sites 183/184/227/228 (parent is VFVS)",
        "sequence": seq, "sequence_sha256": hashlib.sha256(seq.encode()).hexdigest(), "length": len(seq),
        "source_fasta": "CaltechDATA h5rah-5z170 data/ftmlde_data/tm9d8s_AAs.fasta, sha256 d56ebe8d8c556d80bf97329ec34c872b737fb84953f0d83dfe015894e54bbc6c (verified by gpu worker; header Tm9D8*; includes C-terminal LEHHHHHH tag)",
        "residue_numbering": "PDB residue number == 1-based index into the FASTA string (Met1 = 1); also identical to the crystal structure numbering at the four sites. Not wild-type T. maritima numbering.",
        "mutable_sites": {str(p): {"residue_in_this_model": seq[p - 1], "predicted_plddt": round(float(pl[p - 1]), 1)} for p in SITES},
        "pdb_file": f"trpb_{G}_openfold2.pdb", "pdb_sha256": sha256_bytes(pdb_bytes), "pdb_size_bytes": len(pdb_bytes),
        "pdb_b_factor_column_is": "pLDDT (0-100) as written by OpenFold2",
        "ranking_confidence": s["confidence"], "ptm": s["ptm_score"], "inference_seconds": s["inference_seconds"],
        "plddt": {"mean": round(float(pl.mean()), 2), "min": round(float(pl.min()), 1), "max": round(float(pl.max()), 1),
                  "frac_ge_70": round(float((pl >= 70).mean()), 3), "frac_lt_50": round(float((pl < 50).mean()), 3),
                  "per_residue": [round(float(v), 1) for v in pl]},
        "pae": {"shape": list(pae.shape), "mean_A": round(float(pae.mean()), 2), "max_A": round(float(pae.max()), 2),
                "matrix_sha256_of_json": hashlib.sha256(json.dumps(s["predicted_aligned_error"]).encode()).hexdigest(),
                "note": "full matrix retained only in the Nebius customer bucket and by hash here"},
        "crystal_reference": {"file": "data/ftmlde_data/Tm9D8s_refine_19.pdb in CaltechDATA h5rah-5z170 (CC0 1.0)", "sha256": xt_sha,
                              "method_note": "experimental crystal model, PHENIX-refined; two chains (A,B); ligands incl. PLP",
                              "comparison_to_prediction": comp,
                              "caveat": "descriptive geometry only; the crystal is the parent-sequence structure, not each variant"},
        "limits": ["pLDDT/pTM are model self-confidence, NOT functional confidence or fitness",
                   "a structure prediction cannot tell which variants are active; no variant-vs-variant structural difference is claimed",
                   f"this file is for genotype {G} only"]}
    if G != "VFVS" and (OUT / "trpb_VFVS_openfold2.pdb").exists():
        a = ca_atoms((OUT / "trpb_VFVS_openfold2.pdb").read_text()); b = pred
        com = sorted(set(a) & set(b)); A = np.array([a[i][1] for i in com]); B = np.array([b[i][1] for i in com])
        R, pc, qc = kabsch(A, B); metrics["predicted_vs_predicted_VFVS"] = {"ca_rmsd_all_A": round(rmsd((A - pc) @ R + qc, B), 2),
            "note": "difference between two single-sequence low-confidence models; it is not evidence of a structural effect of the mutations"}
    write_json(OUT / f"trpb_{G}_openfold2_metrics.json", metrics)
    print(json.dumps({k: metrics[k] for k in ("ranking_confidence", "ptm")}), metrics["plddt"]["mean"], metrics["plddt"]["frac_ge_70"])
    print(json.dumps(comp["A"]["sites"]), comp["A"]["ca_rmsd_all_A"], comp["A"]["ca_rmsd_plddt_ge_70_A"], comp["A"]["n_plddt_ge_70_in_common"], comp["A"]["frac_ca_within_4A"], comp["A"]["residue_identity_mismatches"])
    print(comp["B"]["ca_rmsd_all_A"], comp["A"]["site_site_ca_distance_crystal_A"], comp["A"]["site_site_ca_distance_predicted_A"])

if __name__ == "__main__":
    main(*sys.argv[1:2])
