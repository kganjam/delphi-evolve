# Company hypothesis — Darwin's Bridge / Delphi Evolve

Written 31 Oct 2026, Seattle PDT. Everything below is a **hypothesis to test**, not a finding. No customer, letter of intent, revenue, market size or willingness to pay exists or is claimed. Nobody has been contacted; the outreach text is a draft in `docs/outreach-draft.md` and was not sent.

## What exists today, and what does not

| Today (observed in this repository) | Not yet established |
|---|---|
| A retrospective engineering tool on one public landscape: four-residue TrpB, 159,129 measured variants (Johnston et al. 2024, CC0). It plans single-substitution routes under an *assumed* noise bound, names the weakest step, and emits a Lean-checked certificate for a route under that assumption. | That any enzyme team would change a purchasing or experiment decision because of it. |
| A retrospective assay-budget replay comparing assay-selection policies on already-measured labels (see the deck, slide 4, for the numbers actually produced; negative comparisons are reported there too). | That the replay's saving transfers to a lab's own assay, noise, cost structure or a different protein. The replay is simulation over measured rows, not new wet-lab measurement. |
| Reusable evidence objects: a JSON demo file, unsigned nanopublication drafts, a Delphi claim record. | That anyone outside this team has reused them. Reuse must be observed, not claimed. |

Prior art, so the pitch does not overreach: active-learning-assisted directed evolution (ALDE, Nat. Commun. 2025, <https://pmc.ncbi.nlm.nih.gov/articles/PMC11739421/>) already benchmarks on TrpB and GB1 in simulation and ran a wet-lab protoglobin campaign; query-efficient path evaluation and certification is established in robotics planning (LazySP, Dellin & Srinivasa 2016, <https://www.ri.cmu.edu/pub_files/2016/3/paper-lazysp.pdf>; Bayesian Active Edge Evaluation, Choudhury et al. 2018, <https://ijcai.org/proceedings/2018/679>). What this project assembles is an *assay-decision, evidence and formal-checking system on real enzyme data*, evaluated on one landscape. It is not a new fundamental algorithm and not a first.

## Buyer, first

**Hypothesised economic buyer:** the head of protein/enzyme engineering (or the R&D director who owns the variant-screening budget) at an industrial-biotech or biocatalysis group that already runs design–build–test rounds on a plate- or sequencing-based assay. Secondary: a contract research organisation that sells variant campaigns and wants to defend why it chose each round.

**Hypothesised user:** the protein engineer or computational biologist who today picks the next round of variants from a model ranking plus judgement.

**Hypothesised pain:** each round's variants are chosen from a prior or a predicted ranking, and nobody can say afterwards which unmeasured step the decision depended on, or whether the same budget could have settled the question with different assays. A purchase would be justified only if the tool shortens time-to-decision or lowers assays-per-decision for a lab's *own* project.

**What would make the hypothesis wrong:** labs already have a good enough internal process; the decision "is this route open?" is rarely the bottleneck; labs' assays are too noisy or too sparse for interval-based reasoning; or the benefit disappears outside combinatorial landscapes. Discovery interviews and the pilot below are meant to expose these.

## The product, narrowly

A decision-and-evidence layer *above* the protein models and lab workflow a team already has — not a competing foundation model. Input: a lab's measured variants plus replicate or noise information. Output per proposed route: the weakest evidential step, the assumption it depends on, the next assay that could settle it, and a machine-checkable certificate conditional on a stated, labelled assumption. The certificate guarantees the logic given the assumed intervals; it does not guarantee the intervals.

## Pilot design: prospective validation with a cost and time-to-decision endpoint

Purpose: convert "retrospective engineering tool" into evidence about a wet-lab advantage — or learn that there is none.

* **Partner:** one enzyme-engineering lab with a completed combinatorial or multi-round campaign on a screening assay (the "history"), and a new target for which it will run further rounds. Ask: one lab, one prior dataset, one prospective round. *Not contacted.*
* **Pre-registration (before any prospective assay):** the decision rule, the assumed noise bound and how it is chosen (from the lab's own replicates, not tuned afterwards), the stopping rule, and the endpoints below. The pilot's value comes from fixing these first.
* **Design:** same assay budget for both arms on the new target — (a) the lab's usual way of choosing variants, (b) tool-guided selection. Assignment of target/sub-campaign to arm decided and recorded before results. Small-n; report all outcomes including unresolved ones, no post-hoc exclusion.
* **Primary endpoint:** wall-clock days and total assay cost to reach a *pre-registered, defensible go/no-go decision* on the target (route opened or ruled out under the pre-registered rule, or an explicit abstain). **Secondary:** assays per decision; best measured activity at budget; false-certification events scored against later full measurement where available; engineer-hours.
* **What counts as failure, stated in advance:** no reduction in cost or days against the lab's usual arm, or a certified decision later contradicted by measurement. A failure is reported as the result.

## 120-day milestones

| Days | Milestone | Evidence produced |
|---|---|---|
| 0–30 | Partner agreement (data terms, confidentiality); pre-registered protocol and endpoints; lab's history loaded and audited exactly as the public TrpB data were (counts, replicates, missing vs imputed). | Signed protocol; data-audit receipt. |
| 31–60 | Blind retrospective replay on the lab's own history: policies start from a frozen early subset and pay an oracle for later rows. | Replay table on the lab's data, including where the tool does not help. |
| 61–100 | Two prospective rounds under the pre-registered rule, tool-guided vs lab-usual, equal assay budget. | Round logs; assays, cost and days recorded at the time. |
| 101–120 | Readout against the pre-registered endpoints; decision memo; go / no-go on a paid second engagement. | Pilot report with all outcomes; public or partner-approved evidence bundle. |

Budget and staffing for this plan are **not estimated here**: any figure would be invented. They should be fixed with the partner in days 0–30.

## Moat hypothesis

Not Lean, and not a public knowledge graph alone — both are replicable. The defensible asset, if the pilot works, is **prospective intervention-and-evidence data** (which decisions were made on which evidence, what was later measured) and **workflow adoption** inside labs' decision routines. Both are unproven and only the pilot can start to create them.

## Distinguishing present from future in every claim

* Say "retrospective" for anything computed from the published landscape; say "prospective" only for pilot results that exist.
* "Fewer assays" is a replay result on one landscape until a lab's own prospective data say otherwise.
* "Certified" always carries its assumption ("under an assumed noise bound κ") and its graph scope (measured four-residue subgraph).

## Ambition

Biologic design starts with justified enzyme experiments. This project does not build, claim or imply text-to-organism design; the nearest real step is a measured sequence → assay-growth bridge on one enzyme, with decisions that carry their evidence.
