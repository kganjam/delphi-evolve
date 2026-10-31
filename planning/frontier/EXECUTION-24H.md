# Frontier 24-hour foundation and research execution contract

User-directed expansion supersedes the older narrow-build exclusions for this phase. Preserve the released baseline and all scientific-honesty rules. This is actual foundation work plus bounded attempts to resolve real, explicitly scoped questions; no promise of a discovery, wet-lab result, universal framework or collective advantage.

## Window and ownership

Start: 2026-10-31T15:25:26.953183+00:00. Twenty-four-hour decision point: 2026-11-01T15:25:26.953183+00:00. Seattle end: 2026-11-01 07:25:26 PST. The time zone changes overnight; use UTC for elapsed time and actual PDT/PST for reports.

Codex coordinates science/evidence acceptance and integrates the requested Frontier package, in coordination with the existing director. Director retains existing entry/pitch integration; primary alone owns native Sites. Existing GPU owners retain ALL raw GPU submissions, shared <=10 H100 total and yielding when other teams queue. Each implementation worker writes only its own branch/checkout. User now explicitly authorizes distributing this work and using Nebius/Google agents/services. No Orchestra queue/supervisor or recursive worker swarms. Existing exact-target/prover holds remain unless their own repair/registration gates pass.

## Foundation acceptance contract, v0.1

A node stores immutable versions of Claim, Problem, Evidence, Assessment, Action, Actor, ResourceOffer, Interest and Event records. Artifact bytes live separately, referenced by SHA-256 and source/access/license metadata. PostgreSQL is the target transactional store; browser and MCP use the same API/domain model. An isolated tested fallback must be explicitly labelled if Postgres cannot be exercised. No capacity/scalability claim without measurement.

Evidence requires exact claim/problem versions, source URI and locator, retrieval/creation times (declared vs witnessed), content/hash availability, evidence kind (observed/predicted/simulated/formal/source assessment), method/context/assumptions, provenance/source dependence, uncertainty and limitations. An extracted provider stance is a provider assessment, not accepted truth. A missing passage, unavailable bytes or unresolved source must remain visible. Never count citations to the same experiment as independent replications.

Assessment is multidimensional: source fidelity, target fidelity, applicability, computational replay/formal check, statistical adequacy, independent replication, empirical relevance. Each dimension has status, reviewer, rationale and evidence links. No invented composite truth probability or confidence intervals. A solver result never self-promotes to scientifically accepted by merely uploading or passing schema validation.

Problem includes known state, narrow question, novelty status, data access, acceptance criteria, falsifiers, next action, required capabilities, cost/stop bounds, downstream uses and dependencies. Distinguish project gap, computational open question and sourced field-level open problem. Preserve existing six seeds and the resolved correction, then add a curated cross-domain portfolio.

Action lifecycle: proposed -> ready -> leased -> running -> submitted -> reviewed -> accepted/disputed/failed; blocked/expired/cancelled remain explicit. Atomic leases/reservations, idempotency keys and append-only events. Roles/identities and scientific review authority distinct. Cache keys include target/input/code/model/environment/parameter/scope and acceptance-policy versions. A stale or incompatible artifact is not an accepted cache hit.

Open contribution interface: anonymous/public discovery where authorized; authenticated proposed writes with operator identity and quotas; read-only export bundles; independent review before acceptance. Interest signals are following, can_contribute, resource_offer and blocked_by_this (last requires a downstream link). Resource offers require units, amount, time window, restrictions and verification status; offered != reserved != consumed.

Distributed operation: peers exchange content-addressed versioned bundles, with per-node acceptance policies and namespaces. Import preserves original issuer, source and reviews; conflicts become explicit forks/disputes. A digest is integrity, not a trusted signature or timestamp. First prove export/import and replay between two isolated stores; do not claim live federation from a single service.

Search: exact identifiers/entities, lexical retrieval and structured scope/status filters first; optional semantic candidate retrieval with measured recall. Return why matched, source versions and opposing evidence; similarity is not truth. Bound pagination/graph traversal. Evidence API adapters are read-only by default. Do not bypass access controls or copy full copyrighted corpora for public export.

## Initial independently owned work packages

