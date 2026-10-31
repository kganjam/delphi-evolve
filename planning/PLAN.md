# Darwin's Bridge — Delphi Evolve

Selected build plan, 30 October 2026, Seattle PDT. A new repository and a 24-hour build, not a continuation of MorphoSwarm's backlog. Working product name; not a trademark clearance.

## The bet

**Biology's next design tool should tell us which change to make, which claim that decision depends on, and which experiment could prove it wrong.**

Our first problem: can we improve an enzyme through a sequence of mutations without passing through a functionally broken intermediate? Build an interactive evolutionary route planner on a real, experimentally measured enzyme landscape. Give every route an evidence trail and a machine-checked conditional certificate. When the evidence cannot support a route, recommend the next measurement instead of inventing confidence.

The demo is a small, real step toward text-to-biological-function. It is not text-to-organism, a new organism, a wet-lab result, or a proof of Darwin. The initial system is **TrpB**, tryptophan synthase beta-subunit, using Johnston et al.'s published combinatorial measurements. Cellular growth in that assay is a proxy for function; it is not a purified-enzyme catalytic constant or a universal fitness measure.

## Why reset

MorphoSwarm's GOAL spans eleven biological scales, model extraction, CAD, inverse problems, formalization, distributed computation and a scientific publication platform. The specifications contain useful scientific discipline. They do not make those capabilities real. SPEC-079's historical demo record explicitly reported zero candidate solutions. The current repository has much more infrastructure than one person can communicate or independently validate in a three-minute pitch.

Keep the useful constraints: observation/simulation/assertion separation; content-addressed evidence; held-out tests; uncertainty; anti-vacuity; claim reuse. Replace the universal product with one experiment whose outputs fit on one screen. No general-purpose registry, task market, eleven-scale UI or new orchestration framework.

## Twenty ideas

These are editorial judgments about this deadline, not measured rankings. The gate is a real artifact plus a falsifiable comparison; sponsor compatibility is a tie-breaker.

