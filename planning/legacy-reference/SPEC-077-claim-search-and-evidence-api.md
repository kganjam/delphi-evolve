# SPEC-077 — Claim search and the evidence API

**Status:** Draft · **Version:** 0.1.2 · **Owner:** G6 · 2026-10-26 (0.1.1, 2026-10-27: rule 9 settled: `hits` flat, `USED_NOT_CITABLE`, `reentry_reason`; open questions 4, on deriving `region`, and 5, on abandoned steps; 0.1.2, the same day: open question 6, on nanopublications from the network)

## Scope

The two read operations every agent needs before it acts, served as one library, one HTTP
surface and one set of MCP tools:

- **Claim search.** Given a statement, a formalization id, a region or a free-text question,
  return what the claim graph already holds about it. The four SPEC-076 §Matching groups come
  first, then a hybrid lexical and vector "suggested" group.
- **The evidence bundle.** Given one claim, return everything recorded about it. That covers its
  formalizations and their ladder levels, the evidence grouped by origin and kind, its logical
  and argumentative neighbours, the nulls that cover its region, its assessments, its belief or
  the reason it is blocked, what would change it, its stamping tier and nanopublications, who
  used it, and who could review it.

In scope:

- the claim index: which records are searchable, how they are embedded under ADR-0030's pinned
  contract, and how the index reports its own staleness;
- the search request and response, and the evidence bundle (§Schema);
- SPEC-045's declared and unbuilt `GET /api/v1/kb/search`, here built for the claim graph;
- `GET /api/v1/kb/claims/{id}/evidence` and the studio mirror of both routes;
- an MCP server so that fleet agents call search and evidence as tools;
- **the search record on an attack step** (an amendment to SPEC-076 §`Step`), which makes
  "agents use it regularly" countable and gives the compounding measurement of SPEC-079 its data;
- seeding the graph with literature claims, typed as extractions, so a search can find what the
  field already says and not only what our agents wrote;
- a retrieval evaluation, and a structural comparison with Paperclip's `claims/support`;
- the claim explorer page that puts search and the bundle in front of a person.

Not in scope, and owned elsewhere:

- What a claim, an edge and an assessment are: SPEC-018, and SPEC-076 §Claim graph.
- The matching groups' semantics (exact, closure, dead ends): SPEC-076 §Matching, unchanged. This
  spec wraps those groups. It does not redefine them.
- Evidence tiers, deciban combination and independence: SPEC-019 and SPEC-049. Belief runs and
  `blocked`: SPEC-050. This spec reads their outputs and computes none of its own.
- The embedding model: ADR-0030 (`sentence-transformers/all-MiniLM-L6-v2` at a pinned revision,
  384 dimensions, `registry/embedding.py`). A different embedder is a new ADR, not a parameter.
- Writing claims. Claims enter through `attack step` and SPEC-045 admission. The tools here are
  read-only.

## Motivation

The owner, 2026-10-26: *"the claim graph is important. we need a way to demo the claim graph. we
should have a nice viewer. vector search (see scidex, scidex v2 repos which use chromadb pgvector
and others) to find claims. we should have this similarity search as an api that agents use
regularly … we should out do the paperclip evidence api. we want to show how the solver for a
specific bio task added claims, found existing claims, and that this accelerates research and
compounds knowledge."*

What exists, measured at `origin/main` `c08420596` (2026-10-26, about 21:50 PDT):

- **Matching is lexical only.** `attacks/match.py` serves SPEC-076's four groups, and its
  "suggested" group is BM25 in pure Python. Nothing embeds a claim.
- **The embedder exists and is unused for claims.** `registry/embedding.py` loads ADR-0030's
  pinned MiniLM from the local cache with no network access. The weights are cached on this host
  (`~/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2`). The generic
  `entity_embedding` table with its HNSW index exists (`0002_vector.sql`, width corrected to 384
  by `0033_embedding_width.sql`).
- **SPEC-045's search route is declared and not served.** SPEC-045 §Read surface lists
  `GET /api/v1/kb/search` ("structured + vector") with a passage and a locator on every hit.
  `kb/http.py` serves `entities/by-curie` and `groundings`, and nothing else.
