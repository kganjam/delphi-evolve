# Frontier publication layer: accepted Frontier assessments as nanopublication drafts

**Status (2026-10-31, Seattle PDT): PREPARED, NOT PUBLISHED. Single-reader, not Codex-reviewed.**
No registry (test or production) has been contacted by this code. No nanopublication of this profile exists anywhere. The test-registry
publisher exists, is inert by default, and was exercised only against a loopback fake. There is no production publish path.
This file is also the profile IRI cited by every draft (`dct:conformsTo`), so it must be on `main` before any publish.

Frontier pin: `kganjam/delphi-frontier` `42cd967a97becefbb1ce67f43ce4be953ce1ec09` (models.py blob `4faad6c2…`, store.py blob `f235c33f…`).
Read from a `git archive` extract; nothing was written to that repository. Its working tree had another session's uncommitted edits,
which is why the pin is a commit and not the tree.

## 1. Implemented versus designed (kept apart)

| | Implemented and tested here | Designed only (not built) |
|---|---|---|
| Binding | `Claim` and `Problem` targets with an accepted `Assessment` -> TriG draft (`frontier_pub/binding.py`) | `Action`, `Evidence`, `Actor`, and other kinds: refused with a message |
| Gates | 20+ independent re-checks; every refusal has its own test (section 3) | Checking a *node-signed* export (Frontier has no node signatures yet) |
| Corrections | superseding nanopub for a new accepted version; superseding *status-change* nanopub for a later disputed/rejected review; ledger-enforced no-fork | Retraction through this layer's CLI (the builder `falsify.nanopub.build_retraction` exists; no Frontier event triggers it); propagation to dependents |
| Collection | read-only `collect()` over Frontier's `Store.get/events` and over its loopback HTTP read endpoints (both paths produce identical bundles) | MCP reader; reading private records with a token (refused by design) |
| Signing | local signing with a key outside the repo, independent verification with `@nanopub/sign` 0.2.0 (a second implementation), tamper negative control | Signing identity (ADR-0005 is open), time anchoring (OpenTimestamps; `ots` is not installed here) |
| Test registry | `registry.post_test`: dry-run by default; role check by asking the registry (`/.json`), host allow-list, user-authorization record bound to the exact signed bytes, one POST, 429 wait, verifying GET fetch-back, HEAD never used. **Exercised only against a loopback fake.** | A real run. Needs the user's own instruction (section 8) |
| Production | nothing. Not in the code, enforced by a source test | any |
| Queries | none new (the SPARQL builders of the Scope Desk profile are separate) | A profile-specific `get-latest-version-of-np` chain-head check before superseding (SPEC-007 rule 4); today the chain head comes from the local ledger |

Tests: `tests/test_frontier_pub.py`, 59 tests (58 plus the Frontier digest cross-check when `FRONTIER_SRC` is set). Fixtures come from Frontier's
**real `Store`** on a private throwaway PostgreSQL 16 (`scripts/frontier_pub_pg.sh`, `scripts/frontier_pub_make_fixtures.py`); every review in them
is a software workflow control, not a scientific review, and says so in its own rationale text.

## 2. The binding: which Frontier field becomes which triple

One nanopublication = one (target record version, accepted Assessment version). **What it asserts is the review, not the reviewed claim.**
The reviewed record's text is quoted inside the assertion as the thing reviewed and is never interpreted. Frontier's acceptance is node-local;
asserting the claim itself would turn it into a statement every reader could take as established.

Inputs (all are Frontier records, each re-verified by recomputing its `version` digest, `frontier_pub/records.py`):
target, assessment, the `review_recorded` Event naming that assessment, the `record_proposed` (or `record_imported`) Event for the target,
and any Evidence records the dimensions link. Plus two facts from `Store.get`: `is_head` and `local_review`.

