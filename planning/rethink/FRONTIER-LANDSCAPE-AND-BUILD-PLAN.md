# Delphi Frontier: a map that helps science move

Research and design update, 2026-10-31, Seattle PDT. This extends the director's existing direction and `ACTIVE-FRONTIER-PITCH-PROPOSAL.md`; it does not restart selection or assert that the proposed network is deployed.

**Pitch:** Delphi Frontier maps what we know, what remains uncertain, and the next action that could change our minds. People and agents contribute evidence, challenge claims and solve scoped problems. Every accepted result carries its conditions and a receipt another contributor can inspect and reuse.

Delphi supplies candidate claims and their provenance. Frontier makes the work around them navigable: known results, disputed interpretations, missing measurements, incomplete derivations, and opportunities to connect fields. The scarce resource is attention that leads to a useful, checked result. The proposed contribution is a working, evaluated connection between these pieces; the general architecture has substantial prior art.

## Closest existing work

This is a bounded primary-source survey, not an exhaustive novelty search or independent replication of others' results.

| Work | Overlap and evidence level | Consequence for Frontier |
|---|---|---|
| [PNNL Mycelium, Networked Intelligence (July 2026)](https://arxiv.org/html/2607.13220v1) | Active shared context graph routes findings between humans and agents; authors report a biological multi-omics campaign. The paper discusses uncertainty in cross-context translation and future conflict handling. Methods/results/discussion inspected; no independent replication here. | Very close biological predecessor. Reuse its evidence-to-action framing. Test scoped transfer, contestation and independently replayable acceptance rather than claiming to invent scientific coordination. |
| [SciDEX](https://scidex.ai/vision) and [quests](https://scidex.ai/quests) | Public project descriptions cover research gaps, ranked questions, markets, resources and execution. Site descriptions are not an audit of runtime effectiveness. | Share problem and action formats where possible. “Agents prioritize scientific questions” is already a stated goal elsewhere. |
| [ASK, Active Scientific Knowledge](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7416579) | Conceptual model: addressability, traceability, conditional execution, response to new evidence, scope-preserving transfer and contestable federation. Primary abstract and local MorphoSwarm full-PDF review available; direct SSRN page returned 403 on this pass. | Use these as acceptance criteria. A searchable graph alone is insufficient. |
| [Virtual Agent Economies (2025)](https://arxiv.org/abs/2509.10147) | Framework for agent economies and allocation mechanisms. | Treat markets as possible institutions to evaluate, not evidence that a token economy improves biology. |
| [Agentic Economies for Autonomous Scientific Discovery (September 2026)](https://arxiv.org/html/2609.31562v1) | Proposes resource management, scientific artifacts, credit, accountability, markets and post-hoc rewards; explicitly discusses delayed impact and idea flooding. | Budget verification and experiments, reward useful negative results and preserve exploratory funding. Our allocation mechanism must earn its place against simple baselines. |
| [Google AI co-scientist](https://research.google/blog/accelerating-scientific-breakthroughs-with-an-ai-co-scientist/) and [Kosmos](https://arxiv.org/abs/2511.02824) | Agentic hypothesis generation/evaluation and persistent analysis/literature workflows, with biomedical examples reported by their authors. | Potential producers of contributions. Do not claim all other systems stop at unsupported assertions or that Frontier invented persistent scientific memory. |
| [INDRA](https://indra.readthedocs.io/en/latest/) | Structured biological statements, evidence, grounding, belief scoring and curation. Documentation inspected. | Reuse entity identifiers and evidence distinctions; track correlated source families rather than counting repeated citations as independent support. |
| [alphaXiv OpenResearch](https://github.com/alphaXiv/OpenResearch) | Experiment execution/history tooling. Existing MorphoSwarm source review pins `703fd4bba66311625cf7e0b0776a0f949d3f4c73`. No new runtime installed. | Import completed runs and archived inputs as evidence. A successfully finished run still needs scientific review. |
| [Nanopublications](https://nanopub.net/) | Small RDF publications with assertion, provenance and publication information, attribution and a decentralized publication ecosystem. | Export portable contributions; retain their evidence kind and exact scope. Hashes/signatures establish content integrity and attribution, not scientific truth. |
| [BioNeMo](https://docs.nvidia.com/bionemo-framework/latest/) | Official toolkit includes model training/inference recipes and biological downstream examples. | Attach model outputs as predictions with reproducible run metadata and an explicit validation question. No automatic promotion to experimental evidence. |

The PNNL paper is the Mycelium meant here, not unrelated projects sharing the name. We have not established availability or licensing of its implementation. No public platform's self-reported activity counts are treated as observed reuse by our project.

## What MorphoSwarm already gives us

Read-only inventory at `/home/ubuntu/git/morphoswarm`, HEAD `eb91a33084a8b28c9833c7a150f908784be39e7f`. Relevant local reviews are `docs/research/active-scientific-knowledge.md`, `active-scientific-knowledge-ask-model.md`, `openresearch-experiment-tree.md` and `delphisci-mcp-and-nanopub-network.md`.

Source inspection confirms dedicated modules for version chains (`versioning/chain.py`), structured evidence (`evidence/types.py`), contestation (`evidence/contested.py`), negative results (`kb/dead_ends.py`) and nanopublications (`nanopub/`). The version-chain module specifies compare-and-set succession and database constraints; contestation represents unresolved disagreement and contributor independence. These are concrete reuse leads. They have not been ported, executed or dependency/license-audited for Frontier. Its local linear version chains also should not be mistaken for a solved federated fork/merge protocol.

Adopt a narrow adapter before importing another project's whole application: pinned claim/version, evidence context, supersession, dispute, run receipt. Preserve both projects' ownership and contracts.

## The map is the product

Give readers three linked views, all backed by the same versioned records:

1. **Knowledge map:** claims, models, evidence, counterevidence and scope. Zoom from a biological question to a particular equation, measurement or proof. Distinguish “supported under these conditions,” “contested,” “unchecked here,” and “open in the field.”
2. **Frontier map:** unresolved questions with a settlement criterion and downstream consequences. A missing measurement, unresolved theoretical link, conflicting results and missing implementation are different gaps. A blank part of our database is not proof of a scientific gap.
3. **Action map:** proposed/running/reviewed actions, responsible people and agents, resources reserved, actual outcomes and who can use them next. Show an available action only when its prerequisites and access requirements are met.

The interesting regions between fields deserve their own layer: possible transfers of a method, a common mathematical structure, incompatible parameter meanings, or an experiment that would distinguish two explanations. An embedding can suggest a connection; it cannot certify a derivation. Every proposed bridge names the mapping, conditions it preserves, what changes, and a test that could reject it.

Do not render a force-directed galaxy whose geometry implies evidence. Label edge types: derives under assumptions, supports in context, contradicts in context, estimates, tests, depends on, proposed analogy. Display provenance and layout semantics. Dependency cycles are allowed in discussion graphs but must not become circular evidence or recursive self-credit.

The initial `site/review/frontier.html` prototype uses the pinned 21-record inventory. Its positions are curated topic groups and its colors describe **our review coverage**. It is a small map of this project, not a map of all biological knowledge. The twelve unchecked records are a review backlog, not twelve discoveries waiting to happen.

## “Prove to me” is a request with a precise meaning

| Reader's challenge | Appropriate response | Acceptance boundary |
|---|---|---|
| Where does this claim come from? | Exact source/version, supporting passage or data, extraction judgment and disagreements. | Correct citation does not establish the claim. |
| Does the conclusion follow? | Formal statement, assumptions, exact theorem type, compiler/dependency/axiom receipt and source correspondence review. | Lean checks a formal proposition; statement fidelity and applicability remain separate. |
| Can I reproduce the computation? | Input/code/model hashes, environment, parameters, seeds, outputs, controls and independent replay. | A reproducible computation can still implement the wrong model. |
| Does this apply in my system? | Compare taxon, tissue, time scale, conditions, interventions and units with the evidence. Expose missing inputs. | Cross-system transfer requires justification and may remain unknown. |
| What would change our minds? | Competing explanation, predicted discriminating outcome and feasible next test. | A proposed experiment is neither evidence nor a completed result. |

The user should be able to challenge any link. Preserve the original artifact; attach a versioned assessment, rebuttal or replacement. A disputed premise marks dependent uses for review rather than silently deleting history. Communities may apply different declared acceptance policies while exchanging the same evidence bundles.

## A scientific community that produces work

[alphaXiv](https://www.alphaxiv.org/) connects research papers and researchers. [Moltbook](https://www.moltbook.com/) presents agent posting, discussion and voting. arXiv, Reddit and these services are useful product references for publication, discovery, discussion and participation; none of those interactions alone certifies a result.

Our proposed social unit is a **contribution to a question**. A post may submit evidence, identify a scope error, propose a test, reproduce a result, offer a resource or report a useful failure. Discussion remains readable as a thread, while reviewed contributions update the relevant map nodes. Votes can prioritize attention; scientific status follows explicit evidence and review policies. Give a problem a human-readable page, an activity digest and a machine-readable contract. Avoid a separate agent feed that drifts away from the evidence.

Recruit through a public capability manifest and a small, verifiable first task: resolve an entity identifier, reproduce one calculation, review a source-to-target mapping or supply a missing measurement. Let agents declare available tools and limits; record demonstrated capabilities separately. An operator authorizes participation, resource use and publication. We have opened an [interoperability discussion on Delphi issue #35](https://github.com/fractastical/delphi/issues/35#issuecomment-6545154966); no new external adoption is established by that comment. We have not posted to Moltbook or registered agents there.

## Agent contract, credit and economics

An action offer needs: immutable problem/claim versions; proposed method; required inputs and their access rights; acceptance predicate; negative controls; expected cost and stop bound; outputs; reviewer role; what it unlocks. Agents discover offers, reserve a short lease and budget, submit artifacts, obtain review and release a result. Use idempotent submissions and compare-and-set versions to avoid duplicate execution and stale claims. Reuse Delphi's existing registry/protocol after its owners confirm the contract; do not create another disconnected leaderboard.

Keep three records separate:

* **Scientific evidence:** result, scope, uncertainty, counterevidence, review and reproducibility.
* **Contribution credit:** who extracted, modeled, proved, implemented, replicated, curated or challenged; explicit links to accepted downstream reuse.
* **Resource accounting:** reserved and actual compute, tokens, instrument time and money, with estimates distinguished from billed amounts.

A contributor's popularity or funding does not set a claim's truth. Start with explicit budgets and bounded task rewards, including replication and informative negative results. Credit downstream reuse when it is observed; do not reward generating many duplicates or invent a citation-based universal merit score. Treat automated credit division, Sybil resistance, independent review and federated dispute resolution as open research problems.

Rank actions by expected improvement in a named decision, downstream uses enabled, cost and uncertainty. These are decision-maker estimates, not measured scientific value. Reserve separate capacity for exploration, replication and consolidation so immediately measurable tasks do not absorb everything. Test a proposed allocation policy against expert order, round-robin and a simple value/cost rule. Later markets require calibrated outcomes and defenses against strategic reporting; transferable tokens are unnecessary for the first working loop.

For nanopublications, distinguish a publisher-declared creation time, repository/server receipt time and independently witnessed timestamp. A content hash alone establishes neither priority nor trustworthy time. Export assertion/provenance/publication information, plus the policy and evidence behind a review. Drafts remain drafts until authorized signing and an actual publication receipt exist.

## Compute that advances a question and produces an honest visual

Use GPU resources through the existing GPU owner. A run should resolve a named uncertainty or produce a meaningful comparison. One useful expansion is a preregistered BioNeMo prediction evaluated against held-out measured outcomes, with model/checkpoint/input hashes, preprocessing, hardware, time, actual metered cost when available and calibration limits. A structure prediction alone does not measure binding affinity or tissue diffusivity.

For the present demonstration, show the computed dispersion relation and admissible modes beside actual PDE simulation frames when a reviewed run exists. Let the reader vary domain, boundary and parameters, and show how conclusions change. Label recorded simulation, live numerical calculation, prediction and observation distinctly. A nonlinear pattern movie cannot serve as ground truth for a linear-mode classification task. A literature diffusivity ratio does not identify a universal robustness cliff across kinetics.

The most useful visuals are a scope boundary with counterexamples, a simulation with parameter and convergence receipts, an evidence disagreement that suggests a discriminating experiment, and a frontier before/after a reviewed contribution. Pair each with a plain-language explanation and accessible table. Never use a graph animation to imply unobserved collaboration, biological validation or GPU execution.

## Small next build and the experiment that would justify expansion

Preserve the released baseline. Director integrates; Codex owns science/review; dx-submit owns landing/deck/blog/storyboard; the existing GPU and runner owners retain execution; primary owns native Sites publication.

1. Publish the reviewed 21-record map and one inspectable question page through the existing site integration. The current prototype has no task leasing, signing, live community or autonomous execution.
2. Agree one contribution format with Delphi maintainers. Import a completed run or proof as a proposed contribution and independently replay it. Produce a portable draft assessment tied to the exact claim version.
3. Have a second participant use that accepted contribution on a different scoped question. Measure correction rate, replay success, useful handoffs, duplicated effort, review time and real cost. Until it happens, there is no external-reuse claim.
4. Test the coordination layer against a persistent agent with the same evidence/tools and a shared-file/manual-routing baseline. Predeclare task acceptance and count refusal, missing coverage, failures and review overhead. New content volume and agent count are not success metrics.

The pitch can show a concrete sequence: **a claim, a challenge, a checked result, a changed next action**. The expansion to a decentralized scientific commons is the vision. The first measured, reusable contribution is the evidence for pursuing it.
