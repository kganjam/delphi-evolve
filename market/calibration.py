"""Calibration curve, expected calibration error, reliability diagram, and cross-family error correlation."""
from __future__ import annotations

import numpy as np


def calibration_table(p, o, bins: int = 10):
    """Equal-width bins on [0,1]; last bin closed on the right. Empty bins are kept with n=0 (no invented values)."""
    p = np.asarray(p, dtype=float)
    o = np.asarray(o, dtype=float)
    edges = np.linspace(0.0, 1.0, bins + 1)
    which = np.minimum(np.floor(p * bins).astype(int), bins - 1)
    rows = []
    ece = 0.0
    for b in range(bins):
        m = which == b
        n = int(m.sum())
        row = {"bin": b, "lo": float(edges[b]), "hi": float(edges[b + 1]), "n": n,
               "mean_forecast": float(p[m].mean()) if n else None,
               "observed_frequency": float(o[m].mean()) if n else None}
        if n:
            ece += n / len(p) * abs(row["mean_forecast"] - row["observed_frequency"])
        rows.append(row)
    return {"bins": rows, "ece": float(ece), "n": int(len(p)), "note": "equal-width bins; ECE = sum_b n_b/n |observed_b - mean_forecast_b|"}


def reliability_figure(panels: dict, path, title: str, bins: int = 10):
    """panels: {label: (p, o)}. One reliability diagram per panel with a count histogram underneath."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    k = max(1, len(panels))
    fig, axes = plt.subplots(2, k, figsize=(3.6 * k, 5.2), squeeze=False, gridspec_kw={"height_ratios": [3, 1]})
    for j, (label, (p, o)) in enumerate(panels.items()):
        t = calibration_table(p, o, bins)
        ax, hx = axes[0][j], axes[1][j]
        ax.plot([0, 1], [0, 1], color="0.6", lw=1, ls="--", label="perfect")
        xs = [r["mean_forecast"] for r in t["bins"] if r["n"]]
        ys = [r["observed_frequency"] for r in t["bins"] if r["n"]]
        ns = [r["n"] for r in t["bins"] if r["n"]]
        ax.plot(xs, ys, color="#1f5aa6", lw=1.2)
        ax.scatter(xs, ys, s=[18 + 6 * np.sqrt(n) for n in ns], color="#1f5aa6", zorder=3)
        ax.set_xlim(0, 1); ax.set_ylim(0, 1)
        ax.set_title(f"{label}\nECE {t['ece']:.3f}, n={t['n']}", fontsize=9)
        ax.set_ylabel("observed frequency" if j == 0 else "")
        hx.bar([r["lo"] + (r["hi"] - r["lo"]) / 2 for r in t["bins"]], [r["n"] for r in t["bins"]], width=1.0 / bins * 0.9, color="0.5")
        hx.set_xlim(0, 1); hx.set_xlabel("forecast probability"); hx.set_ylabel("count" if j == 0 else "")
    fig.suptitle(title, fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


CONST_TOL = 1e-12  # a series whose spread is float noise is constant: correlation undefined, never a spurious number


def _pearson(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float)
    if len(a) < 3 or np.std(a) < CONST_TOL or np.std(b) < CONST_TOL:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def _center_within_outcome(e, o):
    e = np.array(e, float)
    for v in (0.0, 1.0):
        m = o == v
        if m.any():
            e[m] -= e[m].mean()
    return e


def error_correlation(F: dict, o):
    """F: {name: forecast vector over claims}. Signed error e = p - o.
    raw: Pearson corr of signed errors across claims.
    within_outcome: same after removing each series' mean error within outcome=0 and outcome=1, which removes the
    structure shared by any two forecasters merely because both are scored against the same outcomes.
    A null (None) means the series is constant or there are <3 claims; it is never replaced by 0."""
    o = np.asarray(o, float)
    names = list(F)
    E = {n: np.asarray(F[n], float) - o for n in names}
    Ew = {n: _center_within_outcome(E[n], o) for n in names}
    raw = {a: {b: (1.0 if a == b and np.std(E[a]) >= CONST_TOL else _pearson(E[a], E[b])) for b in names} for a in names}
    win = {a: {b: (1.0 if a == b and np.std(Ew[a]) >= CONST_TOL else _pearson(Ew[a], Ew[b])) for b in names} for a in names}

    def offdiag(M):
        v = [M[a][b] for i, a in enumerate(names) for b in names[i + 1:] if M[a][b] is not None]
        return float(np.mean(v)) if v else None

    out = {"names": names, "raw": raw, "within_outcome": win,
           "mean_offdiag_raw": offdiag(raw), "mean_offdiag_within_outcome": offdiag(win)}
    for key in ("mean_offdiag_raw", "mean_offdiag_within_outcome"):
        r = out[key]
        n = len(names)
        # effective number of independent forecasters under an equicorrelation + equal-variance ASSUMPTION
        out["n_eff_equicorr_" + key.split("mean_offdiag_")[1]] = (n / (1 + (n - 1) * r)) if (r is not None and n > 1 and 1 + (n - 1) * r > 0) else None
    out["n_eff_note"] = "N/(1+(N-1)*rho): exact only for equal-variance equicorrelated errors; a descriptive summary, not an estimate with an interval."
    return out


def within_vs_cross_family(unit_forecasts: dict, unit_family: dict, o):
    """Agent/unit-level mean pairwise error correlation, split into same-family and cross-family pairs (raw and within-outcome)."""
    names = list(unit_forecasts)
    ec = error_correlation(unit_forecasts, o)
    res = {}
    for kind in ("raw", "within_outcome"):
        same, cross = [], []
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                v = ec[kind][a][b]
                if v is None:
                    continue
                (same if unit_family[a] == unit_family[b] else cross).append(v)
        res[kind] = {"same_family_mean": float(np.mean(same)) if same else None, "n_same_pairs": len(same),
                     "cross_family_mean": float(np.mean(cross)) if cross else None, "n_cross_pairs": len(cross)}
    return res
