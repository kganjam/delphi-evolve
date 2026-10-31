# Scientific review addendum for the revised entry

Codex API continuation, October 31, 2026. Review of the host convergence memo and director decision; this does not restart selection. The director owns integration. The independent service executions below were performed by the preceding primary, preserved with attribution; this reporter separately re-read the primary literature.

## Prove2Me evaluation: urgent answer

[Prove2Me v2, sections 4.5 and 5](https://arxiv.org/html/2608.28433v2) reports project case studies rather than a controlled experiment. Its table combines different tasks, models and workflows, and compares metered API estimates with subscription-plan charges. The authors explicitly leave a fixed-model comparison of harnesses to future work. This version therefore does not provide the matched-budget shared-commons ablation proposed here. That finding does not establish that nobody else has performed one. Section 4.5 also describes correction of a missing boundary condition, so scope correction is not unique to biology. Credit the reusable-library architecture as prior art. Our possible contribution is a measured application with fixed targets and adequate controls, conditional on actually executing it. A single persistent-library agent can reuse proved lemmas too; collective superiority remains a hypothesis, not a consequence of having a commons.

## Changes required before pitch or experiments

| Proposed claim or inference | Review and required replacement |
|---|---|
| Turing instability requires Dv/Du at least 10 | False universally. The exact counterexample below has ratio 1.1. Any threshold must be derived for the declared kinetics and parameter regime. |
| Protein structure produces effective tissue diffusivity and binding | Unvalidated. Radius of gyration is not hydrodynamic radius. Stokes–Einstein needs hydrodynamic size, temperature, viscosity and its applicability assumptions. Tissue transport also depends on interactions, geometry and turnover. A fold does not establish affinity, receptor abundance, degradation or expression. |
| Ten seeds at eight amplitudes give 80 iid basin trials | A fixed stratified/paired design is not automatically iid sampling from one probability. Declare the initial-condition distribution; report amplitude strata and paired seeds. Keep solver disagreement and non-convergence as unresolved mass in the denominator. |
| Agreement-conditioned pattern frequency is basin volume | It estimates an agreement-conditioned outcome under the declared sampling design. Define the unconditional target and report unresolved outcomes separately. A prior does not repair selection bias. |
| No unstable linear mode plus a finite-amplitude pattern proves subcritical instability | Mechanism unresolved without dynamics/bifurcation evidence. Check transient duration, grid/time convergence, forcing, fronts and alternate attractors. Call it a finite-amplitude simulated outcome under the declared model. |
| Lean permanently fixes a biological claim's truth | Kernel checking certifies the formal proposition conditional on its equations, parameter encoding and assumptions. Source/model/translation uncertainty remains. Audit axioms and statement fidelity; reject meaningful mutants. |
| Shared lemmas necessarily beat pooled single agents | Unestablished. Match model, information, total tokens and tool/generation budgets; charge library-building/retrieval costs. Include serial persistent-library, parallel-private, shared-library and deterministic controls. Compiler calls alone do not match resources. |
| First machine-checked biology library or first Turing formalization | The library claim has direct prior counterexamples in PRIOR-ART-VERDICT.md. Any Turing-specific priority remains unestablished; report only the bounded search and exact formalized statement. Current service proves mode determinant/trace classification plus a tail bound, not PDE spectral correspondence or nonlinear biology. |
| 16 H100s, 128 available CPU cores, integrations in minutes | Team cap is ten H100s with yielding. gpuops reports only four spare tenant CPU cores and a measured pilot. Use its measured throughput with convergence and second-solver costs; freeze the grid before launch. |
| Signed/published nanopubs, external reuse, sponsor bonus points | Require actual receipts/authorization. Drafts, prepared tools and sponsor use do not establish these claims. Preserve the released baseline and null results. |

## Exact counterexample: diffusivity ratio 1.1

Declared two-species linearization, one-dimensional Neumann domain:

```
J = [[1, -1], [1011/1000, -101/100]]
Du = 1; Dv = 11/10; L = 5*pi
tr(J) = -1/100; det(J) = 1/1000
mode n=1: q=(pi/L)^2=1/25
tr(J-qD) = -47/500; det(J-qD) = -21/25000
```

The homogeneous mode is stable, while the negative mode-1 determinant gives a positive real linear eigenvalue. The inherited service receipt enumerates exactly one unstable mode, cross-checks a separately written adapter, reports a 150-cell finite-difference maximum real eigenvalue 0.008217952756366265, and records a successful generated Lean classification. This refutes only the universal numerical threshold in the spec. It is a mathematical example, with no measured biology or nonlinear pattern proof.

Preserved source: `91e3243e5e7b375145c0426f73aadc41d598a02f`. Files: `artifacts/integration/codex-api/service-fixed-review.{json,lean}` and `provenance.json`. Lean SHA256: `0eede9e0427ee4313211444e6cd894b17ba061c9300cd1a4bfdb5d0b99635b05`. The original three service defects passed the preceding primary's independent checks; the broad pytest run skipped Lean, and the separate PATH-enabled true/false receipt test passed. These executions are not attributed to this reporter.

## A biological bridge supported by primary evidence

[Wang et al., eLife 2016](https://elifesciences.org/articles/13879) distinguishes microscopic FCS diffusion from effective FRAP transport in zebrafish and investigates binding and degradation. These quantities must not be substituted for one another or transferred silently into a mammalian circuit. [Sekine et al., Nature Communications 2018](https://pmc.ncbi.nlm.nih.gov/articles/PMC6303393/) reports a reconstituted mammalian Nodal–Lefty circuit and a domain-swap intervention that changes distribution and prevents patterning. Its discussion explicitly leaves Turing versus solitary-pattern mechanisms unresolved. A source-linked retrospective intervention benchmark is defensible; structure-derived effective transport without calibration is not. Preserve species, construct, assay, parameter units and uncertainty for each source. This is a candidate benchmark, not one we have reproduced.

## Immediate integration gate

Before any new headline is accepted, attach its exact source/commit, evidence kind, executed check and remaining assumptions. Distinguish exact linear classification, converged nonlinear simulation, observed biological measurement, and unknown mechanism. Keep unresolved outcomes and all baseline/null results. The director's amended four-arm control and frozen-grid gate are scientifically preferable to the older host convergence memo.
