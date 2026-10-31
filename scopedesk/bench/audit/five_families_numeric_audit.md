# Numeric audit of the five oracle-less families (critic, 2026-10-31 ~09:43 PDT)

Script `audit_five_families_numeric.py`, output `five_families_numeric_audit.json`. It imports none of the generator modules (`fam_*.py`) and re-derives each item's verdict from the
structured parameters with a DIFFERENT method:

| family | n | independent method | agree with frozen key |
|---|---|---|---|
| kimura_regime | 16 | exact rational (Fraction) Gauss solve of the Wright-Fisher chain + 200k-replicate seeded Monte Carlo of the same chain | 16/16 (MC on the same side of the 10% line for all 16) |
| hawk_dove_ess | 16 | replicator ODE (RK4) from three starting frequencies; ESS = attractor | 16/16 |
| hamilton_rule_form | 16 | explicit pair-type enumeration and one-generation recursion for the sign of delta-p; missing frequency swept over p=0.01..0.99 | 16/16 |
| fisher_kpp_speed | 16 | finite-difference PDE front simulation (u_t=u_xx+f(u), D=s=1 after rescaling, dx=0.1, T=160): pulled fronts 0.992-0.996 of 2*sqrt(sD), cubic a=10/3 gives 1.031 (formula 1.033), a=4 gives 1.059 (1.061), Allee 0.071 and 0.141 (formula 0.071, 0.141) | 16/16 |
| greenhill_buckling | 13 | integro-differential buckling eigenproblem (not the generator's Rayleigh-Ritz); reproduces Greenhill 7.8373 (7.83732 at n=400) and the generator's Lambda=13.584 at t=0.4 | 12/13 under the declared-density reading; 13/13 if the missing property is unbounded (see below) |

**One disagreement, disclosed, key NOT changed.** Item `q9f4c0434` (legacy gh-0008: E=6 GPa, density unstated, taper 0.5, H=78.9 m) is labelled underdetermined by the key's blanket rule
"tapered column + a missing material property => underdetermined". Sweeping the density over the benchmark's own declared values {600, 800, 1000} gives the same verdict (applies) every time. The
formula and the exact analysis disagree only for densities in about [1371, 2111] kg/m^3, outside the declared range (denser than wood, within range for concrete-like materials). So the label is defensible only if
density is unbounded. This is the same item the director's AT3 subagent flagged. It is 1 of 127 items and the family's only underdetermined item.

**What this is.** A method-independent recomputation of arithmetic and numerics; same author as the generator; the declared conventions (what counts as "applies") are taken from the family docstrings,
so it does not audit the choice of convention, subcritical behaviour, or phrasing. Two bugs in the audit script were found and fixed on the way (a sign convention in the first Greenhill discretisation caught by the 7.8373 check; a step-count off-by-one and a too-short domain in the dimensional rescaling check, now 0.9875 of 2*sqrt(sD) at D=1.5, s=2.5, T=40). Not a replacement for a human or a different-family oracle review.
