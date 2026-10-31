#!/usr/bin/env python3
"""Descriptive check of the ESM2 prior against the MEASURED TrpB assay (post hoc evaluation).

Inputs
  --summary    CaltechDATA summary_AA.csv (raw per-replicate columns; measured rows only are used)
  --imputed    KNN_imputed_TrpB.csv (only used to prove none of its rows enter the evaluation)
  --zeroshot   zeroshot_prior.npz recovered from the H100 job log
  --embed-sites embedding_sites_pca64.npz (label-free PCA of 4-site embeddings)
  --out        result JSON

Protocol (fixed before running; nothing tuned on the test labels)
  * Outcome y = mean of unnormalised background-subtracted growth, (mu_1-bg + mu_2-bg)/2, over the
    159,129 measured non-stop genotypes (the source max-normalised columns are NOT used).
  * Label-free priors (no outcome used to build them): additive WT-marginal ESM2, 4-site masked
    pseudo-log-likelihood ratio (context-aware), unmasked ratio, BLOSUM62 sum, -Hamming distance.
    Reported as Spearman and top-k overlap against y, with variant-resampling bootstrap (descriptive).
  * Supervised comparison, 10 random 80/20 splits (seeds 0-9): ridge on one-hot additive (80 features),
    one-hot + pairwise one-hot (2480), PCA-64 site embeddings, PCA-64 + one-hot, and one-hot + 3 prior
    scores.  This is an OPTIMISTIC random split (no extrapolation) and is not the benchmark replay.
Predictions are model outputs and never substitute for assay measurements.
"""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import sparse
from scipy.stats import spearmanr, rankdata

sys.path.insert(0, str(Path(__file__).resolve().parent))
import trpb_ref as R  # noqa: E402

AAIDX = {a: i for i, a in enumerate(R.AA20)}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def onehot(geno):
    """(N,80) sparse additive one-hot, plus (N,2400) pairwise."""
    d = np.array([[AAIDX[c] for c in g] for g in geno])
    n = len(d)
    rows = np.repeat(np.arange(n), 4)
    cols = (np.arange(4)[None, :] * 20 + d).ravel()
    add = sparse.csr_matrix((np.ones(n * 4, dtype=np.float32), (rows, cols)), shape=(n, 80))
    pr, pc, k = [], [], 0
    for a in range(4):
        for b in range(a + 1, 4):
            pr.append(np.arange(n))
            pc.append(np.full(n, k * 400) + d[:, a] * 20 + d[:, b])
            k += 1
    pair = sparse.csr_matrix((np.ones(n * 6, dtype=np.float32), (np.concatenate(pr), np.concatenate(pc))), shape=(n, 2400))
    return d, add, pair


def ridge_fit_predict(Xtr, ytr, Xte, lams=(0.1, 1.0, 10.0, 100.0)):
    """Closed-form ridge with intercept; lambda chosen on an inner 80/20 split of the TRAIN rows only."""
    ytr = np.asarray(ytr, dtype=np.float64)
    n = Xtr.shape[0]
    rng = np.random.default_rng(12345)
    perm = rng.permutation(n)
    cut = int(0.8 * n)
    a, b = perm[:cut], perm[cut:]

    def fit(X, y, lam):
        mu_y = y.mean()
        Xd = X
        xtx = (Xd.T @ Xd)
        xtx = xtx.toarray() if sparse.issparse(xtx) else np.asarray(xtx)
        xty = np.asarray(Xd.T @ (y - mu_y)).ravel()
        w = np.linalg.solve(xtx.astype(np.float64) + lam * np.eye(xtx.shape[0]), xty)
        return w, mu_y

    best, bl = -np.inf, lams[0]
    for lam in lams:
        w, m = fit(Xtr[a], ytr[a], lam)
        p = np.asarray(Xtr[b] @ w).ravel() + m
        s = spearmanr(p, ytr[b]).statistic
        if s > best:
            best, bl = s, lam
    w, m = fit(Xtr, ytr, bl)
    return np.asarray(Xte @ w).ravel() + m, bl


