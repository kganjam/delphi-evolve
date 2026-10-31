# Scope verdicts as nanopublications: state, design, gates

**Status (2026-10-31 PDT): PREPARED, NOT PUBLISHED.** Nothing has been posted to any registry, test or production. No nanopublication of ours exists on
the network (read-only SPARQL probe: 0 rows for our profile). Publishing is an irreversible outward-facing act and is held for explicit authorization.
This document is also the profile IRI cited by every prepared nanopub (`dct:conformsTo`), so it must be merged to `main` before any publish.

## 1. What actually existed (verified, not assumed)
| Item | State |
|---|---|
| `claim_runtime/trig.py` and `artifacts/{claim_reuse,evidence}/nanopubs/*.trig` | **Unsigned local drafts**: temporary URIs, `urn:x-delphi-evolve:vocab#` terms, `de:signatureStatus "UNSIGNED DRAFT"`. They **cannot be published as written**: SPEC-007 rule 7 forbids `urn:` IRIs and rule 5 forbids minting into an unregistered namespace. Left untouched. |
| Delphi's own claims on the network | **Real and signed.** `turing-ddi` is published as `https://w3id.org/np/RAaQ-9SCjYC7GBJ0ZtrPcVNxZBB7z-VNAdWa8ImGAi610` (signed by Delphi's author ORCID, CC BY 4.0, 2026-10-30). Fetched from the production registry (HTTP 200) and saved in `artifacts/falsify_np/`. Its trusty hash and signature verify with `@nanopub/sign` 0.2.0 (positive control; a one-character edit fails, negative control). `delphi_get_claim id=turing-ddi source=network` returns content that our adapter's pin accepts (`changed_fields: []`), so the verdict below may cite this exact nanopub. Earlier turing_scope work used only the `local` record. |
| Knowledge Pixels query | `https://query.knowledgepixels.com/repo/full` (Nanopub Query) answers read-only SPARQL; `npx:introduces <turing-ddi>` finds the Delphi nanopub. Nanodash is the human UI. |
| **"Ask"** | **Not verified.** I found no product called Ask on knowledgepixels.com, query.knowledgepixels.com or by web search; `ask.knowledgepixels.com` does not resolve. The verified query surface is Nanopub Query. If Ask is a layer over it, correctly published verdicts become askable with no extra work; if it is something else, Ashley Caselli (Knowledge Pixels) would need to say what. No contact was made (director ruling: no outreach without a user instruction). |

## 2. Design: one verdict = one nanopublication
Profile `scope-desk-verdict v0` uses **no new ontology terms** (nothing irreversible is minted): schema.org `ClaimReview`/`Rating`/`PropertyValue`, PROV, Dublin Core, RDFS and nanopub-core terms only.

| Requirement | Where it lives |
|---|---|
| Classical result | `schema:itemReviewed` and `prov:wasDerivedFrom` = the published Delphi nanopub URI above; statement quoted in the rating explanation |
| Parameter regime | `schema:PropertyValue` rows: Jacobian, diffusivities, dimension, boundary, length(+unit), kinetics source, and `regime_sha256` (hash of the regime and proposition only, no caller identity) |
| Verdict | `schema:Rating/alternateName` = `survived` or `refuted`; `verdict` and `outcome` properties; fixed formal `schema:claimReviewed` (the proposition: some admissible mode has strictly growing linear eigenvalue) |
| Witness | exact-rational unstable-mode witnesses (index, q, trace, determinant), the verified critical-length bracket, agreement flags of the two independent checks (adapter, finite-difference eigenvalues), and the receipt id. **Lean witness fields exist but are HELD** (see 4). |
| Provenance | software agent = this repository; `prov:wasDerivedFrom` the exact commit tree of `falsify/`; pin check hash of the cited Delphi record; engine version |
| Queryability | `dct:conformsTo <this document>`, `npx:hasNanopubType schema:ClaimReview`, label `Scope verdict: turing-ddi on regime <hash12>: <outcome>`; SPARQL builders `q_by_regime`, `q_all_verdicts` in `falsify/nanopub.py` |
| Corrections | a NEW nanopub with `npx:supersedes` (same key); `build_retraction` for `npx:retracts` |
| Never in a nanopub | caller-supplied claim text, caller labels, unresolved/refused results, generic (pin-failed) calculations, anything without a pushed 40-hex code commit |

Evidence typing is unchanged: every number is model-derived; observed = none; linear stability only; no nonlinear, biological, wet-lab or clinical claim. Nulls (`refuted`) are published on equal terms with positives (SPEC-007 rule 20 spirit).

**Reuse by other teams.** Before relying on a certified regime: `python3 -m falsify np-lookup request.json` runs the read-only query. A hit is a pointer, not proof: fetch the nanopub, verify the trusty hash and signature, and decide whether to trust the signer. Honest note: this engine recomputes in milliseconds, so the commons adds **citability, provenance and discoverability**, not compute savings.