| # | Idea and tangible output | Scientific/commercial value | Main 24-hour risk | Decision |
|---|---|---|---|---|
| 1 | **Darwin's Bridge:** measured enzyme landscape, mutation routes, conditional certificates, next-assay selection | Evidence-to-intervention wedge for enzyme teams | Existing MLDE is strong; must demonstrate a precise contribution | Top 3 |
| 2 | **Pattern Surgeon:** choose an intervention distinguishing Turing from mechanochemical pattern formation | Causal developmental biology; beautiful PDE visual | Real perturbation data, identifiability and parameter fit may not be obtainable | Top 3 |
| 3 | **Claim-to-Experiment Exchange:** Delphi disagreements become executable tests and ranked experiments | Directly strengthens Delphi; reusable scientific infrastructure | A graph browser without a decisive scientific case repeats v1 | Top 3; incorporated into #1 |
| 4 | **Glow by Design:** GFP mutation combinations with fluorescence uncertainty and route planning | Visually memorable benign protein engineering | Sparse landscape; predicted brightness cannot be rendered as an observed image | Top 10; fallback |
| 5 | **Wound Closure Controller:** infer motility/proliferation from microscopy, choose distinguishing intervention | Useful mechanobiology assay design | Image access, segmentation and confounding; no wet-lab validation | Top 10 |
| 6 | **Cell Jamming Map:** infer tissue phase transitions and perturbation sensitivity from cell tracks | Connects Thompson to modern mechanics | Domain expertise and real force/shape annotations | Top 10 |
| 7 | **Regeneration Experiment Planner:** compare bioelectric and biochemical hypotheses in planaria | Grand, understandable developmental question | No trustworthy multiscale prediction in one day | Defer |
| 8 | **Organoid Recipe Auditor:** evidence-backed recipes and missing causal links | Valuable repeatability problem | Protocol heterogeneity, private data and no overnight culture | Defer |
| 9 | **Living Material Designer:** infer microstructure-to-mechanics and propose printable scaffold | Attractive materials company wedge | A rendering or predicted modulus is not a manufactured material | Top 10 |
| 10 | **Protein Scaffold Lab:** BioNeMo-designed benign binders to organize cell-free materials | Strong sponsor fit and design artifacts | Structure confidence does not establish binding or material function | Defer |
| 11 | **Metabolic Rescue Atlas:** model nutrient/enzyme interventions against measured auxotroph growth | Concrete molecular-to-cellular causal bridge | Model/data condition alignment; established flux methods | Top 10 |
| 12 | **Evolution Under Changing Environments:** find robust routes across multi-condition landscapes | Industrial robustness and theory of adaptation | TrpB's main dataset cannot supply missing environmental measurements | Defer; expansion only |
| 13 | **Thompson on Trial:** test allometric laws across modern morphometric datasets | Excellent public narrative, reusable claim tests | Descriptive regressions are unlikely to distinguish mechanisms | Top 10 |
| 14 | **Darwin's Exceptions:** test biogeography claims against modern occurrence records | Real corrections to historical claims | Sampling/taxonomy artifacts; weak intervention product | Defer |
| 15 | **Turing Inverse Compiler:** target pattern to feasible reaction parameters | Compelling visual design; formal stability conditions | Known textbook system and self-generated validation | Defer unless real data |
| 16 | **Circadian Reset Planner:** choose pulses robust to uncertain oscillator parameters | Clinically interesting control problem | Human extrapolation and validation beyond event scope | Defer |
| 17 | **Minimal Gene Circuit Contract:** compose motifs with formal dynamic guarantees | Credible Lean and synthetic biology wedge | Small examples risk being symbolic demonstrations only | Defer |
| 18 | **Evolutionary Replay Court:** re-run famous experimental evolution claims and expose failure regimes | Honest, useful reproducibility product | Less visually compelling and needs a design decision | Merge into #1 |
| 19 | **Cell Fate Counterfactuals:** interventions on public single-cell perturbation data | High-value discovery application | Causal ambiguity, data volume, inference time | Defer |
| 20 | **Formal Model Red Team:** automatically discover where published biological models break | Valuable simulation validation layer | Needs a real externally useful repaired model | Top 10; incorporate critic |

## Ten, then three

The ten survivors are **1, 2, 3, 4, 5, 6, 9, 11, 13, 20**. #12 is strategically attractive but loses its place to #13 because a second condition is not yet established.

| Finalist | What would make judges care | What we can actually show | Why it wins/loses the choice |
|---|---|---|---|
| Darwin's Bridge | AI proposes a promising protein change; another agent exposes a bad intermediate; evidence and proof force a better decision | Real assay values, a navigable sequence landscape, leaked-label-resistant experiment, certificate and counterexample | Best combination of real data, GPU relevance, mathematical rigor and investible wedge |
| Pattern Surgeon | Two mechanisms make the same stripe; one intervention makes them diverge | Gorgeous simulator and a proposed distinguishing experiment | Stronger morphogenesis story, weaker guaranteed empirical validation in this window |
| Claim-to-Experiment Exchange | Historical scientific claims become actionable, reusable measurements | Delphi claim → precise hypothesis → executed test → evidence bundle | Useful substrate, but needs #1 as the decisive demonstration; do not ship it alone |

**Selected: Darwin's Bridge, implemented as Delphi Evolve — query to certify.** Fold #3 and the adversarial aspect of #20 into it. Keep #2 as the next scientific vertical, not an overnight parallel product.

## What is new, and what is not

Directed evolution, epistasis, fitness landscapes, ESM, Bayesian optimization, graph reachability and nanopublications are established. Existing work already studies indirect adaptive paths and ML-guided enzyme optimization. We must cite Johnston 2024, Wu 2016, FLIP2 and relevant MLDE/active-learning work. Do not announce discovery of epistasis, a new fundamental law, or the first protein design agent.

