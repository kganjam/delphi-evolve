"""Family: turing_2d_rectangle (v1.1 replacement for the dropped rayleigh_plateau family). Same linear-instability question as turing_finite_domain
on a rectangle with sides a*pi, b*pi. Neumann modes q=(m/a)^2+(n/b)^2 (m,n>=0 not both 0); periodic torus q=(2m/a)^2+(2n/b)^2. Exact Fractions.
Scope content: a domain whose 1-D analysis along the longest side says 'no admissible unstable mode' can still be unstable through a mode in the second
direction (or the converse for the shorter side), so reducing a rectangle to one dimension is a scope violation (condition DIMENSIONALITY)."""
from fractions import Fraction as F
from common import ftxt, signed, item, exclude
import fam_turing as T
FAMILY = "turing_2d_rectangle"
M = 60

def modes2d(a, b, bc):
    mult = 2 if bc == "periodic" else 1
    return sorted({(F(mult * m) / a) ** 2 + (F(mult * n) / b) ** 2 for m in range(0, M) for n in range(0, M) if (m, n) != (0, 0)})

def unstable(J, d, a, b, bc):
    return [q for q in modes2d(a, b, bc) if T.det_q(J, d, q) < 0]

def one_d_longest(J, d, a, b, bc):
    L = max(a, b); return bool(T.unstable(J, d, L, "periodic" if bc == "periodic" else "neumann"))

def key_for(J, d, a, b, bc):
    if not T.stable(J): return "out_of_scope", ["WELLMIXED_STABLE"], {"stable": False}
    def one(bcx):
        um = unstable(J, d, a, b, bcx); return bool(um), um
    if bc is None:
        (x, _), (y, _) = one("neumann"), one("periodic")
        if x != y: return "underdetermined", ["BC_UNSTATED"], {"neumann": x, "periodic": y}
        bc = "neumann"
    u, um = one(bc)
    if u: return "applies", [], {"first_unstable_q": str(um[0]), "det": str(T.det_q(J, d, um[0])), "bc": bc}
    return "out_of_scope", (["DOMAIN_ADMISSIBLE_MODE"] if T.band(J, d) else ["DIFFUSION_RATIO"]), {"bc": bc, "continuum_band": T.band(J, d), "smallest_q": str(modes2d(a, b, bc)[0])}

def render(rng, J, d, a, b, bc, tset):
    x, y, z, w = J
    bct = {"neumann": rng.choice(["with no-flux (Neumann) edges", "with reflecting boundaries all round"]), "periodic": "with periodic boundaries (a torus)", None: ""}[bc]
    if tset == "A":
        s = (f"Linearising about the uniform steady state gives the Jacobian J = [[{ftxt(x)}, {ftxt(y)}], [{ftxt(z)}, {ftxt(w)}]]. Species u diffuses with D_u = 1 and species v with D_v = {ftxt(d)}. "
             f"The domain is a rectangle with sides {ftxt(a)}*pi and {ftxt(b)}*pi {bct}. The requester notes that D_v f_u + D_u g_v > 2 sqrt(D_u D_v det J) is satisfied. Can this system form a Turing pattern from small perturbations?")
    else:
        s = (f"Writing the reaction part as f_u = {ftxt(x)}u {signed(y)}v and g = {ftxt(z)}u {signed(w)}v around the base state, with the second species {ftxt(d)} times as diffusive as the first, "
             f"on a flat rectangular tissue of size pi x {ftxt(a)} by pi x {ftxt(b)} {bct}. The requester states the textbook diffusion-driven-instability inequality holds. Does that give the right answer for this domain?")
    return s.replace("  ", " ")

def make(rng, n, start_id):
    pool = {"band": [], "noband": [], "unstable": []}
    while min(len(v) for v in pool.values()) < 60:
        J = T.rand_J(rng); d = F(rng.choice([4, 6, 8, 10, 15, 20, 30]))
        k = "unstable" if not T.stable(J) else ("band" if T.band(J, d) else "noband")
        if len(pool[k]) < 60: pool[k].append((J, d))
    RS = [F(x, y) for x in (1, 2, 3, 4, 6, 8) for y in (1, 2)]
    want = ["applies"] * 4 + ["dom"] * 3 + ["dim"] * 2 + ["ratio"] + ["unstable"] + ["undet"] * 2
    out, seen = [], set()
    while len(out) < n:
        t = want[len(out) % len(want)]
        for _ in range(3000):
            J, d = rng.choice(pool["noband" if t == "ratio" else "unstable" if t == "unstable" else "band"]); a = rng.choice(RS); b = rng.choice(RS)
            bc = None if t == "undet" else rng.choice(["neumann", "neumann", "periodic"])
            v, c, w = key_for(J, d, a, b, bc)
            ok = {"applies": v == "applies", "dom": v == "out_of_scope" and c == ["DOMAIN_ADMISSIBLE_MODE"], "ratio": c == ["DIFFUSION_RATIO"], "unstable": c == ["WELLMIXED_STABLE"],
                  "undet": v == "underdetermined", "dim": v == "applies" and not one_d_longest(J, d, a, b, bc or "neumann")}[t]
            if ok and (J, d, a, b, bc) not in seen: break
        else: raise RuntimeError("turing2d cannot realise " + t)
        seen.add((J, d, a, b, bc)); tset = "A" if len(out) % 2 == 0 else "B"
        viol = list(c)
        if t == "dim": w = dict(w, trap="reducing to 1-D along the longest side would wrongly say stable")
        out.append(item(f"t2-{start_id+len(out):04d}", FAMILY, "formal", render(rng, J, d, a, b, bc, tset),
                        {"J": [str(x) for x in J], "Dv": str(d), "a_over_pi": str(a), "b_over_pi": str(b), "bc": bc}, v, c, w, {}, tset, t, violated=viol))
    return out
