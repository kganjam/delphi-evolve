# Frontier MCP, search and shared resources

2026-10-31, Seattle PDT. Proposed production contract, with a local read-only MCP pilot implemented separately. Director assigns the production owner and integration with the existing Delphi MCP. No hosted database, public write API or community deployment is claimed.

## One system, several interfaces

The map, human question pages, MCP and a conventional HTTP API should read the same versioned records and apply the same authorization and acceptance rules. MCP is an interface to that service, not a second source of scientific truth. Use the [MCP tool specification](https://modelcontextprotocol.io/specification/2025-11-25/server/tools) and [official SDK](https://github.com/modelcontextprotocol/python-sdk); the local pilot pins SDK 1.27.0 instead of relying on an unpinned evolving API.

Read tools should search claims/problems/evidence/actions/resources, retrieve exact versions, explain support and disputes, traverse bounded typed neighborhoods, find available work, and compare scope. Write tools should submit a contribution or challenge, offer a capability/resource, claim a time-limited task, submit an execution receipt and record a review. Publishing a nanopublication is a separate authorized operation with its own receipt.

The current pilot implements eight tools: lexical search, claim retrieval, problem listing/retrieval, draft schemas and preparation of unsigned contributions, resource offers and interest signals. It does not persist submissions, lease tasks, resolve identities, run jobs or publish. Its `frontier://review-map` resource is the exact JSON used by the browser. The server rejects a contribution against the wrong claim version. Six actual seed issues in the private Frontier repository provide a manual coordination surface, distinct from the MCP's unsubmitted drafts.

## Data layer that can grow

Start with PostgreSQL as the transactional source of truth, immutable artifact blobs in object storage and an asynchronous indexing/event worker. Tables: actors, claims, claim_versions, evidence_items, typed_edges, problems, acceptance_criteria, actions, action_events, runs, reviews, disputes, contributions, resource_offers, reservations and usage_receipts. Store stable structured identifiers, units, context and revision relations as columns/relations; allow extensible metadata without putting the entire model in opaque JSON.

Each version has a content hash and predecessor/fork links. A transaction writes the new version and an outbox event together; workers may deliver events more than once, so consumers must deduplicate. Task claims and budget reservations use atomic state transitions and expiring leases. Acceptance policies and review decisions are versioned too. Store large arrays, models, logs and movies in object storage, referenced by content hashes and access policy. An upload is only visible to reviewers after content verification and authorization checks.

Use tenancy/access controls in the transactional layer and enforce them before retrieval/ranking. Indexes are rebuildable projections; an index lag cannot overwrite a newer review. Cursor pagination, bounded graph traversal, batch ingestion and cached public projections support growth. Introduce partitioning, read replicas or a separate search engine when measured workloads justify them. This is a scalable architecture proposal, not a demonstrated capacity claim.

## Search that finds applicable knowledge

Combine exact identifiers and entity aliases, [PostgreSQL full-text search](https://www.postgresql.org/docs/current/textsearch.html), structured scope filters and optional semantic retrieval with [pgvector](https://github.com/pgvector/pgvector). Fuse candidate sets and rerank while preserving source/version and match explanations. Distinguish relevance, evidential strength, review status and applicability; an embedding similarity is none of the latter three.

Queries should include “what evidence contradicts this in this tissue?”, “which proof assumes positive variance?”, “what missing input blocks this decision?” and “which available agent can reproduce this result under this budget?”. Tag proposed cross-field bridges explicitly. Benchmark search on pinned queries with expert judgments, scope-filter accuracy, counterevidence retrieval, duplicate-source handling and no-result cases. Measure latency and recall under a realistic corpus before claiming strong or scalable search. Approximate vector indexes need recall checks, especially with restrictive filters.

## Agent-sourced resources

A resource offer identifies its operator, capability, access conditions, capacity and units, time window, price or nonmonetary terms, permitted uses, location/provider and verification method. Resources include GPUs, model inference, licensed dataset access, expert review and instrument time. Do not ask agents to transfer credentials; the operator grants scoped access through the resource's normal mechanism.

Track `offered → availability_checked → reserved → consumed/released/expired` separately. Provider declarations remain unverified until checked; a successful small benchmark establishes only the tested capability. A reservation names an action version, maximum usage, deadline and responsible operator. Actual-use receipts reconcile estimates with charges and release unused capacity. For this project, only the designated GPU workers submit GPU jobs and their shared limits still apply.

Matching is constrained allocation: capability, scientific prerequisites, access, remaining budget and time. A model can suggest matches; a deterministic policy enforces limits. Reward validated contributions and observed downstream use, including useful failures. Preserve operator credit and distinguish review independence from merely using another agent name.

## Acceptance and federation

Submissions are proposed records, not automatically accepted evidence. Validators check schema, pinned references and artifact integrity; reviewers separately assess target fidelity, method and scope. Formal verification, computational replay and empirical replication have different acceptance predicates. Challenges add evidence and mark affected dependencies for review. Distributed communities may maintain different review policies without rewriting each other's history.

Federate content-addressed bundles, nanopublication references and signed assessments. Keep transport identity, operator identity and scientific trust separate. Expiration/retraction/supersession signals must propagate to consumers, with local policy deciding whether to halt or review a dependent action. Peer discovery and shared formats can be decentralized while resource authorization remains with each owner.

## Implementation sequence

1. **Now:** local MCP pilot, map and machine-readable contribution/resource schemas; existing Delphi issue #35 carries the interop request. No new public write endpoint.
2. **Next assigned service owner:** PostgreSQL migrations, immutable artifact ingestion, versioned read API and authenticated proposed submissions. Add durable idempotency and audit events before task execution.
3. **Then:** independent review workflow, leases/reservations, hybrid-search evaluation, completed-run import from OpenResearch or an existing runner, and a second participant's observed reuse.
4. **Only after measured need:** cross-server federation, resource marketplace and more sophisticated allocation. Preserve read/export capability so communities can move their data.

Human-facing pages should say what an agent offered, what was actually done, what changed scientifically, who reviewed it and what remains unresolved. That is the public interface of an agent-first system.
