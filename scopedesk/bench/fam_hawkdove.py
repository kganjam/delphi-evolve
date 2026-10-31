"""Family 5/8: hawk_dove_ess. Claim (maynardsmith-hawk-dove): payoffs E(H,H)=(V-C)/2, E(H,D)=V, E(D,H)=0, E(D,D)=V/2;
for C>V the unique ESS plays Hawk with probability V/C. Exact Fractions. C<V: Hawk is the pure ESS (p*=V/C>1 is not a probability)
-> out_of_scope(PAYOFF_REGIME). C==V excluded (degenerate boundary). C unstated -> underdetermined."""
from fractions import Fraction as F
from common import item, exclude, ftxt
FAMILY = "hawk_dove_ess"

def E(V, C, p, q):
    return p*q*(V-C)/2 + p*(1-q)*V + (1-p)*(1-q)*V/2

def decide(V, C):
    if C is None: return "underdetermined", ["PAYOFF_REGIME"], {"missing": "C"}
    if C > V:
        ps = V / C
        # exact ESS checks: E(p*,q)-E(q,q) = (C/2)(p*-q)^2 > 0 for q != p*
        chk = [E(V, C, ps, q) - E(V, C, q, q) == (C / 2) * (ps - q) ** 2 for q in (F(0), F(1), F(1, 3), F(2, 3))]
        assert all(chk)
        return "applies", [], {"p_star": str(ps), "ess_identity_verified": True}
    return "out_of_scope", ["PAYOFF_REGIME"], {"claim_p_star": str(V / C), "exceeds_one": V / C > 1,
                                               "pure_hawk_ess": E(V, C, F(1), F(1)) > E(V, C, F(0), F(1)) or (E(V, C, F(1), F(1)) == E(V, C, F(0), F(1)) and E(V, C, F(1), F(0)) > E(V, C, F(0), F(0)))}

def render(rng, V, C, tset):
    if tset == "A":
        if C is None: return f"In the Hawk-Dove game the prize is V = {ftxt(V)}. Maynard Smith's result says the ESS plays Hawk with probability V/C. What proportion of Hawks should I expect?"
        return f"In the Hawk-Dove game the prize is V = {ftxt(V)} and the cost of an escalated fight is C = {ftxt(C)}. Maynard Smith says the ESS plays Hawk with probability V/C. Is that the stable strategy here?"
    if C is None: return f"Two animals contest a resource worth {ftxt(V)}. Using p* = V/C for the evolutionarily stable Hawk frequency, what is the predicted mix?"
    return f"Two animals contest a resource worth {ftxt(V)}; losing an escalated fight costs {ftxt(C)}. Is the evolutionarily stable fraction of Hawks V/C?"

def make(rng, n, start_id):
    out, seen = [], set()
    want = ["applies"] * 6 + ["oos"] * 5 + ["undet"] * 3 + ["applies"] * 2
    while len(out) < n:
        t = want[len(out) % len(want)]
        V = F(rng.randint(1, 12), rng.choice([1, 2])); C = F(rng.randint(1, 24), rng.choice([1, 2]))
        if t == "undet": C = None
        elif t == "applies" and C <= V: continue
        elif t == "oos" and C >= V: continue
        if C == V: exclude(FAMILY, "C == V degenerate boundary", {"V": V, "C": C}); continue
        if (V, C) in seen: continue
        seen.add((V, C)); v, c, w = decide(V, C); tset = "A" if len(out) % 2 == 0 else "B"
        rep = {"knob": "payoff_regime", "valid_grid": ["C>V: use mixed ESS V/C"]} if v == "out_of_scope" else {}
        out.append(item(f"hd-{start_id+len(out):04d}", FAMILY, "formal", render(rng, V, C, tset), {"V": str(V), "C": None if C is None else str(C)}, v, c, w, rep, tset, t))
    return out
