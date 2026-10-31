# Price identity and one regression corollary: bounded review and feasibility probe

Codex API, October 31, 2026. This answers the specific request while the broader project goal remains paused. It does not restart selection, establish first-ever priority, or resolve the 21 extracted biological claims.

## Prior-art verdict

**Price as a root connecting Fisher and Hamilton is established mathematics, not a new scientific unification.** [Frank (1997), “The Price Equation, Fisher's Fundamental Theorem, Kin Selection, and Causal Analysis”](https://doi.org/10.1111/j.1558-5646.1997.tb05096.x) explicitly links them through regression decompositions. Its author abstract was read directly. [Frank (2012)](https://pmc.ncbi.nlm.nih.gov/articles/PMC3354028/) explains the identity, transmission term, mathematical equivalence and dynamic limitations. [The Value of Price (2024)](https://doi.org/10.1007/s13752-024-00482-4) supplies an explicit axiomatic reconstruction; “formalization” there does not by itself mean proof-assistant compilation.

A bounded search for the biological Price equation with Lean, Lean4, Coq/Rocq, Isabelle/HOL, HOL Light, Agda, proof assistant, formal verification and GitHub symbol forms did **not locate a machine-checked Price formalization**. Local Mathlib source search for `price_equation` / `Price equation` returned no hit. The inspected Lean-Bio repository trees at inventcures revision `09891f572701a96e3677a7352159307cffd42797` and upstream `2d35f9fe64f01fa64be70af95bdf89a1bdd877d0` had no Price/Fisher/Hamilton path names; that is only a filename check, not a proof of code absence. Many search hits concerned economic price equations and were irrelevant. Ryan B. Lewis's author page lists “Generalized Price Equation” (2020), but its relationship to proof-assistant work was not established. A repository listing a “Formal Foundations of Multilevel Game Theory” paper is not evidence of a compiled theorem.

**Permitted priority wording:** “We did not find a prior machine-checked Price formalization in this bounded search.” **Do not say:** “nobody has checked this mechanically”, “biology has no machine-checkable results”, or “first verified foundation of biology.” The prior-art limit remains even if our probe compiles.

## Exact implementation scope

`experiments/price_probe/Price.lean` uses finite weighted sums over a general finite type, real-valued traits, explicit moment/covariance definitions, and the descendant mean obtained by reweighting family descendant trait means by reproductive weights. The general algebra requires nonzero mean fitness; `Population` restricts interpretation to normalized nonnegative frequencies and nonnegative reproductive weights with positive mean. No measured biology is supplied.

Targets:

1. `price`: mean fitness times total trait change equals covariance plus fitness-weighted within-family trait change. `population_price` gives the same result under valid finite-population conditions.
2. `selection_only`: perfectly transmitted trait removes the transmission term.
3. `fitness_selection`: with the same assigned fitness transmitted as the trait, the selection-only change is total fitness variance divided by mean fitness. **This is not additive-genetic Fisher FTNS.** The additive-genetic projection/residual step is absent and must not be hidden in a renamed variance.
4. `hamilton_regression`: write fitness as intercept minus c times the focal trait plus b times partner trait plus residual. Assume residual covariance with focal trait is zero, define r by partner/focal covariance, require positive focal variance and mean fitness, and assume perfect transmission. The Price selection term then gives positive trait change iff `r*b-c>0`. This is a conditional statistical regression theorem, not a causal cost-benefit intervention rule or a derivation of coefficients from empirical data.

The regression corollary explicitly reuses `selection_only`, which reuses `price`. This is a real proof dependency. It is not evidence of measured multi-agent advantage or a biological law newly discovered.

## Execution and limits

Exact diagnostics, source hash, command exits, timings and two changed-target mutants are saved in `artifacts/integration/codex-api/price-probe.json` by `run_probe.py`. Read the original exit before claiming completion. The first compile encountered a missing `noncomputable` marker; a subsequent compile found an unmatched section end. These were implementation failures and were corrected, not passes. Two shell attempts used the wrong working directory; one redundant compile was stopped in its own scope. All actual compiler runs were bounded by systemd resource/runtime caps.

Changed-target mutants reverse the transmission sign and Hamilton cost sign while retaining the attempted original proof; a nonzero exit shows that proof does not establish the changed target. `Witnesses.lean.inc` additionally supplies explicit two-type counterexamples and nonvacuity checks; their compile exit is recorded separately. This author-run feasibility probe is not the frozen independent evaluation and must not contribute to a blinded success count. A separate reader still needs to audit the statements, biological correspondence and assumptions.

## Consequence for the pitch

If the saved original compile succeeds and mutants reject, say: **“We machine-checked the finite Price identity and a conditional regression-form Hamilton corollary, with the assumptions attached.”** Credit the established derivation. Fisher's additive-genetic theorem remains a separate target. Do not call this a universal Principia, causal predictor, empirical validation, first-ever result or three verified fundamental laws.
