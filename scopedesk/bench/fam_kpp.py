"""Family 7/8: fisher_kpp_speed. Claim (fisher-kpp-speed): u_t = D u_xx + s u(1-u): compactly supported data spread at c* = 2 sqrt(sD).
Other reaction terms (compare squared speeds exactly, units D s = 1 scaling):
  logistic            : c = 2 sqrt(sD)                                    -> applies
  f = s u(1-u)(1+a u) : c = 2 sqrt(sD) for a<=2 ; (2+a)/sqrt(2a) sqrt(sD) for a>2   (Hadeler-Rothe), applies iff a<=2
  Allee f = s u(1-u)(u-m), 0<m<1/2 : c = (1-2m) sqrt(sD/2)  (exact front) -> out_of_scope (always slower: front is pushed, c < c*)
Note: the sufficient KPP inequality f(u)<=f'(0)u FAILS for 1<a<=2 yet the 2 sqrt(sD) speed still holds: those are benign items."""
from fractions import Fraction as F
from common import item, ftxt, exclude
FAMILY = "fisher_kpp_speed"

def c2(kind, par):            # squared speed in units of sD
    if kind == "logistic": return F(4)
    if kind == "cubic_pos": return F(4) if par <= 2 else (2 + par) ** 2 / (2 * par)
    if kind == "allee": return (1 - 2 * par) ** 2 / 2

def decide(kind, par):
    if kind == "unspecified": return "underdetermined", ["KPP_NONLINEARITY"], {"missing": "growth nonlinearity"}
    sq = c2(kind, par)
    if sq == 4: return "applies", [], {"c_squared_over_sD": str(sq)}
    return "out_of_scope", ["KPP_NONLINEARITY"], {"c_squared_over_sD": str(sq), "kpp_squared": "4", "slower_than_kpp": sq < 4}

def render(rng, kind, par, D, s, tset):
    if kind == "logistic": rx = "logistic growth s u(1-u)"
    elif kind == "cubic_pos": rx = f"growth s u(1-u)(1+{ftxt(par)}u)" if tset == "A" else f"a reaction term s*u*(1-u)*(1 + {ftxt(par)}*u)"
    elif kind == "allee": rx = f"strong-Allee growth s u(1-u)(u-{ftxt(par)})" if tset == "A" else f"bistable kinetics s*u*(1-u)*(u - {ftxt(par)})"
    else: rx = "some saturating growth term"
    if tset == "A":
        return f"A population with diffusion D = {ftxt(D)} and {rx}, s = {ftxt(s)}, starts as a compactly supported patch. Fisher and Kolmogorov say the front moves at 2*sqrt(sD). Is that the speed here?"
    return f"A compact initial colony spreads with diffusivity {ftxt(D)} and {rx} (rate constant {ftxt(s)}). May I predict the invasion speed as 2 sqrt(s D)?"

def make(rng, n, start_id):
    out, seen = [], set()
    want = ["logistic", "cubic_le2", "cubic_gt2", "allee", "allee", "logistic", "cubic_le2", "unspec", "cubic_gt2", "allee"]
    while len(out) < n:
        t = want[len(out) % len(want)]
        D = F(rng.randint(1, 8), 2); s = F(rng.randint(1, 8), 2)
        kind, par = {"logistic": ("logistic", None), "cubic_le2": ("cubic_pos", F(rng.choice([1, 3, 4, 5, 6]), 3)),
                     "cubic_gt2": ("cubic_pos", F(rng.choice([7, 8, 10, 12, 16]), 3)), "allee": ("allee", F(rng.choice([1, 2, 3, 4]), 10)),
                     "unspec": ("unspecified", None)}[t]
        if (kind, par, D, s) in seen: continue
        if kind == "cubic_pos" and F(4) < c2(kind, par) < F(4) * F(103, 100) ** 2:
            exclude(FAMILY, "pushed speed within 3% of the KPP speed (not measurable apart)", {"kind": kind, "par": par}); continue
        seen.add((kind, par, D, s)); v, c, w = decide(kind, par); tset = "A" if len(out) % 2 == 0 else "B"
        rep = {"knob": "front_type", "valid_grid": ["pushed-front speed formula"]} if v == "out_of_scope" else {}
        out.append(item(f"kp-{start_id+len(out):04d}", FAMILY, "formal", render(rng, kind, par, D, s, tset),
                        {"kind": kind, "par": None if par is None else str(par), "D": str(D), "s": str(s)}, v, c, w, rep, tset, t))
    return out
