"""Family 2/8: wavelength_formula_licence. Claim (Delphi turing-wavelength): at onset k_c^2 = sqrt(det J/(Du Dv)),
lambda_c = 2 pi/k_c; valid near onset and for large domains. Operational truth (float, margins enforced):
the formula is LICENSED iff lambda_c is within 10% of the wavelength of the fastest-growing ADMISSIBLE Neumann mode.
Out-of-scope cause: NEAR_ONSET if even the continuum fastest-growing wavelength is >10% off lambda_c; else LARGE_DOMAIN
(discreteness of admissible modes). Items within +-2% of the 10% threshold are excluded and listed."""
import math, random
from fractions import Fraction as F
from common import ftxt, signed, item, exclude
FAMILY = "wavelength_formula_licence"

import numpy as np

def growth_arr(J, d, q):           # max real part of eigenvalues of J - q diag(1,d), vectorised
    a, b, c, e = [float(x) for x in J]
    A = a - q; E = e - float(d) * q
    tr = A + E; det = A * E - b * c
    disc = tr * tr / 4 - det
    return tr / 2 + np.sqrt(np.where(disc > 0, disc, 0.0))

QS = np.linspace(1e-4, 4.0, 40000)

def evaluate(J, d, r):
    a, b, c, e = [float(x) for x in J]; dd = float(d)
    det = a * e - b * c
    if not (a + e < 0 and det > 0): return None
    q_c = math.sqrt(det / dd); lam_c = 2 * math.pi / math.sqrt(q_c)   # Delphi record: k_c^2 = sqrt(det J/(Du Dv))
    gq = growth_arr(J, d, QS)
    if gq.max() <= 1e-9: return None
    lam_cont = 2 * math.pi / math.sqrt(QS[int(gq.argmax())])
    L = float(r) * math.pi
    nn = np.arange(1, 600); qa = (nn * math.pi / L) ** 2
    ga = growth_arr(J, d, qa)
    if ga.max() <= 1e-9: return {"no_mode": True, "lam_c": lam_c, "lam_cont": lam_cont}
    i = int(ga.argmax())
    return {"lam_c": lam_c, "lam_cont": lam_cont, "lam_adm": 2 * math.pi / math.sqrt(qa[i]), "n": int(nn[i]), "no_mode": False}

def decide(J, d, r):
    """v1.1 rule (declared in the request): adequate iff the admissible fastest-growing mode's wavelength is within 10% of lambda_c."""
    ev = evaluate(J, d, r)
    if ev is None: return None
    if ev["no_mode"]: return ("out_of_scope", ["DOMAIN_ADMISSIBLE_MODE"], ev, 1.0)
    dev_c = abs(ev["lam_cont"] - ev["lam_c"]) / ev["lam_c"]
    dev_a = abs(ev["lam_adm"] - ev["lam_c"]) / ev["lam_c"]
    margin = abs(dev_a - 0.10)
    w = dict(ev, dev_cont=dev_c, dev_adm=dev_a)
    if dev_a <= 0.10: return ("applies", [], w, margin)
    return ("out_of_scope", ["NEAR_ONSET"] if dev_c > 0.10 else ["LARGE_DOMAIN"], w, margin)

def render(rng, J, d, r, tset):
    a, b, c, e = J
    if tset == "A":
        s = (f"A two-species system has Jacobian [[{ftxt(a)}, {ftxt(b)}], [{ftxt(c)}, {ftxt(e)}]] at its uniform state, with D_u = 1 and D_v = {ftxt(d)}, "
             f"on a no-flux interval of length {ftxt(r)}*pi. Is lambda_c = 2*pi/k_c with k_c^2 = sqrt(det J/(D_u D_v)) an adequate prediction of the linear pattern wavelength?")
    else:
        s = (f"Reaction part: f_u = {ftxt(a)}u {signed(b)}v, g = {ftxt(c)}u {signed(e)}v; the second species is {ftxt(d)} times as diffusive as the first; "
             f"the tissue is a sealed line segment of length pi x {ftxt(r)}. Is the onset-wavelength formula 2 pi / k_c (k_c^2 = sqrt(det J/(D_u D_v))) an adequate prediction of the linear pattern wavelength?")
    return s

def critical_d(J):
    a, b, c, e = [float(x) for x in J]; det = a * e - b * c
    if a == 0 or det <= 0 or a + e >= 0: return None
    disc = det * (det - a * e)
    if disc < 0: return None
    roots = [((2 * det - a * e) + sg * 2 * math.sqrt(disc)) / a ** 2 for sg in (1, -1)]
    roots = [x for x in roots if x > 0 and (x * a + e) > 0]
    return min(roots) if roots else None

def rand_activator_J(rng):
    """activator-inhibitor Jacobian: a>0, e<0, tr<0, b*c<0 with |bc| > |ae| so det>0."""
    while True:
        a = F(rng.randint(1, 8), 4); e = -(a + F(rng.randint(1, 12), 4))
        m = F(rng.randint(1, 16), 4); n_ = F(rng.randint(1, 16), 4)
        if m * n_ > abs(a * e):
            sg = rng.choice([1, -1]); return (a, sg * m, -sg * n_, e)

def make(rng, n, start_id):
    out, seen, guard = [], set(), 0
    RS = [F(x, y) for x in (4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128) for y in (1, 2)]
    want = ["applies"] * 6 + ["NEAR_ONSET"] * 4 + ["LARGE_DOMAIN"] * 3 + ["DOMAIN_ADMISSIBLE_MODE"] * 3
    while len(out) < n:
        guard += 1
        if guard > 40000: raise RuntimeError("wavelength: cannot realise targets")
        t = want[len(out) % len(want)]
        J = rand_activator_J(rng)
        dc = critical_d(J)
        if dc is None: continue
        delta = rng.choice([0.02, 0.05, 0.1, 0.3, 1.0, 3.0])
        d = F(round(dc * (1 + delta) * 4), 4)
        if d <= 0: continue
        r = rng.choice(RS)
        res = decide(J, d, r)
        if res is None: continue
        v, c, w, margin = res
        if margin < 0.02 and v != "out_of_scope" or (margin < 0.02 and c and c[0] in ("NEAR_ONSET", "LARGE_DOMAIN")):
            exclude(FAMILY, "within 2% of the 10% licence threshold", {"J": J, "d": d, "r": r}); continue
        got = "applies" if v == "applies" else c[0]
        if got != t or (J, d, r) in seen: continue
        seen.add((J, d, r)); tset = "A" if len(out) % 2 == 0 else "B"
        out.append(item(f"wl-{start_id+len(out):04d}", FAMILY, "formal", render(rng, J, d, r, tset),
                        {"J": [str(x) for x in J], "Dv": str(d), "r_over_pi": str(r)}, v, c,
                        {k: (round(x, 6) if isinstance(x, float) else x) for k, x in w.items()}, {}, tset, t))
    return out
