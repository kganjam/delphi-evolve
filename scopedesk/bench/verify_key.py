"""Independent re-derivation of the key (critic). Deliberately does NOT import the fam_*.py decision code: each family is re-decided by a
different numerical method from the hidden structured parameters. Disagreements are findings. Usage: python3 -I verify_key.py BENCHDIR OUT.json
Methods: turing=numpy eigenvalues of J-qD over admissible modes; wavelength=numpy eigvals scan; rayleigh=Bessel-function dispersion sign;
kimura=power-iteration of the WF transition matrix (absorbing chain); hawk-dove=replicator-dynamics integration; hamilton=explicit Price covariance
over the 4-type joint distribution; greenhill=cubic-Hermite finite elements (60 el.); kpp=explicit finite-difference PDE front-speed measurement for one
representative of each (kind) class, then class-level agreement with the key's analytic classification."""
import json, math, os, sys
from fractions import Fraction as F
import numpy as np
from scipy.special import iv

def load(d):
    full = [json.loads(l) for l in open(f"{d}/instances_full.jsonl")]; key = {json.loads(l)["id"]: json.loads(l) for l in open(f"{d}/key.jsonl")}
    return full, key

def fl(x): return float(F(x))

def lam_max(J, d, q):
    M = np.array([[J[0] - q, J[1]], [J[2], J[3] - d * q]]); return np.linalg.eigvals(M).real.max()

def v_turing(s):
    J = [fl(x) for x in s["J"]]; d = fl(s["Dv"]); r = fl(s["r_over_pi"])
    if np.linalg.eigvals(np.array([[J[0], J[1]], [J[2], J[3]]])).real.max() >= 0: return "out_of_scope"
    def unstable(bc):
        mult = 2 if bc == "periodic" else 1
        qs = (mult * np.arange(1, 400) / r) ** 2
        return any(lam_max(J, d, q) > 1e-9 for q in qs)
    if s["bc"] is None:
        a, b = unstable("neumann"), unstable("periodic"); return "underdetermined" if a != b else ("applies" if a else "out_of_scope")
    return "applies" if unstable("periodic" if s["bc"] == "periodic" else "neumann") else "out_of_scope"

def v_rayleigh(s):
    sv = fl(s["s"])
    def unstable(bc):
        for n in range(1, 50):
            kr = (2 if bc == "periodic" else 1) * n / sv           # k r with l = s*pi*r
            w2 = kr * (1 - kr ** 2) * iv(1, kr) / iv(0, kr)       # Rayleigh inviscid dispersion (up to a positive constant)
            if w2 > 1e-12: return True
        return False
    claim = lambda: sv > 2
    ok = lambda bc: claim() == unstable(bc)
    if s["bc"] is None: return "underdetermined" if ok("periodic") != ok("pinned") else ("applies" if ok("periodic") else "out_of_scope")
    return "applies" if ok(s["bc"]) else "out_of_scope"

def v_kimura(s):
    N = s["N"]; sel = fl(s["s"]); P = np.zeros((N + 1, N + 1))
    for i in range(N + 1):
        p = i * (1 + sel) / (N + i * sel) if i < N else 1.0
        P[i] = [math.exp(math.lgamma(N + 1) - math.lgamma(j + 1) - math.lgamma(N - j + 1)) * p ** j * (1 - p) ** (N - j) for j in range(N + 1)]
    v = np.zeros(N + 1); v[1] = 1.0
    for _ in range(200000):                                          # power iteration to absorption
        v = v @ P
        if v[1:N].sum() < 1e-13: break
    ex = v[N]
    ap = 1 / N if s["kind"] == "neutral" else (1 - math.exp(-2 * sel)) / (1 - math.exp(-2 * N * sel))
    return "applies" if abs(ap - ex) / ex <= 0.10 else "out_of_scope"

