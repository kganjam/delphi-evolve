# Prior-art verdict: the market and the verified commons

Primary review, 2026-10-31. This is a source and methods audit, not a new selection decision. The director owns integration. Read alongside `PRIMARY-REVIEW.md`. The host's verbatim user quotes preserve Delphi as useful material, without treating its existing assessments as ground truth.

## Decision in one paragraph

**Kill the novelty claims that a scoped fitness proposition escapes protein benchmarks, that LLM forecast crowds are new, that a verified biology library is new, or that a growing lemma commons is new. Do not kill the useful prototype merely because its components have predecessors.** The strongest defensible contribution here is a narrow, reproducible demonstration that source-linked, scope-checked mathematics changes a proposed biological-model intervention, with a measured comparison against strong ordinary tools and a persistent single agent. A successful commons ablation would be evidence about this implementation; it would not establish a new principle of collective intelligence.

## Completed checklist and evidence limits

- [x] Read ProteinGym's original evaluation definitions and ensemble/single-model table.
- [x] Read original FLIP's baseline restrictions; download and read FLIP2's TrpB methods and tables.
- [x] Read StructSeq's cross-modal ensemble proposal.
- [x] Read Halawi and Schoenegger methods, aggregation and evaluation scope.
- [x] Search broader scientific forecasting and simulation-grounded agents.
- [x] Check direct prior art for verified biology and growing proof libraries.
- [x] Read the library-learning replication critique and derive the scoring identity's limits.
- [x] Inspect our current Turing proof's stated trust boundary.
- [ ] Rebuild external Lean projects: **not attempted**. Their stated capabilities remain author reports; code inspection is distinguished below.
- [ ] Establish first-ever novelty: **not established**. This is a targeted search, not an exhaustive literature review.

## 1. ProteinGym and FLIP: what they actually establish

**ProteinGym already evaluates more than raw fitness regression.** Section 4.1 evaluates AUC and MCC against binarized measurements, and NDCG/top-10% recall for useful high-fitness variants. Appendix A5 reports corrected mean Spearman: DeepSequence ensemble 0.419 versus single 0.407; EVE ensemble 0.439 versus single 0.433; MSA Transformer ensemble 0.434 versus single 0.421. TranceptEVE L is 0.456, while GEMME is 0.455, in the same top rank group. These are aggregate benchmark results, **not TrpB-specific results, not a guarantee that an ensemble beats its best member, and not a matched-compute crowd experiment**. The table's “single” row is not an oracle selection of the best ensemble member on each assay. [ProteinGym, NeurIPS 2023, §4.1, Table 2 and Table A5](https://proceedings.neurips.cc/paper_files/paper/2023/file/cac723e5ff29f65e3fcbb0739ae91bee-Paper-Datasets_and_Benchmarks.pdf).

