# Scope Desk v1.1: arithmetic agrees; freeze remains on hold

Codex API, October 31, 2026, Seattle PDT. Reviewed critic commit `e7760307f4cad2040715279949a94ead8437735d`, key SHA256 `d3862d0b3397c8abc4eb3d1f9149ecd261f322055f8c60c1dddd851003b70b4e`. This is the requested follow-up to the v1 semantic audit. **Not blinded:** I read the key and generators before implementing the checks. It is not an agent benchmark score or a substitute for the separately requested blinded audit.

The v1 liquid-bridge correction and source receipt were already pushed in `19fae04`, in `CODEX-BENCHMARK-SEMANTICS.md` and `benchmark-semantic-audit.json`. No repeat of that completed work is needed. v1.1 correctly removes the uncertified family rather than quietly relabelling it. The new conventions address the main v1 input defects: linear rather than macroscopic patterning, wavelength and Kimura tolerances, Hamilton growth-rate payoffs and pairing kernel, conditional Allee invasion, and a declared Greenhill outcome-agreement target.

## Executed checks

`artifacts/integration/codex-api/audit_benchmark_v1_1.py` reads immutable git objects and imports no critic generator/verifier. Its receipt is `benchmark-v1-1-review.json` in the same directory.

| Check | Result and scope |
|---|---|
| Manifest | All 17 hashed source/data files match `KEY.sha256`. |
| Public request contract | All 136 public rows match their full-row projection; all contain the declared family conventions and verdict definition. This is byte/content checking, not an independent NLP extraction score. |
| Conditional numerical verdicts | 136/136 agree under the declared conventions and missing-input policy. No numerical label discrepancy found. |
| Exclusions | All 25 logged exclusion entries reproduce their stated arithmetic reason; these are entries, not necessarily unique instances. The stale v1 README's count of 27 does not describe this version. |
| Turing | Exact rational determinants, including the new 2-D mode sets. Enumeration uses a proved algebraic upper cutoff: for well-mixed-stable J, q >= max((Dv*a+e)/Dv,0) implies positive determinant. It does not rely on the generator's fixed mode cap. |
| Wavelength | Independent matrix eigenvalues on all potentially unstable admissible modes; compare the fastest growing wavelength against the declared 10% rule. |
| Kimura | Iteration of lower/upper absorbing-chain boundary values instead of the generator's linear solve. Numerical iteration gaps below 1e-12; these are floating-point convergence diagnostics, not rigorous interval arithmetic. |
| Greenhill | Independent shooting for `-(f^4 theta')' = Lambda F theta`, clamped-base/free-top conditions, with a node-free fundamental mode and two integration tolerances. Largest retained-item Lambda refinement change: 6.81e-10. Both the printed 0.788 constant and the more precise uniform eigenvalue give the same verdict on the specified retained cases. Missing mechanical values follow the declared policy. |
| Hamilton | Explicit four-state joint distribution and covariance using exact Fractions; no negative-reproductive-fitness interpretation. |
| Hawk–Dove | Exact payoff-difference root and slope, probability feasibility, and declared missing-cost handling. |
| KPP | Exact front-profile polynomial residuals for the explicit cubic/bistable solutions; the known minimal-speed selection theorem is not reproved. |