def v_hawkdove(s):
    V = fl(s["V"])
    if s["C"] is None: return "underdetermined"
    C = fl(s["C"]); res = []
    for p0 in (0.05, 0.5, 0.95):
        p = p0
        for _ in range(200000):                                      # replicator dynamics dp/dt = p(1-p)(fH - fD)
            fH = p * (V - C) / 2 + (1 - p) * V; fD = (1 - p) * V / 2
            p += 0.002 * p * (1 - p) * (fH - fD)
        res.append(p)
    target = V / C
    return "applies" if C > V and all(abs(x - target) < 1e-3 for x in res) else "out_of_scope" if all(x > 0.99 for x in res) else "?"

def v_hamilton(s):
    b, c, r, d = (fl(s[k]) for k in ("b", "c", "r", "d"))
    def sel_sign(p):
        # joint distribution of (focal g, partner g'): P(1,1)=p(r+(1-r)p), P(1,0)=p(1-r)(1-p), P(0,1)=(1-p)(1-r)p, P(0,0)=(1-p)(1-(1-r)p)
        pj = {(1, 1): p * (r + (1 - r) * p), (1, 0): p * (1 - r) * (1 - p), (0, 1): (1 - p) * (1 - r) * p, (0, 0): (1 - p) * (1 - (1 - r) * p)}
        w = {(g, h): 1 - c * g + b * h + d * g * h for (g, h) in pj}
        wbar = sum(pj[k] * w[k] for k in pj); gbar = sum(pj[k] * k[0] for k in pj)
        cov = sum(pj[k] * (w[k] - wbar) * (k[0] - gbar) for k in pj)
        return cov
    ps = [fl(s["p"])] if s["p"] is not None else [0.1, 0.9]
    ham = r * b - c
    ok = [(sel_sign(p) > 0) == (ham > 0) for p in ps]
    return "underdetermined" if len(set(ok)) > 1 else ("applies" if ok[0] else "out_of_scope")

def herm_lambda(t, ne=60):
    f = lambda x: 1 - (1 - t) * x
    Fx = lambda x: (f(x) ** 3 - t ** 3) / (3 * (1 - t)) if abs(1 - t) > 1e-12 else 1 - x
    h = 1.0 / ne; nd = 2 * (ne + 1); K = np.zeros((nd, nd)); G = np.zeros((nd, nd)); xg, wg = np.polynomial.legendre.leggauss(6)
    for e in range(ne):
        x0 = e * h; idx = [2 * e, 2 * e + 1, 2 * e + 2, 2 * e + 3]
        for xi, wi in zip(xg, wg):
            s_ = (xi + 1) / 2; x = x0 + s_ * h; ww = wi / 2 * h
            d1 = np.array([(6 * s_ ** 2 - 6 * s_) / h, 1 - 4 * s_ + 3 * s_ ** 2, (-6 * s_ ** 2 + 6 * s_) / h, -2 * s_ + 3 * s_ ** 2])
            d2 = np.array([(12 * s_ - 6) / h ** 2, (-4 + 6 * s_) / h, (-12 * s_ + 6) / h ** 2, (-2 + 6 * s_) / h])
            K[np.ix_(idx, idx)] += ww * f(x) ** 4 * np.outer(d2, d2); G[np.ix_(idx, idx)] += ww * Fx(x) * np.outer(d1, d1)
    keep = list(range(2, nd))                                        # clamp base: y(0)=y'(0)=0
    from scipy.linalg import eigh
    return float(eigh(K[np.ix_(keep, keep)], G[np.ix_(keep, keep)], eigvals_only=True)[0])

def v_greenhill(s):
    if s["E"] is None or s["rho"] is None: return "underdetermined"
    E, rho, D, H, t = s["E"], s["rho"], s["D"], s["H"], s["t"]; g = 9.81
    Hc = lambda lam: (E * (D / 2) ** 2 / (4 * rho * g) * lam) ** (1 / 3)
    Hu, Ht = Hc(herm_lambda(1.0)), Hc(herm_lambda(t))
    return "applies" if (H > Hu) == (H > Ht) else "out_of_scope"

