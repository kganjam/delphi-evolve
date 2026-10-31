"""Method-independent numerical audit of the five families that have no oracle layer (critic, 2026-10-31).

Re-derives the verdict of each item in kimura_regime, hawk_dove_ess, hamilton_rule_form, fisher_kpp_speed, greenhill_buckling
from the structured parameters in instances_full.jsonl using DIFFERENT numerical methods than the generator modules (it imports none of fam_*.py):
  kimura   : exact rational (Fraction) Gauss solve of the Wright-Fisher chain  + vectorised Monte Carlo of the same chain (200k replicates, seeded)
  hawk_dove: replicator-ODE integration (RK4) from several initial frequencies; ESS = the attractor
  hamilton : explicit pair-type enumeration + one-generation recursion for the sign of delta-p (no closed form)
  kpp      : finite-difference PDE simulation of the front (u_t = u_xx + f(u), D=s=1 after rescaling; one dimensional run checks the rescaling)
  greenhill: integro-differential buckling eigenproblem (finite differences, trapezoid), NOT the Rayleigh-Ritz energy form of the generator
Limits: same author as the generator, the DECLARED CONVENTIONS (what counts as 'applies') are taken from the family docstrings, so this audits the
numerics and the arithmetic, not the choice of convention. Underdetermined items are checked by a sweep over the missing input.
Run: python3 -I audit_five_families_numeric.py  (needs numpy, scipy)  -> five_families_numeric_audit.json
"""
import json, math, os, sys
from fractions import Fraction as F
import numpy as np
os.environ.setdefault("OMP_NUM_THREADS", "1")
HERE = os.path.dirname(os.path.abspath(__file__)); B = os.path.join(HERE, "..", "v1_2")
rows = [json.loads(l) for l in open(os.path.join(B, "instances_full.jsonl"))]
key = {json.loads(l)["id"]: json.loads(l) for l in open(os.path.join(B, "key.jsonl"))}
FAMS = ["kimura_regime", "hawk_dove_ess", "hamilton_rule_form", "fisher_kpp_speed", "greenhill_buckling"]
out = {f: [] for f in FAMS}

# ---------------- Kimura ----------------
def exact_fix_rational(N, s):
    s = F(s)
    P = [[F(0)] * (N + 1) for _ in range(N + 1)]
    for i in range(N + 1):
        p = F(i) * (1 + s) / (N + i * s) if i < N else F(1)
        for j in range(N + 1):
            P[i][j] = F(math.comb(N, j)) * p ** j * (1 - p) ** (N - j)
    n = N - 1  # transient states 1..N-1 ; solve (I-Q)h = R
    A = [[(F(1) if i == j else F(0)) - P[i + 1][j + 1] for j in range(n)] + [P[i + 1][N]] for i in range(n)]
    for c in range(n):
        piv = next(r for r in range(c, n) if A[r][c] != 0); A[c], A[piv] = A[piv], A[c]
        inv = 1 / A[c][c]; A[c] = [x * inv for x in A[c]]
        for r in range(n):
            if r != c and A[r][c] != 0:
                fct = A[r][c]; A[r] = [x - fct * y for x, y in zip(A[r], A[c])]
    return A[0][n]

def mc_fix(N, s, reps=200000, seed=7):
    rng = np.random.default_rng(seed); s = float(s)
    i = np.ones(reps, dtype=np.int64); fixed = 0; alive = np.ones(reps, bool)
    while alive.any():
        p = i[alive] * (1 + s) / (N + i[alive] * s)
        i[alive] = rng.binomial(N, p)
        done = alive.copy(); a = np.where(alive)[0]
        fixed += int((i[a] == N).sum()); alive[a[(i[a] == N) | (i[a] == 0)]] = False
    return fixed / reps

for r in rows:
    if r["family"] != "kimura_regime": continue
    h = r["hidden"]["structured"]; N, s, kind = h["N"], F(h["s"]), h["kind"]
    ex = exact_fix_rational(N, s); mc = mc_fix(N, s)
    approx = F(1, N) if kind == "neutral" else (1 - math.exp(-2 * float(s))) / (1 - math.exp(-2 * N * float(s)))
    dev = abs(float(approx) - float(ex)) / float(ex); dev_mc = abs(float(approx) - mc) / mc
    se = math.sqrt(mc * (1 - mc) / 200000) / mc * float(approx) / mc  # rough SE of dev from MC
    v = "applies" if dev <= 0.10 else "out_of_scope"
    out["kimura_regime"].append({"id": r["id"], "N": N, "s": str(s), "kind": kind, "exact_rational": float(ex), "mc": mc, "rel_dev_exact": round(dev, 5), "rel_dev_mc": round(dev_mc, 5),
                                 "verdict_independent": v, "key": key[r["id"]]["verdict"], "mc_same_side_of_10pct": (dev_mc <= 0.10) == (dev <= 0.10)})

