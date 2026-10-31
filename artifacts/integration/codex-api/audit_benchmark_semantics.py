"""Independent, read-only audit of frozen request semantics; no generator imports.
Run from repository root with --output PATH. Reads exact git objects, never credentials.
Findings identify review sets, not silently relabelled benchmark answers.
"""
import argparse
from collections import Counter
from datetime import datetime
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import subprocess
from zoneinfo import ZoneInfo

SOURCE = '70845e6a68c18c4861d07021e5daf3de4e50e34d'

def blob(name):
    return subprocess.check_output(['git', 'show', f'{SOURCE}:scopedesk/bench/{name}'])

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    raw = {name: blob(name) for name in ['instances_full.jsonl', 'instances_public.jsonl', 'key.jsonl']}
    rows = [json.loads(line) for line in raw['instances_full.jsonl'].splitlines()]
    key = {item['id']: item for item in map(json.loads, raw['key.jsonl'].splitlines())}
    rp, wl, km, hm, allee, ts = [], [], [], [], [], []
    for row in rows:
        family = row['family']
        x = row['hidden']['structured']
        if family == 'rayleigh_plateau':
            s = F(x['s'])
            # z in [0,L], eta=sin(pi*z/L): integral eta dz = 2L/pi.
            # L=s*pi*r -> integral eta dz / r = 2s != 0.
            rp.append({'id': row['id'], 'boundary': x['bc'], 'length_over_pi_r': str(s),
                       'frozen_verdict': key[row['id']]['verdict'],
                       'n1_integral_eta_dz_over_r': str(2 * s),
                       'n1_satisfies_fixed_volume_linear_constraint': False,
                       'claim_differs_from_fixed_volume_pinned_threshold': key[row['id']]['verdict'] != 'applies'})
        elif family == 'wavelength_formula_licence':
            wl.append({'id': row['id'], 'ten_percent_tolerance_visible': '10%' in row['request_text'],
                       'frozen_verdict': key[row['id']]['verdict']})
        elif family == 'kimura_regime':
            if '10%' not in row['request_text']:
                km.append(row['id'])
        elif family == 'hamilton_rule_form':
            b, c, r, d = (F(x[k]) for k in ('b', 'c', 'r', 'd'))
            # Source code calls these absolute fitnesses. Negative payoffs can instead
            # be continuous-time rates, or weak-selection increments, if declared.
            pair_fitness = {f'{g}{h}': 1-c*g+b*h+d*g*h for g in (0, 1) for h in (0, 1)}
            negatives = {k: str(v) for k, v in pair_fitness.items() if v < 0}
            if negatives:
                hm.append({'id': row['id'], 'negative_pair_fitness': negatives,
                           'relative_payoff_or_weak_selection_reinterpretation_needed': True})
        elif family == 'fisher_kpp_speed' and x['kind'] == 'allee':
            m = F(x['par'])
            # Any compact initial patch with 0 <= u0 <= m/2 is below the
            # unstable threshold. f(u)<0 on (0,m), so it cannot invade 1.
            allee.append({'id': row['id'], 'threshold_m': str(m),
                          'admissible_compact_patch_maximum': str(m / 2),
                          'reaction_sign_for_0_u_le_patch_max': 'negative',
                          'invasion_not_guaranteed_by_compact_support': True})
        elif family == 'turing_finite_domain' and key[row['id']]['verdict'] == 'applies':
            ts.append(row['id'])
    result = {
        'review': 'Codex API independent input/statement-fidelity audit, not a blinded agent evaluation',
        'recorded_at': datetime.now(ZoneInfo('America/Los_Angeles')).isoformat(),
        'source_commit': SOURCE,
        'source_hashes': {name: hashlib.sha256(data).hexdigest() for name, data in raw.items()},
        'n': len(rows), 'families': dict(Counter(r['family'] for r in rows)),
        'rayleigh_pinned_volume_review': rp,
        'rayleigh_affected_key_ids': [r['id'] for r in rp if r['claim_differs_from_fixed_volume_pinned_threshold']],
        'wavelength_tolerance_review': wl,
        'kimura_missing_visible_tolerance_ids': km,
        'hamilton_absolute_fitness_review': hm,
        'allee_invasion_initial_condition_review': allee,
        'turing_applies_requires_linear_only_task_definition_ids': ts,
        'limitations': [
            'Read frozen key and generator before this audit; not blinded, no model score.',
            'Rayleigh exact integral rejects the claimed n=1 fixed-volume mode; full bridge threshold also supported by primary literature, not Lean-checked here.',
            'Review sets are not all demonstrated wrong labels; underspecified questions may admit several reasonable answers.',
            'No automatic key changes or new pooled accuracy computed.',
            'Negative Hamilton pair values are allowed as game payoffs/rates; source must specify that interpretation or a valid weak-selection mapping.',
            'Allee front-speed formula may be correct conditional on invasion; compact support alone does not imply invasion.',
            'No external claim source pins are wired by this script.'
        ]}
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'n': len(rows), 'source_commit': SOURCE,
                      'rayleigh_review_ids': result['rayleigh_affected_key_ids'],
                      'wavelength_missing_tolerance': sum(not r['ten_percent_tolerance_visible'] for r in wl),
                      'kimura_missing_tolerance': len(km), 'hamilton_pair_fitness_review': len(hm),
                      'allee_invasion_review': len(allee), 'turing_linear_only_review': len(ts)}))

if __name__ == '__main__':
    main()
