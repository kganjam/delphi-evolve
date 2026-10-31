#!/usr/bin/env python3
"""Recover lost episode summaries by replaying saved observations, never policies.

The original shard writer omitted rows.append(out) after adding a prior hook.
This script validates every saved query against the source dataset and rebuilds
the ledger in its original order. It does not choose new queries or rerun search.
Original files remain untouched. Missing wall times remain null.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
import subprocess
import sys
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evolve import data, replay
from evolve.graph import Ledger, verify_cut, verify_route


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def restore(land, ep, policy, queries, budget):
    """Check immutable observations and derive the certificate at the last query."""
    lo, hi = land.intervals()

    def expected(v):
        return [int(lo[v]), int(hi[v]), int(land.s[v])] if land.measured[v] else None

    ledger = Ledger(ep['start'], ep['target'])
    initial = [ep['start'], ep['target']] + [v for v in ep['init'] if v not in (ep['start'], ep['target'])]
    seen = set()
    for v in initial:
        ledger.reveal(v, expected(v))
        seen.add(v)
    if len(queries) > budget:
        raise ValueError('query history exceeds frozen budget')
    for n, row in enumerate(queries, 1):
        count, actor, v, rec, why = row
        if count != n or v in seen:
            raise ValueError(f'duplicate query or broken counter at {n}')
        if ledger.status() != 'unresolved':
            raise ValueError(f'query after certificate at {n}')
        if rec != expected(v):
            raise ValueError(f'source observation mismatch at query {n}')
        if not isinstance(actor, str) or not isinstance(why, str):
            raise ValueError('missing actor/reason')
        ledger.reveal(v, rec)
        seen.add(v)
    status = ledger.status()
    truth_open, closure_size, truth_route = replay.truth(land, ep['start'], ep['target'])
    out = dict(family=ep['family'], seed=ep['seed'], start=data.decode(ep['start']),
               target=data.decode(ep['target']), policy=policy, truth_open=truth_open,
               truth_closure_size=closure_size,
               truth_shortest_route_len=None if truth_route is None else len(truth_route)-1,
               status=status, assays=len(queries), censored=status == 'unresolved',
               stuck=status == 'unresolved' and len(queries) < budget, wall_s=None,
               bmax=budget, observed_max_score=int(max(v[2] for v in ledger.obs.values())),
               n_observed=len(ledger.obs), certificate=None if status == 'unresolved' else status,
               correct=None if status == 'unresolved' else (status == 'open') == truth_open)
    if status == 'open':
        route = ledger.route()
        out.update(verified_by_full_data=bool(verify_route(land.measured, lo, hi, route)),
                   route=[data.decode(v) for v in route], route_len=len(route)-1,
                   min_edge_margin=int(min(lo[b]-hi[a] for a, b in zip(route, route[1:]))),
                   replicate_sign_agree_frac=float(sum(land.s1[b] >= land.s1[a] and land.s2[b] >= land.s2[a]
                                                       for a, b in zip(route, route[1:])) / (len(route)-1)))
    elif status == 'blocked':
        closed, boundary = ledger.cut()
        out.update(verified_by_full_data=bool(verify_cut(land.measured, lo, hi, closed, ep['start'], ep['target'])),
                   cut_size=len(closed), cut_boundary_edges=len(boundary))
    if out['correct'] is False or out.get('verified_by_full_data') is False:
        raise ValueError('reconstructed certificate fails full-data check')
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source', type=Path, required=True, help='original replay directory')
    ap.add_argument('--protocol', type=Path, required=True)
    ap.add_argument('--raw', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True, help='new directory; never the source')
    args = ap.parse_args()
    if args.out.resolve() == args.source.resolve() or args.out.exists():
        raise SystemExit('output must be a new directory, distinct from source')
    protocol_blob = args.protocol.read_bytes()
    protocol = json.loads(protocol_blob)
    land = data.load(args.raw, kappa=protocol['kappa_main'])
    if land.sha != protocol['dataset_sha256']:
        raise ValueError('source manifest differs from frozen protocol')
    episodes = replay.make_episodes(land, protocol['seeds'])
    actual_panel = replay.protocol(land, protocol['seeds'])['panel_sha256']
    if actual_panel != protocol['panel_sha256']:
        raise ValueError('episode panel differs from frozen protocol')
    args.out.mkdir(parents=True)
    (args.out / 'shards').mkdir()
    checked = recovered = queries_checked = 0
    inputs = []
    for policy in protocol['policies']:
        for seed in range(protocol['seeds']):
            name = f'{policy}__seed{seed:02d}.json'
            path = args.source / 'shards' / name
            blob = path.read_bytes()
            original = json.loads(blob)
            panel = [ep for ep in episodes if ep['seed'] == seed]
            expected_keys = {f"{ep['family']}:{data.decode(ep['start'])}>{data.decode(ep['target'])}" for ep in panel}
            if set(original['qlogs']) != expected_keys:
                raise ValueError(f'{name}: incomplete query panel')
            previous = {(r['family'], r['start'], r['target']): r for r in original['rows']}
            if len(previous) != len(original['rows']):
                raise ValueError(f'{name}: duplicate original rows')
            rows = []
            for ep in panel:
                key = f"{ep['family']}:{data.decode(ep['start'])}>{data.decode(ep['target'])}"
                q = original['qlogs'][key]
                out = restore(land, ep, policy, q, protocol['budget_assays_beyond_initial'])
                queries_checked += len(q)
                old = previous.get((out['family'], out['start'], out['target']))
                if old is not None:
                    for k, v in out.items():
                        if k != 'wall_s' and old.get(k) != v:
                            raise ValueError(f'{name} {key}: intact row mismatch {k}: {old.get(k)!r} != {v!r}')
                    out = old
                    checked += 1
                else:
                    out['recovery'] = 'saved query history; no policy rerun; wall_s unavailable'
                    recovered += 1
                rows.append(out)
            if len(rows) != len(panel):
                raise ValueError('incomplete reconstructed panel')
            dest = dict(original, rows=rows, recovery_source_sha256=sha(blob))
            (args.out / 'shards' / name).write_text(json.dumps(dest, default=int) + '\n')
            inputs.append({'file': name, 'sha256': sha(blob), 'original_rows': len(original['rows']), 'restored_rows': len(rows)})
        print(f'{policy}: {protocol["seeds"] * 5} episodes checked', flush=True)
    total = len(episodes) * len(protocol['policies'])
    if checked + recovered != total:
        raise ValueError('incomplete aggregate')
    receipt = dict(kind='query-history-recovery/v1', created_at=datetime.now(ZoneInfo('America/Los_Angeles')).isoformat(),
                   protocol_sha256=sha(protocol_blob), panel_sha256=actual_panel,
                   code_commit=subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip(),
                   script_sha256=sha(Path(__file__).read_bytes()),
                   expected_episodes=total, original_rows_crosschecked=checked,
                   missing_rows_recovered=recovered, queries_checked_against_source=queries_checked,
                   inputs=inputs, limitations=['Policy runtime not reconstructed; missing wall_s is null.',
                   'This checks source observations and ledger outcomes, not biological interval coverage.',
                   'Original seven-policy experiment only; later ablations are separate.'])
    (args.out / 'recovery_receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k != 'inputs'}, indent=2))


if __name__ == '__main__':
    main()
