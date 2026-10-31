# Preregistration — verified-library experiment (written before any scored run)

Written 2026-10-31 (Seattle PDT) on branch `work/guilds`. Pilot runs (3 targets commons; 4 hardest core targets
single-library-less) preceded this file and are reported separately as pilots, not as results.

## Question
At a **matched total budget of model calls** (each call is followed by exactly one Lean-kernel compile) and a
matched safety cap on tokens, does a **shared** verified library raise the number of frozen Lean targets
certified, or reduce calls/tokens/time to certify them, relative to (P) **private** per-agent libraries,
(Q) one **sequential** agent with a persistent verified library, (N) no retention, and (D) deterministic tactics?

## Prior art and what this is NOT (binding wording)
Shared/growing lemma libraries are published (LEGO-Prover, LeanAgent, Prove Together; architecture credit
Prove2Me arXiv 2608.28433). Berlot-Attwell arXiv 2504.03048 re-evaluated LEGO-Prover and found no direct reuse in
final checked proofs and the headline advantage disappearing after compute adjustment. A sequential agent can
retain and reuse its own lemmas, so no structural advantage of sharing is assumed. This experiment is a small
**replication-style measurement on our own frozen set**, not a new mechanism. A null is the expected-plausible outcome.

## Frozen inputs (hashed before running)
- `targets/targets.json` (19 statements, Turing finite-domain / generic quadratic / Hamilton / Hawk-Dove, core Lean
  4.35.0, no Mathlib), `targets/Defs.lean`, `CONTRACT.md` (the single prompt contract). Hashes: `targets/VALIDATION.json`
  and `FREEZE.sha256`. Statements were written by the experimenter, not by any prover agent; agents cannot alter them
  (the checker inserts the frozen statement text). **No independent statement-fidelity review has been done yet**; these
  are integer-arithmetic surrogates of textbook conditions, not claims about biology.
- Every reference proof compiles with axioms ⊆ {propext, Classical.choice, Quot.sound}; every law mutant (a false
  statement) is rejected when the reference proof is replayed (`targets/VALIDATION.json`). Reference proofs are held
  out from agents.
- Acceptance: Lean kernel only; `#print axioms` clean; text scan rejects `sorry`, `native_decide`, new axioms/defs/
  instances/macros/attributes/`set_option`. No LLM judges anything.

## Arms (same model for S/P/Q/N: Claude Sonnet 5.5 via the managed Max allocation, account recorded per call)
| Arm | Agents | Library the prompt shows |
|---|---|---|
| S shared | 3 parallel, pull-claiming from the frozen order | every verified theorem any agent wrote |
| P private | 3 parallel, same board | only that agent's own verified theorems |
| Q sequential | 1 | its own verified theorems (persistent) |
| N none | 3 parallel, same board | nothing retained (base library only) |
| D deterministic | 0 (no model) | fixed tactic scripts; previously certified targets as `grind` hints |
Board (claims/proved/failed) is shared in all model arms, so arms differ only in lemma text visibility.
Heterogeneous variant (M-S, M-P): one agent per live family — claude, gpt, gemini, glm, minimax — same board,
shared vs private library, same call budget. Grok is unavailable (managed account rate-limited to 2026-11-03).

## Budget and protocol
- **Primary budget: 30 model calls per arm-run** (retries after a transport failure are not extra calls; a call
  that returns nothing usable still counts). Safety token cap 400,000 per run (1,200,000 for heterogeneous runs, where
  harness overhead differs by family — codex alone adds ~10k cached input tokens per call).
- Targets are claimed in frozen order (T01…H04…); a target may be claimed at most twice; each claim allows up to 3
  model calls (initial + 2 compiler-feedback repairs). All of this is identical across arms.
- Replicates: 3 per arm (independent runs, fresh stores). Order of arm execution randomized once; runs recorded.

## Outcomes (all reported, none dropped)
1. **Primary: number of the 19 targets certified within the call budget**, per run; arm medians and ranges.
2. Secondary: calls and tokens to the k-th certificate; wall seconds to completion; targets never certified.
3. Mechanism check: for each certified proof, whether its final checked text references a library theorem
   (direct reuse), by author — cross-agent reuse is possible only in S. If direct reuse is ~0 the library cannot
   be credited with any difference.
4. Per-family coverage in heterogeneous runs, and format-compliance failure rate per family.
## Analysis plan
Descriptive only (R=3 per arm; no p-values). A difference is called a *gap* only if every replicate of one arm
exceeds every replicate of the other on the primary outcome; otherwise it is reported as a **null / inconclusive**.
Ceiling rule: if all arms certify all 19 within budget, the primary outcome is uninformative and calls-to-complete
is the headline; this is stated, not hidden. Token counts are provider-reported gross tokens (uncached + cache
read + cache creation + output); cost basis is subscription (CLI list-price figures are estimates, not spend).
## Stopping
Runs stop at the call budget, token cap, all targets certified, or no claimable target. No run is discarded after
seeing its result; infrastructure failures are logged and rerun with the failure kept in the record.

## Addendum A (2026-10-31; written after seeing only the aborted run's partial per-family call success counts, before any completed heterogeneous result)
The five-family heterogeneous run `MP_r1` was started and ABORTED after ~90 s: the managed `codex_outlook`
allocation became unavailable (`orchestra auth` shows "available: NO"), so every GPT call failed with
"no managed allocation available for 'codex'" and consumed budgeted calls. The aborted run is kept unaltered in
`artifacts/commons/aborted/`. Deviation: the heterogeneous arms (MS, MP) are rerun with the four families that
have a live allocation — claude, gemini, glm, minimax — and the same 30-call budget; GPT and Grok are recorded as
unavailable. The GPT adapter itself was verified live earlier (served model `gpt-5.6-sol` read from the codex rollout file).