# ---------------- Hawk-Dove ----------------
def replicator_limit(V, C, p0, T=4000.0, h=0.01):
    p = p0
    f = lambda p: p * (1 - p) * (p * (V - C) / 2 + (1 - p) * V - (1 - p) * V / 2)
    for _ in range(int(T / h)):
        k1 = f(p); k2 = f(p + h * k1 / 2); k3 = f(p + h * k2 / 2); k4 = f(p + h * k3); p += h * (k1 + 2 * k2 + 2 * k3 + k4) / 6
    return p

for r in rows:
    if r["family"] != "hawk_dove_ess": continue
    h = r["hidden"]["structured"]; V = float(F(h["V"])); Cs = h["C"]
    if Cs is None:
        # underdetermined check: attractor class depends on C (sweep both sides of V)
        lo = replicator_limit(V, V / 2 + 1e-9, 0.5); hi = replicator_limit(V, 2 * V + 1.0, 0.5)
        v = "underdetermined" if (abs(lo - 1.0) < 1e-3 and 0 < hi < 0.999) else "check"
        det = {"limit_C_below_V": lo, "limit_C_above_V": hi}
    else:
        C = float(F(Cs)); lims = [replicator_limit(V, C, p0) for p0 in (0.05, 0.5, 0.95)]
        claim = V / C
        v = "applies" if (C > V and all(abs(l - claim) < 1e-3 for l in lims)) else "out_of_scope" if all(abs(l - 1.0) < 1e-3 for l in lims) and claim >= 1 - 1e-12 else "check"
        det = {"limits": lims, "claim_V_over_C": claim}
    out["hawk_dove_ess"].append({"id": r["id"], "V": h["V"], "C": Cs, **det, "verdict_independent": v, "key": key[r["id"]]["verdict"]})

# ---------------- Hamilton ----------------
def delta_p_sign(b, c, r, d, p):
    # explicit pair enumeration: focal type g, partner type g' ; P(g'=1|g=1)=r+(1-r)p, P(g'=1|g=0)=(1-r)p ; w=1-c g+b g'+d g g'
    w = lambda g, g2: 1 - c * g + b * g2 + d * g * g2
    q1, q0 = r + (1 - r) * p, (1 - r) * p
    w1 = q1 * w(1, 1) + (1 - q1) * w(1, 0); w0 = q0 * w(0, 1) + (1 - q0) * w(0, 0)
    wbar = p * w1 + (1 - p) * w0; assert wbar > 0
    return p * w1 / wbar - p          # p' - p after one generation

def sign(x): return (x > 0) - (x < 0)
for r in rows:
    if r["family"] != "hamilton_rule_form": continue
    h = r["hidden"]["structured"]; b, c, rr, d = (F(h[k]) for k in "bcrd"); ham = sign(rr * b - c)
    if h["p"] is None:
        grid = [F(k, 100) for k in range(1, 100)]; agree = {bool(sign(delta_p_sign(b, c, rr, d, p)) == ham) for p in grid}
        v = "underdetermined" if len(agree) == 2 else ("applies" if agree == {True} else "out_of_scope"); det = {"agreement_over_p_grid": sorted(agree)}
    else:
        p = F(h["p"]); ag = sign(delta_p_sign(b, c, rr, d, p)) == ham; v = "applies" if ag else "out_of_scope"; det = {"agrees_at_p": ag}
    out["hamilton_rule_form"].append({"id": r["id"], **{k: h[k] for k in "bcdpr"}, **det, "verdict_independent": v, "key": key[r["id"]]["verdict"]})

