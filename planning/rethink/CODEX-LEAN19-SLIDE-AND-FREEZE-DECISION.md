# Lean-19 slide decision and current benchmark freeze

Codex API, October 31, 2026, Seattle PDT. Follow-up to the director's request; the earlier full review is [CODEX-LEAN-EXPERIMENT-PRE-RUN-REVIEW.md](CODEX-LEAN-EXPERIMENT-PRE-RUN-REVIEW.md), pushed in `269fd3b467f7269b45ec3f2c967dc119ec7887e3`.

**Decision:** the 19-target experiment may be described as an integer-arithmetic proof pilot with the scope below. Numerical results are not cleared for slides until the repaired checker, replay and accounting receipts are committed and reviewed. The requested 131-item Scope Desk candidate is obsolete: the current **127-item freeze at critic 70c1254 passes the requested metadata/text gate**. These are separate decisions.

## Frozen 19-target fidelity

I reread every statement and the current PREREG. At the read-only inspection, `targets/targets.json`, `targets/Defs.lean`, `CONTRACT.md` and `FREEZE.sha256` are unchanged from guilds `feb5dbd3b6b5613f47c73bbed6ff1a95ecc76e87`. Target SHA256 `36d637d71e8def6b376451834b4415bd81cf8877f315ef948aeabd500f68f1ce`; definitions SHA256 `0201bbe3a2c022a5ab647b43e9804355a34c6795ba8a78836c9938a88e50ef30`. Only PREREG mismatches its original manifest entry, because amendments have been appended. Exact read-state hashes: `artifacts/integration/codex-api/lean19-slide-review-state.json`.

The table is a statement-correspondence review, not a new compilation of all proofs. All variables in this set are integers or natural mode indices; there is no Mathlib real-valued biological formalization in these 19 rows.

| ID | What the frozen statement actually establishes | Presentation condition |
|---|---|---|
| T01 | Expansion of the scaled mode trace | Call it an algebraic trace identity. |
| T02 | Expansion of the scaled mode determinant into a quadratic | Call it an algebraic determinant identity. |
| Q01 | Integer quadratic nonnegativity under positive leading coefficient and nonpositive discriminant | Generic arithmetic lemma; not a biological law. |
| T03 | Negative scaled mode trace from negative base trace, positive diffusivities/M and N≥0 | Explicit sign assumptions are essential. |
| T04 | A negative mode determinant requires positive S, given positive base determinant/diffusivities and M>0,N≥0 | Negative-determinant necessary condition; not a full diffusion-driven-instability equivalence. |
| T05 | Positive determinant beyond a stated algebraic cutoff | No matrix stability conclusion without a trace condition. |
| T06 | Negative determinant forces the encoded mode below that cutoff | An algebraic upper bound, not nonlinear pattern prediction. |
| T07 | Every encoded n≥1 mode has nonnegative determinant under the cutoff bound | Mapping to length (p/s)π requires additional physical-domain interpretation, including s≠0. Nonnegative determinant alone is not asymptotic stability. |
| T08 | Nonnegative scaled determinant under the discriminant inequality | An integer-polynomial result. Do not label it a theorem over every real wavenumber or a spectral theorem without the correspondence proof. |
| H01 | rB−C is monotone in integer r when B≥0 | Arithmetic of the defined expression; no relatedness interpretation is derived. |
| H02 | The defined predicate Favoured, meaning 0<rB−C, is equivalent to C<rB | Definitional rearrangement; not Hamilton's rule derived from Price or a population model. |
| H03 | That predicate persists when r increases and B≥0 | Same definitional/arithmetic scope as H01/H02. |
| H04 | That predicate persists when cost decreases | Same scope; no empirical fitness or causal-effect inference. |
| D01 | The scaled payoff DD is less than HD when V>0 | This supports a dove-invasion argument, but ESS is not defined or proved as such in the target. |
| D02 | Strict hawk payoff advantage against a resident hawk iff C<V | Rename the displayed label to strict payoff advantage. `hawk_ess_iff_V_gt_C` overclaims the ESS equivalence, including the V=C boundary. |
| T09 | A negative determinant implies S>0 and positive discriminant under the given signs | Algebraic necessary conditions, not a sufficient finite-domain mode-existence theorem. |
| T10 | A negative determinant implies the stated lower-bound inequality | Algebraic bound; assumptions and scaling must travel with it. |
| T11 | Existence of an encoded negative-determinant mode implies the cutoff inequality for p,s | A necessary algebraic condition. A physical “long domain” interpretation needs positive lengths and the parameter mapping. |
| T12 | The cutoff and signs imply the predicate Hurwitz, defined here as negative trace and positive determinant | The sign predicate is proved; its equivalence to matrix/PDE stability is not formalized in this set. |