- **Agents cannot call any of it as a tool.** The fleet has a Paperclip MCP server
  (`agent.mcp_servers`) and no MorphoSwarm one.
- **No step records that it searched.** The substrate showed **5 cross-attack uses** over
  **258 steps** in the r53 build (presenter card, 2026-10-26 15:50 PDT, measured by that session
  from the served bundle). Nothing can say how many steps searched first, or what they found and
  ignored, because nothing writes it down.

**What "outdo Paperclip" has to mean.** Paperclip's `claims/support` takes a claim of up to 590
characters and returns `supports`, `refutes` and `neutral` passages. Each passage has a model
`confidence`, a `weight` (confidence × study design × citations, 0 when retracted), offsets and
the response's `model_version` (`docs/research/paperclip-literature-access.md`, read at full text
2026-10-25). That is a model's judgment of literature support, and this repository already keeps
it as a *lead* rather than as evidence (`evidence/paperclip_leads.py`). For a problem in
mathematical biology most of the evidence that matters is not a passage. It is a simulation at a
commit, a bounded computation, a Lean proof with its receipt, a held-out fit, or a null result
with the region it covered. So the bundle is better than Paperclip only if it does three things:

1. It returns those kinds beside the literature, each typed by where it came from.
2. It uses Paperclip as one input, marked as a lead.
3. It shows the comparison on the same claims, item by item (§Rules 15).

**Design taken from SciDEX, measured rather than recalled.** The `scidex-sci` portal's tools,
called from this session on 2026-10-26, already show the response discipline this spec adopts:

