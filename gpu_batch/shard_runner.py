#!/usr/bin/env python3
"""Job-side runner: score fixed label-free units of the 20^4 TrpB library with one ESM2 checkpoint.

Reuses the gpu worker's vendored embed_trpb.py (model loading, tokenizer, residue mapping, masking,
`score_batch`) unchanged; this file only adds
  * a model registry (ablation across ESM2 sizes, TE checkpoints, pinned revisions),
  * fixed units of the seeded permutation (so partial completion is a random, label-free subset),
  * one extra scoring protocol (all four sites masked at once),
  * seeded Gaussian random projections of site / mean-pooled embeddings (shard-independent, label-free),
  * resumable per-unit output plus throttled, checksummed log emission (RESULT_FILE/CHUNK/END, same
    format as gpu/recover_from_logs.py).

No fitness value is read here.  Outputs are model predictions, never measurements.
"""
import argparse
import base64
import hashlib
import json
import os
import signal
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# unit k = permutation[k*UNIT : (k+1)*UNIT];  32 units cover the 160,000-variant library
UNIT = 5000
RP_SEED = 20261101          # projection seed, fixed before any output existed

# repo, revision (HF commit sha at time of writing, fetched 2026-10-31), kind
REGISTRY = {
    "te8m":   ("nvidia/esm2_t6_8M_UR50D",    "3674a6acb6c217bbeff709d182a11b196125dfc3", "te"),
    "te35m":  ("nvidia/esm2_t12_35M_UR50D",  "ca13c2d411d8aad9ea8dfa1f24a80a36a8946b5e", "te"),
    "te150m": ("nvidia/esm2_t30_150M_UR50D", "a2e82bef92128da1852464b0864651b1a11337d0", "te"),
    "te650m": ("nvidia/esm2_t33_650M_UR50D", "118f470e7e96ba8741227ab898e54758850e9563", "te"),
    "te3b":   ("nvidia/esm2_t36_3B_UR50D",   "0850cbdf0494675c6db7a5d0d7390ceed3b3504c", "te"),
    "te15b":  ("nvidia/esm2_t48_15B_UR50D",  "5c74319d3e978737870f326e464f142eb2f7c666", "te"),
    "plain3b": ("facebook/esm2_t36_3B_UR50D", "476b639933c8baad5ad09a60ac1a87f987b656fc", "plain"),
    "plain8m": ("facebook/esm2_t6_8M_UR50D", "c731040fcd8d73dceaa04b0a8e6329b345b0f5df", "plain"),
    "plain150m": ("facebook/esm2_t30_150M_UR50D", "a695f6045e2e32885fa60af20c13cb35398ce30c", "plain"),
}

T0 = time.time()
STOP = {"flag": False}


def log(event, **kw):
    print("GPULOG " + json.dumps({"t": round(time.time() - T0, 2), "event": event, **kw}, default=str), flush=True)


# ---------------------------------------------------------------- pure helpers (unit-tested on CPU)
def unit_indices(perm, k, unit=UNIT):
    return np.asarray(perm[k * unit:(k + 1) * unit])


