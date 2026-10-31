"""Family 4/8: kimura_regime. Exact haploid Wright-Fisher chain (binomial sampling after selection p'=p(1+s)/(1+ps))
vs (a) neutral value 1/N and (b) the diffusion formula u=(1-exp(-2 N s p))/(1-exp(-2 N s)), p=1/N.
Verdict: licensed iff the approximation is within 10% of the exact one-copy fixation probability. Items within 2% of threshold excluded."""
import math
import numpy as np
from common import item, exclude, ftxt
from fractions import Fraction as F
FAMILY = "kimura_regime"
_cache = {}

def exact_fix(N, s):
    key = (N, round(s, 6))
    if key in _cache: return _cache[key]
    P = np.zeros((N + 1, N + 1))
    from math import comb
    for i in range(N + 1):
        p = i * (1 + s) / (N + i * s) if i < N else 1.0
        for j in range(N + 1):
            P[i, j] = comb(N, j) * p ** j * (1 - p) ** (N - j)
    Q = P[1:N, 1:N]; R = P[1:N, N]
    h = np.linalg.solve(np.eye(N - 1) - Q, R)
    _cache[key] = float(h[0]); return _cache[key]

def diffusion(N, s):
    x = 2 * N * s; p = 1 / N
    return (1 - math.exp(-x * p)) / (1 - math.exp(-x))

def decide(N, s, kind):
    ex = exact_fix(N, s)
    approx = 1 / N if kind == "neutral" else diffusion(N, s)
    dev = abs(approx - ex) / ex
    margin = abs(dev - 0.10)
    cond = ["DRIFT_DOMINATED"] if kind == "neutral" else ["SMALL_SELECTION_LIMIT"]
    if dev <= 0.10: return "applies", [], {"exact": ex, "approx": approx, "rel_dev": dev}, margin
    return "out_of_scope", cond, {"exact": ex, "approx": approx, "rel_dev": dev}, margin

def render(rng, N, s, kind, tset):
    st = ftxt(s)
    if kind == "neutral":
        A = (f"A single new beneficial mutant (selection coefficient s = {st}) appears in a haploid Wright-Fisher population of N = {N}. "
             f"Can I use Kimura's neutral value 1/N for its fixation probability?")
        B = (f"In a population of {N} haploid individuals, a rare allele gives its carriers relative fitness 1 + {st}. "
             f"Is it fine to treat the chance it eventually fixes as simply 1/{N}, to within about 10%?")
    else:
        A = (f"A single new mutant with selection coefficient s = {st} arises in a haploid Wright-Fisher population of N = {N}. "
             f"Is Kimura's diffusion formula u = (1 - exp(-2Ns/N))/(1 - exp(-2Ns)) accurate (about 10%) for its fixation probability?")
        B = (f"Population size {N} (haploid, Wright-Fisher); the new allele has fitness advantage {st}. "
             f"May I rely on the diffusion-approximation fixation probability (1 - e^(-2s))/(1 - e^(-2Ns)) for it?")
    return A if tset == "A" else B

def make(rng, n, start_id):
    out, seen = [], set()
    want = ["applies"] * 6 + ["oos"] * 7 + ["applies"] * 1 + ["oos"] * 2
    while len(out) < n:
        t = want[len(out) % len(want)]
        N = rng.choice([8, 10, 12, 16, 20, 30, 40]); s = F(rng.choice([1, 2, 5, 10, 20, 50, 100, 200, 300]), 1000)
        kind = rng.choice(["neutral", "diffusion"])
        v, c, w, m = decide(N, float(s), kind)
        if m < 0.02: exclude(FAMILY, "within 2% of the 10% licence threshold", {"N": N, "s": s, "kind": kind}); continue
        if (v == "applies") != (t == "applies") or (N, s, kind) in seen: continue
        seen.add((N, s, kind)); tset = "A" if len(out) % 2 == 0 else "B"
        out.append(item(f"km-{start_id+len(out):04d}", FAMILY, "formal", render(rng, N, s, kind, tset), {"N": N, "s": str(s), "kind": kind},
                        v, c, {k: round(x, 6) for k, x in w.items()}, {}, tset, t))
    return out
