"""Wildcard feasibility check: do independent computational "views" predict measured
binding in the public Adaptyv EGFR round-2 data, and does fusing views beat the best view?

Pre-stated acceptance rule (written before the first run, 2026-10-31):
  The "collective of views" is worth building on only if, under leave-designer-out
  cross-validation, fused AUROC exceeds the best single view AND the 95% designer-cluster
  bootstrap interval of (fused - best single view) excludes zero.
  A best single view with AUROC interval including 0.5 means the data are not usable for
  a validation claim at all.

Inputs (public; see planning/rethink/wildcard/README.md for URLs and SHA256):
  r2_result_summary.csv  (adaptyvbio/egfr_competition_2); biophysics recomputed from sequence
Labels: SPR-derived `binding` in {true,false}; `unknown` rows (no expression) are excluded.
Selection caveat: the 402 measured designs were chosen by the organizers from 1,131
submissions, so predictors are evaluated on a pre-filtered set.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

VIEWS = {
    "structure_confidence": ["pae_interaction", "iptm", "plddt"],
    "language_model": ["esm_pll_per_res"],
    "biophysics": ["gravy", "net_charge_per_res", "frac_aromatic", "frac_gly_pro", "frac_cys"],
    "novelty": ["similarity_check"],
    "length": ["num_residues"],
}


def sha256(path: str) -> str:
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


KD = {"A":1.8,"R":-4.5,"N":-3.5,"D":-3.5,"C":2.5,"Q":-3.5,"E":-3.5,"G":-0.4,"H":-3.2,"I":4.5,"L":3.8,
      "K":-3.9,"M":1.9,"F":2.8,"P":-1.6,"S":-0.8,"T":-0.7,"W":-0.9,"Y":-1.3,"V":4.2}


def seq_features(seq: str) -> dict:
    n = len(seq)
    c = {a: seq.count(a) for a in KD}
    return {
        "num_residues": n,
        "gravy": sum(KD[a] * c[a] for a in KD) / n,
        "net_charge_per_res": (c["K"] + c["R"] - c["D"] - c["E"]) / n,
        "frac_aromatic": (c["F"] + c["W"] + c["Y"]) / n,
        "frac_gly_pro": (c["G"] + c["P"]) / n,
        "frac_cys": c["C"] / n,
    }


def load(res_csv: str, des_csv: str | None = None) -> pd.DataFrame:
    # NOTE: the DE-STRESS table is keyed by internal PDB ids that do not join to result names,
    # so biophysical features are recomputed from the measured sequence instead (des_csv unused).
    r = pd.read_csv(res_csv)
    r = r[r.binding.isin(["true", "false"])].copy()
    r["y"] = (r.binding == "true").astype(int)
    # rows without a username are each their own group (no designer identity to leak)
    r["username"] = [u if isinstance(u, str) else f"__anon{i}" for i, u in enumerate(r.username)]
    feats = pd.DataFrame([seq_features(s) for s in r.sequence], index=r.index)
    df = pd.concat([r, feats], axis=1)
    df["esm_pll_per_res"] = df.esm_pll / df.num_residues
    return df


def fit_predict(train, test, cols, y_col="y"):
    m = make_pipeline(StandardScaler(), LogisticRegression(C=0.3, max_iter=1000))
    tr = train[cols].copy(); te = test[cols].copy()
    med = tr.median()
    m.fit(tr.fillna(med), train[y_col])
    return m.predict_proba(te.fillna(med))[:, 1]


def kmer_set(seq, k=5):
    return {seq[i:i + k] for i in range(len(seq) - k + 1)}


def sequence_clusters(seqs, thr=0.5, k=5):
    """Connected components of pairs whose 5-mer Jaccard >= thr (single linkage). Descriptive
    near-duplicate grouping, not an alignment-based identity cluster."""
    sets = [kmer_set(x, k) for x in seqs]
    n = len(sets)
    parent = list(range(n))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    for i in range(n):
        for j in range(i + 1, n):
            u = len(sets[i] | sets[j])
            if u and len(sets[i] & sets[j]) / u >= thr:
                parent[find(i)] = find(j)
    return np.array([f"c{find(i)}" for i in range(n)])


def cv_scores(df, n_splits=5, seed=0, group_col="username", y_col="y"):
    """Out-of-fold scores for each single view. Folds are RANDOM GROUP 5-FOLD (whole groups are
    held out together), not literal leave-one-designer-out. group_col is 'username' (anonymous
    rows each their own group - an assumption) or 'seqcluster' (near-duplicate sequences kept
    together). Every fold fits only on training groups."""
    groups = df[group_col].values
    uniq = np.unique(groups)
    rng = np.random.default_rng(seed)
    perm = rng.permutation(uniq)
    fold_of = {g: i % n_splits for i, g in enumerate(perm)}
    folds = np.array([fold_of[g] for g in groups])
    oof = {v: np.full(len(df), np.nan) for v in VIEWS}
    for k in range(n_splits):
        tr, te = df[folds != k], df[folds == k]
        for v, cols in VIEWS.items():
            oof[v][folds == k] = fit_predict(tr, te, cols, y_col)
    return oof


def rank01(x):
    return pd.Series(x).rank(pct=True).values


def fused(oof, views):
    return np.mean([rank01(oof[v]) for v in views], axis=0)


def auc(y, s):
    return roc_auc_score(y, s)


def cluster_bootstrap(df, oof, B=2000, seed=1):
    rng = np.random.default_rng(seed)
    g = df.username.values
    ug = np.unique(g)
    idx_by = {u: np.where(g == u)[0] for u in ug}
    y = df.y.values
    names = list(VIEWS)
    stats = {k: [] for k in names + ["fused_all", "fused_nolen", "best_single", "delta_all", "delta_nolen"]}
    for _ in range(B):
        pick = rng.choice(ug, size=len(ug), replace=True)
        ix = np.concatenate([idx_by[u] for u in pick])
        yy = y[ix]
        if yy.min() == yy.max():
            continue
        sc = {v: auc(yy, oof[v][ix]) for v in names}
        fa = auc(yy, np.mean([rank01(oof[v][ix]) for v in names], axis=0))
        nl = [v for v in names if v != "length"]
        fn = auc(yy, np.mean([rank01(oof[v][ix]) for v in nl], axis=0))
        best = max(sc.values())
        for v in names:
            stats[v].append(sc[v])
        stats["fused_all"].append(fa); stats["fused_nolen"].append(fn); stats["best_single"].append(best)
        stats["delta_all"].append(fa - best); stats["delta_nolen"].append(fn - best)
    ci = {k: [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))] for k, v in stats.items()}
    return ci, len(stats["fused_all"])


def refit_permutation(df, group_col, B=200, seed=2):
    """Pipeline-refit label permutation: labels are shuffled across designs, the whole grouped-CV
    pipeline is refit, and the best-of-5-views AUROC is recorded. Designs are treated as
    exchangeable (ignores designer/cluster structure), so this is a DESCRIPTIVE null, not a
    calibrated significance test."""
    rng = np.random.default_rng(seed)
    d = df.copy()
    best_obs = None
    nulls = []
    base = cv_scores(df, group_col=group_col)
    best_obs = max(auc(df.y, base[v]) for v in VIEWS)
    for _ in range(B):
        d["yperm"] = rng.permutation(df.y.values)
        o = cv_scores(d, group_col=group_col, y_col="yperm")
        nulls.append(max(auc(d.yperm, o[v]) for v in VIEWS))
    nulls = np.array(nulls)
    return {"best_view_auc_observed": float(best_obs), "null_mean": float(nulls.mean()),
            "null_95th_pct": float(np.percentile(nulls, 95)), "null_max": float(nulls.max()), "B": B,
            "note": "descriptive; designs treated exchangeable; best-of-5 views"}


def analyze(df, group_col, y_col="y", boot=True, perm=False):
    d = df.copy()
    d["y"] = d[y_col]
    oof = cv_scores(d, group_col=group_col)
    r = {"n": int(len(d)), "n_positive": int(d.y.sum()), "group_col": group_col,
         "n_groups": int(d[group_col].nunique()),
         "auc_single_view": {v: float(auc(d.y, oof[v])) for v in VIEWS},
         "auc_fused_all_views": float(auc(d.y, fused(oof, list(VIEWS)))),
         "auc_fused_without_length": float(auc(d.y, fused(oof, [v for v in VIEWS if v != "length"])))}
    if boot:
        d2 = d.copy(); d2["username"] = d2[group_col]
        ci, nb = cluster_bootstrap(d2, oof)
        r["group_bootstrap_95_conditional_on_fixed_oof"] = ci
        r["bootstrap_replicates_used"] = nb
        r["acceptance"] = {"fused_beats_best_single_with_ci_excluding_zero": bool(ci["delta_all"][0] > 0),
                           "best_single_view_ci_excludes_0.5": bool(ci["best_single"][0] > 0.5)}
    if perm:
        r["refit_permutation"] = refit_permutation(d, group_col)
    return r


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    res = os.path.join(a.data_dir, "r2_result_summary.csv")
    df = load(res)
    raw = pd.read_csv(res)
    df["seqcluster"] = sequence_clusters(df.sequence.tolist())
    out = {"inputs": {os.path.basename(res): sha256(res)}, "views": VIEWS,
           "frozen_acceptance_rule": "fused AUROC > best single view with 95% group-bootstrap CI of the "
                                     "difference excluding 0 (written before first run; NOT relaxed)",
           "primary_designer_groups": analyze(df, "username", perm=True),
           "sens_sequence_cluster_groups": analyze(df, "seqcluster", perm=False)}
    out["sequence_duplicates"] = {"n_exact_duplicate_sequences": int(df.sequence.duplicated().sum()),
                                  "n_seq_clusters_5mer_jaccard_0.5": int(df.seqcluster.nunique()),
                                  "largest_cluster": int(df.seqcluster.value_counts().iloc[0])}
    # end-to-end outcome: expressed binder vs everything else (unexpressed/'unknown' counted as failures)
    full = raw.copy()
    full["y"] = (full.binding == "true").astype(int)
    full["username"] = [u if isinstance(u, str) else f"__anon{i}" for i, u in enumerate(full.username)]
    feats = pd.DataFrame([seq_features(x) for x in full.sequence], index=full.index)
    full = pd.concat([full, feats], axis=1)
    full["esm_pll_per_res"] = full.esm_pll / full.num_residues
    out["sens_end_to_end_unknown_as_failure"] = analyze(full, "username", boot=False)
    # design-format confound: antibody-format (long) vs short designs
    long_ = df.num_residues >= 150
    strat = {}
    for name, m in [("length>=150 (antibody/scFv-like)", long_), ("length<150 (mini-binder-like)", ~long_)]:
        sub = df[m]
        strat[name] = {"n": int(len(sub)), "n_binders": int(sub.y.sum()),
                       "raw_auc_esm_pll_per_res": (float(auc(sub.y, sub.esm_pll_per_res.fillna(sub.esm_pll_per_res.median())))
                                                   if 0 < sub.y.sum() < len(sub) else None),
                       "raw_auc_iptm": (float(auc(sub.y, sub.iptm.fillna(sub.iptm.median())))
                                        if 0 < sub.y.sum() < len(sub) else None)}
    out["stratified_by_length_class"] = strat
    out["caveat"] = ("Organizer-preselected 402 of 1,131 submissions; one target (EGFR); SPR binding label; "
                     "binding is conditional on expression in the primary analysis; retrospective; random "
                     "group 5-fold (not LODO); bootstrap conditions on fixed OOF predictions; best-of-views "
                     "and permutation are exploratory/descriptive; fusion is of precomputed features, "
                     "not evidence about LLM agents.")
    json.dump(out, open(a.out, "w"), indent=2, sort_keys=True)
    print(json.dumps(out, indent=1)[:6500])


if __name__ == "__main__":
    sys.exit(main())