# ---------------- Fisher-KPP ----------------
def front_speed(f, L=520.0, dx=0.1, T=160.0):
    n = int(L / dx); x = np.arange(n) * dx; u = (x < 10).astype(float); dt = 0.2 * dx * dx; steps = int(math.ceil(T / dt)) + 2
    pos = []
    t_rec = (T / 2, T)
    rec = {}
    for k in range(1, steps + 1):
        lap = np.empty_like(u); lap[1:-1] = u[2:] - 2 * u[1:-1] + u[:-2]; lap[0] = 2 * (u[1] - u[0]); lap[-1] = 0
        u = u + dt * (lap / dx ** 2 + f(u)); u = np.clip(u, 0, 1.5)
        tt = k * dt
        for tr in t_rec:
            if tr not in rec and tt >= tr:
                j = np.argmax(u < 0.5); rec[tr] = x[j - 1] + dx * (u[j - 1] - 0.5) / (u[j - 1] - u[j])
    return (rec[T] - rec[T / 2]) / (T / 2)

kpp_cache = {}
def kpp_ratio(kind, par):
    kk = (kind, par)
    if kk in kpp_cache: return kpp_cache[kk]
    a = float(F(par)) if par else 0.0
    f = {"logistic": lambda u: u * (1 - u), "cubic_pos": lambda u: u * (1 - u) * (1 + a * u), "allee": lambda u: u * (1 - u) * (u - a)}[kind]
    kpp_cache[kk] = front_speed(f) / 2.0; return kpp_cache[kk]

for r in rows:
    if r["family"] != "fisher_kpp_speed": continue
    h = r["hidden"]["structured"]
    if h["kind"] == "unspecified":
        lg, al = kpp_ratio("logistic", None), kpp_ratio("allee", "1/5")
        v = "underdetermined" if (abs(lg - 1) < 0.02 and al < 0.5) else "check"; det = {"logistic_ratio": lg, "allee_0.2_ratio": al}
    else:
        ratio = kpp_ratio(h["kind"], h["par"]); v = "applies" if abs(ratio - 1) < 0.015 else "out_of_scope" if abs(ratio - 1) > 0.025 else "indeterminate"
        det = {"measured_speed_over_2sqrt_sD": round(ratio, 4)}
    out["fisher_kpp_speed"].append({"id": r["id"], "kind": h["kind"], "par": h["par"], **det, "verdict_independent": v, "key": key[r["id"]]["verdict"]})
# one dimensional run checks the D, s rescaling: D=3/2, s=5/2, logistic should move at 2 sqrt(3.75)
def dimensional_check(D=1.5, s=2.5, T=40.0, dx=0.1):
    L = 260.0; n = int(L / dx); x = np.arange(n) * dx; u = (x < 3).astype(float); dt = 0.2 * dx * dx / D; steps = int(math.ceil(T / dt)) + 2; rec = {}
    for k in range(1, steps + 1):
        lap = np.empty_like(u); lap[1:-1] = u[2:] - 2 * u[1:-1] + u[:-2]; lap[0] = 2 * (u[1] - u[0]); lap[-1] = 0
        u = u + dt * (D * lap / dx ** 2 + s * u * (1 - u)); tt = k * dt
        for tr in (T / 2, T):
            if tr not in rec and tt >= tr:
                j = np.argmax(u < 0.5); rec[tr] = x[j - 1] + dx * (u[j - 1] - 0.5) / (u[j - 1] - u[j])
    return (rec[T] - rec[T / 2]) / (T / 2) / (2 * math.sqrt(s * D))
out["_kpp_dimensional_rescaling_check"] = {"D": 1.5, "s": 2.5, "speed_over_2sqrt_sD": round(dimensional_check(), 4)}

# ---------------- Greenhill ----------------
from scipy.linalg import eig
def Lambda_integro(t, n=400):
    """Unknown w = y'' at nodes xi_i = i h (i=0..n).  y(xi)=int_0^xi (xi-s) w(s) ds (clamped base y=y'=0 by construction, trapezoid).
    Buckling: f^4 w(xi) = Lam * int_xi^1 f(s)^2 (y(s)-y(xi)) ds  (EI y'' = P(y_tip - y) sign; free end w(1)=0 automatic).  Lam = 1/(largest eigenvalue of f^-4 B K)."""
    h = 1.0 / n; x = np.arange(n + 1) * h; f = 1 - (1 - t) * x
    tw = np.full(n + 1, h); tw[0] = tw[-1] = h / 2                 # trapezoid weights on [0,1]
    K = np.zeros((n + 1, n + 1))
    for j in range(1, n + 1):                                       # y_j = sum_k K[j,k] w_k , trapezoid on [0, x_j]
        wk = np.full(j + 1, h); wk[0] = wk[-1] = h / 2
        K[j, : j + 1] = wk * (x[j] - x[: j + 1])
    Bm = np.zeros((n + 1, n + 1))                                   # (B y)_i = sum_{k>=i} wk f_k^2 (y_k - y_i)
    for i in range(n):
        wk = np.full(n + 1 - i, h); wk[0] = wk[-1] = h / 2
        c = wk * f[i:] ** 2
        Bm[i, i:] += c; Bm[i, i] -= c.sum()
    M = (Bm @ K)[:n, :n] / (f[:n] ** 4)[:, None]                    # drop node n (w=0 there)
    mu = np.linalg.eigvals(M)
    mu = mu[(abs(mu.imag) < 1e-9 * np.abs(mu).max()) & (mu.real > 0)].real
    return float(1.0 / mu.max())

