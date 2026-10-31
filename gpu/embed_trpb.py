#!/usr/bin/env python3
"""ESM2-650M inference over the TrpB four-site library (Tm9D8s* background).

Runs inside an NVIDIA PyTorch container on one H100.  Stages:

  probe   environment record, load both models, tiny parity check, log-transport test
  parity  BioNeMo-TE checkpoint vs plain Meta ESM2 on a seeded label-free batch + throughput
  main    all (or a bounded prefix of a seeded permutation of) 20^4 variants with the TE model

Models (revisions pinned):
  te    nvidia/esm2_t33_650M_UR50D   NVIDIA BioNeMo-recipes TransformerEngine ESM2 checkpoint (HF custom code)
  plain facebook/esm2_t33_650M_UR50D original Meta weights, plain PyTorch/Transformers (NOT BioNeMo)

No fitness/outcome value is read or available to this script.  Predictions are model
outputs, never measurements, and cannot certify fitness.

Result recovery: shards are written to --out (a mounted bucket when available) and
compact artifacts are ALSO emitted into the job log as RESULT_FILE/RESULT_CHUNK lines
(see recover_from_logs.py).
"""
import argparse
import base64
import gzip
import hashlib
import io
import json
import os
import platform
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trpb_ref as R  # noqa: E402

TE_REPO, TE_REV = "nvidia/esm2_t33_650M_UR50D", "118f470e7e96ba8741227ab898e54758850e9563"
PLAIN_REPO, PLAIN_REV = "facebook/esm2_t33_650M_UR50D", "08e4846e537177426273712802403f7ba8261b6c"
T0 = time.time()
DEVICE = "cuda"   # tests override to "cpu" with a tiny plain model


def log(event, **kw):
    print("GPULOG " + json.dumps({"t": round(time.time() - T0, 2), "event": event, **kw}, default=str), flush=True)


# ---------------------------------------------------------------- recovery via logs
CHUNK_CHARS = 6000


def emit_blob(name, raw: bytes):
    """Print a binary blob into the job log as checksummed base64 chunks."""
    b64 = base64.b64encode(raw).decode()
    n = (len(b64) + CHUNK_CHARS - 1) // CHUNK_CHARS
    print("RESULT_FILE " + json.dumps({"name": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                                       "chunks": n}), flush=True)
    for i in range(n):
        part = b64[i * CHUNK_CHARS:(i + 1) * CHUNK_CHARS]
        print(f"RESULT_CHUNK {name} {i} {n} {hashlib.sha256(part.encode()).hexdigest()[:12]} {part}", flush=True)
        if i % 50 == 49:
            time.sleep(0.4)   # the log API returns <=1000 lines per query and timestamps have 1 s resolution
    print("RESULT_END " + name, flush=True)


def npz_bytes(**arrays):
    buf = io.BytesIO()
    np.savez_compressed(buf, **arrays)
    return buf.getvalue()


# ---------------------------------------------------------------- environment
def sh(cmd):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60).stdout.strip()
    except Exception as e:  # noqa: BLE001
        return f"ERR {e}"


def env_record():
    import importlib.metadata as md
    import torch
    rec = {"python": platform.python_version(), "platform": platform.platform(), "torch": torch.__version__,
           "torch_cuda": torch.version.cuda, "cudnn": torch.backends.cudnn.version(),
           "cuda_available": torch.cuda.is_available(), "numpy": np.__version__}
    for pkg in ("transformers", "transformer_engine", "transformer-engine-torch", "huggingface_hub", "safetensors",
                "flash-attn", "tokenizers"):
        try:
            rec[pkg] = md.version(pkg)
        except md.PackageNotFoundError:
            rec[pkg] = None
    if torch.cuda.is_available():
        rec["gpu"] = torch.cuda.get_device_name(0)
        rec["gpu_capability"] = torch.cuda.get_device_capability(0)
    rec["nvidia_smi"] = sh("nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader")
    rec["image_ref"] = os.environ.get("IMAGE_REF")
    rec["job_label"] = os.environ.get("JOB_LABEL")
    rec["cpus"] = os.cpu_count()
    return rec


