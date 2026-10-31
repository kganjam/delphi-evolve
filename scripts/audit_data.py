#!/usr/bin/env python3
"""Independent integration audit of the TrpB source CSVs (does not import evolve/).

Recomputes: file SHA256s, row counts, measured-vs-imputed counts and overlap,
stop-codon exclusion, and checks that raw mu columns exist. Writes JSON to
stdout. Usage: python3 -I scripts/audit_data.py <dir-with-csvs>
"""
import csv, hashlib, json, sys, pathlib


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main(d):
    d = pathlib.Path(d)
    out = {"files": {}}
    for n in ("simplified_AA.csv", "summary_AA.csv", "KNN_imputed_TrpB.csv"):
        out["files"][n] = {"sha256": sha(d / n), "bytes": (d / n).stat().st_size}
    measured, stop_rows, total = set(), 0, 0
    with open(d / "summary_AA.csv", newline="") as f:
        r = csv.DictReader(f)
        out["summary_columns"] = r.fieldnames
        for row in r:
            total += 1
            if float(row["# Stop"]) > 0:
                stop_rows += 1
            else:
                measured.add(row["AAs"])
    imputed = set()
    with open(d / "KNN_imputed_TrpB.csv", newline="") as f:
        for row in csv.DictReader(f):
            imputed.add(row["AAs"])
    out.update(
        total_source_rows=total,
        stop_containing_rows=stop_rows,
        measured_no_stop=len(measured),
        imputed=len(imputed),
        overlap_measured_imputed=len(measured & imputed),
        library_20_pow_4=20**4,
        measured_fraction_of_library=round(len(measured) / 20**4, 5),
    )
    return out


if __name__ == "__main__":
    print(json.dumps(main(sys.argv[1]), indent=2))
