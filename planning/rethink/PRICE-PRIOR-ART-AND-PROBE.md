# Price identity and one regression corollary: bounded review and feasibility probe

Codex API, October 31, 2026. This answers the specific request while the broader project goal remains paused. It does not restart selection, establish first-ever priority, or resolve the 21 extracted biological claims.

## Prior-art verdict

**October 31 follow-up: confirmed proof-assistant predecessor.** Direct source inspection of [atlas-lean, `Selection.lean` at 885e9b9](https://github.com/facebookresearch/atlas-lean/blob/885e9b980ed29e3af153e46323d9a9f8f5718031/MathlibExt/Biology/PopulationGenetics/Selection.lean) found `price` and `meanFitness_select_sub`. Its documentation explicitly distinguishes haploid total-fitness variance from the diploid additive-genetic statement. This supersedes any inference from the earlier bounded search that no Lean predecessor exists. We did not recompile upstream here; absence of a Queller corollary from this one file is not an exhaustive novelty result. Our contribution remains a scoped feasibility/review artifact.

**Price as a root connecting Fisher and Hamilton is established mathematics, not a new scientific unification.** [Frank (1997), “The Price Equation, Fisher's Fundamental Theorem, Kin Selection, and Causal Analysis”](https://doi.org/10.1111/j.1558-5646.1997.tb05096.x) explicitly links them through regression decompositions. Its author abstract was read directly. [Frank (2012)](https://pmc.ncbi.nlm.nih.gov/articles/PMC3354028/) explains the identity, transmission term, mathematical equivalence and dynamic limitations. [The Value of Price (2024)](https://doi.org/10.1007/s13752-024-00482-4) supplies an explicit axiomatic reconstruction; “formalization” there does not by itself mean proof-assistant compilation.

A bounded search for the biological Price equation with Lean, Lean4, Coq/Rocq, Isabelle/HOL, HOL Light, Agda, proof assistant, formal verification and GitHub symbol forms did **not locate a machine-checked Price formalization**. Local Mathlib source search for `price_equation` / `Price equation` returned no hit. The inspected Lean-Bio repository trees at inventcures revision `09891f572701a96e3677a7352159307cffd42797` and upstream `2d35f9fe64f01fa64be70af95bdf89a1bdd877d0` had no Price/Fisher/Hamilton path names; that is only a filename check, not a proof of code absence. Many search hits concerned economic price equations and were irrelevant. [Henry Blanchette's author page](https://www.rybl.net/page/about.html) lists “Generalized Price Equation” (2020), with Mark Bedau, but its relationship to proof-assistant work was not established. The earlier version of this memo misidentified that page's author; this attribution is corrected after directly reading the page. A repository listing a “Formal Foundations of Multilevel Game Theory” paper is not evidence of a compiled theorem.

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

## October 31 follow-up: prior-art coverage and exact requested targets

The follow-up search used exact `Price equation` / `Price_equation` strings with Lean, Lean4, Coq, Rocq and Isabelle/HOL, plus Fisher's fundamental theorem and Hamilton's rule with those assistants. It also searched indexed GitHub, AFP and Rocq pages. No inspected result supplied a prior compiled implementation of these biological targets. The [AFP catalogue](https://isa-afp.org/) itself was opened and searched: no Price entry; Fisher matches were Fisher's combinatorial inequality and Fisher–Yates shuffle, and the Hamilton match was Cayley–Hamilton. This checks catalogue text, not every theory body. The www AFP endpoint timed out, but the canonical endpoint without www succeeded. The [Rocq packages page](https://rocq-prover.org/packages) rendered a landing page rather than all package contents; it cannot support a source-wide absence claim. No exhaustive GitHub code search or full Coq/Isabelle source audit was performed. Search coverage and access limitations are recorded in `artifacts/integration/codex-api/price-prior-art-followup.json`.

The [Frank 1997 author-hosted paper](https://stevefrank.org/reprints-pdf/97Evol-Causal.pdf) directly establishes the historical relationship and the need for a predictor/regression partition. Our possible contribution is a checked implementation with explicit scope and reusable dependencies. Neither the mathematical unification nor worldwide proof-assistant priority is established as new.

| Requested scorecard name | Actual state and acceptable interpretation |
|---|---|
| `price_equation` | Already implemented as `DelphiPrice.price`, with valid-population wrapper `population_price`, at b4e60db. Keep definitions of parent frequencies, reproductive weights and descendant family means attached. |
| `hamilton_rule_from_price` | Already implemented as `hamilton_regression` at b4e60db. It uses `selection_only`, which uses `price`. Scope is a statistical regression criterion with residual orthogonality, positive focal variance and mean fitness, the declared partner covariance and perfect transmission. Valid biological-population use additionally requires nonnegative normalized frequencies and nonnegative reproductive weights. |
| `fisher_ftns_from_price` | **Not implemented or approved under this name.** Existing `fitness_selection` proves total assigned-fitness variance divided by mean fitness. It does not prove an additive-genetic projection or Fisher's partial-change interpretation. |

### Why the proposed Fisher wording is insufficient

In the finite-population notation already used by the probe, setting `z := w` gives

`Delta_sel mean(w) = Cov(w,w)/mean(w) = Var(w)/mean(w)`.

An additive projection needs another explicit object. Fix genetic predictors and their average effects, let `A` be their additive fitness contribution, and write `w = alpha + A + e` with `Cov(e,A)=0`. For normalized weights and positive mean fitness, the narrower algebraic target is

`Cov(w,A) = Var(A)` and therefore `Delta_sel mean(A) = Var(A)/mean(w)`.

The second expression is reweighting the **fixed additive contribution**. To label it Fisher's partial change in mean fitness, freeze the genetic predictor space, the meaning of average effects/additive variance and the correspondence between this reweighting and the selected partial change. The orthogonality premise may be supplied for a conditional lemma, but deriving it from a stated regression fit is a separate obligation. It must not be silently assumed to follow from the word “additive”. Environmental changes, changes of effects and transmission remain outside this partial component. A suitable interim name is `additive_projection_selection`; this is a proposed statement, not a compiled theorem.

There is a small exact counterexample to replacing total variance with additive variance merely because an orthogonal additive decomposition exists. Give four genotype/environment classes equal mass, let `g=(0,0,1,1)`, `A=2g-1=(-1,-1,1,1)`, `e=(-1,1,-1,1)` and `w=3+A+e=(1,3,3,5)`. Then `mean(w)=3`, `Cov(A,e)=0`, `Var(A)=1`, and `Var(w)=2`. Fixed-fitness selection changes mean assigned fitness by `2/3`; the fixed additive component changes by `1/3`. `experiments/price_probe/review_projection.py` computes these values with rational arithmetic and saves `price-projection-review.json`. This is a constructed mathematical witness, not biological data, a new Lean theorem, or a scored prover attempt.

### Freeze wording still requiring repair

The four accepted corrections remain binding, but the proposed B0a wording still overstates the evidence: **“no single theorem target specified here”** is justified by an extracted record saying “no canonical formalization”; **“not formalizable as stated”** is not established by that phrase. B0b should describe the empirical claim separately from any estimator target. The complete 21-row and Admissible-name review is in `CODEX-21-CLAIM-FREEZE-REVIEW.md`; clean compilation and standard axioms do not resolve statement fidelity. Neither that scorecard nor Scope Desk v1.1 is approved for agent runs by this addendum. The director has requested a separate Scope Desk v1.2 revision; this Price review does not supersede its hold.
