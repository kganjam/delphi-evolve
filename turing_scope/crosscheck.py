"""Independent NUMERIC cross-check: builds the explicit 2x2 matrix J - q diag(Du,Dv) and asks
numpy.linalg.eigvals for its eigenvalues. It does not use the trace/determinant formulas that the
exact adapter uses. Floating point: only a numerical check, not a proof (and not Lean)."""
from __future__ import annotations

from fractions import Fraction

AMBIG = 1e-9


def eig_rows(J, D, r, n_max):
    import numpy as np
    Jf = np.array([[float(x) for x in row] for row in J])
    Df = np.diag([float(D[0]), float(D[1])])
    out = []
    for n in range(0, n_max + 1):
        q = float(Fraction(n * n) / (r * r))
        ev = np.linalg.eigvals(Jf - q * Df)
        out.append((n, q, float(ev.real.max()), [complex(e) for e in ev]))
    return out


def crosscheck(result: dict, n_sweep: int = 2000) -> dict:
    """Compare the exact classification of result['modes'] (and an n<=n_sweep sweep) with numpy eigenvalues."""
    try:
        import numpy  # noqa: F401
    except ImportError:
        return {"available": False, "reason": "numpy not installed"}
    inp = result["inputs"]
    J = [[Fraction(x) for x in row] for row in inp["jacobian"]]
    D = [Fraction(x) for x in inp["diffusivities"]]
    r = Fraction(inp["domain"]["length_over_pi"])
    rows = eig_rows(J, D, r, n_sweep)
    exact_unstable = set(result["unstable_modes"])
    mism, ambig = [], []
    for n, q, maxre, _ in rows:
        if abs(maxre) < AMBIG:
            ambig.append(n)
            continue
        if (maxre > 0) != (n in exact_unstable):
            mism.append({"n": n, "q": q, "numpy_max_real_eig": maxre, "exact_unstable": n in exact_unstable})
    return {"available": True, "method": "numpy.linalg.eigvals on float(J - q diag(D))", "modes_checked": n_sweep + 1,
            "mismatches": mism, "ambiguous_within_1e-9": ambig,
            "numpy_unstable_modes": [n for n, _, m, _ in rows if m > AMBIG],
            "max_real_eigenvalue_by_mode_first6": [{"n": n, "max_real_eig": m} for n, _, m, _ in rows[:6]],
            "limitation": f"modes beyond n={n_sweep} are covered only by the analytic tail rule, not by this float sweep",
            "agrees": not mism}
