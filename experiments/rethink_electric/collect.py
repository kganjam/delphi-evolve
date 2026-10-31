"""Fetch the Allen Institute Cell Types metadata + NWB files for a PRE-REGISTERED subset and extract features.

Selection rule (fixed before any prediction was computed): all mouse cells (donor__species == 'Mus musculus') that
have an ephys NWB file id, sorted by specimen id ascending; keep every 19th starting at index 0.
NWB files are downloaded into --workdir (never committed). Output: results/cell_features.json (derived measurements).
"""
from __future__ import annotations

import argparse, hashlib, json, sys, time, urllib.request
from pathlib import Path

from .nwb_features import extract

API = ("https://api.brain-map.org/api/v2/data/query.json?criteria=model::ApiCellTypesSpecimenDetail,"
       "rma::options[num_rows$eq3000]")
DL = "https://api.brain-map.org/api/v2/well_known_file_download/{}"
STRIDE = 19
HERE = Path(__file__).resolve().parent


def fetch(url, dest: Path, tries=3):
    for k in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=120) as r, open(dest, "wb") as fh:
                fh.write(r.read())
            return
        except Exception:
            time.sleep(2 * (k + 1))
    raise RuntimeError(f"download failed {url}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--out", default=str(HERE / "results" / "cell_features.json"))
    a = ap.parse_args()
    wd = Path(a.workdir); wd.mkdir(parents=True, exist_ok=True)
    meta_path = wd / "celltypes_meta.json"
    if not meta_path.exists():
        fetch(API.replace("$", "$"), meta_path)
    meta = json.loads(meta_path.read_text())
    cells = sorted((c for c in meta["msg"] if c["donor__species"] == "Mus musculus" and c["erwkf__id"]),
                   key=lambda c: c["specimen__id"])
    chosen = cells[::STRIDE]
    rows = []
    for c in chosen:
        p = wd / f"{c['erwkf__id']}.nwb"
        if not p.exists():
            fetch(DL.format(c["erwkf__id"]), p)
        feat = extract(str(p))
        feat.pop("nwb")
        feat.update({k: c[k] for k in ["specimen__id", "erwkf__id", "structure__acronym", "structure__layer",
                                       "tag__dendrite_type", "line_name", "ef__ri", "ef__tau", "ef__vrest",
                                       "ef__threshold_i_long_square"]})
        feat["nwb_sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
        feat["nwb_url"] = DL.format(c["erwkf__id"])
        rows.append(feat)
        print(len(rows), c["specimen__id"], feat.get("rheobase_ls_pA"), feat.get("short_thr_hi_pA"), file=sys.stderr, flush=True)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps({"selection": "mouse cells with NWB, sorted by specimen__id, every %dth from 0" % STRIDE,
                                      "n_candidates": len(cells), "n_selected": len(chosen), "api_url": API,
                                      "cells": rows}, indent=1))


if __name__ == "__main__":
    main()
