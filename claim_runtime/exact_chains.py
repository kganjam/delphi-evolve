"""Exact finite absorbing Markov chains used as an INDEPENDENT reference for the
Kimura diffusion formula. Pure Python, small (<200 states), no data.

Models (all with p' = expected allele frequency after selection, then binomial sampling):
  * diploid_wf_genic(N, s): N diploid individuals = 2N gene copies; genotype fitnesses
    1 : 1+s : 1+2s (genic/additive); random mating; binomial(2N, p').
    p' = p(1+s(1+p)) / (1+2sp)   [derived from genotype frequencies in tests]
  * haploid_wf(N, s): N haploid individuals; fitness 1 : 1+s; binomial(N, p'),
    p' = p(1+s)/(1+sp).
  * moran(N, r): N haploid individuals, one birth+one death per step, relative fitness r.
These are textbook models; the code was written from their definitions, not from Delphi.
"""
from __future__ import annotations

import math
from fractions import Fraction


def binom_pmf_row(n: int, q: float) -> list:
    if q <= 0.0:
        return [1.0] + [0.0] * n
    if q >= 1.0:
        return [0.0] * n + [1.0]
    lq, l1q = math.log(q), math.log1p(-q)
    lg = math.lgamma
    row = [math.exp(lg(n + 1) - lg(k + 1) - lg(n - k + 1) + k * lq + (n - k) * l1q) for k in range(n + 1)]
    z = sum(row)            # lgamma rounding leaves the row sum ~1e-13 off; renormalise
    return [x / z for x in row]


def diploid_p_after_selection(p: float, s: float) -> float:
    return p * (1 + s * (1 + p)) / (1 + 2 * s * p)


def haploid_p_after_selection(p: float, s: float) -> float:
    return p * (1 + s) / (1 + s * p)


def wf_transition(n_copies: int, p_after_selection) -> list:
    P = []
    for i in range(n_copies + 1):
        p = i / n_copies
        P.append(binom_pmf_row(n_copies, min(max(p_after_selection(p), 0.0), 1.0)))
    return P


def solve_dense(A: list, b: list) -> list:
    """Gaussian elimination with partial pivoting (pure Python)."""
    n = len(A)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for c in range(n):
        piv = max(range(c, n), key=lambda r: abs(M[r][c]))
        if abs(M[piv][c]) < 1e-300:
            raise ZeroDivisionError("singular system")
        M[c], M[piv] = M[piv], M[c]
        pc = M[c][c]
        for r in range(c + 1, n):
            f = M[r][c] / pc
            if f:
                Mr, Mc = M[r], M[c]
                for k in range(c, n + 1):
                    Mr[k] -= f * Mc[k]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        x[i] = (M[i][n] - sum(M[i][k] * x[k] for k in range(i + 1, n))) / M[i][i]
    return x


def absorption_probabilities(P: list) -> list:
    """P(absorb at top state | start i) for a chain on states 0..n with 0 and n absorbing."""
    n = len(P) - 1
    T = list(range(1, n))
    A = [[(1.0 if i == j else 0.0) - P[i][j] for j in T] for i in T]
    b = [P[i][n] for i in T]
    u = solve_dense(A, b)
    return [0.0] + u + [1.0]


def absorption_by_iteration(P: list, i0: int, tol: float = 1e-13, max_steps: int = 200_000):
    """Independent method: push the distribution forward until absorbed mass stops changing."""
    n = len(P) - 1
    dist = [0.0] * (n + 1)
    dist[i0] = 1.0
    for step in range(max_steps):
        new = [0.0] * (n + 1)
        for i, m in enumerate(dist):
            if m == 0.0:
                continue
            if i in (0, n):
                new[i] += m
                continue
            Pi = P[i]
            for j in range(n + 1):
                new[j] += m * Pi[j]
        dist = new
        if 1.0 - dist[0] - dist[n] < tol:
            return dist[n], step + 1
    raise RuntimeError("did not absorb")


def moran_matrix(N: int, r: float) -> list:
    P = [[0.0] * (N + 1) for _ in range(N + 1)]
    P[0][0] = P[N][N] = 1.0
    for i in range(1, N):
        tot = r * i + (N - i)
        up = (r * i / tot) * ((N - i) / N)
        dn = ((N - i) / tot) * (i / N)
        P[i][i + 1], P[i][i - 1], P[i][i] = up, dn, 1 - up - dn
    return P


def moran_closed_form(N: int, r: float, i: int) -> float:
    """Gambler's-ruin result (Moran 1962): rho_i = (1 - r^-i)/(1 - r^-N), r != 1."""
    if r == 1.0:
        return i / N
    return (1 - r ** (-i)) / (1 - r ** (-N))


# ---- exact rational version for tiny chains (independent of floating-point solve) -------

def _binom_frac(n: int, k: int, q: Fraction) -> Fraction:
    return math.comb(n, k) * q ** k * (1 - q) ** (n - k)


def diploid_exact_fraction(N: int, s: Fraction) -> list:
    n = 2 * N
    P = []
    for i in range(n + 1):
        p = Fraction(i, n)
        q = p * (1 + s * (1 + p)) / (1 + 2 * s * p)
        P.append([_binom_frac(n, k, q) for k in range(n + 1)])
    T = list(range(1, n))
    A = [[(Fraction(1) if i == j else Fraction(0)) - P[i][j] for j in T] for i in T]
    b = [P[i][n] for i in T]
    m = len(T)
    M = [A[i] + [b[i]] for i in range(m)]
    for c in range(m):
        piv = next(r for r in range(c, m) if M[r][c] != 0)
        M[c], M[piv] = M[piv], M[c]
        for r in range(m):
            if r != c and M[r][c] != 0:
                f = M[r][c] / M[c][c]
                M[r] = [x - f * y for x, y in zip(M[r], M[c])]
    return [Fraction(0)] + [M[i][m] / M[i][i] for i in range(m)] + [Fraction(1)]


def diploid_wf_genic(N: int, s: float):
    """Return (P, absorption vector) for the exact diploid WF chain with 2N copies."""
    P = wf_transition(2 * N, lambda p: diploid_p_after_selection(p, s))
    return P, absorption_probabilities(P)


def haploid_wf(N: int, s: float):
    P = wf_transition(N, lambda p: haploid_p_after_selection(p, s))
    return P, absorption_probabilities(P)
