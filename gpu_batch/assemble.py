"""Recover shard-job outputs from Nebius job logs and assemble per-model, library-aligned arrays.

  python -m gpu_batch.assemble recover  <job-id> <outdir>
  python -m gpu_batch.assemble library  <model_key> <outdir-with-unit-files...> --out DIR

Library order is the lexicographic AA20 order with position 183 most significant, i.e. the same linear
index as evolve.data.encode / trpb_ref.all_genotypes (checked in tests).  Nothing here reads a fitness value.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "vendor"))
import recover_from_logs as RL  # noqa: E402  (vendored, pinned)
import trpb_ref as R  # noqa: E402

N = R.N_VARIANTS
UNIT_RE = re.compile(r"unit_(?P<model>[a-z0-9]+)_(?P<k>\d{3})\.npz$")


def recover_job(job_id, outdir, neb="nebius", profile="hackathon", get_job=None, fetch=None):
    """Time-paged log fetch (vendored fetch_job_logs.py) + checksummed blob recovery."""
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    if get_job is None:
        from . import nebius_cli
        get_job = nebius_cli.get_job
    job = get_job(job_id)
    created = job["metadata"]["created_at"]
    end = dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=2)
    log_path = outdir / f"{job_id}.log"
    fetch = fetch or (lambda a, b, p: subprocess.run(
        [sys.executable, str(HERE / "vendor/fetch_job_logs.py"), job_id, a, b, str(p)], check=True, capture_output=True))
    fetch(created, end.isoformat(), log_path)
    written, jsons = RL.recover(log_path.read_text(errors="replace"), outdir / "recovered")
    return {"job_id": job_id, "log": str(log_path), "log_sha256": hashlib.sha256(log_path.read_bytes()).hexdigest(),
            "files": written, "json": jsons}


def load_units(model_key, dirs):
    """Return {unit_index: dict(arrays)}.  Duplicate units from different jobs must be identical or we refuse."""
    units, srcs = {}, {}
    for d in dirs:
        for p in sorted(Path(d).glob(f"unit_{model_key}_*.npz")):
            m = UNIT_RE.search(p.name)
            k = int(m["k"])
            z = np.load(p)
            arr = {f: z[f] for f in z.files}
            if bool(arr.pop("partial", False)):
                raise ValueError(f"{p}: partial smoke output must not be assembled")
            if k in units:
                for f in ("variant_index", "lp_mask", "lp_un", "lp_all"):
                    if not np.array_equal(units[k][f], arr[f]):
                        raise ValueError(f"unit {k} from {p} and {srcs[k]} differ in {f}; refusing silent overwrite")
                continue
            units[k], srcs[k] = arr, str(p)
    return units


def assemble(units, unit_size=5000):
    """Place unit rows at their library index.  Returns arrays + boolean coverage mask; checks the partition."""
    perm = R.permuted_order()
    out, have = {}, np.zeros(N, bool)
    for k, a in sorted(units.items()):
        vi = a["variant_index"].astype(np.int64)
        expect = perm[k * unit_size:(k + 1) * unit_size]
        if not np.array_equal(vi, expect):
            raise ValueError(f"unit {k}: variant_index differs from the seeded permutation block")
        if have[vi].any():
            raise ValueError(f"unit {k} overlaps an earlier unit")
        for f, v in a.items():
            if f == "variant_index":
                continue
            if f not in out:
                out[f] = np.full((N,) + v.shape[1:], np.nan if v.dtype.kind == "f" else 0, dtype=v.dtype)
            out[f][vi] = v
        have[vi] = True
    return out, have


def scalar_priors(lib, wt, have):
    """Label-free scalar priors (higher = predicted more tolerated/functional), relative to the parent VFVS.

    mm_wt   additive WT-marginal: sum_j [ T[j, aa_j] - T[j, parent_j] ]    (T = WT-context single-site-masked table)
    mm_ctx  context-aware single-site-masked pseudo-LLR, sum_j lp_mask - parent
    unmasked  sum_j lp_un - parent                    (observed residue visible to the model)
    allmask   sum_j lp_all - parent                   (all four sites masked at once; independent-site product)
    Each is z-scored over covered variants (mean 0, sd 1); uncovered entries are NaN.
    """
    aa = {a: i for i, a in enumerate(R.AA20)}
    par = [aa[c] for c in R.PARENT]
    T = wt["wt_masked_table_20aa"]
    idx = np.arange(N)
    digs = np.stack([idx // 8000, (idx // 400) % 20, (idx // 20) % 20, idx % 20], 1)
    mm_wt = sum(T[j, digs[:, j]] - T[j, par[j]] for j in range(4))
    raw = {"mm_wt": mm_wt.astype(np.float64),
           "mm_ctx": lib["lp_mask"].sum(1).astype(np.float64) - float(wt["wt_lp_mask"].sum()),
           "unmasked": lib["lp_un"].sum(1).astype(np.float64) - float(wt["wt_lp_un"].sum()),
           "allmask": lib["lp_all"].sum(1).astype(np.float64) - float(wt["wt_lp_all"].sum())}
    z = {}
    for k, v in raw.items():
        v = np.where(have, v, np.nan)
        z[k] = (v - np.nanmean(v)) / np.nanstd(v)
    return raw, z


def load_meta(path):
    z = np.load(path)
    meta = json.loads(bytes(z["meta_json"]).decode())
    return {f: z[f] for f in z.files if f != "meta_json"}, meta


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("recover")
    r.add_argument("job_id")
    r.add_argument("outdir")
    lb = sub.add_parser("library")
    lb.add_argument("model_key")
    lb.add_argument("dirs", nargs="+")
    lb.add_argument("--meta", required=True)
    lb.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.cmd == "recover":
        print(json.dumps(recover_job(a.job_id, a.outdir), indent=1))
        return
    units = load_units(a.model_key, a.dirs)
    lib, have = assemble(units)
    wt, meta = load_meta(a.meta)
    raw, z = scalar_priors(lib, wt, have)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out / f"{a.model_key}_library.npz", have=have, **lib, **{f"raw_{k}": v for k, v in raw.items()},
                        **{f"z_{k}": v for k, v in z.items()}, meta_json=np.frombuffer(json.dumps(meta, default=str).encode(), dtype=np.uint8))
    print(json.dumps({"model": a.model_key, "units": sorted(units), "covered": int(have.sum()), "complete": bool(have.all())}))


if __name__ == "__main__":
    main()