The proposed contribution is **query-to-certify: assay selection aimed at settling a path/cut decision, with decision certificates linked to empirical scope and reusable claims**, evaluated on whether they prevent unsupported interventions and reduce the measurements needed for a justified decision. A route is accompanied by its weakest evidential step; uncertain steps become assay requests; an independent critic can supply a counterexample or a cut. All of that returns to Delphi as machine-readable evidence. This combination is a proposed systems contribution, not an established first-ever novelty claim.

An empirically useful negative result is possible: the collective may fail to beat a strong single policy; a foundation-model prior may degrade selection; no robust path may be supported at the chosen threshold. Report it. A measured answer to a narrow research question is stronger than a fabricated victory over a grand one.

## Scientific contract

1. Fetch the authors' original dataset. Record URL, retrieval date, SHA256, license, assay context, reference sequence and residue coordinates. Count observed, missing, censored and imputed rows separately. Never import a completed benchmark table and silently call its imputed rows measured.
2. Freeze a manifest before the main benchmark. Separate exploratory full-data route visualization from predictive/replay evaluation. The former is descriptive; it cannot demonstrate prediction.
3. Retrospective assay-budget replay: start each policy from the same admissible observations and seed; hold the same assay budget. An oracle alone exposes newly requested measured rows. Log every query. No hidden labels or global ranking in policy inputs, prompts, evidence caches or choice of favorable starting points.
4. Compare random search, greedy measured-neighbor walk, additive regression, an epistasis-aware baseline, and the proposed collective. Add foundation-model prior versus no prior. Aim for 20 fixed seeds; report paired outcomes, uncertainty and all seeds. Scale computation down before reducing scientific controls.
5. Primary outcome: assays needed to issue a correct open/blocked certificate for prespecified start/target pairs, with abstention and false-certification rates at a fixed budget. Use survival-style summaries or explicitly censored outcomes for unresolved cases, never exclude them. Secondary: best observed assay score, bottleneck score, route length, runtime and cost. Compare random, greedy and uncertainty acquisition as well as a strong non-agent query-to-certify policy. Fix targets using training information or published biology, never the held-out top percentile. The benchmark truth is finite measured-graph reachability under a declared assay/noise model, not biological truth.
6. Mathematical certificate: for genotype graph G and intervals [L(v), U(v)], accepting an edge only when L(v_next) >= U(v_current) implies nondecreasing fitness for every assignment inside all those intervals. Prove it for arbitrary routes, and connect a decidable checker to that property. Also prove that a separating cut with no admissible outgoing edge rules out a path in the declared graph.
7. Unknown nodes/edges stay possible in any negative certificate: absence of measurement is not evidence of no path. A certificate restricted to a measured subgraph says so prominently. Finite four-residue graph completeness never implies impossibility in the full protein sequence space. Two replicates alone do not justify simultaneous 95% bounds across 159,129 variants. This theorem assumes interval containment; it does not prove the empirical intervals contain reality. If assay replicates cannot support intervals, use point-value certificates labeled descriptive and a sensitivity parameter labeled assumed error bound. Do not manufacture confidence levels.
8. Formal status requires original compilation, no sorry/admit/unjustified axioms, a statement correspondence note, actual dataset-linked instance, and a mutation that changes the scientific condition and is rejected. Graph statements must not merely prove arithmetic constants.
9. Novel designs are proposals until measured. Retrospectively recovered variants were already assayed in the source study, not new discoveries. Sequence → assay growth spans a measured molecular/cellular bridge; organism and tissue predictions remain absent.
10. Unresolved historical claims stay unresolved. A Darwin statement about domestic breeds is motivation, not a theorem about four enzyme residues. Record the modern operationalization as a new claim linked by motivation/analogy, never equivalentTo without justification.

## Product and demo

One screen, three aligned views:

- **Landscape:** measured genotypes and single-mutation edges; distinguish observed, predicted and unknown visually. A 2D/3D layout is a projection, not molecular geometry or a physical energy surface.
- **Decision:** start and target, route, weakest step, required assay and explicit assumptions. A threshold slider changes the graph and can invalidate the certificate.
- **Evidence:** source assay, raw row, model comparison, Delphi claim, proof receipt, and downloadable nanopub draft. Clicking a step must change the evidence shown.

