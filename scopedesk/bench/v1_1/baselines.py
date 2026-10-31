"""Deterministic baselines for the Scope Desk bench (critic).
B0: scope-rule gate. Regex-extracts parameters from request_text using the TEMPLATE-A phrasings only (author saw them), then applies the
family's exact decision rule (same arithmetic as the key's family module). Anything it cannot parse -> 'underdetermined' (safe refusal).
R : one-pass retrieval - looks up the textbook claim for the family and answers 'applies' (no scope reasoning).
FMT: format-only classifier - predicts the verdict from request length / digit count / position, trained on dev families, tested on held-out.
None of these see the key or the hidden field."""
import json, os, re, sys
from fractions import Fraction as F
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fam_turing, fam_turing2d, fam_kimura, fam_hawkdove, fam_hamilton, fam_kpp, fam_greenhill, fam_wavelength

NUM = r"(-?\d+(?:/\d+)?)"
def fr(s): return F(s)

def b0_turing(t):
    m = re.search(r"J = \[\[%s, %s\], \[%s, %s\]\]" % ((NUM,) * 4), t) or re.search(r"u' = %s\s*u\s*([+-]) %s\s*v, v' = %s\s*u\s*([+-]) %s\s*v" % (NUM, NUM, NUM, NUM), t)
    if m and "u' =" in t:
        a, sb, b, c, se, e = m.groups(); J = (fr(a), fr(b) * (1 if sb == "+" else -1), fr(c), fr(e) * (1 if se == "+" else -1))
    elif m: J = tuple(fr(x) for x in m.groups())
    else:
        m = re.search(r"rows \(%s, %s\) and \(%s, %s\)" % ((NUM,) * 4), t)
        if not m: return "underdetermined"
        J = tuple(fr(x) for x in m.groups())
    d = re.search(r"D_v = %s" % NUM, t); r = re.search(r"%s\*pi|L = %sπ" % (NUM, NUM), t)
    if not (d and r): return "underdetermined"
    rr = fr([g for g in r.groups() if g][0])
    bc = "periodic" if re.search(r"periodic|\bring\b", t) else "neumann" if re.search(r"Neumann|reflecting", t) else "dirichlet" if re.search(r"Dirichlet|held at zero", t) else None
    return fam_turing.key_for(J, fr(d.group(1)), rr, bc)[0]

def b0_wavelength(t):
    m = re.search(r"Jacobian \[\[%s, %s\], \[%s, %s\]\].*?D_v = %s.*?length %s\*pi" % ((NUM,) * 6), t)
    if not m: return "underdetermined"
    a, b, c, e, d, r = [fr(x) for x in m.groups()]
    res = fam_wavelength.decide((a, b, c, e), d, r)
    return "underdetermined" if res is None else res[0]

def b0_turing2d(t):
    m = re.search(r"J = \[\[%s, %s\], \[%s, %s\]\]" % ((NUM,) * 4), t)
    if not m: return "underdetermined"
    J = tuple(fr(x) for x in m.groups()); d = re.search(r"D_v = %s" % NUM, t); s = re.search(r"sides %s\*pi and %s\*pi" % (NUM, NUM), t)
    if not (d and s): return "underdetermined"
    bc = "periodic" if re.search(r"periodic|torus", t) else "neumann" if re.search(r"Neumann|reflecting", t) else None
    return fam_turing2d.key_for(J, fr(d.group(1)), fr(s.group(1)), fr(s.group(2)), bc)[0]

def b0_kimura(t):
    m = re.search(r"s = %s\)? (?:appears|arises).*?N = (\d+)|s = %s\) appears.*?N = (\d+)" % (NUM, NUM), t) or re.search(r"s = %s .*?N = (\d+)" % NUM, t)
    mm = re.search(r"coefficient s = %s.*?N = (\d+)" % NUM, t)
    if not mm: return "underdetermined"
    s, N = fr(mm.group(1)), int(mm.group(2)); kind = "neutral" if "neutral value 1/N" in t else "diffusion" if "diffusion formula" in t else None
    return "underdetermined" if kind is None else fam_kimura.decide(N, float(s), kind)[0]

def b0_hawkdove(t):
    V = re.search(r"V = %s" % NUM, t); C = re.search(r"C = %s" % NUM, t)
    if not V: return "underdetermined"
    return fam_hawkdove.decide(fr(V.group(1)), fr(C.group(1)) if C else None)[0]

def b0_hamilton(t):
    m = re.search(r"cost c = %s .*?benefit b = %s; relatedness between partners is r = %s\.(.*?)Hamilton" % (NUM, NUM, NUM), t)
    if not m: return "underdetermined"
    c, b, r = fr(m.group(1)), fr(m.group(2)), fr(m.group(3)); rest = m.group(4)
    d = re.search(r"synergy of %s" % NUM, rest); p = re.search(r"frequency %s" % NUM, rest)
    res = fam_hamilton.decide(b, c, r, fr(d.group(1)) if d else F(0), fr(p.group(1)) if p else None)
    return "underdetermined" if res is None else res[0]

def b0_kpp(t):
    if "some saturating" in t: return "underdetermined"
    if "logistic" in t: kind, par = "logistic", None
    else:
        m = re.search(r"s u\(1-u\)\(1\+%su\)" % NUM, t); a = re.search(r"s u\(1-u\)\(u-%s\)" % NUM, t)
        if m: kind, par = "cubic_pos", fr(m.group(1))
        elif a: kind, par = "allee", fr(a.group(1))
        else: return "underdetermined"
    return fam_kpp.decide(kind, par)[0]

def b0_greenhill(t):
    D = re.search(r"base diameter ([\d.]+) m, height ([\d.]+) m", t)
    if not D: return "underdetermined"
    E = re.search(r"E = ([\d.]+) GPa", t); rho = re.search(r"density ([\d.]+) kg", t)
    if not (E and rho): return "underdetermined"
    tp = re.search(r"top diameter is (\d+)/(\d+)", t); tt = float(F(int(tp.group(1)), int(tp.group(2)))) if tp else 1.0
    return fam_greenhill.decide(float(E.group(1)) * 1e9, float(rho.group(1)), float(D.group(1)), float(D.group(2)), tt)[0]

B0 = {"turing_finite_domain": b0_turing, "wavelength_formula_licence": b0_wavelength, "turing_2d_rectangle": b0_turing2d, "kimura_regime": b0_kimura,
      "hawk_dove_ess": b0_hawkdove, "hamilton_rule_form": b0_hamilton, "fisher_kpp_speed": b0_kpp, "greenhill_buckling": b0_greenhill}

def predict_B0(inst):
    try: return B0[inst["family"]](inst["request_text"].split(" Conventions:")[0])      # boilerplate conventions block is not parsed
    except Exception: return "underdetermined"

def predict_R(inst):
    return "applies"
