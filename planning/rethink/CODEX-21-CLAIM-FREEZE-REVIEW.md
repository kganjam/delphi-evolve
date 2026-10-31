# Review gate for the Admissible 21-record freeze

Reviewed October 31, 2026 by Codex API. The broader persistent project goal is paused; this is the specifically requested freeze review and Price feasibility work.

## Revision identity: current file is not the supplied hash

Fetched exact repository commit `d75e245f660f9dfc1e7971d6b71c332b0c31987c` from `kganjam/admissible` into git objects without editing that repository. Its `bench/bench-v1-freeze.json` matches the local external file, SHA256 **dbf233d1ebe7156576e8e24bb4f7b7f3f6c3c75d4552efde198798eeb482ba0e**. This differs from the supplied `6d61ae56...`. The exact Lean file matches local SHA256 `c51b98a8c4218c5e272223c5d710de0d765804d78beace544850f9749cf07236`. Preserved review snapshots are under `artifacts/integration/codex-api/admissible-review/`.

**Do not launch the 21-record evaluation from this version.** The promised revised freeze must have its own commit/hash, corrected bucket semantics, and full formal statements/preconditions. Current rows contain descriptions, not a sufficient statement freeze. Previously compiled targets are reused baseline results, not prospectively frozen new proofs.

## Correct the bucket ontology

An extracted field saying “no canonical formalization” supports “no theorem target supplied for this statement,” not a proof of impossibility of formalization. Use B0a **no single theorem target specified here** and B0b **empirical claim not settled by a model proof**. For kimura-neutral-theory, the McDonald–Kreitman estimator is a separate mathematical object with domain assumptions; formalizing it does not settle the neutral theory. Neither excluded row should be counted as attempted-and-unreached or as a theorem refutation.

B1 versus B2 currently classifies proof effort and quantification inconsistently. Every general cancellation is quantified too. Define B1 as “algebraic identity conditional on explicit model quantities,” B2 as “model-derived algebraic result with substantive preconditions,” B3 as “analytic/stochastic/dynamical target.” These are operational triage categories, not mathematical impossibility theorems. Proving an identity and rejecting a mutant does not by itself establish scientific value.

## Row-level target review

