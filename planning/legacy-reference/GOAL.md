# GOAL

## The vision

Biology is the last major engineering domain without a design stack. Electronics has EDA —
specification, synthesis, simulation, verification, physical implementation, test. Mechanical
engineering has CAD/CAE. Biology has atlases, foundation models and wet labs, but nothing that
turns what is known into **executable mathematical models you can compose, check, and design
against**.

**MorphoSwarm builds that stack, for any organism, at every scale.**

<!-- claims: aspirational -->
*What follows is the goal, not a measured result. Every capability claim in this document
is an open empirical question; G8 is how it gets answered, and SPEC-025 R10 forbids the
word "self-improving" in any results context without a random and a naive-best baseline
and a confidence interval. `scripts/check_claims.py` enforces that mechanically.*

> A self-improving system that discovers, constructs, composes and verifies executable
> mathematical models of living systems — and uses them to design — with evidence, uncertainty and
> *verification level* carried as first-class, versioned, signed, timestamped objects.

### The capabilities

| | | |
|---|---|---|
| **img2sim** | Photograph → model | Take a picture of a sunflower head, a shell, a wing, a biofilm. Get back segmented morphometrics, ranked candidate equation systems, fitted posteriors, a running simulation, and a prediction of something the photograph did not show. |
| **vid2sim** | Video ↔ equations | Match a time-lapse to a dynamical model, and render a model back as a comparable video with a quantified discrepancy field. Fit on an early window, predict a later one that was never fitted — the strongest held-out discipline available. |
| **Deconstruction** | Any natural object → every level | A plant, a shell, a tissue, an insect, a mammal — taken apart at every level we can reach, with the levels we *cannot* reach reported rather than filled. |
| **txt2organism** | Specification → blueprint | Describe an organism or a capability in words. Get back a multi-scale design, molecular through ecological, with every claim's evidence tier and the cheapest experiment that would settle it. |
| **MorphoCAD** | Models → assembly | Compose across eleven levels with typed ports, contracts and CAD-style interference checking, drawing on a library of reusable biological components characterised by what they actually interface with. Designs pass around as diffable files. |
| **A universal surface** | Any tool, one canvas | Viewers, simulators and analysis tools plug in behind one contract — SBML simulators first. 2D, 3D and 4D views with semantic channels, and modality emulation that renders a model as a microscope or a MERFISH run would measure it, so model and data are compared in the data's own domain. |
| **The studio** | All of it, usable | Galleries of natural form at morphoswarm.ai, and one action to take any specimen into a workbench that models it at every level of detail. |
| **The loop** | Design → experiment → better models | Plan, cost and prioritise experiments by expected information gain; absorb results; improve the designs *and* the models that produced them. |

### Growing, not finished

The system is built to accrete. It maintains a ledger of what it can currently do, derives the
gaps from a (taxon × scale × mechanism) coverage matrix, turns those gaps into typed work, and
validates every closure before it counts. What accumulates is concrete: models, solver adapters,
resource connectors, skills, proofs, cached simulations, segmentation priors, selection policies —
and, most interestingly, **compositional rules**: accumulating evidence about which biological
subsystems actually compose, which need adaptation, and which are incompatible.

Formalization runs through all of it. Natural language → symbolic form → Lean 4 → machine-checked
proof → knowledge graph → reuse, with the informal↔formal correspondence recorded as its own
reviewed artifact, because a valid proof of a wrong translation is the failure mode no kernel
catches.

### Every organism, every scale

**Eleven levels** — molecular, macromolecular, subcellular, cellular, tissue, organ, neural,
whole-organism, developmental, collective, ecological — with explicit cross-scale coupling
contracts, approximations declared and uncertainty propagated (SPEC-026).

**Model organisms first, then anything** — *Drosophila*, zebrafish, *Xenopus*, *C. elegans*,
planaria, *Hydra*, mouse, chick, ascidian, plants; and the biomineralising, colonial and social
systems where form is most legible: cone shells, *Turritella*, diatoms, corals, stromatolites,
*Dictyostelium*, *Bacillus* and *Vibrio* biofilms, termites. Progress is measured by an honest
(taxon × scale) occupancy matrix, not by a model count.

