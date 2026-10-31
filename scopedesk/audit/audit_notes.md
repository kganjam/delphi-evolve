# AT3 audit notes (independent; scripts audit_turing.py, audit_kimura.py, audit_rest.py, audit_pde.py, audit_merge.py)

All derivations done in exact Fractions (Turing, Rayleigh, Hamilton, Hawk-Dove, KPP rules), mpmath 40-50 digits (Kimura exact chain, wavelength fastest mode). Greenhill constant checked: 9/4 * j^2 with j=1.86635 (first zero of J_{-1/3}) = 7.83735, and uniform-column H_cr = 0.788 (E/(rho g))^(1/3) D^(2/3) agrees.

## Operational tests used
- Turing: Du=1, q_n=(n/r)^2 (Neumann n>=0, Dirichlet n>=1), periodic q=(2n/r)^2 n>=0; unstable iff Dv q^2-(Dv a+d) q+det J<0. verdict applies iff homogeneous state stable (tr<0,det>0) AND at least one admissible mode unstable; else out_of_scope; bc unstated -> underdetermined if the three BC completions disagree (here Neumann==Dirichlet, periodic is a sparser mode set). Neumann and Dirichlet always agree (n=0 mode is stable).
- Wavelength: Neumann, modes wavelength 2*pi*r/n (n>=1). Fastest-growing admissible = argmax_n Re lambda_max(J - q_n D). Licensed (applies) iff stable, >=1 unstable admissible mode, and |lambda_c - lambda_fastest|/lambda_fastest <= 10%. No separate "domain large" test beyond this (so small domains with a single unstable mode, e.g. wl-0003, wl-0004, count as applies if the single mode's wavelength is within 10%; if the key adds an explicit L/lambda requirement these two could differ). Three items (wl-0014/15/16) have no admissible unstable mode at all (domain quantisation gap) -> out_of_scope. Borderline band = error in [7%,13%].
- Kimura: exact haploid WF chain, carrier fitness 1+s, p_i=i(1+s)/(i(1+s)+N-i), Binomial(N,p_i) offspring, fixation from i=1. Applies iff |approx-exact|/exact <= 10%. Diffusion formula as written = (1-e^{-2s})/(1-e^{-2Ns}). Borderline band: rel err in [7%,13%].
- Rayleigh-Plateau: unstable iff exists admissible k with k r<1; periodic k=2 pi n/l -> threshold s>2 (matches cited); pinned k=n pi/l -> threshold s>1 (cited threshold wrong). Verdict by OUTCOME agreement of cited criterion with the exact answer.
- Hawk-Dove: applies iff C>V; C<V -> Hawk is a pure ESS (V/C>1 not a probability); C unstated -> underdetermined; no C==V items.
- Greenhill: uniform => applies (buckling yes/no recorded in rule string); taper t!=1 => out_of_scope; uniform & rho missing => underdetermined.
- Hamilton: carrier advantage = r b - c + d (r+(1-r)p). d=0 -> applies; d!=0 with p given -> compare sign with r b - c > 0 (outcome agreement); p unstated -> underdetermined iff advantage over p in [0,1] changes sign, else outcome agreement.
- KPP: logistic applies; allee out_of_scope (pushed speed sqrt(sD/2)(1-2a)); cubic_pos f=u(1-u)(1+alpha u): derived front u=1/(1+e^{kz}), k^2=s alpha/(2D), c=(2+alpha)/sqrt(2 alpha) sqrt(sD), selected only if k>sqrt(s/D) i.e. alpha>2; so alpha<=2 pulled (2 sqrt(sD) holds), alpha>2 out_of_scope. PDE check (audit_pde.py, D=s=1, T=120; Bramson lag ~ -3/(2t)): alpha=0:1.95, 5/3:1.955, 2:1.96, 4:2.078 (theory 2.121), 10/3:2.027 (theory 2.066) -> consistent. Unspecified kind -> underdetermined.

## Disagreements with the requests' own premises
- ts-0007, ts-0017: requester claims the DDI inequality holds but it is false (Dv a + d <= 0 or discriminant fails) -> out_of_scope.
- ts-0008, ts-0018: det J = 0 (homogeneous state only marginal, not stable) and the stated inequality is false; ts-0008 would have unstable admissible modes but the stable-state precondition is violated -> out_of_scope (medium).
- Many "inequality holds" items (ts-0005, 0006, 0015, 0016) are true in the infinite domain but no admissible mode exists in the finite domain/BC -> out_of_scope (the intended finite-domain point).
- Taper items: Greenhill's quoted formula is for uniform columns; tapered items would give H/H_cr(uniform) of 0.80 to 1.6, i.e. the uniform formula would produce misleading buckle predictions.

## Borderline / low-confidence / ambiguous items
- km-0011 (N=8, s=1/50 neutral): rel err 12.6%, borderline (verdict out_of_scope, low).
- wl-0009: rel err 8.5%, borderline (applies, low).
- km-0006, km-0014 (diffusion, errs 6.1%, 6.0%) just outside the 3-pt borderline band but close.
- gh-0004 and gh-0012: rho unstated -> underdetermined by the task rule, but over any plausible density (300-2500 kg/m^3) the answer is the same (gh-0004: no buckling, H=11.4 vs H_cr 17-34; gh-0012: buckles, H=181.6 vs H_cr 56-114). Only unconstrained rho makes it underdetermined. gh-0016 genuinely crosses (H=127 vs 88-178). Confidence low/low/medium.
- gh-0008: tapered AND rho missing; I chose out_of_scope (taper decides irrespective of rho). A key following "rho missing -> underdetermined" first would differ.
- Semantics ambiguity (outcome-based vs scope-based "applies"): (a) Rayleigh pinned with s>2 (rp-0001, 0002, 0003, 0006): cited criterion predicts instability and the thread is unstable, but the threshold is not the true one for pinned ends; I output applies (medium). A scope-based key would say out_of_scope. (b) Hamilton non-additive with p given and sign coinciding (hm-0005, hm-0015): applies (medium) under outcome agreement; scope-based would be out_of_scope. (c) hm-0008 is sensitive to the convention for d (if the bonus is split between partners, advantage becomes slightly negative and the verdict flips to applies); confidence medium.
- KPP kp-0007 (alpha=2 exactly) is the critical case: speed equals 2 sqrt(sD) exactly (pulled/pushed transition), applies (medium); kp-0002/0012 (alpha 5/3, 4/3) fail the sufficient KPP bound f<=f'(0)u yet the front is still pulled, applies.
- Request text vs structured: no conflicts found beyond the premise disagreements above; wording about boundary conditions was always consistent with structured bc.