- `search_corpus` names the backend that actually searched ("the site's hybrid search, lexical
  arms only"), the index commit and how far it lags the checkout. It also states its own limits:
  "a page that says the same thing in other words is not found, so no hit is not evidence that
  the portal holds nothing on the question".
- `evidence_for` returns a rollup: edges, papers and labs for and against, and preparation tiers.
  It returns a separate weight (a Bayes factor and a posterior under a stated prior). For a claim
  with no evidence it says *"it sits at its prior: untested, not unlikely"*, and it adds that
  neither figure "is the probability that the artifact is true".

The local SciDEX repositories hold the prior implementation: chromadb in SciDEX v1
(`vector_search.py`), and pgvector with a search contract in `scidex-platform`
(`scidex/web/app/search_contract.py`, `scidex/web/db/schema.sql`). Their design notes are in
`scidex-substrate` (`docs/design/spec-005-semantic-search.md`, `spec-063-semantic-search-backend.md`).
The comparison is in [`docs/research/evidence-apis-and-claim-search.md`](../docs/research/evidence-apis-and-claim-search.md).

## Concepts

- **Searchable record.** A versioned SPEC-018 node with a statement a reader can match against.
  The kinds are attack results and nulls (`claim_kind: attack_result | attack_null`), Questions
  (register problems and decomposition subgoals), formalizations (statement plus `reading`), and
  literature claims (§Literature claims).
- **Arm.** One retrieval method. The arms are `exact`, `closure` and `dead_end` (SPEC-076 groups
  1–3), `lexical` (BM25) and `vector` (cosine over the pinned embedding). The first three decide
  a group of their own. The last two are fused into the `suggested` group.
- **Origin.** Where an evidence item's content came from, from a closed list:
  - `computed-here`: a run, computation or proof this platform executed, with its reproduction
    tuple;
  - `read`: a source a person or agent read at a recorded read-level;
  - `extracted`: a model's extraction from text;
  - `lead`: a tool's judgment, such as Paperclip's `claims/support`;
  - `asserted-by-source`: the source's own statement, quoted at a locator;
  - `elicited`: a prior from a SPEC-050 elicitation.

## Schema

### Search request

```yaml
q: str                     # a statement or a question, at most 590 characters (Paperclip's limit, for comparability)
formalization_id: str?     # sha256:… ; makes the exact arm a lookup
region: {param: [lo, hi]}? # makes the dead_end arm a box-containment check (SPEC-076 §Matching 3)
problem: str?              # register slug; scopes, never filters out a refutation found elsewhere
kinds: [str]?              # attack_result | attack_null | question | formalization | literature
limit: int = 10            # per group
arms: [str]?               # default: all available; a requested arm that cannot run is reported, never dropped silently
```

### Search response

```yaml
groups:
  exact:     [Hit]         # identity only: same formalization_id, or the same statement verbatim
  closure:   [Hit]         # via implies / special_case_of / equivalent_to; refutations included as reasons to stop
  dead_end:  [Hit]         # nulls whose covered region contains (or overlaps, labelled) the requested one
  suggested: [Hit]         # lexical and vector, fused by reciprocal rank (k = 60); always labelled a suggestion
provenance:
  arms_run: [str]
  arms_skipped: {arm: reason}          # e.g. vector: "index absent", "contract digest differs"
  contract_digest: str?                # ADR-0030 EmbeddingContract digest the vector arm used
  index_commit: str?                   # the commit the index was built from
  checkout_commit: str
  records_newer_than_index: int        # searched lexically only, and counted
  limits: [str]                        # what a non-hit does and does not mean, in words
  locator: str                         # a citable string for this exact answer
```

`Hit`:

```yaml
id: str                    # the versioned IRI; a later version is a different hit
kind: str
statement: str
problem: str?
level: str                 # computed by the SPEC-009 ladder, never stated
correspondence: str        # unreviewed | agent-reviewed | person-reviewed | disputed
stamping_tier: str         # signed | anchored | sealed | published | none (SPEC-076 rule 22)
belief: {posterior, engine, exact, run_id} | {blocked: reason, decibans} | {untested: true}
matched_by: [{arm, rank, score}]
passage: str               # the matched text of the record (SPEC-045 §Read surface)
locator: str               # field name and character span inside the record
why: str                   # one line naming the arm and the reason
```

### The evidence bundle (`GET /api/v1/kb/claims/{id}/evidence`)

```yaml
claim: Hit
formalizations: [{id, mode, reading, departs_from_prose, correspondence, level, receipt?}]
evidence:                    # grouped by origin, then kind; never summed across origins
  computed-here: [{kind: simulation | bounded-computation | proof | fit | analysis-plan-run,
                   reproduction: {commit, command, input_hashes, output_hashes},
                   level, limits, step?}]
  read:          [{kind, source, read_level, tier, locator}]
  extracted:     [{kind, source, extracted_by: {model, prompt_hash}, locator, correspondence}]
  lead:          [{tool, model_version, polarity, confidence, weight, locator}]   # Paperclip claims/support
  asserted-by-source: [{source, quote_locator}]
  elicited:      [{question_id, aggregate_rule, n_forecasters}]                   # priors, never evidence
rollup: {supports, opposes, refutes, replicates, papers_for, papers_against,
         independence_classes_for, independence_classes_against}                # counts, SciDEX-style
logical: {implies: [Hit], implied_by: [Hit], refutes: [Hit], refuted_by: [Hit],
          special_case_of: [Hit], equivalent_to: [Hit]}                           # each with its proof step
argumentative: {supports: [..], opposes: [..], contradicts: [..], replicates: [..]}
nulls_nearby: [{hit: Hit, covered, relation: contains | overlaps}]
assessments: [{assessor, first_estimate, second_estimate, basis}]                 # IDEA order (SPEC-076 rule 21)
belief: {run_id, engine, exact, diagnostics, posterior} | {blocked: reason, decibans} | {untested: true}
what_would_change_it: [{factor, voi, direction}]   # SPEC-049 M97's single VOI implementation
stamping: {tier, nanopubs: [iri], tamper_check: pass | fail | not-run}
used_by: [{attack, step, relation: uses_results | statement_edge}]
experts: [{name, orcid?, basis}]                    # SPEC-076 §Experts; no email
provenance: {as in the search response}
```

### The search record on a step (amendment to SPEC-076 §`Step`)

```yaml
searched:                    # optional on every step; required on hypothesis and method steps (rule 9)
  - query: {q, formalization_id?, region?, problem?}
    at: datetime
    response_locator: str    # the provenance.locator of the answer
    hits: [str]              # flat, not per group: the versioned IRI of every hit returned, the
                             # groups concatenated in the response's order (exact, closure,
                             # dead_end, suggested), each group in its own order
    used: [str]              # subset of hits; each must also appear in uses_results or statement_edges
    skipped_dead_ends: [str] # nulls the step chose not to re-enter, with the region they covered
    reentry_reason: str?     # non-empty; why the step re-enters a region a recorded null covers
```

## Rules

1. **One search returns four groups and a suggestion, in SPEC-076's order, and never merges
   them.** A hit in `exact` is exact by identity alone (SPEC-076 rule 19). A hit found only by
   lexical or vector similarity is in `suggested`, whatever its score.
2. **A similarity score is never evidence and never an edge.** Using a suggested hit means
   recording a `uses_results` or `statement_edges` entry, which the loader validates (SPEC-076
   §Matching 4).
   - The pinned model cannot see negation. Measured on 2026-10-26, "Bicoid does not form a
     morphogen gradient in the zebrafish embryo" scored a cosine of 0.982 against the same
     sentence without "not"; unrelated text scored 0.184. The measurement is in
     [`evidence-apis-and-claim-search.md`](../docs/research/evidence-apis-and-claim-search.md),
     and the host session re-ran it. So a hit at a cosine of 0.9 or more carries
     `near_duplicate_text: true` and the warning that it may say the opposite.
   - The vector arm abstains when its best hit is below a floor. The floor is a contract
     parameter, recorded in the retrieval contract's digest, and set on a judged set, never chosen
     by eye.
3. **A response names every arm that ran and every arm that did not, with the reason.** An
   absent index, a contract digest that differs, or a database that does not answer produces an
   `arms_skipped` entry. A response with no vector arm is labelled "lexical only" in its limits.
   It is never presented as a full search.
4. **The vector arm uses ADR-0030's pinned contract and no other, through the index that
   already exists.** `registry/retrieval.py` already has the pieces: `EmbeddingContract`,
   `EmbeddingRow`, `IndexMeta` with its contract-and-commit pin, and `ExactIndex`, which
   `evidence/priors.py` already uses for rows that are not ModelCards. Claim vectors are
   `EmbeddingRow`s keyed by claim IRI and version and held in that `ExactIndex` offline. The
   database form is `entity_embedding` with `search_index_meta` (migrations 0002 and 0003), and
   it is reached by generalising `PgVectorIndex`, which today holds cards only. It is not a
   second index class. A record is embedded one text at a time, because `registry/embedding.py`
   measured that batching moves components by up to 5.3e-8. A changed contract is a new index,
   rebuilt in full, and no retrieval figure crosses the change.
5. **Staleness is reported, never hidden.** `index_commit`, `checkout_commit` and
   `records_newer_than_index` are on every response, and records newer than the index are still
   searched by the lexical arm.
6. **Every hit carries a computed level, a correspondence state, a stamping tier and a belief
   field** of one of three shapes: a run with its engine, `blocked` with its decibans, or
   `untested`. A claim with no evidence is `untested`. It is never shown as a low probability.
7. **Literature claims are extractions.** A claim drawn from a paper carries `asserted_by` (the
   paper, at a locator) and `extracted_by` (model and prompt hash) and starts at `correspondence:
   unreviewed` (SPEC-076 rule 20). Its statement is written in our words. Quoted text is carried
   only where the source's licence permits it, as SPEC-074 rule 2 and the PMC connector's posture
   already require.
   *Amended 2026-10-28 (owner ruling: "dont worry about licensing. please remove any blockers
   related to that. it is not our concern."):* the licence no longer decides whether quoted text is
   carried. The PMC connector keeps section text for every article, and a literature attestation
   carries its quote under every licence (`quote_withheld` is no longer a field). The statement is
   still written in our words, and one that repeats the quote's words is still refused
   (`COPIED_QUOTE`).
8. **The evidence bundle groups by origin and never sums across origins.** The rollup counts
   items. It does not add a lead's confidence to a proof's level, and no field of the bundle is a
   single score for the claim (SPEC-045 rule 9, SPEC-009 rule 11).
9. **Hypothesis and method steps record their search.** An attack's `hypothesis` and `method`
   steps carry `searched` with at least one query. The loader refuses:
   - a `used` IRI that is not among that query's hits;
   - a `used` IRI that is not cited in `uses_results` or `statement_edges`;
   - a `used` IRI of a kind those two fields cannot cite (`USED_NOT_CITABLE`): both hold step
     refs, which are results and nulls, so a Question, a formalization or a literature claim has
     no field to be cited in. Such a hit can be in `hits` and cannot be in `used`. Widening the
     two fields is not part of this rule;
   - an entry whose `query.region` a recorded null of the same problem, earlier than the step,
     already contains (SPEC-076 §Matching 3: the null's `covered` box contains the region, and the
     region names every dimension that box covers), unless the entry names that null in
     `skipped_dead_ends` or carries a non-empty `reentry_reason`. A step that re-enters covered
     ground says why; one that avoids it names the null.

   The attack-agent brief (`tasks/briefs/attack-agent.md`) tells agents to search before they
   propose. The generic runner calls the library directly.
10. **The tools are read-only and cheap.** The MCP server exposes `claims_search`,
    `claim_evidence`, `claim_get` and `nulls_covering`, and no write. They spend no external quota.
    - "Cheap" is a design rule, because agents skip a slow call. One attack agent recorded waiting
      about three minutes for the matcher, which reloads the whole substrate on every call (the
      evidence-API report; not reproduced here). So the index is loaded once per process and
      reused until the substrate commit changes.
    - A `compact` view (statement, group, level, locator: about 2 KB for five hits) is the
      default for agents. `full` is on request.
    A Paperclip lead appears in a bundle only if it was recorded earlier through
    `paperclip_leads`. Spending Paperclip's quota stays the explicit act that module makes it.
11. **Offline is a mode, not a failure.** With no database, search runs over the repository's
    records with the `exact`, `closure`, `dead_end` and `lexical` arms, and reports the `vector`
    arm as skipped. Every acceptance test runs offline. A database-backed test is marked and skips
    with its reason.
12. **The bundle is a view over records.** Every field is read from a record that exists, at a
    commit, and its locator lets a reader re-open that record. A field with no record behind it is
    absent, and the absence is listed in `provenance.limits`.
13. **Retrieval quality is measured on recorded reuse, not asserted.** The evaluation set is
    built from the substrate's own `uses_results` and `statement_edges`. In each pair the using
    step's need statement is the query and the used result is the relevant record. Recall@10 and
    MRR are reported per arm and for the fusion, with the set's size. A positive control (a
    record's own statement returns it in `exact`) and a negative control (a nonsense string
    returns no `exact` hit) run with every evaluation.
14. **Paperclip is an input, and its passages stay leads.** The bundle's `lead` group is
    Paperclip's output as recorded, with its `model_version`. It never moves a claim's tier or
    belief until a `read` item records the passage at a read-level (SPEC-019 rule 5).
15. **The comparison with Paperclip is structural and item by item, and it says what it does not
    measure.** For each claim in a fixed set of at least 20, chosen before either side is called,
    it records per item:
    - the evidence kinds each side returns;
    - the fraction of items whose locator resolves;
    - the contradicting items surfaced;
    - the items that can be re-executed;
    - the time taken.

    It does **not** claim better literature recall. Neither side has a labelled recall set, and
    the comparison says so on the page. If a person reviews a sample of Paperclip's `supports`
    passages, the reviewed count and the agreement are reported with that sample's size.
16. **The explorer is a view over this API.** `/claims` shows search, the four groups, facets
    (problem, kind, level, correspondence, stamping tier) and a neighbourhood graph. In that graph
    logical edges are drawn differently from argumentative ones and from suggestions, and a
    suggestion is never drawn as an edge. Clicking a node opens the bundle. A growth view counts
    claims and cross-attack uses over time from records, and nothing on it is typed. The
    explorer extends the claim page M2385 already serves at `/claims/<claim-id>`
    (`studio/panels/claims.py`, over `attacks/claims.py`'s projection). It adds the index and the
    search to that page and does not replace it.

## Acceptance

| id | what | test |
|---|---|---|
| M2447 | Claim index and hybrid search: exact, closure, dead-end, lexical and vector arms over the projected claim graph; RRF fusion for `suggested`; provenance with arms skipped and staleness; offline mode; `morphoswarm claims search` | `uv run pytest tests/test_claim_search.py -q` |
| M2448 | The evidence bundle: origins, rollup, logical and argumentative neighbours, nulls nearby, assessments, belief or blocked or untested, what would change it, stamping, used-by, experts | `uv run pytest tests/test_claim_evidence.py -q` |
| M2449 | `GET /api/v1/kb/search` and `GET /api/v1/kb/claims/{id}/evidence`, with the studio mirrors; passage and locator on every hit; read-only | `uv run pytest tests/test_kb_claim_routes.py -q` |
| M2450 | MCP server `morphoswarm-claims` (`claims_search`, `claim_evidence`, `claim_get`, `nulls_covering`), read-only, and the runbook entry that adds it to the fleet's `agent.mcp_servers` | `uv run pytest tests/test_claims_mcp.py -q` |
| M2451 | The `searched` record on steps (rule 9): schema, loader refusals, the runner writing it, the attack-agent brief telling agents to search first, and `morphoswarm claims usage` | `uv run pytest tests/test_attacks_search_record.py -q` |
| M2452 | Literature claims seeded for every attacked problem from register attestations and recorded Paperclip leads, typed as extractions (rule 7) | `uv run pytest tests/test_literature_claims.py -q` |
| M2453 | Retrieval evaluation over recorded reuse, per arm and fused, with controls (rule 13) | `uv run pytest tests/test_claim_search_eval.py -q` |
| M2454 | The structural comparison with Paperclip's `claims/support` on at least 20 pre-chosen claims (rule 15), offline over recorded responses | `uv run pytest tests/test_evidence_vs_paperclip.py -q` |
| M2455 | The claim explorer at `/claims`: search, groups, facets, neighbourhood graph, evidence drawer, growth view (rule 16) | `uv run pytest tests/test_studio_claim_explorer.py -q` |

## Open questions

1. **Whether `suggested` should include register problems from other domains by default.** A
   refutation found in another domain is a reason to stop, and closure already returns it
   whatever the scope. A cross-domain suggestion may only be noise. Proposed: include, ranked and
   labelled with its domain, because the platform's claim is that it is domain-neutral.
2. **Whether a person's search from the explorer is recorded.** Agents' searches are recorded on
   steps. A person's search has no step. Proposed: count it in an anonymous usage tally with no
   query text kept, so the growth view can say "searches by people" without storing what they
   typed.
3. **When MiniLM stops being enough.** ADR-0030 calls it a provenance baseline. If rule 13's
   evaluation shows the vector arm adding nothing over lexical, that is a finding to report, and
   a stronger embedder is a new ADR measured on the same set.
4. **How a caller derives `region` from a hypothesis.** A search with no `region` returns no dead
   ends (the landed search reports `dead_end` skipped, "no region in the request"), and `region`
   is optional in the step record. The generic runner's search before a hypothesis passes the
   hypothesis statement and the problem and no region, because a `Hypothesis` carries a statement,
   an operator and free-form `parameters` and states no box, and an operator's `covered` is known
   only after its run. So an entry the runner wrote has an empty `skipped_dead_ends`, and rule 9's
   re-entry refusal can fire only on an entry written with a region. Whether a hypothesis or an
   operator should declare, before the run, the box it will cover, so that the runner can pass it,
   is open. Proposed: the agent that knows the box passes it, and the generic runner passes none
   until operators declare theirs; a `searched` entry with no `region` says by that absence that
   no dead end was matched by containment, and nothing reads it as "dead ends were checked".
5. **Whether a step with `status: abandoned` carries `searched`.** Rule 9 says an attack's
   `hypothesis` and `method` steps carry `searched` with at least one query, and does not say what
   an abandoned one does. The runner writes abandoned steps for the hypotheses it never attempted
   (`_write_abandoned_remaining` in `attacks/runner.py`), and such a step made no search because it
   made no attempt: its `abandon_reason` is the record. Read literally, rule 9 would refuse each of
   them for want of a search record, and counting them as `unrecorded` would blame the runner for
   something it also did not do. Proposed: an abandoned step makes no claim to have searched and is
   exempt from rule 9, and the usage report counts it as `abandoned` and not as `unrecorded`.
   M2451 implements that reading. *Moved here from rule 9 on 2026-10-27, by a session ruling and
   not the owner's, so that the rule stays as it was while M2451 implements it; when this closes,
   rule 9 gains the sentence.*
6. **Nanopublications from the network as an evidence origin.** The bundle groups evidence by
   origin, and our own results are shaped as nanopublications (M2469). A nanopublication someone
   else published, such as a `mira:Claim`, an assessment or a review, is neither a paper we read
   nor a result we computed. Proposed: a new origin, `network`, holding the trusty URI, the
   signer's key, the output of SPEC-007 rule 1b's fetch-back and the template. It never counts as
   `read` literature, and it enters no belief graph until its likelihood is declared, as SPEC-081
   rule 15 requires of a forecast. *Added 2026-10-27 from the owner's 02:00 PDT message: "build
   our own evidence api on top of our own corpus of nanopubs ... but perhaps also integrate with
   paperclip/literature style evidence".*

**Proposed from MorphoLib (2026-10-28).** Rule 7 describes a literature claim as an extraction from
a paper. A claim can also be a record in another project's repository, such as a node of a problem
graph or an entry of a prediction registry. Add `asserted_by.kind: repository-record` (source,
locator, commit, `stated_on`), and keep the source's own verdict in a separate
`asserted_status{value, vocabulary}` that never maps into `level`, so that a source's "solved" stays
the source's "solved". Widen `extracted_by`, which the M2565 brief says admits only register
curation today, and write the record's schema, `morphoswarm/literature-claim/0.1.0`, into §Schema:
it is now only in the docstring of `claimgraph/literature.py`, and no spec names it. This is P2 in
[`docs/research/morpholib-spec-coverage.md`](../docs/research/morpholib-spec-coverage.md). **Not
normative.** M2565 (pending) maps upstream's findings onto the existing record without changing this
spec or `literature.py`; the schema change itself has no row (none filed yet).

## References

- [SPEC-076](SPEC-076-open-problem-attacks.md) §Matching, §Claim graph, §`Step` (amended here by
  the `searched` record); [SPEC-045](SPEC-045-knowledge-base-api.md) §Read surface;
  [SPEC-018](SPEC-018-entity-graph.md); [SPEC-019](SPEC-019-evidence-accumulation.md) rule 5;
  [SPEC-049](SPEC-049-evidence-calculus.md) (M97's what-would-change-my-mind);
  [SPEC-050](SPEC-050-causal-factors-belief-graph.md) rules 7 and 15;
  [ADR-0030](../docs/decisions/ADR-0030-embedding-contract.md).
- Code this joins: `attacks/match.py`, `attacks/claims.py`, `registry/embedding.py`,
  `registry/retrieval.py`, `evidence/paperclip_leads.py`, `kb/http.py`.
- Research: [`docs/research/evidence-apis-and-claim-search.md`](../docs/research/evidence-apis-and-claim-search.md),
  [`docs/research/paperclip-literature-access.md`](../docs/research/paperclip-literature-access.md),
  [`docs/research/claim-graphs-and-claim-stamping.md`](../docs/research/claim-graphs-and-claim-stamping.md).
- The demonstration that uses all of this: [SPEC-079](SPEC-079-compounding-demonstration.md).