**Original FLIP does not establish ensemble superiority on TrpB.** It covers GB1, AAV and thermostability. Table 3 explicitly uses only one ESM-1v ensemble member because of compute limits. Its useful warning is that simple supervised models can be competitive and evaluation splits matter. Calling FLIP a proof that all such prediction problems are solved would overstate the source. [FLIP, 2021, Table 3 and §5](https://flip.protein.properties/assets/FLIP_2021_manuscript.pdf).

**FLIP2 directly overlaps our data family.** Its TrpB collection derives from Johnston et al. (2024), combining nine three-site landscapes and one four-site landscape. It tests mutation-count and position transfer; its by-position split includes the four-site landscape in testing. Tables A7–A9 report:

| TrpB split | Ridge, one-hot | Ridge, one-hot plus model likelihoods | Best reported model in that table |
|---|---:|---:|---|
| One-to-many | 0.441 | 0.453 | Augmented ridge, 0.453 |
| Two-to-many | 0.437 | 0.410 | Fine-tuned CARP, 0.509 ± 0.010 |
| By-position | 0.274 | 0.294 | Augmented ridge, 0.294 |

Values are Spearman, not Brier scores. This is feature fusion, not a general theorem about ensembles; it helps in two splits and hurts in one. Table A7 also lists fine-tuned CARP at 0.451 ± 0.022. The paper uses a growth-based assay, **not direct catalytic-efficiency measurements**. [FLIP2 manuscript, §3.2.4 and Tables A7–A9](https://flip.protein.properties/assets/FLIP_manuscipt.pdf).

**Cross-modal protein aggregation is also prior art.** StructSeq combines sequence, multiple-sequence-alignment and structural information, motivated by different predictors' strengths across assay types; its authors report improved aggregate ProteinGym performance. Thus “different guilds see sequence versus structure” is not a new scientific mechanism by itself. [StructSeq, 2023, abstract and §§3–4](https://www.mlsb.io/papers_2023/Combining_Structure_and_Sequence_for_Superior_Fitness_Prediction.pdf).

**Our inference:** converting “predict fitness” into “is this variant above threshold t under assay A?” is ordinary classification. Declared scope is good scientific bookkeeping, but does not rescue novelty. A genuinely different task could concern whether an assay supports transferring a conclusion to another environment, whether an intervention is licensed by a model, or which additional observation resolves a decision. That requires a distinct target, independent oracle and corresponding baseline; changing the wording is insufficient. These benchmarks establish substantial prior work, not that protein engineering has been solved.

## 2. Forecast crowds: the broad novelty claim fails; the exact combination is unestablished

**Halawi et al. already combine retrieval, reasoning and aggregation.** Their system uses dated news retrieval, prompted/fine-tuned forecasts and an aggregation rule; §4.3 and Appendix E compare aggregation methods, including a small-ensemble trimmed-mean variant. Questions cover several domains, including healthcare/biology and science/technology, so “only geopolitical forecasting” is inaccurate. In baseline Table 2, the zero-shot aggregate and best displayed single model both score 0.208 Brier; scratchpad aggregation is worse than the strongest displayed single. This is another warning against assuming aggregation wins. The inspected workflow does not use Lean or a reaction–diffusion solver as its settlement oracle. [Halawi et al., 2024](https://arxiv.org/html/2402.18563v1).

**Schoenegger et al. already test a heterogeneous LLM crowd.** Study 1 aggregates twelve models on 31 binary tournament questions against 925 human forecasters; the preregistered comparison is against a no-information benchmark and human aggregation. Some models have internet access. Study 2 adds human forecasts as information and compares combination strategies. This is prior art for model diversity and human/model fusion, but not the proposed formal/PDE/TrpB settlement system. Absence of a significant difference from humans is not proof of universal equivalence or superiority to the best model. [Schoenegger et al., 2024, Methods and Results](https://arxiv.org/html/2402.19379v2).

**The broader field is not limited to news.** SciPredict explicitly evaluates predicting empirical physics, biology and chemistry outcomes and reliability of confidence. SGA couples LLM scientific hypotheses to differentiable simulation feedback. Neither inspected source establishes the exact three-tier forecast market, but together they invalidate the broad claim that science prediction or simulator-grounded agents are untouched. [SciPredict, ICML 2026, author abstract](https://proceedings.mlr.press/v306/sehwag26a.html); [SGA, ICML 2024, author abstract](https://proceedings.mlr.press/v235/ma24m.html).

**Search limit:** targeted searches covered the two named forecasting papers, scientific outcome prediction, LLM simulation feedback, and forecast/Lean/simulation aggregation combinations. I did **not** find a primary paper in that set implementing the exact Lean + nonlinear PDE + TrpB market. This supports “our particular integration,” not “nobody has done tool-grounded or cross-modal forecasting.” Combining three unrelated target families is not automatically a scientific contribution. Report each tier separately. A simulated label settles a numerical question only under a declared solver/convergence contract.

If a forecaster can cheaply call the same exact settlement oracle, compare with that direct tool call. Making it guess while denying the tool creates artificial difficulty. If settlement is expensive, the research question becomes cost-aware acquisition or deferred computation, with the oracle costs counted.

## 3. The refined Lean pitch has direct prior art

| Primary source inspected | Existing contribution | Consequence for our pitch |
|---|---|---|
| [Rashid et al., PLOS ONE 2017](https://hvg.ece.concordia.ca/Publications/Journals/PONE17.pdf) | HOL Light reaction kinetics, biological networks and case studies, integrating earlier Zsyntax work | Formal theorem proving in mathematical biology is established. Switching proof assistants is not a biological discovery. |
| [Lean-Bio source and general schema](https://github.com/inventcures/lean-bio/blob/main/lean/BslLean/ReversibleTwoSpecies.lean) | I read a real-valued mass-action vector field, steady-state predicate, general parameter-interval bounds and proof bodies; its documentation describes generated certificates | Model-relative, parameter-bounded, executable Lean biology already has a very close example. I did not compile it. The repository identifies itself as independent of GSK. |
| [crnt-lean](https://github.com/marpaia/crnt-lean), [analyzer contract](https://github.com/marpaia/crnt-lean/blob/master/docs/analyze-contract.md) | Authors document a chemical-reaction-network library, executable structural checks, certificates, stability and explicit remaining hypotheses | Even “library plus executable scope checks” has close prior art. Documentation was inspected; the extensive theorem/build claims were not independently audited. |
| [Ripple v2, §§2, 9–10](https://arxiv.org/html/2607.13531v2) | Authors report an extensible Lean CRN framework, agent-assisted formalization and explicit axiom auditing | Do not claim the first agent-built formal biology library. Its v2 also retracts an alleged error in a published proof that was actually an error in its own formalization—a particularly relevant warning. |

The latter examples do not independently establish the quality of every claimed proof. They are nevertheless enough to prohibit a confident first-library claim. A narrower finite-domain intervention checker can still be useful. **The observation that domain geometry restricts unstable wavelengths is classical; this particular example is a checked illustration, not a newly solved biological problem.** For example, a recent primary treatment explicitly distinguishes the discretized finite-domain dispersion relation from its infinite-domain limit. [General conditions for Turing and wave instabilities, 2023](https://link.springer.com/article/10.1007/s00285-023-01870-3).

## 4. The commons mechanism must survive the existing negative result

[LEGO-Prover](https://arxiv.org/abs/2310.00656) already proposes growing libraries of verified lemmas. [LeanAgent](https://arxiv.org/abs/2410.06209) already develops a dynamic knowledge database and lifelong theorem proving. The public [Prove Together site](https://provetogether.ai/) explicitly describes agents sharing Lean-checked lemmas in a common ledger; I inspected its advertised workflow, not its operational performance. “Agents reuse one another's proofs” is therefore an established architecture, not the novelty claim.

More seriously, **Berlot-Attwell et al. directly challenge the claimed mechanism**. Their LEGO-Prover re-evaluation finds no direct reuse in final checked proofs and evidence against soft reuse. The one apparent name-reuse event in a reported run was removed during proof repair. They estimate substantially greater computation per attempt and find the headline advantage disappears after compute adjustment. This is a study of that implementation, not a proof that reusable libraries cannot help. [LLM Library Learning Fails, 2025, §§4.3–5](https://arxiv.org/html/2504.03048v1).

The refinement's “pooled information cannot reproduce proved lemmas” is false as a general claim: a serial agent can write, check, retain and reuse lemmas too. Likewise, more context is not guaranteed to improve an LLM forecast. Neither task has a guaranteed winner.

**Required comparison, if claiming a collective benefit:**

1. Parallel agents with a shared evolving verified library.
2. The same parallel agents with private evolving libraries: this isolates sharing.
3. A sequential agent with a persistent verified library and the same total generation/tool budget: this tests the collective against an adequate single-agent control.
4. Ordinary deterministic tactics/schema instantiation on the same frozen initial library: this measures whether agents add anything on these tasks.

Give all arms the same initial Mathlib, source material and theorem targets. Count library construction, failed attempts, reviewer calls and tool outputs in the budget; report checker time and wall time separately. Equal tokens alone do not equalize cost across different models, so initially keep the model fixed. Shared-versus-private is a valid ablation, but does not by itself show superiority to the persistent serial arm.

Freeze target statements and allowed imports before running. The worker must not weaken a statement, assume its conclusion, or choose which successful targets to report. Split by genuinely distinct theorem/model families, not merely substituted constants. Keep failed goals in the denominator.

Measure cross-author reuse from proof-term constant dependencies, with artifact hashes and timestamps. An imported file or a cited lemma name is not proof of use. Removing a needed declaration and seeing compilation fail shows a dependency, not a measured reduction in solving cost; a budget-matched replay without the shared artifact supplies the causal comparison. Count new parameter instances separately from new general results. No success claim should rest on hundreds of one-line applications of a single schema.

## 5. Lean does not make extraction errors unable to propagate

An extractor can replace a finite-domain claim by a continuum condition, omit a boundary condition, or strengthen an assumption until the statement is easy. Lean may correctly prove the resulting, wrong-target statement. **Formal validity, source correspondence and empirical applicability are separate checks.** Delete “feedstock whose errors cannot propagate.” Replace it with:

> Delphi supplies candidate claims. We check their source correspondence, formalize explicit assumptions, and let Lean check the resulting mathematical implication. Biological validity remains a separate empirical question.

Compilation alone is insufficient: Lean accepts declarations containing `sorry` and custom axioms. Require fixed target types, an axiom/dependency audit, trusted imports, non-vacuous assumption examples and model-law mutants. Do not describe the compiler as an unfakeable oracle of biological truth.

Our current `turing_scope/lean/TuringScope/Basic.lean` explicitly says the Routh–Hurwitz eigenvalue equivalence, real-root intermediate-value argument, PDE dynamics and nonlinear patterns are **not formalized**. The checked artifact proves integer determinant/trace formulas, unbounded mode-tail inequalities and an instance of domain dependence. The correspondence from the Neumann PDE to these arithmetic mode conditions remains documented mathematics plus numerical cross-checks. Preserve that boundary on the slide unless new proofs actually close it.

Mathlib is an enabling dependency, not a scientific milestone. Its [official installation instructions](https://leanprover-community.github.io/install/project.html) support `lake exe cache get`; use a pinned compatible cache before deciding a full rebuild needs 128 CPUs. Installing it does not automatically supply the missing spectral/PDE theorem, and core Lean's expressiveness is not limited to rational algebra—developing the missing library from scratch is simply impractical here. Avoid importing all of Mathlib when a smaller dependency closure suffices.

## 6. Diversity prediction theorem: exact slide language

For a resolved binary outcome y, predictions p_i, nonnegative weights w_i summing to one, and their arithmetic pool p̄ = Σw_i p_i:

`(p̄ − y)² = Σw_i(p_i − y)² − Σw_i(p_i − p̄)²`.

This follows by expanding the squares; it holds pointwise and after averaging the same questions. **It needs no independence or unbiasedness assumption.** Page's exposition describes the mean-individual-error decomposition. [Page, Making the Difference](https://depts.washington.edu/ctu/wordpress/wp-content/uploads/2019/07/Making-the-Difference_Applying-a-Logic-of-Diversity_Page_AcadMgtPerp-2011.pdf).

Exact rational check performed here: y=1, predictions 0.9 and 0.1 give mean individual Brier 0.41, diversity 0.16, and pooled Brier 0.25. The best individual has Brier 0.01. Thus the identity holds while the crowd is much worse than the best. Replacing 0.1 with 0.8 reduces diversity to 0.0025 and improves pooled Brier to 0.0225. Increasing diversity alone does not guarantee improvement because individual error changes too.

Use on the slide:

> For an arithmetic probability pool, Brier loss equals weighted mean member loss minus weighted prediction variance. This guarantees improvement over the weighted mean member loss, not over the best member. We measure the latter separately.

Limits: this is not the same decomposition for log loss, a median, an LLM's synthesized verdict, or a market price without a defined arithmetic pooling rule. Log loss has its own convexity inequality, not this variance identity. The Brier identity does not establish calibration, learning, causality or biological truth. Verifying it numerically is an implementation check, not experimental evidence of emergent capability. Preselect a best-single baseline on validation data; label a test-set hindsight best as an oracle comparator. Keep formal, simulated and empirical strata separate.

## Recommended entry wording and kill gates

**Proposed wording, conditional on delivered outputs:** “Delphi turns a literature claim into a checked model decision: show the missing assumption, propose a small repair, and return a reusable proof plus an independent simulation receipt. We test whether agents sharing verified results do this better at the same budget.”

- [ ] One source-pinned claim changes a real request's verdict and a useful repair.
- [ ] The exact checked theorem, its unproved correspondence obligations and numerical scope are visible.
- [ ] At least one independent nonlinear check tests the repair with a convergence criterion; it remains simulated.
- [ ] The claimed reuse appears in proof dependencies and improves a prespecified outcome against adequate controls, or is reported as a null.
- [ ] The story names its closest predecessors; no first-library, solved-biology, guaranteed-collective-win or thresholding-as-novelty claim.

This supports a credible systems contribution. It does not yet establish an investible moat or a winning entry. A narrower useful result is preferable to claiming to have built all of formal mathematical biology overnight.

## Access and reproducibility record

ProteinGym's PMC page became a browser challenge; the public Jina fallback was inaccessible through the web tool; the official NeurIPS PDF succeeded. The 2017 systems-biology PMC page similarly challenged access; the authors' institution-hosted PDF succeeded. Halawi's v2 HTML was unavailable; v1 HTML was read. FLIP2's PDF exceeded the web tool's size limit; it was downloaded directly and read with `pdftotext -layout` under a bounded scope. Its SHA256 is `d0e61ca27863c023adddcc225a3e4af1718f2e3fdfe3642bef89c24c93621a17`, 16,409,080 bytes; the local reading copy is under `/data/artifacts/delphi-evolve-rethink/primary-prior-art/`. No downloaded paper is committed or redistributed here. LEGO-Prover's author-hosted PDF returned 404; the arXiv abstract and the replication's full text were read instead.
