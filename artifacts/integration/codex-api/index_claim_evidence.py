"""Hash reviewed evidence at exact git revisions; recount original replay outcomes.
This is a source-integrity/indexing check, not a rerun of experiments or proofs.
"""
import csv
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import subprocess
from zoneinfo import ZoneInfo

BASE = '51a38057aebe7e7e0801d8f67af7fd4a81a8935f'
AUDIT = '19fae04'
SERVICE = '596ae9e'
GPU = '29bb42f9359e39885c42d19d3c9ecd22eb312ba7'
PRICE = 'b4e60db'
BENCH_V1_1 = '7f9035ac3a92aa33d829f6e528d1481bfdd3c289'

def git(*args):
    return subprocess.check_output(['git', *args])

def main():
    entries = {
        'F01': (BASE, ['artifacts/turing_scope/results.json','artifacts/turing_scope/lean_receipt.json']),
        'F02': (BASE, ['artifacts/turing_scope/results.json']),
        'F03': (BASE, ['turing_scope/source.py','turing_scope/adapter.py','tests/test_turing_scope.py']),
        'F04': (SERVICE, ['artifacts/integration/codex-api/service-fixed-review.json','artifacts/integration/codex-api/service-fixed-review.lean','artifacts/integration/codex-api/provenance.json']),
        'F05': (AUDIT, ['planning/rethink/CODEX-BENCHMARK-SEMANTICS.md','artifacts/integration/codex-api/benchmark-semantic-audit.json']),
        'F06': (AUDIT, ['planning/rethink/CODEX-SCIENTIFIC-ADDENDUM.md','planning/rethink/CODEX-BENCHMARK-SEMANTICS.md']),
        'F07': (PRICE, ['experiments/price_probe/Price.lean','experiments/price_probe/Witnesses.lean.inc','artifacts/integration/codex-api/price-probe.json','planning/rethink/PRICE-PRIOR-ART-AND-PROBE.md']),
        'F08': (BENCH_V1_1, ['planning/rethink/CODEX-BENCH-V1-1-REVIEW.md','artifacts/integration/codex-api/audit_benchmark_v1_1.py','artifacts/integration/codex-api/benchmark-v1-1-review.json']),
        'F09': (BENCH_V1_1, ['site/review/index.html','site/review/app.js','site/review/style.css','scripts/check_review_walkthrough.py','artifacts/integration/codex-api/review-walkthrough/browser-receipt.json']),
        'F10': (BENCH_V1_1, ['artifacts/integration/codex-api/admissible-review/469874b/Admissible.lean','artifacts/integration/codex-api/admissible-review/469874b/compile-review.json','planning/rethink/CODEX-21-CLAIM-FREEZE-REVIEW.md']),
        'B01': (BASE, ['data/manifest.json','artifacts/evidence/route_summary.json','scripts/audit_data.py']),
        'B02': (BASE, ['artifacts/core/replay/episodes.csv','artifacts/lazysp/results/episodes.csv','artifacts/lazysp/results/table_primary.csv']),
        'B03': (BASE, ['artifacts/scale/library_receipts.json','artifacts/scale/replay_summary.csv','artifacts/scale/ablation_descriptive.json']),
        'B04': (BASE, ['artifacts/integration/publication.json']),
        'B05': (BASE, ['artifacts/integration/fresh-checkout-317203a0.json']),
        'A01': (BASE, ['planning/rethink/PRIOR-ART-VERDICT.md']),
        'A02': (SERVICE, ['planning/rethink/CODEX-SCIENTIFIC-ADDENDUM.md']),
        'R01': (GPU, ['artifacts/gpuops/pde_pilot/rate_summary.json','artifacts/gpuops/pde_pilot/estimate_384k.json','tasks/results/gpuops.json']),
        'R02': (BASE, ['artifacts/gpu/orx/receipt.json'])}
    indexed = {}
    for claim, (ref, paths) in entries.items():
        sha = git('rev-parse', ref).decode().strip()
        indexed[claim] = {'source_commit': sha, 'inspection': 'read artifact/receipt; no fresh experiment rerun',
                          'artifacts': {p: hashlib.sha256(git('show',f'{sha}:{p}')).hexdigest() for p in paths}}
    core = list(csv.DictReader(io.StringIO(git('show',BASE+':artifacts/core/replay/episodes.csv').decode())))
    lazy = list(csv.DictReader(io.StringIO(git('show',BASE+':artifacts/lazysp/results/episodes.csv').decode())))
    recount = {}
    for policy, rows in [('q2c',core),('collective_shared',core),('lazysp_alternate',lazy)]:
        selected = [r for r in rows if r['policy'] == policy]
        resolved = [r for r in selected if r['status'] in ('open','blocked') and r['correct']=='True' and int(float(r['assays']))<=1000]
        recount[policy] = {'episodes':len(selected),'correctly_resolved_within_1000_extra_assays':len(resolved),
                            'unique_endpoint_pairs':len({(r['start'],r['target']) for r in selected}),
                            'limitation':'Repeated targets/initializations; retrospective transductive sensitivity, not prospective biology.'}
    assert [recount[k]['correctly_resolved_within_1000_extra_assays'] for k in ('q2c','collective_shared','lazysp_alternate')] == [78,78,96]
    assert all(r['episodes']==100 for r in recount.values())
    out={'recorded_at':datetime.now(ZoneInfo('America/Los_Angeles')).isoformat(),
         'description':'Evidence blob hashes plus independent CSV recount. No experiment/Lean rerun.',
         'claims':indexed,'independent_baseline_recount':recount,
         'pending_claims':['P%02d'%i for i in range(1,11)],
         'limitations':['Git SHA identifies artifact snapshot, not necessarily experiment source; each receipt records its own source revision.','Hash integrity does not establish scientific validity.','No API billing, external use, revised deployment, or organizer-submission claim.']}
    Path('artifacts/integration/codex-api/claim-evidence-index.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({'indexed_claims':len(indexed),'recount':recount}))

if __name__ == '__main__':
    main()