For the last distinction, [Crooks and Grinfeld (2020), p. 4](https://strathprints.strath.ac.uk/74892/7/Crooks-Grinfeld-EJQTDE-2020-Minimal-travelling-wave-speed-and-explicit-solutions.pdf) explicitly gives the Hadeler–Rothe cubic family and the minimal-speed switch at parameter 2. The paper also explains why existence of an explicit front alone does not establish its minimality. This supports the source correspondence; it does not turn our calculation into a new PDE theorem.

I read 30 request stems selected with `random.Random(20261031).sample(public_rows,30)` and inspected the ten smallest retained numerical threshold margins. No additional numerical label error emerged. I did not manufacture a wording-only reviewer accuracy after reading the answers. The actual independently executed metadata baseline below is more informative.

The first execution exposed an absorbing-state floating-point endpoint bug in my audit (a computed probability slightly above one); exact absorbing endpoints fixed it. The second completed calculations but failed JSON serialization of a NumPy scalar. The final execution exited 0. These are implementation failures, not benchmark findings. Every run used the required 128-task, 4-GiB, 600-second systemd scope and one BLAS thread.

## Required before freeze

1. **Remove answer-order information from agent-visible IDs.** Row order is shuffled, but numeric suffixes still encode the generator's fixed verdict schedule. With only that numeric suffix as a feature, a depth-3 decision tree trained on the declared 40 development items gets **58/96 held-out items**, versus **43/96** for the development-majority classifier. An unrestricted tree gets 57/96. These are diagnostic checks, not a preregistered superiority result. More directly, all 16 development Hawk–Dove labels occur in exactly the same ordinal order as all 16 held-out Hamilton labels. The existing n-gram audit does not test this channel. Give models opaque IDs assigned independently of labels, or omit IDs from the model-visible payload and map replies outside the model. Preserve old IDs in a private migration map. Freeze and inspect the actual prompt payload, not just a JSON export that a runner might transform.

2. **Complete the diagnosis field or narrow its advertised meaning.** `conventions.py` promises that violated conditions are recorded even when the answer agrees. `hm-0005` and `hm-0015` have nonzero interaction terms but empty `violated_conditions`. Their outcome labels may remain `applies`; the raw additive-payoff assumption still fails. Record `HAMILTON_NONADDITIVE` consistently, with the caveat that regression-form Hamilton is not invalidated by synergy itself. Audit analogous benign condition violations before scoring diagnosis correctness. An outcome-agreement verdict is not proof that all source assumptions hold.

3. **Resolve the evaluation grouping before runs.** The 1-D Turing, 2-D Turing and wavelength groups share the same Jacobian/mode mathematics; the split puts one in development and two in held-out. Eight benchmark groups are not eight independent scientific mechanisms. Report this as within-mechanism transfer, and prespecify a sensitivity analysis grouping these three together. Do not call a binomial item interval a family-clustered interval, or imply broad unseen-mechanism generalization from the existing split.

4. **Replace the inherited contradictory README and update the audit brief.** v1.1's README still contains the removed bridge threshold, old counts, outdated wavelength target and v1 commands. Its preamble says the diff overrides them, but a frozen benchmark should have one unambiguous current contract. The audit brief still asks the next reader to derive the rejected bridge rule. Keep these historical texts under v1, and make v1.1's instructions self-contained. State gravity (9.81 m/s²), the missing-input policy, and that a purported Turing inequality in the request is a claimant assertion to check, not an additional guaranteed premise.

Delphi record identity and version pins remain unwired in these benchmark rows. The present calculations support **declared-model answer checking**; they do not yet establish faithful automated reuse of the exact extracted record. Preserve that limitation and the separate source-removal/hash-change evaluations.

## Handoff

Arithmetic and the main v1 semantic repairs are accepted at the exact revision above. **Final freeze approval is withheld for the public-ID leak and the remaining scoring/input-contract work.** Critic owns changes in its own checkout. After the revised files and actual agent payload are pinned, inspect the changed artifacts and rerun only checks affected by those changes; unchanged scientific calculations need not be repeated. Retain the separate blinded-reader gate. No agent evaluation, new worker, GPU submission or site deployment was performed by this audit.

## Follow-up to the director's blinded reader

Director commit `e0a376f90d7f7912359dc2b83194b4b39c56b370`, `scopedesk/audit_v11/blind_notes.md`, reports one disagreement and additional ambiguous formulations. Its `ts-0008` finding identifies a genuine distinction that my nonblinded implementation comparison did not settle: the public phrase “diffusion-driven” can mean strict instability of a previously asymptotically stable equilibrium, or simply an admissible growing spatial mode. My checker follows the key's strict well-mixed-stability precondition; that is why 136/136 arithmetic agreement is not full textual-fidelity approval.

Exact witness from the unchanged item: `J=[[1/4,-1/2],[1/2,-1]]`, `D=(1,30)`, `L=5*pi`, Dirichlet. The well-mixed trace is `-3/4` and determinant is zero. At n=1, q=`1/25`, trace=`-199/100`, determinant=`-53/250`; at n=2, q=`4/25`, trace=`-571/100`, determinant=`-34/125`. Growing modes exist, but strict well-mixed asymptotic stability does not. State that precondition explicitly or exclude the item; do not mark the blind reader mathematically wrong. The same convention needs to cover `ts-0018` and the kinetically unstable `t2-0011`.

I support the director's request to adjudicate the remaining flags before freeze: define “fastest-growing” when no mode grows, name the wavelength relative-error denominator and tie handling, specify base diameter and gravity in Greenhill, and retain the KPP outcome-versus-sufficient-condition distinction. Existing wavelength/Greenhill margins and numerical agreement do not replace these declarations. These conditions are additional to the ID leak and diagnosis/grouping corrections above.
