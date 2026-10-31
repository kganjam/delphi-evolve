"""Build scientific_services/demo/structure.html: standalone (no CDN, no npm) PREDICTED-structure panel next to
OBSERVED growth scores for the four mutable TrpB sites. Pure canvas Calpha trace with drag-rotate.

Observed numbers are recomputed from the pinned CaltechDATA summary_AA.csv (raw mu minus stop-codon mean, as in
core's score definition) so the page never shows source max-normalised columns. Predicted coordinates come from
artifacts/services/nebius/*.pdb (OpenFold2, single-sequence dummy MSA)."""
import json, sys
from pathlib import Path
import pandas as pd

NEB = Path("artifacts/services/nebius")
SITES = (183, 184, 227, 228)
CSV = "/data/artifacts/v2-scout/data/caltech/summary_AA.csv"
CSV_SHA = "a631d8cf6c5b188a801555cc4117547a1bf8e294240e1757c2d2d78dcb25ee82"

def ca(pdb):
    out = []
    for l in pdb.splitlines():
        if l.startswith("ATOM") and l[12:16].strip() == "CA":
            out.append((int(l[22:26]), float(l[30:38]), float(l[38:46]), float(l[46:54]), float(l[60:66])))
    return out

def observed(genos):
    d = pd.read_csv(CSV); stop = d["# Stop"] > 0
    b1, b2 = d.loc[stop, "mu_1"].mean(), d.loc[stop, "mu_2"].mean()
    r = {}
    for g in genos:
        row = d[d.AAs == g].iloc[0]
        s1, s2 = row.mu_1 - b1, row.mu_2 - b2
        r[g] = {"score_rep1": round(float(s1), 4), "score_rep2": round(float(s2), 4), "score_mean": round(float((s1 + s2) / 2), 4),
                "input_count_rep1": int(row.InputCount_1), "input_count_rep2": int(row.InputCount_2)}
    return r

def main():
    entries = []
    for g in ("VFVS", "AIKG"):
        m = NEB / (f"trpb_{g}_openfold2_metrics.json"); p = NEB / (f"trpb_{g}_openfold2.pdb")
        if m.exists() and p.exists():
            met = json.loads(m.read_text())
            entries.append({"genotype": g, "coords": ca(p.read_text()), "metrics": {k: met[k] for k in ("ranking_confidence", "ptm", "plddt", "operation_id", "pdb_sha256", "model", "msa", "sequence_sha256", "mutable_sites")},
                            "crystal": met.get("crystal_reference", {}).get("comparison_to_prediction", {}).get("A")})
    obs = observed([e["genotype"] for e in entries])
    for e in entries:
        e["observed"] = obs[e["genotype"]]
        e["coords"] = [[a, round(x, 2), round(y, 2), round(z, 2), round(pl, 1)] for a, x, y, z, pl in e["coords"]]
        e["metrics"]["plddt"] = {k: v for k, v in e["metrics"]["plddt"].items() if k != "per_residue"}
    data = {"sites": SITES, "summary_AA_sha256": CSV_SHA, "entries": entries}
    html = TEMPLATE.replace("__DATA__", json.dumps(data, separators=(",", ":")))
    Path("scientific_services/demo/structure.html").write_text(html)
    print("entries:", [e["genotype"] for e in entries], len(html), "bytes")