def topk_overlap(pred, y, k):
    return len(set(np.argsort(-pred)[:k]) & set(np.argsort(-y)[:k])) / k


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", required=True)
    ap.add_argument("--imputed", required=True)
    ap.add_argument("--zeroshot", required=True)
    ap.add_argument("--embed-sites", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--boot", type=int, default=200)
    a = ap.parse_args()
    t0 = time.time()
    df = pd.read_csv(a.summary, usecols=["AAs", "# Stop", "mu_1-bg", "mu_2-bg", "active"])
    meas = df[df["# Stop"] == 0].copy()
    imp = pd.read_csv(a.imputed)
    overlap = len(set(meas["AAs"]) & set(imp["AAs"]))
    assert len(meas) == 159129 and overlap == 0, (len(meas), overlap)
    zs = np.load(a.zeroshot)
    es = np.load(a.embed_sites)
    geno_all = np.array(R.all_genotypes())
    vi = zs["variant_index"]
    assert (es["variant_index"] == vi).all()
    row_of = {g: i for i, g in enumerate(geno_all[vi])}
    meas = meas[meas["AAs"].isin(row_of)].reset_index(drop=True)
    geno = meas["AAs"].to_numpy()
    rows = np.array([row_of[g] for g in geno])
    y = ((meas["mu_1-bg"] + meas["mu_2-bg"]) / 2).to_numpy()
    y1, y2 = meas["mu_1-bg"].to_numpy(), meas["mu_2-bg"].to_numpy()
    active = meas["active"].astype(bool).to_numpy()
    d, add, pair = onehot(geno)

    # ---- label-free priors
    tab = zs["wt_masked_table_20aa"]            # (4,20)
    wt_i = [AAIDX[c] for c in R.PARENT]
    additive = sum(tab[j, d[:, j]] - tab[j, wt_i[j]] for j in range(4))
    pll4 = zs["lp_masked_obs"][rows].sum(1) - zs["wt_lp_masked_obs"].sum()
    unm = zs["lp_unmasked_obs"][rows].sum(1) - zs["wt_lp_unmasked_obs"].sum()
    from Bio.Align import substitution_matrices
    B = substitution_matrices.load("BLOSUM62")
    blosum = np.array([sum(B[R.PARENT[j]][g[j]] for j in range(4)) for g in geno], dtype=float)
    ham = -np.array([sum(g[j] != R.PARENT[j] for j in range(4)) for g in geno], dtype=float)
    priors = {"esm2_wt_marginal_additive": additive, "esm2_pll4_context": pll4, "esm2_unmasked_ratio": unm,
              "blosum62_sum": blosum, "neg_hamming_to_parent": ham}
    ry = rankdata(y)
    rng = np.random.default_rng(99)
    out = {"inputs": {"summary_sha256": sha(a.summary), "imputed_sha256": sha(a.imputed), "zeroshot_sha256": sha(a.zeroshot),
                      "embed_sites_sha256": sha(a.embed_sites)},
           "n_measured_nonstop_in_prior": int(len(meas)), "imputed_overlap": overlap,
           "n_active_flag": int(active.sum()), "replicate_spearman": float(spearmanr(y1, y2).statistic),
           "outcome": "mean(mu_1-bg, mu_2-bg), unnormalised", "label_free_priors": {}}
    # bootstrap indices shared across priors (paired)
    boots = [rng.integers(0, len(y), len(y)) for _ in range(a.boot)]
    for name, s in priors.items():
        rs = rankdata(s)
        rho = float(np.corrcoef(rs, ry)[0, 1])
        bs = []
        for ix in boots:
            bs.append(spearmanr(s[ix], y[ix]).statistic)
        # AUROC for the source "active" flag
        from sklearn.metrics import roc_auc_score
        auc = float(roc_auc_score(active, s))
        out["label_free_priors"][name] = {
            "spearman_vs_y": rho, "spearman_bootstrap_2.5_97.5": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
            "auroc_active": auc, "top100_overlap": topk_overlap(s, y, 100), "top1000_overlap": topk_overlap(s, y, 1000),
            "note_bootstrap": "resamples variants; descriptive only, variants are not independent draws"}
    out["chance_top100_overlap"] = 100 / len(y)

    # ---- supervised comparison
    emb = es["projection"][rows].astype(np.float32)
    emb = (emb - emb.mean(0)) / (emb.std(0) + 1e-6)
    embs = sparse.csr_matrix(emb)
    pri = np.stack([additive, pll4, unm], 1)
    pri = sparse.csr_matrix((pri - pri.mean(0)) / pri.std(0))
    feats = {"onehot_additive": add, "onehot_plus_pairwise": sparse.hstack([add, pair]).tocsr(),
             "esm2_sites_pca64": embs, "esm2_sites_pca64_plus_onehot": sparse.hstack([add, embs]).tocsr(),
             "onehot_plus_3_esm2_priors": sparse.hstack([add, pri]).tocsr()}
    sup = {k: {"spearman": [], "top100_overlap": [], "lambda": []} for k in feats}
    for seed in range(a.seeds):
        perm = np.random.default_rng(seed).permutation(len(y))
        te, tr = perm[:len(y) // 5], perm[len(y) // 5:]
        for k, X in feats.items():
            p, lam = ridge_fit_predict(X[tr], y[tr], X[te])
            sup[k]["spearman"].append(float(spearmanr(p, y[te]).statistic))
            sup[k]["top100_overlap"].append(topk_overlap(p, y[te], 100))
            sup[k]["lambda"].append(lam)
        print(f"seed {seed} done {time.time() - t0:.0f}s", flush=True)
    for k, v in sup.items():
        v["spearman_mean"] = float(np.mean(v["spearman"]))
        v["spearman_sd_over_splits"] = float(np.std(v["spearman"], ddof=1))
        v["top100_overlap_mean"] = float(np.mean(v["top100_overlap"]))
    # paired differences vs one-hot additive
    base = np.array(sup["onehot_additive"]["spearman"])
    out["paired_spearman_diff_vs_onehot_additive"] = {
        k: {"mean": float(np.mean(np.array(v["spearman"]) - base)), "min": float(np.min(np.array(v["spearman"]) - base)),
            "max": float(np.max(np.array(v["spearman"]) - base))} for k, v in sup.items() if k != "onehot_additive"}
    out["supervised_random_split"] = sup
    out["protocol_note"] = ("random 80/20 splits are optimistic; descriptive only; not the assay-budget replay and no "
                            "claim about certificate quality. Split SD is variability across seeds, not a confidence interval.")
    out["wall_seconds"] = round(time.time() - t0, 1)
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(json.dumps({"label_free": {k: (round(v["spearman_vs_y"], 4), round(v["auroc_active"], 4)) for k, v in out["label_free_priors"].items()},
                      "supervised_spearman_mean": {k: round(v["spearman_mean"], 4) for k, v in sup.items()}}, indent=1))


if __name__ == "__main__":
    main()
