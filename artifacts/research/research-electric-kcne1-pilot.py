#!/usr/bin/env python3
"""Descriptive pilot on KCNE1 MaveDB score sets (CC0). Not a benchmark result.

usage: python3 -I research-electric-kcne1-pilot.py TRAFFICKING.csv FUNCTION.csv OUT.json
Inputs: MaveDB urn:mavedb:00000674-a-2 (trafficking) and -b-1 (function) scores CSVs.
Standard library only; single thread.
"""
import csv, re, sys, json, math, hashlib, collections


def load(path):
    out = {}
    for r in csv.DictReader(open(path)):
        m = re.match(r'p\.([A-Za-z]{3})(\d+)([A-Za-z]{3}|=)$', r['hgvs_pro'])
        if not m:
            continue
        try:
            s = float(r['score'])
        except ValueError:
            continue
        out[(m.group(1), int(m.group(2)), m.group(3))] = (s, r['category'])
    return out


def rank(x):
    o = sorted(range(len(x)), key=lambda i: x[i]); r = [0.0] * len(x); i = 0
    while i < len(o):
        j = i
        while j + 1 < len(o) and x[o[j + 1]] == x[o[i]]:
            j += 1
        for t in range(i, j + 1):
            r[o[t]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(a, b):
    ra, rb = rank(a), rank(b); n = len(a); ma = sum(ra) / n; mb = sum(rb) / n
    c = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    return c / math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))


def main(tp, fp, outp):
    E, F = load(tp), load(fp)
    mis = lambda k: k[2] not in ('Ter', '=')
    Em = {k: v for k, v in E.items() if mis(k)}
    Fm = {k: v for k, v in F.items() if mis(k)}
    both = [k for k in Em if k in Fm]
    pos = collections.defaultdict(list)
    for k in both:
        pos[k[1]].append(k)
    pred, obs = [], []
    for k in both:
        others = [Fm[o][0] for o in pos[k[1]] if o != k]
        if len(others) >= 2:
            pred.append(sum(others) / len(others)); obs.append(Fm[k][0])
    # held-out-position cheap baseline: mean function of variants at neighbouring positions (|d|<=W), excluding the held-out position
    import random
    def window_baseline(W):
        pr, ob, ps = [], [], []
        for k in both:
            vals = [Fm[o][0] for d in range(-W, W + 1) if d != 0 for o in pos.get(k[1] + d, [])]
            if len(vals) >= 3:
                pr.append(sum(vals) / len(vals)); ob.append(Fm[k][0]); ps.append(k[1])
        rho = spearman(pr, ob)
        byp = collections.defaultdict(list)
        for i, q in enumerate(ps):
            byp[q].append(i)
        plist = sorted(byp); rng = random.Random(0); bs = []
        for _ in range(200):
            idx = [i for q in (rng.choice(plist) for _ in plist) for i in byp[q]]
            bs.append(spearman([pr[i] for i in idx], [ob[i] for i in idx]))
        bs.sort()
        return {'window': W, 'n': len(pr), 'n_positions': len(plist), 'spearman': rho,
                'position_bootstrap_2.5_97.5_percentile': [bs[5], bs[194]], 'bootstrap': '200 resamples of positions, seed 0; empirical spread, not a formal confidence level'}
    windows = [window_baseline(W) for W in (1, 2, 3)]
    ct = collections.Counter((Em[k][1], Fm[k][1]) for k in both)
    res = {
        'inputs_sha256': {p: hashlib.sha256(open(p, 'rb').read()).hexdigest() for p in (tp, fp)},
        'n_trafficking_rows_parsed': len(E), 'n_function_rows_parsed': len(F),
        'n_missense_trafficking': len(Em), 'n_missense_function': len(Fm), 'n_paired_missense': len(both),
        'spearman_trafficking_vs_function': spearman([Em[k][0] for k in both], [Fm[k][0] for k in both]),
        'leave_one_variant_out_same_position_mean': {'n': len(pred), 'spearman': spearman(pred, obs),
            'caveat': 'uses same-position variants; a ceiling, NOT a held-out-position baseline'},
        'held_out_position_window_mean_baseline': windows,
        'crosstab_trafficking_by_function': {f'traf={a}|func={b}': n for (a, b), n in sorted(ct.items())},
        'limits': 'descriptive; categories as supplied by MaveDB; no held-out-position evaluation; not a benchmark',
    }
    json.dump(res, open(outp, 'w'), indent=1, sort_keys=True)
    print(json.dumps({k: res[k] for k in ('n_paired_missense', 'spearman_trafficking_vs_function', 'leave_one_variant_out_same_position_mean', 'held_out_position_window_mean_baseline')}))


if __name__ == '__main__':
    main(*sys.argv[1:4])
