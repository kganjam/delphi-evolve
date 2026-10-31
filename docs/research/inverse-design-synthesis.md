# Inverse design, cellular computation and electrical fabrication

Research checkpoint, October 31, 2026. These are candidate experiments, not claims that a new material or organism has been built. Three subscription workers are independently examining NCA/amorphous computing, electrical fabrication, and FutureHouse challenges. The existing build continues.

## Checklist and decision rule

- [x] Read prior amorphous-computing and biology Millennium Problems notes as leads.
- [x] Read primary sources for NCA, electrical cellulose assembly, bioelectric computation and differentiable simulation.
- [x] Query live Delphi claims and their complete assumptions.
- [x] Calculate an exact model example in which domain size changes whether a Turing claim applies.
- [x] Reconcile independent research reports, correcting scope and provenance errors; unreplicated pilot calculations remain scout-reported.
- [ ] Inspect actual data files for any proposed new empirical benchmark.
- [ ] Freeze one bounded experiment before allocating additional training jobs.
- [ ] Change the main pitch only after a new direction produces a stronger measured result.

A candidate must name the thing being designed, controllable variables, available observations, independent evaluator, strong baseline, failure criterion, and specific Delphi claim that changes a decision. Attractive animation alone is insufficient. A model proof cannot establish a fabricated material's performance.

## What is established

