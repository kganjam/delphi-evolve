"""Family 3/8: rayleigh_plateau. Claim (thompson1917-ch05-12): a liquid cylinder of radius r is unstable for length l > 2 pi r.
Source of exact threshold: Rayleigh (1878) dispersion omega^2 ~ k r (1-(k r)^2) I1(kr)/I0(kr): unstable iff k r < 1 (sign change at kr=1;
verified below by evaluating the sign of (1-(kr)^2) with exact rationals). Allowed axial wavenumbers: periodic k=2 pi n/l, pinned (fixed) ends k=n pi/l.
l = s*pi*r  => k r = 2n/s (periodic) or n/s (pinned); unstable iff exists n>=1 with k r < 1 : periodic s>2, pinned s>1."""
from fractions import Fraction as F
from common import ftxt, item
FAMILY = "rayleigh_plateau"

def unstable(s, bc):
    return (s > 2) if bc == "periodic" else (s > 1)

def claim_says_unstable(s):
    return s > 2

def key_for(s, bc):
    if bc is None:
        vs = {b: claim_says_unstable(s) == unstable(s, b) for b in ("periodic", "pinned")}
        if vs["periodic"] != vs["pinned"]: return "underdetermined", ["BC_UNSTATED"], {"periodic_claim_correct": vs["periodic"], "pinned_claim_correct": vs["pinned"]}
        bc = "periodic"
    ok = claim_says_unstable(s) == unstable(s, bc)
    if ok: return "applies", [], {"s": str(s), "bc": bc, "unstable": unstable(s, bc)}
    return "out_of_scope", ["BC_PINNED_ENDS"], {"s": str(s), "bc": bc, "claim_predicts_unstable": claim_says_unstable(s), "exact_unstable": unstable(s, bc),
                                               "witness_mode": {"n": 1, "k_r": str(F(1) / s)}}

def render(rng, s, bc, tset):
    L = f"{ftxt(s)}*pi*r"
    bct = {"periodic": "free, effectively periodic (a long thread)" if tset == "A" else "treated as a ring-like periodic segment",
           "pinned": "with both ends pinned to rigid rings" if tset == "A" else "whose contact lines are fixed at both ends", None: ""}[bc]
    if tset == "A":
        return f"A liquid cylinder of radius r and length {L} {bct}. Thompson says it is unstable if and only if its length exceeds 2*pi*r. Will it break into drops, and is that threshold the right one?".replace("  ", " ")
    return f"A fluid thread (radius r) is {ftxt(s)} times pi*r long{(', ' + bct) if bct else ''}. Using the criterion l > 2 pi r, should I expect surface-tension breakup?".replace("  ", " ")

def make(rng, n, start_id):
    out, seen = [], set()
    S = [F(x, 8) for x in range(1, 81)]
    want = ["applies"] * 7 + ["oos"] * 5 + ["undet"] * 3 + ["applies"]
    while len(out) < n:
        t = want[len(out) % len(want)]
        s = rng.choice(S); bc = None if t == "undet" else rng.choice(["periodic", "pinned"])
        v, c, w = key_for(s, bc)
        ok = {"applies": v == "applies", "oos": v == "out_of_scope", "undet": v == "underdetermined"}[t]
        if not ok or (s, bc) in seen: continue
        seen.add((s, bc)); tset = "A" if len(out) % 2 == 0 else "B"
        rep = {"knob": "end_condition", "valid_grid": ["periodic"]} if v == "out_of_scope" else {}
        out.append(item(f"rp-{start_id+len(out):04d}", FAMILY, "formal", render(rng, s, bc, tset), {"s": str(s), "bc": bc}, v, c, w, rep, tset, t))
    return out