The visual climax: an attractive route breaks when its weakest assumption is challenged. The collective either repairs it using real evidence or asks for a measurement. The audience sees why the proof and the evidence both matter.

Runtime specialists exchange immutable evidence messages: a literature/claim specialist proposes an operational hypothesis; a data specialist controls admissibility and oracle access; a model specialist predicts; a route specialist chooses queries; a critic challenges assumptions/certificates. Build-time coding workers alone do not establish decentralized agency. Record actual decisions, information boundaries and response to challenge. Compare shared-evidence and isolated specialists under matched budgets; if a central coordinator prescribes all decisions, describe that honestly.

## Reuse and integration

Read MorphoSwarm GOAL, backlog, SPEC-001, 009, 026, 077–079, goal-status, winning-plan, Delphi MCP research and Nebius compute instructions. Selectively adapt small tested modules only after inspecting dependencies; retain Apache notices. Do not copy the whole application or its thousands of tasks.

Independent local CSV audit counted 193,170 source rows, 159,129 measured non-stop genotypes and 871 imputed genotypes with zero overlap. CaltechDATA API metadata declares CC0 1.0. Use unnormalized growth columns for predictive work: source max-normalization can leak hidden-label information. Scout exploratory full-data statistics are not benchmark results.

Delphi's hosted MCP was called live: local overview reports 880 claims across five domains and draft assessments. Local/network differ; preserve provenance. Query specific relevant claims, preserve disagreement, and link new operational claims and result objects. A model's truth rating is an elicitation, not a posterior likelihood. Do not multiply correlated reviewer opinions or re-count the same paper as independent evidence. Publish-ready TriG is the minimum; public-network status requires actual submission, resolution and validation. No fake trusty URIs or invented scientist identities.

## Resources and limits

| Resource | Useful job | Limit / fallback |
|---|---|---|
| Claude Max | Three or more independent implementation workers and an integrator; Sonnet first | Use available subscription quota; no manual reset grants or unlimited API spend |
| Nebius H100 | Batched protein embeddings/inference, GPU surrogate evaluation if warranted | User amendment Oct31: up to 10 H100s for our team while others are not queueing; bounded sharded jobs, preserve outputs, yield capacity when other teams request it; never cancel others |
| BioNeMo | ESM2 inference as a tested representation/prior baseline | Verify actual BioNeMo invocation; ordinary ESM2 is labeled ordinary ESM2 |
| NVIDIA Brev | Dedicated GPU fallback or extension | Total authorized credits $150; reserve $30, stop before cap; check live hourly rate and terminate our own idle instance |
| OpenResearch | Literature-grounded experiment project and run ledger | Use official alphaXiv CLI, record actual experiment; do not substitute an unrelated similarly named service |
| Nebius scientific workspace | Optional model/structure jobs | Team API key may be absent; do not make the core dependent on access |
| CPU host | Graphs, small regressions, Lean, website | Task/process/memory caps; no training large models here |

Do not spend compute for sponsor logos. GPU max means productive bounded jobs. User permits up to 10 H100s while others are not queueing; return capacity when they do. CPU capacity and Nebius LLMs may also be used for useful measured work. No model pretraining. No structure-as-function claim. A null result from a sponsor model is a valid result.

## 24-hour execution and kill gates

T0 is kickoff; actual wall-clock timestamps belong in STATUS.md. Internal deliverable deadline T0+24h, with a deployable version at T0+18h. Official site says slides due Sunday Nov 1 at 1pm in Boston; interpreting venue time yields **10am PST (UTC−8)** in Seattle, after the DST transition. This is separate from our internal deadline.