**Electric fields can participate in biofabrication.** Sano and colleagues demonstrated electric-field-guided bacterial cellulose assembly in 2010. This is externally powered biological manufacturing, not evidence that endogenous cellular voltages can position arbitrary nanoscale components. [Primary author record](https://research.chalmers.se/en/publication/123959), DOI 10.1007/s10439-010-9999-0.

A 2025 study measured cellulose-producing bacteria's response to AC fields and subsequent growth. Its material-growth experiments extend over days, so a new fabricated specimen is not a credible hackathon promise. The publisher's data statement offers underlying data on request; we have not obtained raw measurements. The publisher's public minimal HTML was readable with a direct HTTP request after a web-tool redirect failure. [Baddam et al.](https://academic.oup.com/ooms/article/5/1/itaf007/8116960).

**Inverse NCA design exists.** Growing NCA demonstrated learned growth, persistence and regeneration in 2020. Richardson et al. learned spatiotemporal patterns and tested new initial conditions in 2024; their studied systems include simulated PDE trajectories, not empirical programming of living cells. A July 2026 preprint uses NCA for disordered metamaterial design. Target-image generation, damage recovery and NCA material generation are insufficient novelty claims. [Growing NCA](https://distill.pub/2020/growing-ca/), [Richardson et al.](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1011589), [Xiang and Wang](https://arxiv.org/abs/2607.14475).

**Bioelectric computation has close prior art.** Manicka and Levin modeled non-neural electrical logic and pattern detection in 2019. Jaxley supports GPU differentiation of biophysical neural models, fitting measured recordings and training computational tasks. A generic differentiable bioelectric simulator is not a new contribution. [BEN paper](https://www.nature.com/articles/s41598-019-54859-8), [Jaxley](https://www.nature.com/articles/s41592-025-02895-w).

The public MIT-licensed `bioelectrics` package is closer still: ion-level tissues, intervention optimization, attractor analysis and published-model checks. Its limitations matter: a fixed extracellular bath, phenomenological channels producing bistability, and missing osmotic regulation. Its validation distinguishes matching equations from validating a tissue. I cloned and read README, validation and limitations at commit `7c061c5041c4a75b074f59d94235ff8cb7f24f50`; I have not run its tests. These remain author-reported capabilities. [Repository](https://github.com/tlcdv/bioelectrics).

**FutureHouse supplies validation targets.** Its September 2026 announcement lists twelve Millennium Problems chosen partly for experimentally checkable criteria. The announcement does not state a monetary award. Solving a simulation surrogate does not solve the corresponding biological problem. Exact thresholds are under independent review. [Official announcement](https://www.futurehouse.org/news/millennium-problems-for-biology).

## Ten candidates

This is qualitative judgment, not a measured ranking. All outputs below are proposed.

| Candidate | Tangible result and decisive test | Main obstacle |
|---|---|---|
| Intervention-tested NCA | Predict withheld perturbation trajectories and choose a discriminating intervention | Real perturbation data and an observable-to-state mapping |
| Bioelectric control under uncertainty | Control program reaching a target across an ensemble; independent solver and unseen conditions | An arbitrary parameter ensemble is not calibrated biology |
| Electrical cellulose planner | Electrode/frequency schedule; test against measured field-response or growth conditions | Raw data and a validated spatial material model |
| Ion-channel protocol selection | Choose the next recorded protocol; evaluate withheld real current traces | Strong optimal-design and IonBench prior art |
| Domain-aware Turing design | Target wavelength translated into admissible parameters; spectrum and independent integration | Classical theory; correct reuse is the contribution |
| NCA-to-reaction-network compilation | Restricted rules mapped to supported primitives; translation checks | Arbitrary neural rules lack physical implementations |
| Cellular communication primitives | Routing, consensus or memory under noise and failures | Software cells do not establish engineered living cells |
| DNA-tile algorithm verification | Finite program certificate and error sensitivity | Existing physically programmable tile systems |
| Functional material design | Structure with target anisotropy or permeability; independent mechanics/transport solver | Crowded field and uncertain biological mapping |
| Millennium threshold audit | Comparable evidence and exact distance to a target | Useful evidence work, limited standalone design demo |

The top three research bets are **intervention-tested NCA**, **bioelectric control under uncertainty**, and **electrical cellulose fabrication**. They match the requested ambition, but data inspection can change their order. Ion-channel protocol selection is a practical fallback if they lack measurements; it must improve on established comparisons.

### Decision after the three scouts

Keep the measured TrpB build on the critical path. The NCA scout located no downloadable measured damage-and-regeneration benchmark in its bounded search; its strongest proposal is a computational cross-solver test. The electrical scout found usable paired channel-expression/function assays, but these do not directly measure voltage gating or tissue control. The grand-problem scout recommends strengthening the existing experiment before adding a new platform. See `research-nca.md`, `research-electric.md`, and `research-grand.md` for source-level limits.

A new worker is implementing a faithful LazySP-style comparison, because the current Hamming-directed policy is not that baseline. The current random policy already samples the unknown frontier, rather than the entire sequence space; the scout's contrary characterization was corrected after reading `evolve/policies.py`. Results against a stronger baseline may reduce or remove the claimed advantage. No NCA training or electrical fabrication job has been launched.

The long-term ambition remains inverse design of collective behavior. An investible first claim would require a prospectively useful intervention or a demonstrated reduction in experimental work; neither a self-repairing animation nor the presence of a claims graph establishes that.

## Useful legacy code, and a trap to avoid

MorphoSwarm's `lean/morphoswarm-core/MorphoSwarm/Mechanism/GiererMeinhardt.lean` contains parameterized rational proofs about a particular well-mixed reaction model, including opposite local responses to pressing and clamping the inhibitor. This is a more substantial reuse candidate than an unrelated constant identity. The coordinator read the source but has not rerun its compiler in this review. It does not prove a tissue intervention works.

Conversely, `lean/problems/_examples/turing_criterion.lean` defines a Boolean predicate checking positive activation/inhibition and a diffusion ratio above one. Those three conditions alone are not the general two-species instability criterion. Do not reuse that example as a physical oracle merely because its Lean definition compiles. The live Delphi record and the finite-domain calculation below provide the relevant additional conditions.

## Actual existing Delphi claims

Live MCP responses and retrieval hashes are saved in `artifacts/research/delphi-inverse-search.json` and `delphi-inverse-claims.json`. These responses identify local unsigned nanopubs, not confirmed network publications.

- `turing-ddi`: reject a proposed reaction/diffusion design that fails linear-instability conditions. A finite domain additionally requires an admissible spatial mode; the continuum inequality alone is insufficient.
- `turing-wavelength`: its stated near-onset and large-domain conditions must gate any wavelength guarantee.
- `turing-morphogen-hypothesis`: its context warns that matching patterns cannot identify the mechanism. Require a discriminating intervention before accepting a causal interpretation.
- `wolfram2002-ch09-08`: motivates a conservation-respecting automaton family. It is a computational observation, not a theorem about all NCAs. Its LLM assessment scores are not probabilities.

Remove or change a claim's applicability conditions and measure whether the proposed design, admissibility decision or required experiment changes. A citation-only link fails this reuse test.

### Exact finite-domain example calculated

Take a two-species linearization with

```
J = [[1, -2], [2, -3]], Du = 1, Dv = 10.
trace(J) = -2, det(J) = 1.
det(J - q D) = 10 q^2 - 7 q + 1.
```

The homogeneous state is stable. The continuum instability interval is `1/5 < q < 1/2`. On a one-dimensional Neumann domain of length `pi`, admissible values are `q = n^2`: none lies in that interval. The constant mode is stable; for every `n >= 1`, `q >= 1`, and `q(10q - 7) + 1 >= 4` while the trace stays negative. Every mode is linearly stable.

With the same chemistry on a domain of length `2 pi`, the first nonconstant mode has `q = 1/4` and determinant `-1/8`, giving a positive eigenvalue. The decision changes solely because the domain changes. Python exact rational arithmetic checked the displayed modes; the analytic tail argument covers all higher modes. See `artifacts/research/turing-domain-counterexample.json`.

This is an established mathematical phenomenon demonstrating a transfer condition, not a refutation of Turing, a biological discovery, a Lean proof, or a guarantee of nonlinear pattern stability. [Finite-domain prior art](https://pmc.ncbi.nlm.nih.gov/articles/PMC9884266/).

## Proposed bounded experiment

Pitch hypothesis: **Specify a collective behavior. Design local controls. Test whether it survives conditions the model did not see.**

For one physical system, compare a freely learned NCA, a mechanistic optimizer, and a constrained hybrid. Freeze training observations, intervention budgets, targets and held-out conditions. Use GPUs for matched seeds, parameter ensembles and optimization; use CPU solvers for independent checks. Report errors, success rates, intervention costs and unresolved cases. Include shuffled constraints and removal of Delphi-derived conditions. Track ordinary numerical constraints separately from literature claims.

A useful Lean target is preservation of nonnegative concentrations or mass, a finite-domain instability criterion, or equivalence between restricted local rules and their evaluator. It must be parameterized and fail a changed-law mutant. It would not prove biological validity.

First confirm measurements, then obtain a strong baseline and independent evaluator. If that fails, retain the measured TrpB demonstration and label this direction a research roadmap. No additional implementation or GPU training was launched by this research checkpoint.