def parse_units(spec):
    """'0-3,7,9-10' -> [0,1,2,3,7,9,10]"""
    out = []
    for part in str(spec).split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-")
            out += list(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return sorted(set(out))


def projection_matrix(d_in, d_out, tag):
    """Deterministic Gaussian JL projection; depends only on (d_in, d_out, tag, RP_SEED)."""
    seed = int.from_bytes(hashlib.sha256(f"{RP_SEED}|{d_in}|{d_out}|{tag}".encode()).digest()[:8], "little")
    return (np.random.default_rng(seed).standard_normal((d_in, d_out)) / np.sqrt(d_out)).astype(np.float32)


def npz_bytes(**arrays):
    import io
    buf = io.BytesIO()
    np.savez_compressed(buf, **arrays)
    return buf.getvalue()


def emit_blob_throttled(name, raw, chunk_chars=6000, sleep_s=0.02, out=None):
    """Same wire format as embed_trpb.emit_blob, but throttled to <=~50 lines/s so that second-resolution
    log timestamps can be paged without collapsing >1000 lines into a single second (see logpage.py)."""
    out = out or (lambda s: print(s, flush=True))
    b64 = base64.b64encode(raw).decode()
    n = (len(b64) + chunk_chars - 1) // chunk_chars
    out("RESULT_FILE " + json.dumps({"name": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "chunks": n}))
    for i in range(n):
        part = b64[i * chunk_chars:(i + 1) * chunk_chars]
        out(f"RESULT_CHUNK {name} {i} {n} {hashlib.sha256(part.encode()).hexdigest()[:12]} {part}")
        time.sleep(sleep_s)
    out("RESULT_END " + name)


# ---------------------------------------------------------------- scoring (needs torch + vendored embed_trpb)
def score_all_masked(E, model, tk, digits):
    """log p(observed aa) at the four library sites with ALL four sites masked simultaneously (one pass).
    Independent-site factorisation: an alternative scoring protocol, not a joint likelihood."""
    import torch
    ids = E.make_ids(tk, digits)
    sites = torch.tensor(E.R.SITES, device=ids.device)
    obs = ids[:, sites]
    ids2 = ids.clone()
    ids2[:, sites] = tk.mask
    h = E.hidden(model, ids2)
    lg = model.lm_head(h[:, sites]).float().log_softmax(-1)
    return lg.gather(-1, obs.unsqueeze(-1)).squeeze(-1).cpu().numpy()


def score_unit(E, model, tk, lin, bs, proj_site, proj_mean):
    import torch
    parts = []
    with torch.inference_mode():
        for i in range(0, len(lin), bs):
            digs = E.lin_to_digits(lin[i:i + bs])
            r = E.score_batch(model, tk, digs, want_emb=True)
            r["lp_all"] = score_all_masked(E, model, tk, digs)
            se = torch.as_tensor(r.pop("site_emb"), dtype=torch.float32, device=proj_site.device)   # (B,4,d)
            mp = torch.as_tensor(r.pop("meanpool"), dtype=torch.float32, device=proj_site.device)    # (B,d)
            r["site_rp"] = (se @ proj_site).half().cpu().numpy()                                      # (B,4,e)
            r["mean_rp"] = (mp @ proj_mean).half().cpu().numpy()                                      # (B,e)
            parts.append(r)
    return {k: np.concatenate([p[k] for p in parts]) for k in parts[0]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-key", required=True, choices=sorted(REGISTRY))
    ap.add_argument("--units", required=True, help="e.g. 0-7")
    ap.add_argument("--unit-size", type=int, default=UNIT)
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--rp-dim", type=int, default=32, help="random-projection dims per site and for mean-pool")
    ap.add_argument("--max-minutes", type=float, default=95.0, help="do not START a unit after this many minutes")
    ap.add_argument("--out", default="/output/scale")
    ap.add_argument("--no-emit-logs", action="store_true")
    ap.add_argument("--limit-variants", type=int, default=0, help="smoke tests only; marks output as partial")
    ap.add_argument("--device", default="cuda")
    a = ap.parse_args()

    import embed_trpb as E   # vendored, pinned by sha256 in the job manifest
    E.DEVICE = a.device
    repo, rev, kind = REGISTRY[a.model_key]
    if kind == "te":
        E.TE_REPO, E.TE_REV = repo, rev
        load_kind = "te_bf16"
    else:
        E.PLAIN_REPO, E.PLAIN_REV = repo, rev
        load_kind = "plain_bf16"
    import torch
    if a.device == "cpu":
        load_kind = "plain_fp32" if kind == "plain" else load_kind
    signal.signal(signal.SIGTERM, lambda *_: STOP.update(flag=True))

    hdr, ref = E.R.load_reference()
    log("reference", header=hdr, length=len(ref), sites={p: ref[p - 1] for p in E.R.SITES}, fasta_sha256=E.R.FASTA_SHA256)
    env = E.env_record()
    log("env", **env, model_key=a.model_key, repo=repo, revision=rev)
    # tokenizer comes from the (identical-vocab) Meta repo pinned inside embed_trpb
    tk = E.Tok()
    model = E.load_model(load_kind)
    d = E.base_of(model).config.hidden_size if hasattr(E.base_of(model), "config") else model.config.hidden_size
    proj_site = torch.as_tensor(projection_matrix(d, a.rp_dim, "site"), device=a.device)
    proj_mean = torch.as_tensor(projection_matrix(d, a.rp_dim, "mean"), device=a.device)
    perm = E.R.permuted_order()
    os.makedirs(a.out, exist_ok=True)
    units = parse_units(a.units)

    # per-model WT references (parent VFVS) so a prior can be expressed relative to the parent
    with torch.inference_mode():
        wt_tab = E.wt_masked_table(model, tk)
        wt_idx = np.array([E.R.all_genotypes().index(E.R.PARENT)])
        wt = score_unit(E, model, tk, wt_idx, 1, proj_site, proj_mean)
    meta = dict(model_key=a.model_key, repo=repo, revision=rev, hidden_size=int(d), rp_dim=a.rp_dim, rp_seed=RP_SEED,
                unit_size=a.unit_size, permutation_seed=E.R.PERMUTATION_SEED, aa_order=E.R.AA20, sites=list(E.R.SITES),
                env=env, job_label=os.environ.get("JOB_LABEL"))
    meta_name = f"meta_{a.model_key}_{os.environ.get('JOB_LABEL', 'local')}.npz"
    meta_raw = npz_bytes(wt_masked_table_20aa=wt_tab.astype(np.float32), wt_lp_un=wt["lp_un"][0], wt_lp_mask=wt["lp_mask"][0],
                         wt_lp_all=wt["lp_all"][0], meta_json=np.frombuffer(json.dumps(meta, default=str).encode(), dtype=np.uint8))
    if not a.no_emit_logs:
        emit_blob_throttled(meta_name, meta_raw)
    open(os.path.join(a.out, meta_name), "wb").write(meta_raw)

    t_start, done = time.time(), []
    for k in units:
        path = os.path.join(a.out, f"unit_{a.model_key}_{k:03d}.npz")
        if os.path.exists(path):
            done.append(k)
            log("unit_skip_existing", unit=k)
            continue
        if STOP["flag"] or (time.time() - t_start) / 60 > a.max_minutes:
            log("stop_before_unit", unit=k, sigterm=STOP["flag"], minutes=round((time.time() - t_start) / 60, 1))
            break
        lin = unit_indices(perm, k, a.unit_size)
        if a.limit_variants:
            lin = lin[:a.limit_variants]
        t = time.time()
        r = score_unit(E, model, tk, lin, a.batch, proj_site, proj_mean)
        dt = time.time() - t
        raw = npz_bytes(variant_index=lin.astype(np.int32), partial=np.array(bool(a.limit_variants)), **r)
        open(path + ".tmp", "wb").write(raw)
        os.replace(path + ".tmp", path)
        name = os.path.basename(path)
        if not a.no_emit_logs:
            emit_blob_throttled(name, raw)
        done.append(k)
        log("unit_done", unit=k, n=int(len(lin)), seconds=round(dt, 1), variants_per_s=round(len(lin) / dt, 1),
            bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(), peak_mem_gb=round(torch.cuda.max_memory_allocated() / 1e9, 2)
            if a.device == "cuda" else None)
    summary = dict(model_key=a.model_key, repo=repo, revision=rev, units_requested=units, units_done=done,
                   wall_seconds=round(time.time() - T0, 1), complete=bool(set(units) <= set(done)),
                   partial=bool(a.limit_variants))
    print("RESULT_JSON summary_" + a.model_key + "_" + os.environ.get("JOB_LABEL", "local") + " " + json.dumps(summary), flush=True)
    log("done", **summary)
    return 0     # a deliberate time-guard stop is not a failure; completeness is in the summary


if __name__ == "__main__":
    sys.exit(main())