# ---------------------------------------------------------------- models
def load_model(kind):
    import torch
    from transformers import AutoModelForMaskedLM
    if kind == "te_bf16":
        repo, rev, dt, kw = TE_REPO, TE_REV, torch.bfloat16, {"trust_remote_code": True}
    elif kind == "plain_bf16":
        repo, rev, dt, kw = PLAIN_REPO, PLAIN_REV, torch.bfloat16, {"attn_implementation": "sdpa"}
    elif kind == "plain_fp32":
        repo, rev, dt, kw = PLAIN_REPO, PLAIN_REV, torch.float32, {"attn_implementation": "sdpa"}
    else:
        raise ValueError(kind)
    t = time.time()
    try:
        m = AutoModelForMaskedLM.from_pretrained(repo, revision=rev, dtype=dt, **kw)
    except TypeError:
        m = AutoModelForMaskedLM.from_pretrained(repo, revision=rev, torch_dtype=dt, **kw)
    m = m.to(DEVICE).eval()
    log("model_loaded", kind=kind, repo=repo, revision=rev, seconds=round(time.time() - t, 1),
        params=sum(p.numel() for p in m.parameters()), class_name=type(m).__name__)
    return m


def base_of(model):
    return model.esm if hasattr(model, "esm") else model.model


class Tok:
    """Minimal ESM tokenizer view: ids for the 20 amino acids, <cls>, <eos>, <mask>."""

    def __init__(self):
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained(PLAIN_REPO, revision=PLAIN_REV)
        self.tok = tok
        self.aa = [tok.convert_tokens_to_ids(a) for a in R.AA20]
        self.mask = tok.mask_token_id
        _, ref = R.load_reference()
        self.base_ids = tok(ref)["input_ids"]
        assert len(self.base_ids) == len(ref) + 2, "expected <cls> + residues + <eos>"
        assert self.base_ids[0] == tok.cls_token_id and self.base_ids[-1] == tok.eos_token_id
        assert all(isinstance(a, int) and a != tok.unk_token_id for a in self.aa)
        self.ref = ref


