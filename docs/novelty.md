# Novelty boundaries and honest comparison

Written 31 Oct 2026, Seattle PDT, by the experience worker. Sources were read from the pages cited below on that date; where only an abstract or a fetched summary was available, that is stated. This file limits claims; it does not argue for a win.

## What is already established (we claim none of it)

| Topic | Established work | Notes |
|---|---|---|
| The TrpB four-site landscape itself, epistasis, local optima, path accessibility, simulated directed-evolution strategies | Johnston et al., *PNAS* 121(32):e2400439121 (doi 10.1073/pnas.2400439121; data CC0 at doi 10.22002/h5rah-5z170) | The paper reports 520 local optima among active variants (5.3%), analyses how much fitness loss routes to the top variant must tolerate, and compares simulated directed-evolution approaches. **Route accessibility analysis on this exact table exists.** |
| Active-learning-assisted directed evolution | ALDE, *Nature Communications* 2025 (PMC11739421) | Wet-lab campaign on a protoglobin (five residues). Computational simulations on **both GB1 and TrpB** four-residue combinatorial datasets: 96 random starting variants, four rounds of 96, averaged over 70 random initialisations; compares encodings (one-hot, ESM2) and model classes with calibration analysis. It reports no path/reachability decision and no formal certificate. |
| Sequence-to-fitness benchmarks | FLIP and FLIP2 (flip.protein.properties) | FLIP2 adds TrpB sub-landscapes (about 228k variants over 10 sub-landscapes; a different table from the four-site set) and 16 splits. Evaluates predictors (Spearman, NDCG), not assay decisions. |
| Indirect adaptive paths and sign epistasis | Wu et al., eLife 2016 (e16965, GB1); Ribeca et al., arXiv:2604.22611 (April 2026): proof that simple sign epistasis is associated with evolutionary detours, plus analysis of experimental landscapes | Our 5/6/7-step detours are instances of this phenomenon, not a finding about it. Only the abstract-level statement of Ribeca et al. was read. |
| Selecting expensive evaluations to settle path feasibility on a graph | Dellin & Srinivasa, *LazySP* (2016, https://www.ri.cmu.edu/pub_files/2016/3/paper-lazysp.pdf); Choudhury et al., *Bayesian Active Edge Evaluation on Expensive Graphs*, IJCAI 2018 (https://ijcai.org/proceedings/2018/679) | Primary sources read by the coordinator, not by us. **Query-efficient path finding and decision-region determination are established.** Our `q2c` policies are an instance of the idea on an enzyme-assay graph, not an invention of it. |
| Embedding-space Bayesian optimisation for proteins | PELLM (github.com/soldatmat/PELLM) | Listed in planning/PLAN.md as adjacent; **not inspected by the experience worker**, so no comparison is made. |
| Nanopublications, PROV, interval arithmetic, graph reachability | standard | Used, not contributed. |

## What this project built (a systems contribution)

**Query-to-certify:** treat the engineering decision "is there a route / is it cut?" as the object to be certified, and select the next assay to settle *that* decision. Concretely in this repository:

1. a single decision rule (`L(next) ≥ U(current)`) whose assumption parameter is exposed and swept, with the point at which the decision flips reported (for the parent→highest-measured pair in the measured four-site graph, `site/lib.js maxEps`);
2. a three-valued edge status so a negative answer is *no route certifiable* only if it holds even when every unmeasured genotype is allowed to be perfect (overlapping intervals are not admitted, so this is weaker than "every ascending route is ruled out"), and otherwise *undetermined* with the unmeasured genotypes named as assay requests;
3. a conditional machine-checked certificate (proof worker, Lean) whose input is the same table;
4. nanopublication drafts and a Delphi claim record, so the decision links to its evidence and scope.

The retrospective replay is now implemented: original seven policies × 100 episodes, plus four explicitly post-hoc arms × 100 episodes. The original query-to-certify policy resolves 78/100 cases at 1,000 paid assays versus 32/100 for directed frontier search. The shared collective also resolves 78/100: it adds no completion-rate benefit over a single planner. A post-hoc no-GP variant resolves 96/100 at that budget but is worse at 250 assays (16/100 versus 43/100). These results describe this table, this assumed interval model and this panel, not new biology or superiority to ALDE. Source: `artifacts/core/replay/table_primary.csv`; methods and limitations: `artifacts/core/README.md`. A closer LazySP-style baseline is being evaluated separately; no result is claimed here until its run is complete.

Existing Delphi claims also have a separate operational use. The `claim_runtime` adapters bind existing Kimura and Fisher records to explicit applicability conditions and source hashes. A valid request computes; withdrawing a source or requesting an invalid biological transfer refuses. These are hand-authored adapters, not automatic theorem extraction, and their population-genetic calculations are not premises of the TrpB route result. In recorded-request accounting, same-context typed evidence saves exactly as many repeat lookups as ordinary caching. Its additional protection against injected context errors is a software test, not an empirical assay saving. See `docs/claim-reuse.md`.

The distinctive deliverable is this integrated, inspectable chain: a scientific decision, paid information acquisition, an explicit evidence context, a conditional formal certificate, and a refusal when the premises are not available. We make no claim that the individual ingredients or their general combination are first inventions. The company hypothesis requires prospective evidence of reduced experiment cost or time-to-decision.

## Where we would be wrong to claim novelty

* "First" tool for TrpB routes: no. Johnston et al. analysed accessible paths on this table.
* Better active learning than ALDE: unknown. ALDE ran on TrpB; we have not run ALDE or its code as a baseline. If the replay compares against our own greedy/uncertainty policies, it says nothing about ALDE.
* A new epistasis result: no. Sign epistasis and detours are known.
* Proof of Darwin or of "gradual modification": no. See below.
* Interval correctness: the theorem is conditional on interval containment. Two replicates do not provide simultaneous 95% bounds across 159,129 variants. The slider parameter (ε or κ) is an *assumed* sensitivity, not a confidence level.

## Darwin and Delphi: motivation, not equivalence

Delphi (queried live; see `artifacts/evidence/delphi_queries.json`) contains Darwin 1859 claims such as `darwin1859-ch06-08` ("if any complex organ were shown to exist that could not possibly have been formed by numerous, successive, slight modifications, the theory of natural selection would break down; no such case is known") and `darwin1859-ch06-16` ("nature makes no leaps"). Our operational question — *on this finite measured TrpB graph, does a route of single substitutions with every step admitted exist?* — is linked to them only as **motivation by analogy**. It does not test, support or refute them: Delphi's own local assessments of `darwin1859-ch06-08` record "not-empirically-resolvable" (0.118) and "partially-resolvable" (0.362) from two LLM assessors, which are elicited judgments, not probabilities. Delphi's `fisher-ftns` record notes the partial-change theorem is false as a statement about total change under epistasis; that is context for why additive intuition fails here, not a result of ours.

Delphi text searches for "epistasis" and "fitness landscape" returned zero hits in both the local and network sources on 31 Oct 2026. That is a limited title/statement text match and does not show Delphi lacks related knowledge.

## Company wedge (hypothesis only)

Enzyme-engineering teams and CROs that spend assays on variant libraries could use an auditable decision layer above existing models: *which assay settles the decision, which assumption does the answer depend on, and what evidence backs each step*. **Unvalidated:** market size, willingness to pay, customer list, prospective wet-lab uplift, and defensibility. A plausible moat is prospective intervention-and-evidence data and workflow adoption, not the use of Lean or a public graph. The measurable pilot metrics would be cost per validated improvement and time to a defensible decision. No customer or market number appears anywhere in this repository because none has been measured.

## What a reviewer should check

* `site/lib.js` ↔ `evolve/evidence.py` (Python mirror) ↔ core's `evolve/graph.py` ↔ the proof worker's Lean checker implement the same edge rule; `tests/test_evidence.py::test_js_matches_python_mirror` checks the first pair.
* Score definition is core's (raw μ minus per-replicate stop-codon mean), not the source's row-specific `mu_k-bg` or `/max` columns.
* Route and cut statements are about the declared finite graph; absence of measurement is not evidence of absence of a path.

## Added by the integrator (2026-10-31, after the 20-seed replay)

* **Measured behaviour, exploratory arms flagged.** Of the seven pre-specified policies, query-to-certify (GP-priced) certified 0.78 of 100 episodes at 1000 assays against 0.32 for our best-first baseline and 0.21 for random; the shared-evidence collective was indistinguishable from it (difference 0.00). A no-model variant added after the first results reached 0.96 and is exploratory. See `site/data/results.json`.
* **No claim of novelty for the policy class.** Given LazySP and Bayesian active edge evaluation, the defensible contribution is the enzyme-assay setting, the leakage-controlled retrospective replay, the evidence/claim trail and the Lean-checked certificates, together with their measured behaviour — not a new way to choose which edge to evaluate.
* **Calibration is transductive.** The noise bins (replicate-difference SD by read-count bin) are estimated over all 159,129 measured rows before the replay. That is a retrospective sensitivity calibration, not an independently held-out replicate validation, and kappa is an assumed sensitivity multiplier, not a confidence level.
* **Claim reuse is proposed, not established here.** Historical Darwin links are motivation and Fisher is context; deleting Delphi does not change the route planner in the artifacts merged so far. See `docs/claim-reuse.md` only if that worker's tests pass in the integrated tree.
