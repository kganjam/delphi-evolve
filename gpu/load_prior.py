"""Load the recovered ESM2 prior arrays keyed by genotype string (e.g. "VFVS").

    from load_prior import load_prior
    P = load_prior("artifacts/gpu/main")
    P["VFVS"]["pll4_delta"]   # float, model prediction (NOT a measurement)

All fields are model outputs.  Unmeasured/imputed genotypes are present too (the library is the full 20^4);
whether a genotype was measured is decided by the data loader, never by this file.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import trpb_ref as R  # noqa: E402


def load_prior(dirpath):
    d = Path(dirpath)
    z = np.load(d / "zeroshot_prior.npz")
    es = np.load(d / "embedding_sites_pca64.npz")
    mp = np.load(d / "embedding_meanpool_pca64.npz")
    z = {k: z[k] for k in z.files}          # materialise once; NpzFile re-reads the array on every access
    es = {k: es[k] for k in es.files}
    mp = {k: mp[k] for k in mp.files}
    vi = z["variant_index"]
    assert (es["variant_index"] == vi).all() and (mp["variant_index"] == vi).all()
    geno = R.all_genotypes()
    aa = {a: i for i, a in enumerate(R.AA20)}
    tab = z["wt_masked_table_20aa"]
    wt = [aa[c] for c in R.PARENT]
    wt_pll = float(z["wt_lp_masked_obs"].sum())
    wt_un = float(z["wt_lp_unmasked_obs"].sum())
    out = {}
    for r, i in enumerate(vi):
        g = geno[i]
        out[g] = {
            "additive_wt_marginal_delta": float(sum(tab[j, aa[g[j]]] - tab[j, wt[j]] for j in range(4))),
            "pll4_delta": float(z["lp_masked_obs"][r].sum() - wt_pll),
            "unmasked_delta": float(z["lp_unmasked_obs"][r].sum() - wt_un),
            "emb_sites_pca64": es["projection"][r],
            "emb_meanpool_pca64": mp["projection"][r],
            "evidence_kind": "predicted",
        }
    return out
