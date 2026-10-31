"""Family 6/8: hamilton_rule_form. Claim (hamilton-rule): allele spreads iff r*b - c > 0 with r,b,c regression coefficients (Queller).
Exact haploid model: fitness w(g,g') = 1 - c g + b g' + d g g' (synergy d), partner has same type with prob r+(1-r)p for focal=1, (1-r)p for focal=0.
Delta p ~ p(1-p)(w1-w0)/wbar, w1-w0 = -c + b(r+(1-r)p)... - b(1-r)p + d(r+(1-r)p) = r b - c + d(r+(1-r)p).
Request gives the ADDITIVE b,c; Hamilton verdict sign(rb-c) vs exact sign. Frequency unstated + synergy present => may be underdetermined."""
from fractions import Fraction as F
from common import item, exclude, ftxt
FAMILY = "hamilton_rule_form"

def exact_sign(b, c, r, d, p):
    return (r * b - c) + d * (r + (1 - r) * p)

def decide(b, c, r, d, p):
    ps = [p] if p is not None else [F(1, 10), F(9, 10)]
    verdicts = []
    for pp in ps:
        ex = exact_sign(b, c, r, d, pp); ham = r * b - c
        if ex == 0 or ham == 0: return None
        verdicts.append((ex > 0) == (ham > 0))
    if len(set(verdicts)) > 1: return "underdetermined", ["HAMILTON_NONADDITIVE"], {"agree_at_p": [str(x) for x in ps], "agree": verdicts}
    if verdicts[0]: return "applies", [], {"rb_minus_c": str(r * b - c), "exact": str(exact_sign(b, c, r, d, ps[0]))}
    return "out_of_scope", ["HAMILTON_NONADDITIVE"], {"rb_minus_c": str(r * b - c), "exact_selection_sign_term": str(exact_sign(b, c, r, d, ps[0])), "synergy_d": str(d)}

def render(rng, b, c, r, d, p, tset):
    syn = "" if d == 0 else (f" If both partners carry the allele there is an extra synergy of {ftxt(d)} in fitness." if tset == "A" else f" Carrying pairs also get an interaction bonus of {ftxt(d)}.")
    pt = "" if p is None else (f" The allele currently has frequency {ftxt(p)}." if tset == "A" else f" Its present frequency is {ftxt(p)}.")
    if tset == "A":
        return (f"An allele makes its carrier pay a fitness cost c = {ftxt(c)} to give its partner a benefit b = {ftxt(b)}; relatedness between partners is r = {ftxt(r)}.{syn}{pt} "
                f"Hamilton's rule says it spreads iff r*b > c. Will it spread?")
    return (f"A helping allele costs the helper {ftxt(c)} and gives the recipient {ftxt(b)}; the coefficient of relatedness is {ftxt(r)}.{syn}{pt} "
            f"Using rb - c > 0, should I expect the allele to increase in frequency?")

def make(rng, n, start_id):
    out, seen = [], set()
    want = ["applies"] * 6 + ["oos"] * 5 + ["undet"] * 3 + ["applies"] * 2
    while len(out) < n:
        t = want[len(out) % len(want)]
        b = F(rng.randint(1, 12), 2); c = F(rng.randint(1, 10), 2); r = F(rng.randint(1, 8), 8)
        d = F(0) if (t == "applies" and rng.random() < 0.6) else F(rng.choice([-6, -4, -3, 3, 4, 6]), 2)
        p = None if t == "undet" else F(rng.choice([1, 2, 5, 8]), 10)
        res = decide(b, c, r, d, p)
        if res is None: exclude(FAMILY, "tie at zero", {"b": b, "c": c, "r": r, "d": d, "p": p}); continue
        v, cc, w = res
        if {"applies": v == "applies", "oos": v == "out_of_scope", "undet": v == "underdetermined"}[t] is False or (b, c, r, d, p) in seen: continue
        seen.add((b, c, r, d, p)); tset = "A" if len(out) % 2 == 0 else "B"
        rep = {"knob": "use_regression_b_c", "valid_grid": ["partial-regression coefficients b,c (Queller form)"]} if v == "out_of_scope" else {}
        out.append(item(f"hm-{start_id+len(out):04d}", FAMILY, "formal", render(rng, b, c, r, d, p, tset),
                        {"b": str(b), "c": str(c), "r": str(r), "d": str(d), "p": None if p is None else str(p)}, v, cc, w, rep, tset, t))
    return out