lam_cache = {}
def lam(t):
    if t not in lam_cache:
        lam_cache[t] = Lambda_integro(t)
    return lam_cache[t]
G = 9.81
def Hcr(E, rho, D, t): return (E * (D / 2) ** 2 / (4 * rho * G) * lam(t)) ** (1 / 3)
def Hform(E, rho, D): return 0.788 * (E / (rho * G)) ** (1 / 3) * D ** (2 / 3)
out["_greenhill_Lambda_uniform_integro_n400"] = lam(1.0); out["_greenhill_Lambda_uniform_reference_Greenhill_7.8373"] = 7.8373

def gh_verdict(E, rho, D, H, t):
    pred = H > Hform(E, rho, D); true = H > Hcr(E, rho, D, t)
    return "applies" if pred == true else "out_of_scope"

for r in rows:
    if r["family"] != "greenhill_buckling": continue
    h = r["hidden"]["structured"]; E, rho, D, H, t = h["E"], h["rho"], h["D"], h["H"], h["t"]
    if E is None or rho is None:
        Es = [E] if E is not None else [4e9, 6e9, 10e9, 15e9]; rhos = [rho] if rho is not None else [600.0, 800.0, 1000.0]
        vs = {gh_verdict(e, q, D, H, t) for e in Es for q in rhos}
        v = "underdetermined" if len(vs) > 1 else next(iter(vs)); det = {"verdicts_over_declared_ranges": sorted(vs)}
        # reading 2: the missing property is unbounded -> does ANY value flip the verdict?  (continuous sweep; report the disagreement interval)
        grid = np.geomspace(100, 20000, 20000) if rho is None else np.geomspace(1e8, 1e12, 20000)
        flips = [g for g in grid if (gh_verdict(E, g, D, H, t) if rho is None else gh_verdict(g, rho, D, H, t)) != gh_verdict(*( (E, 800.0) if rho is None else (1e10, rho)), D, H, t)] if len(vs) == 1 else []
        agree_set = {gh_verdict(E, g, D, H, t) if rho is None else gh_verdict(g, rho, D, H, t) for g in grid}
        det["verdicts_if_property_unbounded"] = sorted(agree_set)
        det["verdict_if_property_unbounded"] = "underdetermined" if len(agree_set) > 1 else next(iter(agree_set))
        if len(agree_set) > 1:
            dis = [g for g in grid if (gh_verdict(E, g, D, H, t) if rho is None else gh_verdict(g, rho, D, H, t)) == "out_of_scope"]
            det["out_of_scope_value_interval"] = [float(min(dis)), float(max(dis))]
            det["property"] = "rho_kg_m3" if rho is None else "E_Pa"
    else:
        v = gh_verdict(E, rho, D, H, t); det = {"H_formula": round(Hform(E, rho, D), 3), "H_cr_independent": round(Hcr(E, rho, D, t), 3), "H": H, "t": t}
    out["greenhill_buckling"].append({"id": r["id"], **det, "verdict_independent": v, "key": key[r["id"]]["verdict"]})

summary = {}
for f in FAMS:
    L = out[f]; agree = sum(x["verdict_independent"] == x["key"] for x in L)
    summary[f] = {"items": len(L), "agree_with_key": agree, "disagree": [x["id"] for x in L if x["verdict_independent"] != x["key"]]}
    if f == "greenhill_buckling":
        a2 = sum(x.get("verdict_if_property_unbounded", x["verdict_independent"]) == x["key"] for x in L)
        summary[f]["agree_with_key_if_missing_property_unbounded"] = a2
out["_summary"] = summary
json.dump(out, open(os.path.join(HERE, "five_families_numeric_audit.json"), "w"), indent=1, default=str)
print(json.dumps(summary, indent=1)); print({k: v for k, v in out.items() if k.startswith("_") and k != "_summary"})
