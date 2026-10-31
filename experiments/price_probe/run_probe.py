"""Run the bounded Price feasibility check and save exact diagnostics.
Invoke this driver inside the task's systemd-run scope. Requires pinned Lean/Mathlib.
Creates temporary mutants; never edits other checkouts or reads credentials.
"""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parent
OUT=ROOT.parent.parent/'artifacts/integration/codex-api/price-probe.json'
LAKE='/home/ubuntu/.elan/bin/lake'

def run(path):
    started=time.monotonic()
    p=subprocess.run([LAKE,'env','lean','-j2',str(path)],cwd=ROOT,text=True,capture_output=True,timeout=180,
                     env={**os.environ,'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1'})
    return {'command':[LAKE,'env','lean','-j2',str(path)],'exit':p.returncode,'wall_seconds':round(time.monotonic()-started,3),'output':p.stdout+p.stderr}

def main():
    src=(ROOT/'Price.lean').read_text()
    original=run(ROOT/'Price.lean')
    results={'source_sha256':hashlib.sha256(src.encode()).hexdigest(),'recorded_at':datetime.now(ZoneInfo('America/Los_Angeles')).isoformat(),
             'original':original,'mutants':[], 'scope':'Finite weighted identity and conditional statistical regression corollary; feasibility, not blinded benchmark or biological validation.'}
    if original['exit']==0:
        with tempfile.TemporaryDirectory(prefix='delphi-price-') as td:
            # Change scientific targets while retaining the original attempted proof.
            mutants={
                'transmission_sign_reversed':src.replace('cov p w z + mean p (fun i => w i * (zDesc i - z i)) := by','cov p w z - mean p (fun i => w i * (zDesc i - z i)) := by',1),
                'hamilton_cost_sign_reversed':src.replace('↔ 0 < r * b - c := by','↔ 0 < r * b + c := by',1)}
            for name, changed in mutants.items():
                assert changed!=src
                path=Path(td)/(name+'.lean');path.write_text(changed)
                r=run(path);r.update(name=name,sha256=hashlib.sha256(changed.encode()).hexdigest(),rejected=r['exit']!=0)
                results['mutants'].append(r)
        with tempfile.TemporaryDirectory(prefix='delphi-price-witness-') as td:
            witness=(ROOT/'Witnesses.lean.inc').read_text()
            path=Path(td)/'WitnessControls.lean'
            path.write_text(src+'\n'+witness)
            results['witness_controls']=run(path)
            results['witness_source_sha256']=hashlib.sha256(witness.encode()).hexdigest()
    results['forbidden_declarations']=[token for token in ['sorry','admit','native_decide','axiom '] if re.search(r'\b'+token,src)]
    results['limitations']=['No additive-genetic Fisher FTNS projection proved.','Regression corollary assumes orthogonal residual and positive focal variance and mean fitness; it does not establish causal benefit/cost.','Population interpretation requires normalized nonnegative weights; general algebra theorems allow broader inputs.','Author implemented and tested feasibility; not an independent statement-fidelity review.','Price/Hamilton relation is established mathematics; machine-checking priority not established.']
    OUT.write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps({'original_exit':original['exit'],'mutants_rejected':[m['rejected'] for m in results['mutants']],'receipt':str(OUT)}))
    if original['exit'] or len(results['mutants'])!=2 or not all(m['rejected'] for m in results['mutants']) or results.get('witness_controls',{}).get('exit')!=0:raise SystemExit(1)

if __name__=='__main__':main()
