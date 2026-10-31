"""Audited loader for the Johnston et al. TrpB four-site table (raw growth rates).

Design rules (see specs/CONTRACT.md):
* labels are RAW growth rates mu_1, mu_2 minus the per-replicate mean over
  stop-codon rows (a negative-control offset, constant per replicate).  The
  source's `/max` columns are never used (they embed the global library maximum),
  nor are the authors' row-specific `mu-bg` columns;
* the KNN-imputed rows are never observations;
* memory is compact: flat arrays indexed by base-20 genotype code (160,000
  entries), never a pairwise matrix.
All decision arithmetic uses int64 micro-units so a Lean checker can be exact.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
MANIFEST = ROOT / "data" / "manifest.json"

AA = "ACDEFGHIKLMNPQRSTVWY"
POSITIONS = (183, 184, 227, 228)  # residue numbers in Tm9D8s* TrpB (source paper)
N_GENO = 20 ** 4
UNITS = 1_000_000  # integer micro-units of growth-rate score
PARENT = "VFVS"

# --- Declared (assumed) noise model, frozen before any benchmark run ---------
# Replicate-difference SD of (s1 - s2) by min(InputCount_1, InputCount_2) bin,
# computed over the 159,129 measured genotypes (`python -m evolve audit` recomputes
# and checks these).  Half-width of the interval on the 2-replicate mean is
#   eps = KAPPA * sd_bin / 2 ,
# KAPPA is an ASSUMED sensitivity multiplier, NOT a confidence level.
COUNT_BIN_EDGES = (20, 50, 200)
REPLICATE_DIFF_SD = (0.014953, 0.009995, 0.005851, 0.002992)
DEFAULT_KAPPA = 2.0


def encode(g: str) -> int:
    a = AA.index
    return ((a(g[0]) * 20 + a(g[1])) * 20 + a(g[2])) * 20 + a(g[3])


def decode(i: int) -> str:
    return AA[i // 8000] + AA[(i // 400) % 20] + AA[(i // 20) % 20] + AA[i % 20]


def digits(idx):
    idx = np.asarray(idx)
    return np.stack([idx // 8000, (idx // 400) % 20, (idx // 20) % 20, idx % 20], axis=-1)


# neighbor table pieces: 76 single substitutions = 4 positions x 19 other residues
_POW = np.array([8000, 400, 20, 1])


def neighbors(idx):
    """Single-substitution neighbours; shape (..., 76)."""
    idx = np.asarray(idx)
    d = digits(idx)  # (...,4)
    out = []
    for p in range(4):
        for k in range(1, 20):
            nd = (d[..., p] + k) % 20
            out.append(idx + (nd - d[..., p]) * _POW[p])
    return np.stack(out, axis=-1)


def hamming(a, b):
    return (digits(a) != digits(b)).sum(-1)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


@dataclass
class Landscape:
    measured: np.ndarray   # bool (160000,)
    s1: np.ndarray         # int64 micro-units, replicate 1 (0 where unmeasured)
    s2: np.ndarray
    s: np.ndarray          # int64, round(mean of replicates)
    count_min: np.ndarray  # int32, min input count (0 where unmeasured)
    raw_mu1: np.ndarray    # float64 raw growth rates (nan where unmeasured)
    raw_mu2: np.ndarray
    bg: tuple              # per-replicate stop-codon mean mu
    counts: dict
    sha: dict
    kappa: float

    def eps(self, kappa=None) -> np.ndarray:
        k = self.kappa if kappa is None else kappa
        sd = np.array(REPLICATE_DIFF_SD)[np.searchsorted(COUNT_BIN_EDGES, self.count_min, side="right")]
        return np.ceil(k * sd / 2 * UNITS).astype(np.int64)

    def intervals(self, kappa=None):
        e = self.eps(kappa)
        return self.s - e, self.s + e  # Lo, Hi (int64); meaningful only where measured

    def with_kappa(self, kappa):
        import copy
        c = copy.copy(self)
        c.kappa = kappa
        return c


def load(raw_dir: Path = RAW, kappa: float = DEFAULT_KAPPA, verify: bool = True) -> Landscape:
    man = json.loads(MANIFEST.read_text())
    sha = {n: sha256_file(raw_dir / n) for n in man["files"]}
    if verify:
        bad = [n for n, m in man["files"].items() if sha[n] != m["sha256"]]
        if bad:
            raise RuntimeError(f"data hash mismatch vs data/manifest.json: {bad}; run scripts/fetch_data.py")
    d = pd.read_csv(raw_dir / "summary_AA.csv")
    stop = d["# Stop"] > 0
    bg = (float(d.loc[stop, "mu_1"].mean()), float(d.loc[stop, "mu_2"].mean()))
    ok = d[~stop]
    idx = np.array([encode(g) for g in ok["AAs"]])
    assert len(set(idx.tolist())) == len(idx)
    meas = np.zeros(N_GENO, bool); meas[idx] = True
    s1 = np.zeros(N_GENO, np.int64); s2 = np.zeros(N_GENO, np.int64)
    s1[idx] = np.round((ok["mu_1"].to_numpy() - bg[0]) * UNITS)
    s2[idx] = np.round((ok["mu_2"].to_numpy() - bg[1]) * UNITS)
    s = np.zeros(N_GENO, np.int64); s[idx] = np.round((s1[idx] + s2[idx]) / 2).astype(np.int64)
    cm = np.zeros(N_GENO, np.int32)
    cm[idx] = np.minimum(ok["InputCount_1"], ok["InputCount_2"]).astype(np.int32)
    m1 = np.full(N_GENO, np.nan); m2 = np.full(N_GENO, np.nan)
    m1[idx] = ok["mu_1"].to_numpy(); m2[idx] = ok["mu_2"].to_numpy()
    knn = pd.read_csv(raw_dir / "KNN_imputed_TrpB.csv")
    kidx = np.array([encode(g) for g in knn["AAs"]])
    counts = {
        "source_rows_summary_AA": int(len(d)),
        "stop_containing_rows": int(stop.sum()),
        "measured_nonstop_genotypes": int(meas.sum()),
        "library_nonstop_genotypes": N_GENO,
        "unmeasured_nonstop_genotypes": int(N_GENO - meas.sum()),
        "knn_imputed_rows_separate_file": int(len(knn)),
        "knn_imputed_overlap_with_measured": int(meas[kidx].sum()),
        "knn_imputed_equals_unmeasured_set": bool((~meas[kidx]).all() and len(kidx) == N_GENO - meas.sum()),
        "source_declared_active_rows": int(ok["active"].sum()),
        "source_declared_censored_rows": 0,
        "low_count_rows_min_input_lt_10_flagged_not_dropped": int((cm[idx] < 10).sum()),
        "imputed_rows_used_as_observations": 0,
    }
    return Landscape(meas, s1, s2, s, cm, m1, m2, bg, counts, sha, kappa)
