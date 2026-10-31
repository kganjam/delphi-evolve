"""Family 1/8: turing_finite_domain. Verdict = is a linear Turing instability available on the stated 1-D domain.
Neumann/Dirichlet: q=(n pi/L)^2; periodic: q=(2 n pi/L)^2; L=r*pi (r rational) => exact Fractions."""
import random
from fractions import Fraction as F
from common import ftxt, signed, item, exclude

NMAX = 200
FAMILY = "turing_finite_domain"

def det_q(J, d, q):
    a, b, c, e = J
    return (a - q) * (e - d * q) - b * c

def stable(J):
    a, b, c, e = J
    return (a + e) < 0 and (a * e - b * c) > 0

def band(J, d):
    a, b, c, e = J
    B = -(d * a + e); C = a * e - b * c
    return B < 0 and B * B - 4 * d * C > 0

def modes(r, bc):
    m = 2 if bc == "periodic" else 1
    return [(F(m * n) / r) ** 2 for n in range(1, NMAX + 1)]

def unstable(J, d, r, bc):
    return [(n + 1, q) for n, q in enumerate(modes(r, bc)) if det_q(J, d, q) < 0]

def decide(J, d, r, bc):
    if not stable(J): return "out_of_scope", ["WELLMIXED_STABLE"], {"stable": False}
    um = unstable(J, d, r, bc)
    if um:
        n, q = um[0]; return "applies", [], {"first_unstable_mode": n, "q": str(q), "det": str(det_q(J, d, q))}
    return "out_of_scope", (["DOMAIN_ADMISSIBLE_MODE"] if band(J, d) else ["DIFFUSION_RATIO"]), {
        "continuum_band": band(J, d), "n_modes_checked": NMAX, "first_mode_q": str(modes(r, bc)[0])}

def key_for(J, d, r, bc):
    if bc is not None:
        return decide(J, d, r, "periodic" if bc == "periodic" else "neumann")   # dirichlet shares the Neumann mode set
    vn, cn, wn = decide(J, d, r, "neumann"); vp, cp, wp = decide(J, d, r, "periodic")
    if vn != vp: return "underdetermined", ["BC_UNSTATED"], {"neumann": vn, "periodic": vp}
    return vn, cn, wn

def repairs(J, d, bc):
    if not stable(J) or not band(J, d): return {}
    grid = [str(F(k, 2)) for k in range(1, 61) if unstable(J, d, F(k, 2), "periodic" if bc == "periodic" else "neumann")]
    return {"knob": "domain_length_over_pi", "valid_grid": grid}

def rand_J(rng):
    while True:
        J = tuple(F(rng.randint(-8, 8), rng.choice([2, 4])) for _ in range(4))
        if J[0] != 0 or J[3] != 0: return J

def render(rng, J, d, r, bc, tset):
    a, b, c, e = J
    if tset == "A":
        kin = rng.choice([f"Linearising about the uniform steady state gives the Jacobian J = [[{ftxt(a)}, {ftxt(b)}], [{ftxt(c)}, {ftxt(e)}]]",
                          f"Near its uniform steady state the kinetics are u' = {ftxt(a)}u {signed(b)}v, v' = {ftxt(c)}u {signed(e)}v",
                          f"The reaction Jacobian at the homogeneous state has rows ({ftxt(a)}, {ftxt(b)}) and ({ftxt(c)}, {ftxt(e)})"])
        dif = f"Species u diffuses with D_u = 1 and species v with D_v = {ftxt(d)}."
        dom = rng.choice([f"The domain is a one-dimensional interval of length {ftxt(r)}*pi", f"The strip has length L = {ftxt(r)}π"])
        bct = {"neumann": rng.choice(["with no-flux (Neumann) ends", "with reflecting boundaries"]),
               "dirichlet": "with the perturbation held at zero at both ends (Dirichlet)",
               "periodic": rng.choice(["with periodic boundaries (a ring)", "wrapped into a ring"]), None: ""}[bc]
    else:
        kin = rng.choice([f"Writing the reaction part as f_u = {ftxt(a)}u {signed(b)}v and g = {ftxt(c)}u {signed(e)}v around the base state",
                          f"Self-feedback of u is {ftxt(a)}, cross-effect of v on u is {ftxt(b)}, effect of u on v is {ftxt(c)}, self-feedback of v is {ftxt(e)}"])
        dif = rng.choice([f"The second species spreads {ftxt(d)} times faster than the first (unit diffusivity for the first).",
                          f"With the inhibitor's diffusivity set to {ftxt(d)} relative to the activator's 1."])
        dom = rng.choice([f"The tissue is a line segment whose length is {ftxt(r)} times pi", f"Take the domain length to be pi x {ftxt(r)}"])
        bct = {"neumann": rng.choice(["with sealed ends", "with closed (zero-flux) boundaries"]),
               "dirichlet": "with both ends clamped to the base state",
               "periodic": rng.choice(["and its two ends are identified (periodic)", "closed into a loop"]), None: ""}[bc]
    lure = rng.choice(["The requester states that the textbook diffusion-driven-instability inequality holds for these numbers.",
                       "The requester notes that D_v f_u + D_u g_v > 2 sqrt(D_u D_v det J) is satisfied, so a Turing pattern is expected."])
    ask = "Does the uniform state have an admissible, linearly growing diffusion-driven mode on this domain?"
    return " ".join(x for x in [kin + ".", dif, dom + (" " + bct if bct else "") + ".", lure, ask] if x)

TARGETS = ["applies"] * 4 + ["dom"] * 2 + ["ratio"] + ["unstable"] + ["undet"] * 2

def make(rng, n, start_id=1):
    pools = {"band": [], "noband": [], "unstable": []}
    while min(len(v) for v in pools.values()) < 100:
        J = rand_J(rng); d = F(rng.choice([4, 6, 8, 10, 15, 20, 30]))
        k = "unstable" if not stable(J) else ("band" if band(J, d) else "noband")
        if len(pools[k]) < 100: pools[k].append((J, d))
    RS = [F(x, y) for x in (1, 2, 3, 4, 5, 6, 8, 10, 12, 16) for y in (1, 2)]
    out, seen = [], set()
    while len(out) < n:
        t = TARGETS[len(out) % len(TARGETS)]
        for _ in range(800):
            J, d = rng.choice(pools["band" if t in ("applies", "dom", "undet") else "noband" if t == "ratio" else "unstable"])
            r = rng.choice(RS)
            bc = None if t == "undet" else rng.choice(["neumann", "neumann", "periodic", "dirichlet"])
            v, c, w = key_for(J, d, r, bc)
            ok = {"applies": v == "applies", "dom": v == "out_of_scope" and c == ["DOMAIN_ADMISSIBLE_MODE"],
                  "ratio": v == "out_of_scope" and c == ["DIFFUSION_RATIO"], "unstable": c == ["WELLMIXED_STABLE"],
                  "undet": v == "underdetermined"}[t]
            if ok and (J, d, r, bc) not in seen: break
        else: raise RuntimeError(t)
        seen.add((J, d, r, bc)); tset = "A" if len(out) % 2 == 0 else "B"
        rep = repairs(J, d, bc) if v == "out_of_scope" else {}
        out.append(item(f"ts-{start_id+len(out):04d}", FAMILY, "formal", render(rng, J, d, r, bc, tset),
                        {"J": [str(x) for x in J], "Dv": str(d), "r_over_pi": str(r), "bc": bc}, v, c, w, rep, tset, t))
    return out
