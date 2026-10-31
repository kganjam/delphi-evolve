"""AT5: gate vs ablations vs plain formula on a frozen Scope Desk bench (Turing 1-D, Turing 2-D, wavelength-licence families).
Usage: python3 -m scopedesk.oracles.at5 BENCHDIR OUT.json [LABEL]
BENCHDIR must contain instances_full.jsonl and key.jsonl (ids are the bench's opaque model_payload ids in v1.2). Exact counts and exact
(Clopper-Pearson) 95% intervals on counts; no statistics beyond that. Refused decisions (record_hash_changed) count as not agreeing
with the key and are also reported as refusals: they are a provenance property, not a scientific error."""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

from scipy.stats import beta

from . import gate, linear

MODES = (("full", {}), ("record_removed", {"record_removed": True}), ("record_hash_changed", {"record_hash_changed": True}),
         ("continuum_only", {"continuum_only": True}))
FAMS = ("turing_finite_domain", "turing_2d_rectangle", "wavelength_formula_licence")


def cp(k, n, a=0.05):
    if n == 0:
        return None
    lo = 0.0 if k == 0 else float(beta.ppf(a / 2, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(1 - a / 2, k + 1, n - k))
    return [round(lo, 3), round(hi, 3)]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(bench, out, label=""):
    bench = Path(bench)
    full = [json.loads(l) for l in open(bench / "instances_full.jsonl")]
    key = {json.loads(l)["id"]: json.loads(l) for l in open(bench / "key.jsonl")}
    rows = []
    for it in full:
        fam = it["family"]
        if fam not in FAMS:
            continue
        s, k = it["hidden"]["structured"], key[it["id"]]
        row = {"id": it["id"], "family": fam, "key": k["verdict"], "key_conditions": k["condition_ids"]}
        if fam == "wavelength_formula_licence":
            row["C0"] = "applies"
            for m, fl in MODES:
                d = gate.decide_wavelength(s, **fl)
                row[m] = d["decision"]
                if m == "full":
                    row["full_conditions"] = d["condition_ids"]
        else:
            row["C0"] = linear.plain_formula(s)["scope_verdict"]
            for m, fl in MODES:
                d = gate.decide(s, **fl)
                row[m] = d["decision"]
                if m == "full":
                    row["full_conditions"] = d["condition_ids"]
        rows.append(row)
    tab, cols = {}, ["C0"] + [m for m, _ in MODES]
    for fam in FAMS + ("ALL",):
        fr = [r for r in rows if fam == "ALL" or r["family"] == fam]
        n = len(fr)
        e = {"n": n, "key_counts": dict(Counter(r["key"] for r in fr))}
        for c in cols:
            ok = sum(r[c] == r["key"] for r in fr)
            ref = sum(r[c].startswith("refused") for r in fr)
            flips = sum(r[c] != r["full"] for r in fr)
            e[c] = {"agree_with_key": ok, "of": n, "ci95_exact": cp(ok, n), "refused": ref, "wrong_non_refusal": n - ok - ref,
                    "changed_vs_full_gate": flips}
        e["C0_wrong_but_full_right"] = sum(r["C0"] != r["key"] and r["full"] == r["key"] for r in fr)
        e["C0_right_but_full_wrong"] = sum(r["C0"] == r["key"] and r["full"] != r["key"] for r in fr)
        tab[fam] = e
    res = {"label": label, "bench_dir_files_sha256": {f: sha(bench / f) for f in ("key.jsonl", "instances_full.jsonl")},
           "bench_commit": (bench / "COMMIT").read_text().strip() if (bench / "COMMIT").exists() else None,
           "table": tab, "rows": rows,
           "notes": ["C0 = plain textbook inequality for Turing families; for the wavelength family C0 = 'the formula is adequate' (always applies)",
                     "record_removed falls back to C0 by construction; continuum_only = records valid, finite-domain/boundary/dimensionality ignored",
                     "record_hash_changed refuses every item: it measures provenance dependence, not scientific value",
                     "agreement with the key shares the bench's convention document; not external validation"]}
    Path(out).write_text(json.dumps(res, indent=1))
    for fam, e in tab.items():
        print(fam, e["n"], {c: f"{e[c]['agree_with_key']}/{e['n']}" for c in cols}, "C0 wrong/full right:", e["C0_wrong_but_full_right"])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "")