## Why this, and not something else

The adjacent categories are crowded and better-resourced: AI-scientist agents (Edison, Biomni),
biomedical knowledge graphs (Causaly), genetic CAD (Asimov), autonomous labs (Ginkgo, Lila,
Recursion), virtual cells (Arc). ScienceClaw and Infinite already own decentralized scientific
coordination and provenance-aware discourse.

We are not competing with any of them, and the differentiator is not "agents" or "a knowledge
graph". It is this: **a system that learns to engineer biology by continually improving its
mathematical understanding of biology** — automated model *synthesis*, model *composition* across
scales, and a verification ladder that records exactly what has and has not been checked. Most
generative biology maps desired molecular function → sequence. We are after desired biological
capability → organism architecture.

A second group appeared in 2026 and sits closer to our substrate than any neighbour above:
agent-native research records (ARA, Symposium, Traxia and four more proposals), a registry of
machine-checked Lean results (Palomar) and open-problem benchmarks (Epoch's, First Proof). Famous
problems were resolved with AI help that year, and the field accepted those results on external
verification or an independently checkable object; that is our bar too, so we offer a candidate
answer until someone else has checked it, and we claim the combination, not any single part. The
record, with the depth each source was read at, is in
[the landscape report](docs/research/ai-science-landscape-2026.md).

### The category, named by someone else

"World models for biomedicine" (Noori, Fishman, Fang, Fesser & Zitnik, *Cell* 189(19):5845–5869,
September 2026, [doi:10.1016/j.cell.2026.08.032](https://doi.org/10.1016/j.cell.2026.08.032) —
checked against Crossref) defines the category we are in, and defines it by **capability rather
than training scale**: a world model represents the state of a system and simulates how it evolves
*under alternative actions*. Their axes are scale (molecular → clinical), affordances
(novel-perturbation prediction, intervention search toward desired states, long-horizon experiment
planning), and obstacles (partially observed state, destructive assays giving snapshots not
trajectories, observational data dominating interventional).

That framing suits MorphoSwarm better than "foundation model" ever did. It is **interventional and
counterfactual by construction**, which is exactly what a mechanistic, unit-checked,
applicability-bounded model is for — and it carries none of the scale-maximalist baggage. All
three of their stated obstacles are arguments *for* mechanistic models with declared validity
regimes, not against them.

**Where we differ, and it is the whole of our contribution: the paper is silent on provenance and
verification.** It says what such a model should *do*, not how anyone would know whether a given
one is trustworthy. That silence is the gap this project fills.

### The record, named by someone else

"Active Scientific Knowledge" (Fırat, SSRN preprint 2026,
[doi:10.2139/ssrn.7416579](https://doi.org/10.2139/ssrn.7416579) — checked against Crossref; the
PDF and its record are in `papers/10.2139%2Fssrn.7416579/`) names the other half of
what we build. The world-model paper says what a model must *do*. ASK says what a scientific
record must *keep* when a machine reuses it: claim, evidence for and against, method, provenance,
scope and epistemic status, travelling together and versioned, with missing capacities shown
rather than filled. Its six activation dimensions are:

- addressability;
- evidential traceability;
- conditional executability;
- version responsiveness;
- context-preserving transferability;
- contestable federation.

Its rule that a machine-proposed structure stays a candidate until data, an analysis or an
accountable person confirms it is already ours (AGENTS.md §1). It also states the choice we made:
*accountable activation* over opaque reconstruction.

**Where we differ from it:** ASK treats verification as one layer of "repeatable checks". We name
the level a result reached and the levels it did not, which the paper does not ask for. Where we
meet ASK and where we do not, dimension by dimension and on the site, is in
[the ASK report](docs/research/active-scientific-knowledge.md). The gaps are backlog rows
M2644–M2653, and M2644 is the page that draws the six dimensions from records. Federation waits
on ADR-0005.

## Non-goals

- **Not** another biological foundation model. We incorporate them; we do not train one.
- **Not** another universal simulator. VCell, PhysiCell, CompuCell3D, BioDynaMo, Chaste, Morpheus
  and tyssue exist. We discover, construct, select, connect, validate and improve models across them.
- **Not** a claim to have invented *Executable Biology* (Fisher & Henzinger, 2006/2007) or
  *Bio-Design Automation* (Densmore et al.). Those are foundations and we cite them as such.
- **Not** a wet lab. We design, predict, cost and prioritise; partners execute.
- **Not** a system that assigns probabilities it cannot justify. A number needs a method and a prior.

## Subgoals

| | Goal | Owns specs |
|---|---|---|
| **G1** | **MorphoIndex** — every model, solver, tool and external resource behind one contract, each with an earned `validation_status` | 000, 001, 002, 014, 023, 044, 066, 071, 073 |
| **G2** | **MorphoCAD** — multi-scale assembly, typed ports, interference checking, component library | 003, 013, 026, 036, 046, 059, 060, 064 |
| **G3** | **Observation → model** — img2sim, vid2sim, and deconstruction of any natural object | 004, 022, 030, 035, 053, 061, 065 |
| **G4** | **txt2organism** — specification to multi-scale blueprint with evidence tiers | 005, 063, 070, 074, 076 |
| **G5** | **Verification** — L0→L5 ladder, the NL→math→Lean pipeline, anti-triviality gate | 009, 034, 041, 043 |
| **G6** | **Knowledge** — entity graph, versioning, identifiers and DOIs, governance, citation, evidence, predictions, causal structure, conformant nanopubs with time anchors, claim search and the evidence API, problem belief graphs, the discovery graph | 007, 008, 015, 016, 017, 018, 019, 021, 031, 040, 045, 049, 050, 051, 062, 067, 068, 072, 077, 078, 080, 081 |
| **G7** | **Swarm** — typed-needs market, multi-VM fabric, credential broker, slot campaigns, VM/skill provisioning | 010, 011, 012, 024, 052, 058 |
| **G8** | **Measurement** — MorphoBench, pre-registered ablation, active learning and its own calibration, the compounding demonstration | 006, 020, 025, 047, 048, 079 |
| **G9** | **morphoswarm.ai** — galleries of natural form, the design studio, the plugin surface, the public API | 027, 028, 029, 033, 037, 038, 039, 042, 054, 055, 056, 057, 075 |
| **G10** | **Growth** — capability ledger, gap queue, content-addressed caches, validated self-extension | 032, 069 |

**The spec column is a copy, and the owner fields are the authority.** Each spec states its goal
in its own `**Owner:**` field, and [`goals/README.md`](goals/README.md) is generated from those
fields by `scripts/sync_goal_index.py`, which a gate checks. Nothing checks this table. Until
2026-10-27 its column named 44 of the 82 specs, and a note named two more, 000 and 013. Fifteen
of the missing ones (062–076) were owned by a
goal but named by neither this table nor the goal's own `**Specs:**` header. They included the
project pipeline, certification, skills, the open-problems register and the attacks. It also
put SPEC-020 under G6, while SPEC-020's owner is G8. Re-derived from the owner fields on
2026-10-27. When the two disagree, `goals/README.md` is right and this table is stale. A
goal's own file may also name specs it draws on without owning them, as G4 does with 003 and
026.

**Where each of these came from, and how to check that it is covered.** This table is the plan.
It maps the brief's ambitions onto goals, and the goals onto the specs they own, so a reader who
starts here should be able to get to the evidence without knowing which file to open:

| Question | Read |
|---|---|
| What did the user actually ask for, clause by clause? | [`docs/coverage-audit.md`](docs/coverage-audit.md) — 248 clauses (81 `artifact`, 34 `specified`, 133 `partial`, 0 `gap`, as `coverage_round.py` computed them on 2026-10-28), each with a status and, when unresolved, an owning task. `scripts/coverage_round.py` recomputes the counts and **fails** if any `gap` or `partial` clause is unowned; the latest recorded round is 28 (2026-10-28, the fan-out and login-token clauses) |
| Where did the ideas come from? | [`docs/sources/`](docs/sources/) — the three ChatGPT conversations the brief linked, verbatim (3,069 lines), a fourth linked from *Delphi Planning.pdf* (63 lines), both Delphi PDFs, five screenshots, the hackathon snapshot |
| Which spec owns an element of those conversations? | The audit's **section I**, 20 substantive elements traced to their specs. Added 2026-10-22 because rows A1–A3 recorded only that the conversations were *copied in*, which is the capture and not the coverage |
| What is built, and what only specified? | [`docs/goal-status.md`](docs/goal-status.md) per criterion, and `tasks/backlog.yaml` per task. A dependency counts as satisfied only when `passed` is backed by a recorded check result |
| In what order? | [`docs/build-order.md`](docs/build-order.md), and [`docs/hackathon-strategy.md`](docs/hackathon-strategy.md) for what must exist by Oct 30 — whose "what must exist" list is now read against a **41-hour** build window and a **slide deck** deliverable, both re-read from the rules page on 2026-10-22 |
| What are we showing at the hackathon, and how is it checked? | [`docs/hackathon-goal.md`](docs/hackathon-goal.md) — five closed `/goal` statements, the demo's stops, what we may and may not say, and the decisions only the owner can make. Specs 077–079, rows M2447–M2476 |
| How does it run on more than one machine? | [`docs/scale-out-plan.md`](docs/scale-out-plan.md) — topology, the credential broker as the one genuinely hard part, the provider matrix, and what will actually break |

**The honest reading of the statuses.** `partial` means *specified with an owning task and not yet
built* — it is the normal state of most of this plan, not a defect, and the round gate is what
stops it becoming a place where work goes to be forgotten. `specified` means the spec is written
and nothing is built. Only `artifact` means a thing exists. Nobody should read a green round row
as "done"; it means every unresolved clause has somewhere to go.

## Success criteria

A thing is done when its acceptance command passes, not when it looks finished.

1. **img2sim end-to-end.** On a real specimen photograph, the system estimates its own geometry
   (nothing hard-coded), ranks model families, fits parameters, and predicts a **held-out**
   statistic it did not fit.
2. **txt2organism end-to-end.** A natural-language specification yields a multi-scale blueprint
   whose every claim carries an evidence tier, with a named falsifying experiment.
3. **Coverage that means something.** The (taxon × scale) occupancy matrix grows, counting only
   cells backed by an `independently-verified` or `source-only` model.
4. **Verification that means something.** Every published claim states which ladder levels it
   passed; the anti-triviality gate rejects vacuous proofs automatically.
5. **Everything versioned and citable.** Models, artifacts, wiki pages, graph entries, decisions —
   all versioned, content-addressed, immutable once published, corrected by supersession, citable
   by permanent identifier, and time-anchored.
6. **Falsifiable.** Predictions are registered before their resolving data exists and scored with
   proper scoring rules; the track record is public.
7. **Reusable by others.** At least one external team successfully uses a MorphoSwarm capability.

## The standard we hold ourselves to

During research we found a public morphogenesis corpus advertising 1,116 models and 1,101
machine-checked proofs, in which roughly 1,000 entries are generated: their scores are arithmetic
on the slot index, their "empirical" and "simulated" series are drawn from the same curve, and
their Lean theorems prove `p + q - q = p`. Verified at source; written up in
[`docs/prior-art/morpholib.md`](docs/prior-art/morpholib.md).

That is the failure mode this project exists to make impossible — not because the people involved
were careless, but because at scale, nothing in the pipeline could tell the difference. So the
first thing MorphoSwarm's validator runs on is our own corpus. **We audit ourselves first, and we
publish what fails.**

Ambition in what we build. Rigour in what we claim.