def lin_to_digits(idx):
    """Linear index -> (B,4) digits in AA20, position 183 most significant (== all_genotypes order)."""
    idx = np.asarray(idx)
    return np.stack([idx // 8000, (idx // 400) % 20, (idx // 20) % 20, idx % 20], axis=1)


def make_ids(tk, digits, device=None):
    device = device or DEVICE
    import torch
    base = torch.tensor(tk.base_ids, dtype=torch.long, device=device)
    ids = base.unsqueeze(0).repeat(len(digits), 1)
    aa = torch.tensor(tk.aa, dtype=torch.long, device=device)
    d = torch.as_tensor(digits, dtype=torch.long, device=device)
    for j, p in enumerate(R.SITES):
        ids[:, p] = aa[d[:, j]]          # residue p (1-based) sits at token index p because <cls> is index 0
    return ids


def hidden(model, ids):
    import torch
    return base_of(model)(input_ids=ids, attention_mask=torch.ones_like(ids)).last_hidden_state


def score_batch(model, tk, digits, want_emb=True):
    """Unmasked pass (embeddings, observed-aa log-prob) + 4 single-site-masked passes.

    lp_un[b, j]   log p(observed aa at site j | full variant, nothing masked)   (full 33-token softmax)
    lp_mask[b, j] log p(observed aa at site j | variant with ONLY site j masked)  (others are the variant's residues)
    """
    import torch
    ids = make_ids(tk, digits)
    sites = torch.tensor(R.SITES, device=ids.device)
    obs = ids[:, sites]                                              # (B,4)
    out = {}
    h = hidden(model, ids)
    if want_emb:
        out["meanpool"] = h[:, 1:-1].float().mean(1).half().cpu().numpy()
        out["site_emb"] = h[:, sites].half().cpu().numpy()
    lg = model.lm_head(h[:, sites]).float().log_softmax(-1)          # (B,4,V)
    out["lp_un"] = lg.gather(-1, obs.unsqueeze(-1)).squeeze(-1).cpu().numpy()
    lpm = []
    for j, p in enumerate(R.SITES):
        ids2 = ids.clone()
        ids2[:, p] = tk.mask
        h2 = hidden(model, ids2)
        l2 = model.lm_head(h2[:, p:p + 1]).float().log_softmax(-1)[:, 0]   # (B,V)
        lpm.append(l2.gather(-1, obs[:, j:j + 1]).squeeze(-1))
    out["lp_mask"] = torch.stack(lpm, 1).cpu().numpy()
    return out


def wt_masked_table(model, tk):
    """(4,20) log-softmax over the full vocabulary, restricted to the 20 amino acids, WT context, one site masked."""
    import torch
    base = torch.tensor(tk.base_ids, device=DEVICE).unsqueeze(0)
    tab = []
    for p in R.SITES:
        ids = base.clone()
        ids[0, p] = tk.mask
        h = hidden(model, ids)
        lp = model.lm_head(h[:, p:p + 1]).float().log_softmax(-1)[0, 0]
        tab.append(lp[torch.tensor(tk.aa, device=DEVICE)].cpu().numpy())
    return np.stack(tab)


def run_all(model, tk, lin, bs, want_emb=True):
    import torch
    parts = []
    with torch.inference_mode():
        for i in range(0, len(lin), bs):
            parts.append(score_batch(model, tk, lin_to_digits(lin[i:i + bs]), want_emb))
    return {k: np.concatenate([p[k] for p in parts]) for k in parts[0]}


def throughput(model, tk, lin, bs):
    """Single unmasked forward pass over len(lin) variants; warm-up excluded."""
    import torch
    with torch.inference_mode():
        for _ in range(2):
            hidden(model, make_ids(tk, lin_to_digits(lin[:bs])))
        torch.cuda.synchronize()
        torch.cuda.reset_peak_memory_stats()
        t = time.time()
        for i in range(0, len(lin), bs):
            hidden(model, make_ids(tk, lin_to_digits(lin[i:i + bs])))
        torch.cuda.synchronize()
        dt = time.time() - t
    L = len(tk.base_ids)
    return {"variants": int(len(lin)), "batch": bs, "seconds": round(dt, 3), "seq_per_s": round(len(lin) / dt, 1),
            "tokens_per_s": round(len(lin) * L / dt, 0), "peak_mem_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2)}


# ---------------------------------------------------------------- parity
def cos_rows(a, b):
    a, b = a.astype(np.float64), b.astype(np.float64)
    return (a * b).sum(-1) / (np.linalg.norm(a, axis=-1) * np.linalg.norm(b, axis=-1))


def compare(ref, got, wt_ref, wt_got):
    c_mp = cos_rows(ref["meanpool"], got["meanpool"])
    c_se = cos_rows(ref["site_emb"], got["site_emb"])
    d_mask = np.abs(ref["lp_mask"] - got["lp_mask"])
    d_un = np.abs(ref["lp_un"] - got["lp_un"])
    s_ref, s_got = ref["lp_mask"].sum(1), got["lp_mask"].sum(1)
    r = float(np.corrcoef(s_ref, s_got)[0, 1])
    return {"n": int(len(c_mp)),
            "meanpool_cosine_min": float(c_mp.min()), "meanpool_cosine_mean": float(c_mp.mean()),
            "site_emb_cosine_min": float(c_se.min()), "site_emb_cosine_mean": float(c_se.mean()),
            "meanpool_max_abs_diff": float(np.abs(ref["meanpool"].astype(np.float32) - got["meanpool"].astype(np.float32)).max()),
            "lp_mask_max_abs_diff": float(d_mask.max()), "lp_mask_mean_abs_diff": float(d_mask.mean()),
            "lp_unmasked_max_abs_diff": float(d_un.max()), "lp_unmasked_mean_abs_diff": float(d_un.mean()),
            "summed_lp_mask_pearson": r,
            "wt_table_max_abs_diff": float(np.abs(wt_ref - wt_got).max()),
            "wt_table_argmax_agreement": float((wt_ref.argmax(1) == wt_got.argmax(1)).mean())}


def parity(tk, n, bs, n_thr, out_dir):
    import gc
    import torch
    rng = np.random.default_rng(7)        # fixed before inspecting any output; unrelated to any measurement
    lin = np.concatenate([[R.all_genotypes().index(R.PARENT)], rng.choice(R.N_VARIANTS, n - 1, replace=False)])
    res, wts, thr = {}, {}, {}
    thr_lin = rng.choice(R.N_VARIANTS, n_thr, replace=False)
    for kind in ("plain_fp32", "plain_bf16", "te_bf16"):
        m = load_model(kind)
        res[kind] = run_all(m, tk, lin, bs)
        with torch.inference_mode():
            wts[kind] = wt_masked_table(m, tk)
        thr[kind] = throughput(m, tk, thr_lin, bs)
        log("parity_model_done", kind=kind, throughput=thr[kind])
        del m
        gc.collect()
        torch.cuda.empty_cache()
    rec = {"reference": "plain_fp32", "variants_index_seed": 7,
           "plain_bf16_vs_plain_fp32": compare(res["plain_fp32"], res["plain_bf16"], wts["plain_fp32"], wts["plain_bf16"]),
           "te_bf16_vs_plain_fp32": compare(res["plain_fp32"], res["te_bf16"], wts["plain_fp32"], wts["te_bf16"]),
           "te_bf16_vs_plain_bf16": compare(res["plain_bf16"], res["te_bf16"], wts["plain_bf16"], wts["te_bf16"]),
           "throughput_single_pass": thr,
           "note": "Differences are numerical (bf16/TE kernels); the bf16-vs-fp32 plain row is the noise floor."}
    log("parity_result", **rec)
    os.makedirs(out_dir, exist_ok=True)
    json.dump(rec, open(os.path.join(out_dir, "parity.json"), "w"), indent=1)
    print("RESULT_JSON parity " + json.dumps(rec), flush=True)
    return rec


# ---------------------------------------------------------------- probe
def probe(tk, out_dir, log_test_mb):
    rec = env_record()
    log("env", **rec)
    os.makedirs(out_dir, exist_ok=True)
    stamp = os.path.join(out_dir, "probe_write_test.txt")
    open(stamp, "w").write(f"written {time.time()}\n")
    log("bucket_write_ok", path=stamp, listing=sorted(os.listdir(out_dir)))
    log("output_root_listing", entries=sh(f"ls -la {os.path.dirname(out_dir.rstrip('/'))} | head -30"))
    # log-transport test: deterministic pseudo-random bytes, checksum known to recovery script
    blob = np.random.default_rng(3).integers(0, 256, size=int(log_test_mb * 1e6), dtype=np.uint8).tobytes()
    emit_blob("log_transport_test.bin", blob)
    parity(tk, n=64, bs=32, n_thr=256, out_dir=out_dir)
    json.dump(rec, open(os.path.join(out_dir, "env.json"), "w"), indent=1)


# ---------------------------------------------------------------- PCA
def pca_gpu(X, k):
    """Top-k PCA of rows of X (float32 numpy) via covariance eigendecomposition on GPU. Label-free."""
    import torch
    Xt = torch.as_tensor(X, dtype=torch.float32, device=DEVICE)
    mu = Xt.mean(0)
    Xc = Xt - mu
    cov = (Xc.T @ Xc) / (len(Xc) - 1)
    ev, vec = torch.linalg.eigh(cov.double())
    order = torch.argsort(ev, descending=True)[:k]
    comps = vec[:, order].T.float()
    proj = (Xc @ comps.T)
    ratio = (ev[order] / ev.clamp(min=0).sum()).float()
    return mu.cpu().numpy(), comps.cpu().numpy(), ratio.cpu().numpy(), proj.cpu().numpy()


# ---------------------------------------------------------------- main
def main_stage(tk, out_dir, shard, bs, max_variants, max_minutes, pca_k, emit_logs):
    import torch
    model = load_model("te_bf16")
    perm = R.permuted_order()[:max_variants]
    shard_dir = os.path.join(out_dir, "shards")
    os.makedirs(shard_dir, exist_ok=True)
    with torch.inference_mode():
        wt_tab = wt_masked_table(model, tk)
    wt_scores = run_all(model, tk, np.array([R.all_genotypes().index(R.PARENT)]), 1)
    nshards = (len(perm) + shard - 1) // shard
    log("main_start", variants=int(len(perm)), shards=nshards, shard=shard, batch=bs, max_minutes=max_minutes,
        existing=sorted(os.listdir(shard_dir))[:3])
    t_start, done_v = time.time(), 0
    completed = []
    for k in range(nshards):
        path = os.path.join(shard_dir, f"shard_{k:03d}.npz")
        lin = perm[k * shard:(k + 1) * shard]
        if os.path.exists(path):
            completed.append(k)
            continue
        if (time.time() - t_start) / 60 > max_minutes:
            log("deadline_stop", at_shard=k, minutes=round((time.time() - t_start) / 60, 1))
            break
        t = time.time()
        r = run_all(model, tk, lin, bs)
        tmp = path + ".tmp.npz"
        np.savez(tmp, variant_index=lin.astype(np.int32), **r)
        os.replace(tmp, path)
        completed.append(k)
        done_v += len(lin)
        el = time.time() - t_start
        log("shard_done", shard=k, n=int(len(lin)), seconds=round(time.time() - t, 1),
            variants_per_s=round(len(lin) / (time.time() - t), 1), elapsed_min=round(el / 60, 2),
            eta_min=round(el / done_v * max(len(perm) - (k + 1) * shard, 0) / 60, 1))
    # assemble
    parts = [np.load(os.path.join(shard_dir, f"shard_{k:03d}.npz")) for k in sorted(completed)]
    cat = {key: np.concatenate([p[key] for p in parts]) for key in parts[0].files}
    n = len(cat["variant_index"])
    log("assembled", variants=int(n), shards=len(parts))
    del parts
    geno = np.array(R.all_genotypes())
    summary = {"variants_done": int(n), "variants_planned": int(len(perm)), "complete_library": bool(n == R.N_VARIANTS),
               "seed": R.PERMUTATION_SEED, "order": "seeded permutation prefix; label-free",
               "wt_masked_table_shape": list(wt_tab.shape), "te_model": {"repo": TE_REPO, "revision": TE_REV}}
    vi = cat["variant_index"]
    zs = dict(variant_index=vi, lp_masked_obs=cat["lp_mask"].astype(np.float32), lp_unmasked_obs=cat["lp_un"].astype(np.float32),
              wt_masked_table_20aa=wt_tab.astype(np.float32), wt_lp_masked_obs=wt_scores["lp_mask"][0].astype(np.float32),
              wt_lp_unmasked_obs=wt_scores["lp_un"][0].astype(np.float32), aa_order=np.array(list(R.AA20)),
              sites=np.array(R.SITES))
    arts = {"zeroshot_prior.npz": npz_bytes(**zs)}
    mp = cat["meanpool"].astype(np.float32)
    mu, comps, ratio, proj = pca_gpu(mp, pca_k)
    arts[f"embedding_meanpool_pca{pca_k}.npz"] = npz_bytes(variant_index=vi, mean=mu, components=comps,
                                                            explained_variance_ratio=ratio, projection=proj.astype(np.float16))
    sc = cat["site_emb"].astype(np.float32).reshape(n, -1)
    mu2, comps2, ratio2, proj2 = pca_gpu(sc, pca_k)
    arts[f"embedding_sites_pca{pca_k}.npz"] = npz_bytes(variant_index=vi, mean=mu2, components=comps2,
                                                         explained_variance_ratio=ratio2, projection=proj2.astype(np.float16))
    summary["pca_k"] = pca_k
    summary["pca_meanpool_explained_variance_ratio_sum"] = float(ratio.sum())
    summary["pca_sites_explained_variance_ratio_sum"] = float(ratio2.sum())
    summary["unique_variants"] = int(len(np.unique(vi)))
    summary["genotype_first5"] = [str(geno[i]) for i in vi[:5]]
    pub = os.path.join(out_dir, "compact")
    os.makedirs(pub, exist_ok=True)
    manifest = {}
    for name, raw in arts.items():
        open(os.path.join(pub, name), "wb").write(raw)
        manifest[name] = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    summary["compact_artifacts"] = manifest
    json.dump(summary, open(os.path.join(out_dir, "summary.json"), "w"), indent=1)
    print("RESULT_JSON main_summary " + json.dumps(summary), flush=True)
    if emit_logs:
        for name, raw in arts.items():
            emit_blob(name, raw)
    log("main_done", **{k: v for k, v in summary.items() if k != "compact_artifacts"})


def parse():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["probe", "parity", "main", "all"], required=True)
    ap.add_argument("--out", default="/output/run")
    ap.add_argument("--batch", type=int, default=128)
    ap.add_argument("--shard", type=int, default=4096)
    ap.add_argument("--max-variants", type=int, default=R.N_VARIANTS)
    ap.add_argument("--max-minutes", type=float, default=75.0)
    ap.add_argument("--pca-k", type=int, default=64)
    ap.add_argument("--parity-n", type=int, default=256)
    ap.add_argument("--parity-thr", type=int, default=2048)
    ap.add_argument("--log-test-mb", type=float, default=4.0)
    ap.add_argument("--no-emit-logs", action="store_true")
    return ap.parse_args()


if __name__ == "__main__":
    a = parse()
    hdr, ref = R.load_reference()
    log("reference", header=hdr, length=len(ref), sites={p: ref[p - 1] for p in R.SITES}, fasta_sha256=R.FASTA_SHA256)
    tk = Tok()
    if a.stage == "probe":
        probe(tk, a.out, a.log_test_mb)
    elif a.stage == "parity":
        log("env", **env_record())
        parity(tk, a.parity_n, a.batch, a.parity_thr, a.out)
    elif a.stage == "all":
        log("env", **env_record())
        log("output_root_listing", entries=sh("ls -laR /output | head -40"))
        try:
            parity(tk, a.parity_n, a.batch, a.parity_thr, os.path.join(a.out, "parity"))
        except Exception as e:  # noqa: BLE001  (parity is a side check; never block the main sweep)
            log("parity_failed", error=repr(e))
        main_stage(tk, a.out, a.shard, a.batch, a.max_variants, a.max_minutes, a.pca_k, not a.no_emit_logs)
    else:
        log("env", **env_record())
        main_stage(tk, a.out, a.shard, a.batch, a.max_variants, a.max_minutes, a.pca_k, not a.no_emit_logs)
    log("done", wall_seconds=round(time.time() - T0, 1))
