#!/usr/bin/env python3
"""Descriptive pilot on the KCNQ1 MAVE supplement (medRxiv 2025.12.15.25341924, CC BY 4.0). Not a benchmark.

usage: python3 -I research-electric-kcnq1-pilot.py media-2.xlsx OUT.json
File S1 = MAVE scores per variant; File S2 = literature patch-clamp rows (V1/2act etc.).
Stdlib only; single thread; xlsx parsed directly from XML.
"""
import zipfile, re, sys, json, math, hashlib, collections


def read_sheets(path):
    x = zipfile.ZipFile(path)
    strs = [re.sub(r'<[^>]+>', '', s) for s in re.findall(r'<si>(.*?)</si>', x.read('xl/sharedStrings.xml').decode(), flags=re.S)]
    sheets = {}
    for i, name in enumerate(re.findall(r'<sheet [^>]*name="([^"]+)"', x.read('xl/workbook.xml').decode()), 1):
        d = x.read(f'xl/worksheets/sheet{i}.xml').decode(); rows = []
        for r in re.findall(r'<row [^>]*>(.*?)</row>', d, flags=re.S):
            row = {}
            for col, attr, v in re.findall(r'<c r="([A-Z]+)\d+"([^>]*?)(?:/>|>(?:<v>(.*?)</v>)?)', r):
                row[col] = strs[int(v)] if 't="s"' in attr and v else v
            rows.append(row)
        sheets[name] = rows
    return sheets


def table(rows):
    hdr = rows[0]; cols = {c: hdr[c] for c in hdr}
    return [{cols[c]: r.get(c, '') for c in cols} for r in rows[1:]]


def fl(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


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
    if len(a) < 5:
        return None
    ra, rb = rank(a), rank(b); n = len(a); ma = sum(ra) / n; mb = sum(rb) / n
    d = math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))
    return sum((x - ma) * (y - mb) for x, y in zip(ra, rb)) / d if d else None


def main(path, outp):
    sh = read_sheets(path)
    s1 = table(sh['File S1']); s2 = table(sh['File S2'])
    mave = {r['mutation']: r for r in s1}
    res = {'xlsx_sha256': hashlib.sha256(open(path, 'rb').read()).hexdigest(),
           'S1_rows': len(s1), 'S1_mut_type_counts': dict(collections.Counter(r['mut_type'] for r in s1)),
           'S2_rows': len(s2), 'S2_cell_types': dict(collections.Counter(r['cell type'] for r in s2)),
           'S2_distinct_mutations': len({r['mutation'] for r in s2}),
           'S2_distinct_papers': len({r['paper'] for r in s2})}
    # pair literature V1/2act with MAVE scores; one value per mutation (median over papers/cell types) to avoid pseudo-replication
    per = collections.defaultdict(list)
    for r in s2:
        dv = fl(r['deltaV1/2act(Mut-WT)'])
        if dv is not None and r['mutation'] in mave:
            per[r['mutation']].append(dv)
    med = lambda v: sorted(v)[len(v) // 2]
    muts = sorted(per)
    res['n_mutations_with_deltaV12_and_MAVE'] = len(muts)
    for field in ('trafficking_score', 'function_score'):
        pr = [(med(per[m]), fl(mave[m][field])) for m in muts if fl(mave[m][field]) is not None]
        res[f'spearman_deltaV12act_vs_{field}'] = {'n': len(pr), 'rho': spearman([a for a, _ in pr], [b for _, b in pr])}
        res[f'spearman_abs_deltaV12act_vs_{field}'] = {'n': len(pr), 'rho': spearman([abs(a) for a, _ in pr], [b for _, b in pr]),
                                                      'note': 'absolute shift removes the sign ambiguity (activation can shift either way)'}
    # does MAVE function separate "normal-gating" from "shifted" variants? count only; no model
    shifted = [m for m in muts if abs(med(per[m])) >= 10]
    res['n_with_abs_deltaV12_ge_10mV'] = len(shifted)
    res['among_shifted_function_scores_ge_0.75_of_WT_like'] = sum(1 for m in shifted if (fl(mave[m]['function_score']) or 0) >= 0.75)
    res['caveats'] = ('literature rows are heterogeneous (cell type, protocol, KCNE1 co-expression not tracked here); one median per mutation; '
                      'descriptive only; thresholds 10 mV and 0.75 are arbitrary illustration, not validated; no held-out evaluation')
    json.dump(res, open(outp, 'w'), indent=1, sort_keys=True)
    print(json.dumps(res, sort_keys=True)[:1500])


if __name__ == '__main__':
    main(*sys.argv[1:3])
