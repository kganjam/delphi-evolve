"""Deterministic keyword match: Frontier register problems -> Nebius hosted model families.
No inference, no network, no jobs. Usage: python -I bionemo_match/match.py REGISTER.yaml OUT.json
A hit means 'a model family is named by vocabulary in the problem text'. It is a CANDIDATE
filter only; the 'what would/would not settle' judgement is written by hand in the message."""
import json, re, sys, hashlib, yaml
FAM = {
 "structure (alphafold3/openfold3/protenix/esmfold2)": r"\b(protein structure|crystal structure|cryo-?em|fold(ing|ed)?|conformation|structure prediction|binding site|complex(es)?|interface|ligand|docking|binding|receptor|allost|domain)\b",
 "sequence LM (esm2-650m/3b)": r"\b(variant|mutation|fitness landscape|deep mutational|missense|substitution|evolution(ary)? of (a )?protein|epistasis|ancestral|stability|paralog)\b",
 "binding-ddG/stability words (stab-ddg is BINDING ddG per catalogue, not folding stability)": r"\b(thermostab|stability|ddg|destabili[sz]|melting|unfold)\w*",
 "dynamics/MD (gromacs/openmm/amber/namd/lammps/bioemu2)": r"\b(molecular dynamics|membrane|lipid|channel|pore|conformational (change|dynamics|ensemble)|intrinsically disordered|disordered|phase separation|condensate|transporter|gating)\b",
 "design (rfdiffusion/boltzgen/proteina/mosaic)": r"\b(de novo|design(ed|ing)? (a )?(protein|binder|enzyme)|binder|enzyme design)\b",
 "single-cell (scvi-scanvi)": r"\b(single-cell|scrna|transcriptom\w*|cell type|cell-type|atlas|expression)\b",
 "imaging/medical (monai/holoscan/isaac)": r"\b(ct scan|mri|segmentation|endoscop\w*|radiolog\w*|imaging data)\b",
}
def text(p):
    return " ".join(str(p.get(k) or "") for k in ("statement","why_it_matters","data_needed","model_handles")) + " " + " ".join(p.get("tags") or [])
def main(reg, out):
    raw=open(reg,'rb').read(); ps=yaml.safe_load(raw)["problems"]
    res=[]
    for p in ps:
        t=text(p).lower(); hits={}
        for fam,rx in FAM.items():
            m=sorted(set(x.group(0) if x.group(0) else '' for x in re.finditer(rx,t)))
            if m: hits[fam]=m[:6]
        src = "locator+quote" if (p.get("why_source") or {}).get("locator") and (p.get("why_source") or {}).get("quote") else ("topic-ref" if p.get("attestations") or p.get("why_source") else "none")
        res.append({"slug":p["slug"],"levels":p.get("levels"),"tags":p.get("tags"),"hits":hits,"source":src})
    json.dump({"register_sha256":hashlib.sha256(raw).hexdigest(),"n":len(ps),"results":res},open(out,"w"),indent=1,allow_nan=False)
    import collections
    c=collections.Counter(); 
    for r in res:
        for f in r["hits"]: c[f]+=1
    print(len(ps),"problems; with any hit:",sum(1 for r in res if r["hits"])); print(c)
main(*sys.argv[1:3])