| Frontier source | Graph | Triple (schema.org / PROV / DC only; no IRI minted) |
|---|---|---|
| `Assessment` as a whole | assertion | `sub:review a schema:ClaimReview` (Claim targets) or `schema:Review` (Problem targets); `schema:itemReviewed sub:item`; `schema:author sub:reviewer`; `schema:hasPart` the seven dimension reviews |
| each of the 7 `dimensions[d]` | assertion | its own `sub:dim_<d> a schema:Review` with `schema:reviewAspect "<d>"`, `schema:reviewRating -> schema:Rating / schema:alternateName "<status>"`, `schema:reviewBody "<rationale>"`, `schema:author` (the dimension's reviewer), `schema:citation` -> each `evidence_links` entry |
| `decision` | assertion | `PropertyValue frontier_node_decision = accepted`, with a description that it is a node-local policy outcome and not a truth rating, probability, combination of dimensions, or other node's agreement |
| `policy_version`, `independence_rationale`, `limitations[]` | assertion | one `PropertyValue` each (limitations stay separate items) |
| (none) | assertion | `PropertyValue aggregation = none`, and `scope_limit` text |
| target `title`, `statement`, `context` | assertion | `sub:item a schema:Claim`: `schema:name`, `schema:text`, `schema:description`; `schema:claimReviewed` carries the statement verbatim |
| target `assumptions[]`, `limitations[]` | assertion | one `PropertyValue` per item (scope travels, not as one prose blob) |
| target `source` | assertion | one `PropertyValue` per recorded field; `source_bytes_available_to_frontier` with the note that any `content_sha256` is a declared pin. **No source recorded -> `source_status = "no source recorded"` plus "Curator statement"** (the register correction of 2026-10-31) |
| Problem fields | assertion | `question`, `problem_kind`, `completeness` (or "not_stated_by_this_record_version"), `acceptance_criteria`, `falsifiers`, `next_action`, `cost_stop_bounds` as properties |
| Claim `prior_review` | (nowhere) | deliberately not published: an earlier provider's label must not travel as if it were this review |
| Assessment `issuer` | provenance | `sub:reviewer a prov:Agent`, `schema:identifier "<issuer>"`; `sub:assertion prov:wasAttributedTo sub:reviewer` |
| review Event `operator` | provenance | `sub:reviewerOperator a prov:Agent`; `sub:reviewer prov:actedOnBehalfOf sub:reviewerOperator` |
| target `issuer`; proposal/import Event `operator` | provenance | `sub:submitter`, `sub:submitterOperator` (labelled "importing operator" for imported targets), `prov:actedOnBehalfOf` |
| Assessment `namespace` | provenance | `sub:reviewNode a prov:Agent`, `schema:identifier "<namespace>"`, comment: not a registered IRI namespace, not a verified organisation |
| target `namespace` | provenance | `sub:originNode` (differs from the review node when the target was imported) |
| the four records' `version` digests | provenance | `sub:assessmentRecord`, `sub:targetRecord`, `sub:reviewEventRecord`, `sub:proposalEventRecord` each `a prov:Entity` with `schema:identifier ns/Kind/id`, `schema:version "<64-hex digest>"`, `dct:created`; all `prov:wasDerivedFrom` of the assertion. Digest recipe is written in the pubinfo |
| review Event `witnessed_at` | provenance | `sub:reviewActivity prov:endedAtTime`, commented as the node's own clock, not a third-party timestamp |
| target `source.uri` (only if it passes the IRI policy) | provenance | `prov:wasDerivedFrom <uri>`; otherwise it stays a literal |
| publication-layer code | provenance | `prov:wasDerivedFrom <repo/tree/<40-hex commit>/frontier_pub>` |
| (publication) | pubinfo | pinned `dct:created`, `dct:creator <repo>`, `dct:license` (CC BY 4.0 prepared; owner decides), `dct:conformsTo` this file, `npx:hasNanopubType`, `npx:introduces sub:review`, `npx:supersedes` when correcting, label, comment that Frontier remains the system of record |

**No composite, and how that is enforced.** There is no numeric rating term anywhere. `conform()` rejects `ratingValue`, `bestRating`,
`worstRating`, `confidence`, `probability` and `score`, with a positive control. A differential test changes one dimension's status in the
Assessment and shows that exactly that dimension's rating differs in the output. The `decision` is a categorical outcome label carried with its
meaning, not derived from the dimensions by this layer.

**What the signature means.** The signing key signs this *rendering*. It does not verify the identities of the reviewer or operator, which are
whatever the Frontier node was configured with (Frontier calls them `declared` or `operator_configured`). The draft says so beside the operator.

## 3. Refusals (each has its own test; the node's own checks are re-verified, not trusted)

Record digest mismatch · wrong schema · any record not `public` · assessment not pinning exactly this (namespace, kind, id, version) · policy not
`frontier-independent-review-0.1` · decision other than `accepted` for a first publication · not exactly seven named dimensions · a dimension reviewer that
is not the assessment issuer · empty rationale · an accepted assessment with a dimension that is not passed or not_applicable · `target_fidelity` or
`applicability` not passed · same actor as target issuer · same operator submitting and reviewing · review event not naming this assessment or wrong
event type · local state not equal to the decision (stale/superseded) · target not the current head · unsupported kind · evidence supplied but not
linked by any dimension · `dct:created` not pinned · publication-layer commit not a 40-hex id · more than 1,100 triples · supersede target not a trusty URI ·
an exact version already published · a dispute with no published acceptance in the ledger · a draft that would fork the chain when marked published.
IRI policy: no `urn:`, `ms:`, `example.org`, `localhost`; nothing under `w3id.org` except existing `w3id.org/np/…`; an unvettable source URI travels as a literal.

## 4. Corrections, and what a nanopublication cannot do

- **New accepted version** -> new nanopub, `npx:supersedes` the ledger's published chain head for the same (namespace, kind, id), same signing key.
- **Later disputed/rejected review of the published version** -> a superseding *status-change* nanopub carrying the dimension outcomes of that review.
  It is not a retraction, because it records a changed status, not a mistaken publication. Retraction (`npx:retracts`) is for a publication that should
  never have been made. A dispute is never a *first* publication in this version (design choice, open to change).
- **A new Frontier version that nobody has reviewed** changes nothing in any nanopub. The published nanopub remains true of the version it names. It cannot
  tell a reader that a newer version exists. That is a property of the node, not of an immutable file (section 5, row 3).
- Frontier's `local_states.status` is overwritten by each review (last review wins), so a lone dispute flips an accepted version's state and a later review can
  flip it back. The layer publishes each flip as a superseding file; the *history* is reconstructable only from Frontier's `reviews` table or events.

## 5. What ASK adds beyond nanopublications (quoted from the paper, not from memory)

Source: Fırat, *Active Scientific Knowledge: A Conceptual Model for Machine-Actionable and Versioned Science*, SSRN, doi 10.2139/ssrn.7416579. Quoted from a text copy
(`/home/ubuntu/scidex/data/scidex-artifacts/ask-paper-fulltext.txt`, sha256 `c47aff5b3e96eb4e7c786022cb6be839bebb3fb6ad21829b2fe4f93c27ed6aa9`; identical copies at
`ask-full-paper.txt` and `/tmp/dbba-ask-paper.txt`). **I could not check that this text file is the PDF's text:** the repository PDF
(`morphoswarm/papers/10.2139%2Fssrn.7416579/paper.pdf`, recorded sha256 `cc709a91…`) is a git-LFS pointer on this host. Page numbers are the paper's own footers in that text. The paper is CC-BY-NC-ND per Crossref; only short quotes are given.

**Limit first.** The paper calls itself "a conceptual framework" and says "ASK is not another knowledge graph, publication format, or artificial intelligence system" (p.4).
So there is no "ASK serialization" and no ASK profile to conform to. The assertion / provenance / publication-info structure here is the nanopublication format; ASK supplies requirements
on what must stay coupled. SPEC-087 says the same (it is "not a claim of ASK conformance"). Nothing in this layer is ASK-conformant, and the paper offers no evidence that the model improves research.

| # | ASK passage | Nanopublication alone | Frontier store | This layer | Anywhere |
|---|---|---|---|---|---|
| 1 | p.4: nanopublications "make assertions and their provenance addressable... These capacities are necessary but do not individually define an active epistemic state." | addressable assertion + provenance | stores versions and typed edges | renders them | the "active epistemic state" below |
| 2 | p.4: "four relations remain coupled during reuse": claim-evidence, status changes "when relevant evidence or method validity changes", scope "govern[s] whether transfer to a new project is permissible", "a versioned path to the sources and judgments" | evidence/scope can be *stated* in the assertion; nothing couples them to a status that changes | version digests, typed edges, per-version status, `applicability` dimension | carries scope and evidence pins as separate items | **Not enforced anywhere:** nothing computes "scope forbids this transfer"; `applicability` is a human judgment recorded as passed/failed |
| 3 | p.5: "Earlier states remain visible. Retractions and corrections propagate to dependent entities" | immutability keeps old states; `supersedes`/`retracts` give a chain | append-only versions, reverse edges via `neighborhood` | status-change supersession | **Propagation to dependents is not built.** Nothing marks consumers of a changed claim |
| 4 | p.6: "Version responsiveness. Can new evidence alter epistemic status or scope without overwriting earlier states?" | only by publishing a new file | yes within the node | only when someone publishes | a *live* link: a reader of the nanopub cannot learn the node's current state without asking the node (no public node exists yet) |
| 5 | p.8: "Each decision could be recorded rather than collapsed into a single editorial outcome" and p.8 "Competing ontologies and interpretations need not be forced into one score" | no rule either way | seven dimensions, no composite | enforced and tested (no numeric rating) | |
| 6 | p.8: "ASK records the decision, reasons, author, date, and version." | provenance/pubinfo can hold them | reviewer, rationale, version in the record; operator and time only in the Event | all four preserved in the draft, with the digest recipe | author *date* is the node's own clock |
| 7 | p.8: candidate status "must remain visible until source data, executable analysis, or accountable human review confirms the representation" | not addressed | `unreviewed` / `imported_unreviewed` states | only `accepted` is a first publication; imported targets are labelled | |
| 8 | p.9: "a valid place for unknown, disputed, and not applicable" | not addressed | `insufficient`, `not_applicable`, `disputed` | carried verbatim per dimension | |
| 9 | pp.5-6: federation: "No single platform should define or own the scientific state"; alternative interpretations "represented, attributed, exchanged, and audited across interoperable nodes" | registries are federated exchange infrastructure; signatures give integrity | `import_bundle` keeps imported reviews as untrusted claims and detects forks | a node's review becomes a signed, mirrorable claim another node can ingest as *dissent*, not authority | local acceptance policy per node is Frontier's; this layer defines none |

The honest summary: a nanopublication gives immutable, signed, citable *snapshots*. ASK's added requirements are about what happens *between* snapshots (status change,
scope-governed reuse, propagation, contestation across nodes). Frontier is where those live; the publication layer can only export snapshots and corrections of them.