TEMPLATE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>TrpB: observed growth vs PREDICTED structure</title>
<style>
:root{--ink:#1d2330;--mut:#5b6472;--line:#d9dde3;--bg:#fbfbfa;--obs:#14663f;--pred:#8a4b08;--site:#c0262d}
body{margin:0;font:15px/1.45 system-ui,sans-serif;color:var(--ink);background:var(--bg)}
main{max-width:1100px;margin:0 auto;padding:20px}
h1{font-size:1.35rem;margin:.2em 0}.sub{color:var(--mut);margin:0 0 14px}
.grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:16px}@media(max-width:800px){.grid{grid-template-columns:1fr}}
.card{background:#fff;border:1px solid var(--line);border-radius:8px;padding:14px}
.tag{display:inline-block;font-size:.72rem;font-weight:700;letter-spacing:.04em;padding:1px 7px;border-radius:99px;color:#fff}
.obs{background:var(--obs)}.pred{background:var(--pred)}
canvas{width:100%;height:auto;aspect-ratio:1/1;background:#f4f5f7;border-radius:6px;touch-action:none;cursor:grab}
table{border-collapse:collapse;width:100%}td,th{padding:3px 6px;border-bottom:1px solid var(--line);text-align:left;font-variant-numeric:tabular-nums}
.warn{border-left:4px solid var(--site);padding:6px 10px;background:#fff6f6;margin:10px 0;font-size:.92rem}
button{font:inherit;padding:3px 10px;border:1px solid var(--line);background:#fff;border-radius:6px;cursor:pointer}button[aria-pressed=true]{background:#1d2330;color:#fff}
small,.mut{color:var(--mut)}
</style></head><body><main>
<h1>TrpB parent and published top variant: observed growth, predicted structure</h1>
<p class="sub">Four mutable sites (183, 184, 227, 228; numbering = index into the expressed construct, Met1). Left: <span class="tag obs">OBSERVED</span> growth-assay scores. Right: <span class="tag pred">PREDICTED</span> backbone.</p>
<div class="warn"><b>Read before interpreting.</b> The predicted structures come from OpenFold2 with a single-sequence <em>dummy</em> MSA (Nebius Scientific AI). pLDDT is the model's self-confidence, not evidence of function. A coordinate difference between two predicted models is not a cause of the fitness difference. The mean pLDDT is low (see below) and the Calpha RMSD to the deposited crystal structure is large, so treat these models as a label of where the sites are in <em>sequence</em>, not as a reliable fold.</div>
<div class="grid">
<section class="card" id="obsCard"><h2 style="font-size:1.05rem;margin-top:0">Observed <span class="tag obs">OBSERVED</span></h2>
<p class="mut">CaltechDATA h5rah-5z170 <code>summary_AA.csv</code> (CC0), Johnston et al. 2024. Score = raw growth rate minus stop-codon mean, per replicate; not the source's max-normalised column. Cellular growth is a proxy for function.</p><table id="obsTable"></table></section>
<section class="card"><h2 style="font-size:1.05rem;margin-top:0">Predicted <span class="tag pred">PREDICTED</span> <span id="pickers"></span></h2>
<canvas id="cv" width="640" height="640" aria-label="Calpha trace of the predicted structure; drag to rotate"></canvas>
<div style="margin-top:6px"><button id="mCol" aria-pressed="true">color: pLDDT</button> <button id="mSite" aria-pressed="false">dim backbone</button> <small>drag to rotate; red spheres = the four mutable sites</small></div>
<table id="predTable" style="margin-top:8px"></table></section></div>
<p class="mut" style="margin-top:14px">Descriptive only. No claim of structural cause for the fitness difference. Provenance: operation id, PDB sha256 and sequence hash are in <code>artifacts/services/nebius/*_metrics.json</code>.</p>
<script id="d" type="application/json">__DATA__</script>
<script>
const D=JSON.parse(document.getElementById('d').textContent);const cv=document.getElementById('cv'),cx=cv.getContext('2d');
let cur=0,rx=-0.4,ry=0.6,dim=false,byConf=true;
function plddtColor(v){return v>=90?'#0053d6':v>=70?'#65cbf3':v>=50?'#ffdb13':'#ff7d45'}
function rot(p,c){const[x,y,z]=[p[1]-c[0],p[2]-c[1],p[3]-c[2]];const cy=Math.cos(ry),sy=Math.sin(ry),cxx=Math.cos(rx),sxx=Math.sin(rx);
const x1=x*cy+z*sy,z1=-x*sy+z*cy,y1=y*cxx-z1*sxx,z2=y*sxx+z1*cxx;return[x1,y1,z2]}
function draw(){const e=D.entries[cur];const P=e.coords;const c=[0,1,2].map(i=>P.reduce((s,p)=>s+p[i+1],0)/P.length);
const R=P.map(p=>rot(p,c));let ext=0;R.forEach(r=>{ext=Math.max(ext,Math.abs(r[0]),Math.abs(r[1]))});const s=cv.width*0.46/ext;
cx.clearRect(0,0,cv.width,cv.height);const W=cv.width/2,H=cv.height/2;
cx.lineWidth=2;cx.lineCap='round';for(let i=1;i<P.length;i++){if(P[i][0]-P[i-1][0]!==1)continue;
cx.strokeStyle=dim?'#c9ced6':(byConf?plddtColor((P[i][4]+P[i-1][4])/2):'#8895a7');cx.globalAlpha=0.55+0.4*((R[i][2]/ext+1)/2);
cx.beginPath();cx.moveTo(W+R[i-1][0]*s,H-R[i-1][1]*s);cx.lineTo(W+R[i][0]*s,H-R[i][1]*s);cx.stroke()}
cx.globalAlpha=1;D.sites.forEach(a=>{const k=P.findIndex(p=>p[0]===a);if(k<0)return;const r=R[k];cx.fillStyle='#c0262d';cx.beginPath();cx.arc(W+r[0]*s,H-r[1]*s,7,0,6.3);cx.fill();cx.strokeStyle='#fff';cx.lineWidth=1.5;cx.stroke();cx.fillStyle='#1d2330';cx.font='13px system-ui';cx.fillText(a,W+r[0]*s+9,H-r[1]*s-6)})}
function tables(){const e=D.entries[cur];const m=e.metrics;
document.getElementById('obsTable').innerHTML='<tr><th>genotype</th><th>replicate 1</th><th>replicate 2</th><th>mean</th><th>input counts</th></tr>'+D.entries.map(x=>{const o=x.observed;return`<tr${x===e?' style="background:#f3f7f4"':''}><td><b>${x.genotype}</b></td><td>${o.score_rep1}</td><td>${o.score_rep2}</td><td>${o.score_mean}</td><td>${o.input_count_rep1} / ${o.input_count_rep2}</td></tr>`}).join('');
const c=e.crystal;
document.getElementById('predTable').innerHTML=`<tr><td>genotype shown</td><td><b>${e.genotype}</b> (residues at 183/184/227/228 = ${e.genotype.split('').join('/')})</td></tr>
<tr><td>model</td><td>${m.model}</td></tr><tr><td>MSA</td><td>${m.msa}</td></tr>
<tr><td>ranking confidence / pTM</td><td>${m.ranking_confidence.toFixed(1)} / ${m.ptm.toFixed(3)}</td></tr>
<tr><td>mean pLDDT, fraction ≥70</td><td>${m.plddt.mean} , ${m.plddt.frac_ge_70}</td></tr>
<tr><td>pLDDT at 183 / 184 / 227 / 228</td><td>${Object.values(m.mutable_sites).map(s=>s.predicted_plddt).join(' / ')}</td></tr>
<tr><td>Calpha RMSD to deposited parent crystal (chain A, Kabsch, common residues)</td><td>${c?c.ca_rmsd_all_A+' Å; '+Math.round(c.frac_ca_within_4A*100)+'% of Calpha within 4 Å':'n/a'}</td></tr>
<tr><td>operation / PDB sha256</td><td><small>${m.operation_id} / ${m.pdb_sha256.slice(0,16)}…</small></td></tr>`}
const pk=document.getElementById('pickers');D.entries.forEach((e,i)=>{const b=document.createElement('button');b.textContent=e.genotype;b.setAttribute('aria-pressed',i===0);b.onclick=()=>{cur=i;[...pk.children].forEach((x,j)=>x.setAttribute('aria-pressed',j===i));tables();draw()};pk.appendChild(b)});
document.getElementById('mCol').onclick=ev=>{byConf=!byConf;ev.target.setAttribute('aria-pressed',byConf);draw()};
document.getElementById('mSite').onclick=ev=>{dim=!dim;ev.target.setAttribute('aria-pressed',dim);draw()};
let drag=null;cv.addEventListener('pointerdown',e=>{drag=[e.clientX,e.clientY];cv.setPointerCapture(e.pointerId)});
cv.addEventListener('pointermove',e=>{if(!drag)return;ry+=(e.clientX-drag[0])*0.01;rx+=(e.clientY-drag[1])*0.01;drag=[e.clientX,e.clientY];draw()});
cv.addEventListener('pointerup',()=>drag=null);tables();draw();
</script></main></body></html>
"""
if __name__ == "__main__":
    main()