**Decentralization claim, scoped.** Once published, anyone can mirror, query and verify these records without our server; ours is then one signer among many. Today there is **no commons**: zero records published. Do not describe it as one.

## 3. Commands that were run (all local or read-only)
Build + conformance + local signing with a throwaway key kept outside the repo: `python3 -m falsify np-build artifacts/falsify_np/requests/neumann_L2pi.json --commit 09b895f62f230edb39cd433e19f10fda3275a60b --created 2026-10-31T14:15:00Z --out-dir <dir> --sign-local-key ~/.nanopub/collab-throwaway/rsa.pem`. The signed copies are **verification only** (throwaway key, filename says NOT-FOR-PUBLICATION) and are not committed. Prepared drafts: `artifacts/falsify_np/prepared/L{1,2}pi/unsigned.trig`.

## 4. Gates and decisions for the owner (nothing below was done)
1. **Signing identity** (morphoswarm ADR-0005 is OPEN; same-key supersession makes the choice irreversible): ORCID vs a bot introduced per Knowledge Pixels' pattern. Required before any publish.
2. **May a throwaway-identity publish to the TEST registry happen?** (ADR-0005 D1, untaken.) Test is not proof of production acceptance; the test registry has no trust layer. Procedure when authorized: `GET <registry>/.json` must say `isTestInstance: true`; post one at a time; fetch back with `GET` + `Accept: application/trig`, verify hash/signature with a second implementation; record `stage: test`.
3. **Production publish** only after (2) succeeded for the same bytes, a human go, `dct:created` re-pinned within 60 s of posting, a time anchor submitted (OpenTimestamps; the `ots` client is not installed here, so none exists yet; pending is not a confirmed anchor, RFC-3161 is weaker), and merge of this document to `main` so the profile IRI resolves.
4. **Lean witness**: SPEC-007 rule 21 holds every Lean result until a gate-verdict term exists. Fields are built only with `--include-lean` for local inspection. Override is the owner's call.
5. **Licence** (prepared as CC BY 4.0 to match the Delphi record) and whether third-party-submitted regimes may be published at all (default: no; the requester would have to opt in).
6. **What "Ask" is**, and whether to tell Knowledge Pixels (outreach: needs a user instruction).

## 5. Interface to the Scope Desk
`falsify.nanopub.record_from_response` is the only coupling: it takes a verdict dict and raises `NotPublishable` unless it is decided, pin-verified and tied to a pushed commit. When the director hands over the Scope Desk response shape, add one adapter producing the same record fields; the builder, conformance, signing and query code are interface-independent.

## 6. Convergence pass 2: what it changes here, and three conflicts to resolve (2026-10-31)
Built (this lane, exact arithmetic, tested): `diffusion_requirement` in every response: the exact bracket of D_inhibitor/D_activator the textbook band needs for the caller's kinetics (the textbook example needs exactly 9, supplied 10), "no ratio suffices" when neither species self-activates, the Stokes-Einstein consequence (bare ratio R needs mass ratio R^3, so 729:1 here), and an optional comparison with caller-declared protein masses. It is recorded in the nanopub as a `PropertyValue`. It makes no claim about real tissue: effective diffusion also depends on binding, hindrance and dimerization, and no literature value (e.g. for Nodal/Lefty) has been checked here; that is the OpenResearch grounding task.

Not built here (other roles / not authorized): the factor graph, the Beta-Binomial basin posterior, the dual-solver H100 sweep, ESMFold/Boltz-2 radii (GPU jobs belong to the gpu worker), the three-arm Lean experiment.

Conflicts for the director/owner:
1. **Lean proof hash in published nanopubs vs SPEC-007 rule 21.** The spec wants the Lean hash published; rule 21 holds every Lean result until a gate-verdict term exists. Our builder holds it by default. Overriding is a decision, not a default.
2. **Solver-agreement score and updated pattern probability.** The v0 profile can carry them as `PropertyValue` rows with no new namespace, but only once real solver runs and a real posterior exist. None do today, so none are written; the builder will not accept invented values.
3. **"First machine-checked formalization of Turing instability."** What the repository's Lean proves is finite-mode determinant/trace algebra and a tail bound, with Routh-Hurwitz taken as a *definition* (`Hurwitz T D := T < 0 ∧ 0 < D`); the eigenvalue equivalence, the PDE and the Neumann spectrum are not formalized (see `turing_scope/lean/TuringScope/Basic.lean`). Whether that is "first" is a prior-art question I have not searched. The claim should be scoped to what is proved.
Also: a Lean clamp `F=0` is a statement about the linearization at the declared homogeneous state under those definitions; the "subcritical finite-amplitude instability" re-indexing is legitimate only for a pattern found by the solvers at that same state.
