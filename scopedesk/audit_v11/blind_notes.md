# Blind audit notes (no key consulted)
Scripts: blind_turing.py (ts, t2; exact rational h(q)<0 test over admissible modes), blind_km.py (exact WF absorbing chain, Fractions), blind_hm_hd.py, blind_gh.py (ODE (EI th')' + W th = 0, th'(0)=0, th(H)=0; kappa uniform=0.78828, r=1/2: 0.90991, r=2/5: 0.94690), blind_wl.py (argmax Re lambda over n, mpmath), blind_compile.py (assembles blind_verdicts.jsonl).

Ambiguous / non-high-confidence items
- t2-0011 (low): det J<0, base state unstable without diffusion; quoted inequality has sqrt of negative. Unstable admissible modes exist. out_of_scope if "diffusion-driven" is strict, applies if it just means growing mode.
- ts-0008 (medium): det J=0 exactly (marginal state), band 0<q<0.2167, Dirichlet n=1,2 unstable -> applies; strict "det>0" reading gives out_of_scope. ts-0018 same J, out_of_scope either way.
- ts-0009/0010/0019/0020, t2-0012/0013: BC not stated -> underdetermined by text rule; outcomes do differ across BCs (so this is robust).
- ts-0007, ts-0017, t2-0010: requester's "inequality holds" is actually false (D_v a11 + a22 < 0 or fails); out_of_scope.
- kp-0002, kp-0012 (alpha=5/3, 4/3), kp-0007 (alpha=2): non-KPP (f(u)/u > f'(0) somewhere) but still pulled, c=2 sqrt(sD) (exact front c=(2+a)/sqrt(2a) only valid a>=2). Applies; a KPP-inequality reader would say out_of_scope. kp-0007 is exactly the critical value.
- wl-0014/0015/0016: all modes decay; 'fastest-growing' read as least damped; out_of_scope under both readings (errors 13%, 12%, 11.8%; 10.6% if measured vs mode wavelength).
- wl-0010: near-tie n=9 vs n=8 (growth .2306 vs .2299); exact picks n=9 (out_of_scope); n=8 would give applies.
- gh tapered items (0002,0003,0005,0007,0010,0011,0013,0015): which diameter the 'uniform formula' uses is not stated (base diameter assumed); g not stated (9.81 assumed; insensitive).
- hm-0012/0013/0014: frequency not stated and covariance sign flips with p -> underdetermined.
- hd-0012/0013/0014: C not stated -> underdetermined. kp-0008: growth term unknown -> underdetermined. gh-0004/0008/0012/0016: density not stated -> underdetermined.