EVIDENCE: inspect Paperclip GXL Evidence API and existing MorphoSwarm evidence adapters; implement a normalized, source-preserving adapter and dimensional assessment schema with meaningful controls. Include source-dependence/contradiction handling. No metered Paperclip request without verified access/price/cap; local authorized client may be used without displaying credentials.

CURATION: import a bounded public SciDEX snapshot (user expressly authorizes scraping), consult Delphi and MorphoSwarm; propose 12-20 sourced questions across benign enzyme/protein engineering, chemistry, agrochemical/environmental measurements, synthetic biology, mechanistic parameter estimation and community allocation. Verify real data links and separate new-science vs reproduction. Select <=3 execution candidates with achievable acceptance in this window. Public-source-only Gemini critique/sourcing calls allowed within the per-worker cap below; model text is a lead until checked.

FOUNDATION: implement in an isolated worktree of the new private kganjam/delphi-frontier repo: persistence/schema + bounded read API/MCP + authenticated proposed contributions + idempotency/version checks + typed events/export/import. Port existing map/seed contracts by reference, not blind migration of Delphi Evolve. Test persistent restart, wrong-version rejection, two-worker lease conflict, proposed-not-accepted evidence and export/import preservation. No public deployment or shared infra mutation until the artifact and its configuration are reviewable.

RESOURCE EXECUTION: existing GPU/resources owner inventories current Nebius science catalog and Gemini/Nebius LLM access without reading/exposing credentials. No inference or GPU batch just for appearance. Once a curated data-backed problem passes the gate, freeze protocol and pilot one useful job before bounded expansion. Preserve prior five-ESM2 TrpB nulls; do not relabel repetition as novelty.

ATTENTION/ECONOMICS: existing market/coordination owner designs separate preference/help/resource/blocking signals, bounded nontransferable attention credits, simple priority baselines, negative-result/replication credit and measured resource receipts. No fabricated votes, money, usage or promise that voting estimates truth. Predictions require explicit resolution criteria/horizon and scoring; distributions and aggregate dependence remain explicit. Federated Metaculus-like forecasting is a design/evaluation candidate, not an existing integration.

## Bounds and scientific go/no-go

First language-model wave across new scoped review workers: max12 generation calls total, <=300k input and <=72k output tokens including thinking. Each delegated review/curation worker: max4 calls, <=100k input, <=24k output; reserve worst-case output before calls; no retry storms. Public source material only. Gemini3.8Flash official Oct31 price is $0.75/M input and $3.75/M output through Dec31; aggregate maximum token-price estimate $0.495, not a billing receipt. Verify actual selected model/price and live availability before dispatch; other providers require their own verified ceiling. Existing arms and their ledgers remain separate and untouched. We may expand only after inspecting useful results and remaining resource constraints.

All local build/test/agent processes: systemd-run --user --scope -p TasksMax=128 -p MemoryMax=4G -p MemorySwapMax=0 -p RuntimeMaxSec=600; CPU threads <=2. Longer work is split into bounded resumable phases, not an unbounded process. No secrets in prompts/logs; use existing configured authenticated clients in memory. No raw credential reads, credential copies, global auth edits or usage-reset grants. No others' jobs/services touched.

A selected scientific task must have: accessible legal public data, precise claim/question, prior-art check, independent acceptance method, baseline/control, contamination/split strategy, cost and stop bound, and artifact/visual plan. Simulated or predicted outputs can settle a model-specific question, not establish a biological intervention. Candidate failures and unresolved outcomes remain results. Use actual held-out measurements where appropriate; choose benign targets and do not claim activity from structure or docking alone.

## Milestones

0-2h: runnable persistence/contribution/evidence contracts, sourced candidate portfolio and resource inventory. 2-6h: freeze <=3 accepted experiment protocols; run bounded pilots and establish controls. 6-18h: independently check useful computations; expand only promising validated workloads; publish interim versioned artifacts. 18-24h: replay, review scope/uncertainty, consolidate negative and positive outcomes, deliver integrated map/evidence/action receipts and exact source SHA to director/primary.

Completion is a working reusable foundation plus honestly adjudicated scientific attempts and at least one independently checkable resolved scoped question if the evidence permits. A website, agent debate or uploaded model output alone does not meet that condition.