## Addendum B (2026-10-31; after viewing partial per-family outcomes of the second aborted heterogeneous run)
In that run Gemini 3.8 flash returned `finishReason=MAX_TOKENS` on 4 of 7 calls because hidden thinking tokens
(1.5k–4.8k) consumed the 2,500-token output cap that the adapter applied to every family. That is an adapter handicap
on one family, not a measurement of the model. Fix: the Gemini adapter now adds 8,000 tokens of thinking headroom
(thinking tokens are still counted in the ledger). The aborted run is kept in `artifacts/commons/aborted/`. The
heterogeneous arms are rerun from scratch under the same registered call budget; the same-model runs (S, P, Q, N, which
use the Claude CLI and never hit an output cap) are unaffected.

## Addendum C (2026-10-31 07:40 PDT; after seeing partial per-family latencies of the third aborted heterogeneous run)
In that run all 3 real-prompt GLM calls (`glm-4.5` via the managed `glm_kg` key, z.ai Anthropic-compatible endpoint)
timed out at the adapter's 240 s limit with 0 tokens returned, although a one-line probe earlier succeeded in 2.5 s;
an orphaned GLM process from the previous aborted run was also still waiting after ~19 min. Each stuck claim costs ~12
wall-minutes (3 retries), which makes the registered 6 runs infeasible. GLM is therefore EXCLUDED from the heterogeneous
arms and recorded as "endpoint unresponsive for real prompts, cause not diagnosed (rate limit vs outage unknown)".
Heterogeneous arms now use claude, gemini, minimax at the same 30-call budget. Evidence kept in `artifacts/commons/aborted/`.

## Addendum D (2026-10-31, written AFTER all 12 registered same-model outcomes were observed): checker repair and re-scoring
Everything above this line, including the original same-model protocol, results and Addenda A–C, is unaltered. This addendum is
post-outcome and says so. Nothing in it was prospective for the 12 runs already observed.

**Defects found by independent review (Codex, against commit feb5dbd) and repaired in commit b349bb2 or later:**
1. *Target weakening.* Helper text containing `variable (h : False)` + `include h` made a frozen `False` elaborate as `False → False` and pass the
   axiom audit. Repair: the trusted checker now compares the target constant's ELABORATED type, by exact expression equality, with the elaborated
   frozen statement (`#fid`), in addition to rejecting `variable/include/omit/section/namespace/open/def/...` and requiring helpers to be a sequence of
   top-level `theorem` declarations. Both layers are tested independently (the type comparison rejects the attack even with the text scan bypassed).
2. *Non-atomic budget.* Two in-flight reservations of 60 passed a cap of 100. Repair: `TokenLedger.reserve_tokens` holds budget under a lock and
   `record` releases it; reservations are sized from the actual prompt length plus output allowance. Tested with a two-thread race.
3. *Reuse by source regex.* Repair: dependencies are read from the accepted theorem's kernel term (`ConstantInfo.thmInfo.value.getUsedConstants`),
   intersected with the library names that were in scope. The extractor first returned an empty list for every proof (`value?` is `none` for theorems);
   this was caught by a positive control (reference T05 must depend on T02) which is now a permanent test, and the first audit outputs were discarded to
   `artifacts/commons/aborted/audit_v1_dependency_extractor_defect/`.
4. *Publication order.* Helpers were stored before the replay, and the replay saw them twice. Repair: the full candidate closure is replayed first
   (existing library + candidates, fidelity-checked target) and published atomically under one lock (`Commons.add_many`); a failed replay publishes nothing.
5. Worker exceptions now leave `agent_exception` rows, and summaries carry `status` (`clean` | `infrastructure_incident`) and the count of infrastructure-failed calls.

**Re-scoring of the 12 registered runs** (zero model calls; `python -m lean_commons.audit`, `rescore_report`; `artifacts/commons/runs/RESCORE_SUMMARY.json`):
every accepted proof (228) was reconstructed with the library it saw, recompiled with the repaired checker including the exact-type check,
and replayed against its paired false mutant. **228/228 re-certify; 0 reconstruction failures; 0 mutants accepted; 0 helper-structure violations.**
A text scan of all 357 parsed model responses on disk (including pilots and aborted runs) found no use of `variable`, `include`, or any non-theorem
helper; the one forbidden-token hit was a `sorry` that was already rejected. So the loophole was NOT used by any recorded response, and the registered
outcome (19/19 in every arm) is unchanged. Proof-term library dependencies equal the old regex counts exactly (per-run in RESCORE_SUMMARY.json):
this removes a measurement concern but does not by itself make reuse causal.

**What the mutant replay does and does not show.** A reference/agent proof failing on a mutated statement shows the proof depends on the statement's
content; it does not prove the mutant false (the mutants were chosen as false statements by hand, and Q01's first mutant was true over ℤ and was
replaced before the freeze). It is a guard against vacuous green, not a proof of fidelity.

**Wording constraints adopted from review** (binding for any slide): the 12 runs are *call-matched* (30 model calls per run; tokens, wall time and compiler
time are reported, not matched); the 19 statements are integer-arithmetic *surrogates* of textbook conditions (not biological laws, not the Mathlib 21-record
scorecard); D02 `hawk_ess_iff_V_gt_C` is a strict payoff-advantage statement (its name overstates ESS); `Hurwitz` is the defined sign predicate; H02 is a
definitional rearrangement. The original text "every call is followed by exactly one compile" is corrected: format failures, transport errors, replay and the
fidelity check add compiles or none. Lean is run with `-j2`; the registered launcher used a 1500 s scope, above the project's 600 s contract (actual runs
took 59–220 s). Heterogeneous (multi-family) arms were NOT completed: they were stopped by the director's hold after the checker finding and are not scored.