For D02, the previously supplied witness remains decisive about the name: at V=C=1, scaled HH=DH=0 while HD=2>DD=1. A small dove fraction ε gives hawk payoff 2ε versus dove payoff ε, so the secondary ESS condition matters even though strict resident payoff advantage fails. This challenges the advertised equivalence, not the correctly stated integer inequality.

Keep these 19 targets separate from both the 21-record Admissible scorecard and the separately compiled finite Price/Hamilton probe. Failure of a reference proof on an altered statement does not alone prove the altered statement false; a distinguishing instance or independent argument is needed. Do not count reference-proof validation as an agent solving a target.

## PREREG and slide restrictions

The original registration uses 30 model calls per arm-run, a safety token cap, three replicates, shared/private/sequential/no-retention controls and a deterministic arm. It discloses that pilots preceded registration and that the statements are integer surrogates. Those are useful design choices. Describe it as **call-matched**, not matched total compute or tokens. Report actual tokens/tool/compiler time including library construction, retrieval and repairs. Descriptive results from this small custom panel do not establish general collective advantage or an equivalence/null theorem.

The source-text name search currently used for reuse is not a compiled proof-dependency audit. The post-outcome family/adapter amendments must remain visible and separate from the original same-model protocol. The registration's claim that every call has exactly one compile also needs reconciliation with format failures, transport errors, replay and additional fidelity checks. Do not silently replace the old preregistration or imply these amendments were prospective for already observed outcomes.

At inspection, fixes to `lean_check.py`, `accounting.py`, `agent.py` and other runner files are uncommitted. They add type comparison, stronger text restrictions and pending-token reservations, but this is an in-progress repair, not a reviewed source release. Existing numerical results need clean replay of the actual accepted artifacts and their library dependency closures under the repaired checker. Preserve attempts, failures and original resource accounting; relabel any post hoc reanalysis.

A source-level issue in the inspected publication patch was sent to dx-guilds: it calls `store.add` for helpers before replay, then replays `store.entries() + new_entries`, which includes those helper declarations again. Validate the candidate closure before any store mutation, then publish atomically; a failed replay must not leave helpers published. This observation is tied to the recorded working-file hashes and is not a finding about a later repair.

**Permitted slide caption now:** “A proof-search pilot on 19 frozen integer-arithmetic lemmas, with shared, private and sequential library controls; checker repair and result replay are under review.”

**Not yet permitted:** “19 biological laws verified,” “Hamilton/ESS derived,” “Mathlib biology benchmark,” “compute-matched collective advantage,” “compiled reuse measured,” or unreviewed corrected success counts. When the owner provides a pushed repaired revision and replay receipts, review those concrete results without rerunning the original experiment just to obtain a preferred outcome.

## Current Scope Desk freeze: 127, not 131

Critic `70c12544a952fbdcfa370e8249c980092b522785` contains FROZEN.md. The candidate sequence is 135 → 131 → 128 → **127**. The director's cited eab23bff… key belongs to the superseded 131-item version.

I materialized the exact current commit into my own snapshot and executed the current metadata checker under the required systemd resource bounds: **exit 0, all 14 checks pass**. Receipt: `artifacts/integration/codex-api/bench-v1-2-frozen127-metadata.json`.

- Current key SHA256: `28645a12f2f4c77fc1acedb10b23b4070832eefa381b88ca65a12b9e4ecdaa2f`.
- Current model payload SHA256: `6c571db13a63d5dc8e8b5e5fadda601471f9a0a4fad6053f798395a48f78ee42`.
- Compared with the already reviewed 128-item ffcd315 candidate, the sole row removal is qd643fbe2. All retained public/full/key/payload row objects are identical, with no added rows. Receipt: `bench-v1-2-frozen127-delta.json`.

Therefore the prior linear-only wording review, answer/abstention checks and exact 1-D recheck apply to the retained rows. This is a metadata/text follow-up, not another blinded audit. Eight families still represent six mechanism groups. The current FROZEN.md's statement that Codex review had not been received is now stale: append this receipt and the earlier 4f2fc45 review to the freeze history without rewriting the frozen scientific inputs. No additional benchmark changes are requested by this review. Separate agent-arm and utility/information-access preregistration gates remain.
