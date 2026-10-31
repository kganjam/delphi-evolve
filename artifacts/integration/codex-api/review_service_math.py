"""Independent bounded finite-mode/property review of an immutable service snapshot.
No HTTP server, credentials, signing, network requests, or FD eigensolver calls.
"""
import argparse
from datetime import datetime
from fractions import Fraction as F
import hashlib
import importlib
import json
from pathlib import Path
import random
import sys
from zoneinfo import ZoneInfo

SOURCE = '05be25f0d8b478bb1fd40f52cdecb888c85a8bab'

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    sys.path.insert(0,str(args.snapshot.resolve()))
    eng=importlib.import_module('falsify.engine')
    assert Path(eng.__file__).resolve()==(args.snapshot/'falsify/engine.py').resolve()
    J=[[F(1),F(-2)],[F(2),F(-3)]]
    D=[F(1),F(10)]
    cases=[]
    for bc in ['neumann','dirichlet','periodic']:
        first=1 if bc=='dirichlet' else 0
        mult=2 if bc=='periodic' else 1
        for rx,ry in [(F(1),F(1)),(F(2),F(2)),(F(5,2),F(3)),(F(4),F(7,2))]:
            for physical in [False,True]:
                lengths=[rx,ry] if not physical else [rx*F('3.1415926535897932384626433832795'),ry*F('3.1415926535897932384626433832795')]
                req={'jacobian':[[str(v) for v in row] for row in J], 'diffusivities':['1','10'],
                     'domain':{'dimension':2,'boundary':bc,('lengths' if physical else 'lengths_over_pi'):[str(v) for v in lengths]},'crosscheck':False}
                norm=eng.normalize(req)
                result=eng.classify_modes(J,D,norm['domain'])
                # Independent full Cartesian grid and direct 2x2 determinant.
                # This grid reaches q >= (40/4)^2, well above every unstable q (<1/2)
                # for these fixed kinetics. It does not reuse the service tail loop.
                ractual=[v/F('3.141592653589793238462643383279502884197169399375105820974944592307816') for v in lengths] if physical else lengths
                truth=set()
                for n in range(first,41):
                    for m in range(first,41):
                        q=F(mult*mult)*(F(n*n)/(ractual[0]**2)+F(m*m)/(ractual[1]**2))
                        # For this J and D: det=(1-q)*(-3-10q)+4.
                        if (1-q)*(-3-10*q)+4<0:truth.add((n,m))
                found={tuple(row['index']) for row in result['unstable']}
                if not result['ambiguous'] and not result['marginal']:
                    assert found==truth,(bc,rx,ry,physical,found,truth)
                else:
                    assert found<=truth
                    unresolved={tuple(row['index']) for row in result['ambiguous']+result['marginal']}
                    assert truth-found<=unresolved
                cases.append({'boundary':bc,'lengths':list(map(str,lengths)),'physical':physical,'unstable_canonical_indices':len(found),
                              'ambiguous':len(result['ambiguous']),'marginal':len(result['marginal']),'independent_exact_reference_agrees':True})
    rng=random.Random(314159)
    interval_checks=0
    for _ in range(80):
        P=F(rng.randint(1,20),3);S=F(rng.randint(-5,30),7);det=F(rng.randint(1,20),11)
        left=F(rng.randint(0,60),20);right=left+F(rng.randint(1,10),30)
        sign=eng.det_range_sign(P,S,det,left,right)
        samples=[left+(right-left)*F(k,10) for k in range(11)]
        if sign in [-1,1]:
            assert all(((P*q*q-S*q+det)>0 if sign==1 else (P*q*q-S*q+det)<0) for q in samples)
        interval_checks+=1
    ratios=[]
    for j in [J,[[F(1),F(-1)],[F(1011,1000),F(-101,100)]],[[F(-3),F(2)],[F(-2),F(1)]]]:
        for rho in [F(1),F(11,10),F(2),F(10),F(20)]:
            a,b=j[0];c,d=j[1];act_first=a>0
            Ds=[F(1),rho] if act_first else [rho,F(1)]
            out=eng.diffusion_requirement(j,Ds)
            # Necessary and sufficient continuum band: upward quadratic has
            # negative value at its positive vertex and J is Hurwitz.
            det=a*d-b*c;vertex=(a*Ds[1]+d*Ds[0])/(2*Ds[0]*Ds[1])
            direct=vertex>0 and (a-Ds[0]*vertex)*(d-Ds[1]*vertex)-b*c<0
            assert out['supplied_ratio_meets_textbook_condition']==direct
            low,high=map(F,out['required_inhibitor_over_activator_ratio_greater_than_bracket'])
            if rho<low:assert not direct
            if rho>high:assert direct
            ratios.append({'J':[[str(v) for v in row] for row in j],'ratio':str(rho),'continuum_band':bool(direct)})
    result={'review':'Codex independent bounded service-math execution','source_commit':SOURCE,
            'recorded_at':datetime.now(ZoneInfo('America/Los_Angeles')).isoformat(),
            'source_hashes':{str(p.relative_to(args.snapshot)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [args.snapshot/'falsify/engine.py',args.snapshot/'falsify/presets.py']},
            'two_dimensional_cases':cases,'determinant_interval_sample_checks':interval_checks,'diffusion_ratio_checks':ratios,
            'findings':['No decided 2D enumeration mismatch in 24 fixed cases (3 boundaries, 4 rectangles, exact/physical lengths).',
                        'No sampled interval-sign contradiction in 80 cases; convex-quadratic endpoint/vertex argument separately read in source.',
                        'Diffusion ratio formula and supplied-condition test agreed in 15 fixed checks, including ratio1.1 and swapped activator.',
                        'Periodic unstable_count counts canonical nonnegative index tuples, not Fourier eigenspace multiplicity; document this.',
                        'MCP schema still promises complete returned list despite detail cap50; source-only wording issue.',
                        'Protein reading says excess MUST come from binding/hindrance/dimerization; those are examples, not an exhaustive established cause.'],
            'limitations':['Finite mathematical checks, no nonlinear or biological validation.','No service HTTP/privacy/rate-limit penetration test.','No fresh Lean compile in this script.','Physical pi reference is a longer declared rational approximation; tests are not a proof of the pi bracket.','Counted canonical wave-number indices, not eigenvalue multiplicities.']}
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'two_dimensional_cases':len(cases),'interval_samples':interval_checks,'diffusion_ratio_cases':len(ratios),'mismatches':0}))

if __name__=='__main__':main()