def v_wavelength(s):
    J = [fl(x) for x in s["J"]]; d = fl(s["Dv"]); r = fl(s["r_over_pi"])
    det = J[0] * J[3] - J[1] * J[2]; lam_c = 2 * math.pi / math.sqrt(math.sqrt(det / d))
    qs = np.linspace(1e-4, 4, 20000); g = np.array([lam_max(J, d, q) for q in qs]); lc = 2 * math.pi / math.sqrt(qs[g.argmax()])
    qa = (np.arange(1, 600) * math.pi / (r * math.pi)) ** 2; ga = np.array([lam_max(J, d, q) for q in qa])
    if ga.max() <= 1e-9: return "out_of_scope"
    la = 2 * math.pi / math.sqrt(qa[ga.argmax()])
    return "applies" if abs(lc - lam_c) / lam_c <= .1 and abs(la - lam_c) / lam_c <= .1 else "out_of_scope"

def kpp_speed(f, D=1.0, L=400.0, nx=4000, T=120.0):
    x = np.linspace(0, L, nx); dx = x[1] - x[0]; u = (x < 10).astype(float); dt = 0.2 * dx * dx / D; pos = []
    t = 0.0
    while t < T:
        lap = np.empty_like(u); lap[1:-1] = (u[2:] - 2 * u[1:-1] + u[:-2]) / dx ** 2; lap[0] = (u[1] - u[0]) * 2 / dx ** 2; lap[-1] = 0
        u = u + dt * (D * lap + f(u)); t += dt
        if abs(t - 60.0) < dt: p1 = x[np.argmax(u < 0.5)]
    p2 = x[np.argmax(u < 0.5)]
    return (p2 - p1) / (T - 60.0)

def v_kpp(s):
    k = s["kind"]
    if k == "unspecified": return "underdetermined"
    sc, D = fl(s["s"]), fl(s["D"]); par = None if s["par"] is None else fl(s["par"]); key = ("kpp", k, par)
    if key not in _kcache:
        # unit D=s=1 scaling; speeds scale as sqrt(sD)
        f = {"logistic": lambda u: u * (1 - u), "cubic_pos": lambda u: u * (1 - u) * (1 + par * u) if par is not None else u, "allee": lambda u: u * (1 - u) * (u - par) if par is not None else u}[k]
        _kcache[key] = kpp_speed(f, D=1.0)
    return "applies" if abs(_kcache[key] - 2.0) / 2.0 < 0.03 else "out_of_scope"
_kcache = {}

V = {"turing_finite_domain": v_turing, "rayleigh_plateau": v_rayleigh, "kimura_regime": v_kimura, "hawk_dove_ess": v_hawkdove,
     "hamilton_rule_form": v_hamilton, "greenhill_buckling": v_greenhill, "wavelength_formula_licence": v_wavelength, "fisher_kpp_speed": v_kpp}

if __name__ == "__main__":
    d, out = sys.argv[1], sys.argv[2]
    full, key = load(d); res = {}; dis = []
    for it in full:
        fam = it["family"]; v = V[fam](it["hidden"]["structured"]); k = key[it["id"]]["verdict"]
        r = res.setdefault(fam, {"n": 0, "agree": 0}); r["n"] += 1; r["agree"] += int(v == k)
        if v != k: dis.append({"id": it["id"], "independent": v, "key": k, "structured": it["hidden"]["structured"]})
    json.dump({"per_family": res, "disagreements": dis, "kpp_speeds_measured_D1": {str(k): v for k, v in _kcache.items()},
               "greenhill_Lambda_uniform_hermite_fe": herm_lambda(1.0)}, open(out, "w"), indent=1)
    print(json.dumps(res)); print("disagreements:", len(dis)); [print(x["id"], x["independent"], x["key"]) for x in dis[:12]]