- [ ] H0–2: original data downloaded and audited; exact assay semantic contract; tiny route computed; all workers active.
- [ ] H2–6: data loader, sparse graph, measured baseline, first Lean checker, first real screen. Kill gate: absent real data means switch to audited GFP; no switch merely to improve a disappointing result.
- [ ] H6–10: budgeted replay and strong baselines, evidence events, Delphi import, initial GPU run. BioNeMo setup gets at most two hours before explicit fallback.
- [ ] H10–14: complete ablations, uncertainty/sensitivity results, mutation proof checks; no new product scope.
- [ ] H14–18: results integrated into site, draft nanopubs validated, CLI/API another team can run, replay video and slides.
- [ ] H18–22: fresh checkout reproduction; leakage and claims audit; factual blog, 3-minute pitch rehearsal, fallback recording.
- [ ] H22–24: freeze scientific results, verify links and artifacts, package submission. Leave actual human presentation/submission steps explicit if no submission credentials exist.

## Pitch and venture

**Opening:** “A protein design is not a plan. Which mutation do you make first—and what evidence says the next step will still work?”

**0:00–0:25:** Show a tempting route and its bad intermediate. **0:25–1:15:** specialists disagree; reveal the measured row, fix the route or request the missing experiment. **1:15–1:50:** measured benchmark against strong baselines, including negative outcomes. **1:50–2:20:** open the conditional Lean certificate and the mutation that fails; connect to the Delphi claim. **2:20–2:45:** another agent can reuse the evidence bundle; show actual reuse if achieved. **2:45–3:00:** “From scientific claims to experiments we can justify. Enzymes first; biological design next.”

Commercial hypothesis: enzyme engineering teams, industrial biotech labs and CROs pay for fewer wasted assays and auditable experiment choices. The initial product is a decision/evidence layer above existing protein models and lab workflows, not a competing foundation model. Measure cost per validated improvement and time to a defensible decision in a pilot. Market size, willingness to pay, prospective wet-lab uplift and defensibility remain unvalidated. A company-worthy moat would be prospective intervention/evidence datasets and workflow adoption, not the use of Lean or a public knowledge graph alone.

Why competitive: one understandable consequential task; real data; adversarial specialist coordination; a matched-budget collective comparison; useful reusable evidence; a live visual demonstration. The rubric gives 45% to decentralized agency plus collective capability, so a pretty simulation cannot carry it alone. The official page confirms a +10 collaboration bonus, not a general sponsor-use bonus. Winning is a hypothesis, never a promised outcome.

## Sources and read scope

- https://scienceclawhack.ai/ — judging and schedule read live; weights 20/25/20/25/10, collaboration +10.
- https://github.com/fractastical/delphi — redirected from delphisci; README and MCP README read; live local overview/search called. No wholesale upstream code reuse without license review.
- https://raw.githubusercontent.com/fractastical/delphi/main/mcp/README.md — local/network distinction and unpublished truth scores.
- https://doi.org/10.1073/pnas.2400439121 — original TrpB study; exact data files audited in the data scout report.
- https://elifesciences.org/articles/16965 — known protein adaptation through indirect paths; prior art, not our discovery.
- https://flip.protein.properties/ — current TrpB benchmark/split context.
- https://pmc.ncbi.nlm.nih.gov/articles/PMC11739421/ — ALDE, Nature Communications 2025; direct competing optimization approach, not a method to relabel as new.
- https://data.caltech.edu/records/h5rah-5z170 — primary CC0 dataset; original files retrieved and counted.
- https://github.com/soldatmat/PELLM — adjacent embedding-space Bayesian optimization; inspect before claiming novelty.
- https://arxiv.org/abs/2604.22611 — recent theory of sign epistasis and evolutionary detours; no claim of inventing this connection.
- https://github.com/alphaXiv/OpenResearch and https://openresearch.sh/docs/experiments — official research workspace and run records.
- https://nvidia-bionemo.github.io/bionemo-recipes/main/recipes/models/esm2/ — actual BioNeMo integration target.
- Local resource guide: /home/ubuntu/git/scienceclaw-hackathon-ideas/resources/research/nebius-compute.md.

Scouts' reports are leads until checked. Final results and spend belong in the new repository's run manifests, not in this planning document.