| Claim | Assessment before freeze |
|---|---|
| fisher-ftns | B2 only for a precisely defined partial selection change and additive-genetic projection. Setting trait equal to total fitness proves a total-variance selection identity, not automatically additive-genetic FTNS. Define genetic effects and residual orthogonality; retain environment/transmission term for total change. |
| fisher-infinitesimal | B3 plausible, but specify random variables, scaling, independence/dependence, metric and rate hypotheses. Do not assume a universal O(M^-1/2) bound. Not attempted is different from attempted-and-unreached. |
| fisher-kpp-speed | B3 for wave existence/selection with D,s>0, state/solution class, domain and initial-data assumptions. Distinguish traveling-wave existence from spreading of a compact patch. |
| fisher-sex-ratio | B2 for the equilibrium investment identity after specifying the reproductive competition/mating model; equal-cost arithmetic is a separate corollary. The identity is not an ESS proof without an invasion-fitness definition. |
| hamilton-haplodiploidy | B1 pedigree arithmetic only after specifying parentage, monandry, sex/chromosome convention, no inbreeding and reproductive-value convention. Arithmetic relatedness does not prove eusociality. |
| hamilton-lmc | B2 only with foundress relatedness, mating and dispersal assumptions, ploidy and explicit invasion objective. The formula alone is not a proof of unbeatability. |
| hamilton-rule | B2 for the regression-form criterion with defined b,c,r, residual orthogonality, positive mean fitness and focal variance, and transmission assumption. Regression coefficients are not automatically causal intervention effects. |
| hamilton-senescence | B2 for monotonicity of the specified sum with nonnegative terms and correct indexing. A monotone invented sum is not correspondence to the biological force-of-selection claim. |
| kimura-fixation-probability | B3 under the given definitions if proving the exponential neutral limit/diffusion connection. Evaluating a supplied expression or proving its range is a narrower B2 task. Separate analytic limit, diffusion derivation and finite Wright–Fisher approximation. |
| kimura-fixation-time | B3 if deriving a diffusion expectation; a limit of an already assumed formula may be much simpler. State conditioning, units, ploidy and effective-population-size convention. |
| kimura-heterozygosity | B1 only for downstream algebra. Deriving H=theta/(1+theta) needs the infinite-alleles equilibrium model/recurrence and assumptions; declaring the formula as an assumption does not prove it from that model. |
| kimura-neutral-theory | B0b for the empirical prevalence claim; MK estimator formalization gets a separate target and domain/nonzero-denominator conditions. No empirical resolution from algebra. |
| kimura-substitution-rate | B1 cancellation with N>0 and neutral fixation probability supplied. State that fixation probability and substitution-process assumptions are premises. Mutation rejection does not turn cancellation into a major theorem. |
| maynardsmith-ess | B3 for asymptotic stability under replicator dynamics, including game class, state-space/topology and boundary hypotheses. B2 can formalize the ESS predicate or an explicit game's ESS, not the full dynamics theorem. |
| maynardsmith-hawk-dove | B2 with exact payoff matrix, V>0 and C>V. Separate a mixed strategy's ESS property from convergence of population dynamics; handle C=V explicitly or exclude it. |
| maynardsmith-hitchhiking | B3; the literal phrase “increasing ... tending to 0” needs its variable/limit checked against the source. Do not freeze incompatible monotonicity/asymptotic clauses without resolving them. |
| maynardsmith-twofold-cost | B1 recurrence conditional on equal fecundity, sex ratio and comparison convention; distinguish odds-doubling from frequency-doubling. Derive recurrence or label it assumed. |
| maynardsmith-war-of-attrition | B3 for density normalization plus ESS over a continuum of strategies/integral payoffs. A formal expression for the density is a smaller target. Need V>0 and full payoff/tie convention. |
| turing-ddi | B2 for determinant algebra and specified mode admissibility. Require well-mixed stability, positive diffusion, q>=0, and existence of admissible q with det(J-qD)<0. An eigenvalue/PDE equivalence is a separate obligation. |
| turing-wavelength | B2 for algebraic scaling after onset assumptions are fixed; analytic onset derivation is separate. Intrinsic continuum wavelength is distinct from a finite-domain selected mode and nonlinear spacing. Do not claim unconditional size independence refuted at a source scope that already assumes large domains. |
| turing-morphogen-hypothesis | B0a: no single target fixed here. A broad mechanistic proposal can be represented mathematically and empirically tested; “not formalizable” is unjustified. |

## Existing Lean file: specific fidelity failures

- `unstable_iff_pos_eigenvalue` is **not an iff**. It accepts a positive real root and negative trace as premises, then derives negative determinant. It does not prove existence of such a root from negative determinant, identify eigenvalues of the actual matrix, or address complex eigenvalues. Rename it `negative_det_of_positive_root` or prove the missing direction and correspondence.
- `finite_domain_stable` assumes `forall n, not Unstable(...)`, where Unstable is defined as negative determinant, and concludes `forall n, determinant>=0`. This is a logical restatement. `hL` is unused; neither well-mixed stability nor negative mode trace is required. The conclusion is **not linear asymptotic stability**. Nonnegative determinant allows marginal modes, and positive trace is not excluded. Keep as `det_nonneg_of_no_negative_mode`; add the genuine trace/determinant theorem if stability is claimed.
- `worked_unstable_iff` supplies meaningful factored determinant algebra for one parameter set. `worked_stable_on_pi` excludes negative determinant for every mode at pi. Together with `worked_wellmixed`, positive diffusivities and trace negativity, these support a stronger mathematical statement; the connecting stability theorem is not yet in the file.
- A clean axiom audit certifies proof dependencies, not the accuracy of theorem names/docstrings or translation. Mutants should reject wrong scientific conditions, not merely cause syntax/type errors. Save exact diagnostics and original controls.

Approved next action: revise/freeze full target statements, review changed statements, then run a bounded feasibility or evaluation with the recorded distinctions. This memo is not an authorization to call the existing 21 rows mechanically verified.