## 6. Facts about Frontier found while binding (for the Frontier owner; unchanged by this work)

1. `Store.get` returns only `status` and `policy_version`; it does not expose `submitter_operator`. The operators needed for provenance exist only in Event records (`events()`), so the layer reads the event log. `events()` has no per-target filter, so collection scans pages (bounded, 200 pages).
2. The `Assessment` record has no operator or review time. They are in the `review_recorded` Event (and the `reviews` table); `export_bundle` includes `review_claims` but not Events.
3. For an imported target the store's independence test compares the *importing* operator, not the origin's. The draft says so.
4. `witnessed_at` is the node's database clock. It is not a witnessed or anchored time in the sense of Frontier's own `TimeClaim.basis`.
5. Review-last-wins state (section 4).
6. `Claim.prior_review` is a free `dict`; the layer does not publish it.

## 7. Commands actually run (all local; bounded with `systemd-run --user --scope -p TasksMax=128 -p MemoryMax=4G -p MemorySwapMax=0 -p RuntimeMaxSec=600`)

- `git -C delphi-frontier/foundation archive 42cd967 …` into the session scratchpad (read-only extract).
- `bash scripts/frontier_pub_pg.sh python3 scripts/frontier_pub_make_fixtures.py tests/fixtures/frontier_pub 42cd967a97be…` -> exit 0, wrote `bundles.json` (7 bundles, one private-record read refused: `Missing: Exact record version unavailable`).
- `FRONTIER_SRC=<extract> python3 -m pytest tests/test_frontier_pub.py -q -p no:cacheprovider` -> **59 passed**.
- Six one-line guard removals (operator independence, head check, IRI vetting, registry test-flag, dimension-reviewer check, ledger fork guard); each made the suite fail (baseline `58 passed, 1 skipped` without `FRONTIER_SRC`).

## 8. What needs the user (nothing below was done)

1. Whether to publish **anything** to a test registry, and which files. The module needs an `Authorization` record carrying the user's own words and the sha256 of the exact signed files. HOST and director messages are not that.
2. Signing identity (ADR-0005). Same-key supersession makes the choice irreversible.
3. Licence (CC BY 4.0 prepared) and whether imported or third-party records may be published at all.
4. The profile IRI target: this file must be merged to `main` first.
5. Time anchoring before any production publish (SPEC-007 rule 16). `ots` is not installed here.
6. Not verified against a real registry: the POST content type (`application/trig` assumed; the registry design document names `POST /` and `201` but not the content type), and the exact status-document flag (`isTestInstance` per SPEC-007's measurement, `testInstance` per the registry design doc; the module accepts either and refuses if any present flag is not `true` or none is present).
7. Fixtures use obviously fake claims. Publishing a *real* Frontier claim needs a real independent review first; this layer will not manufacture one.
