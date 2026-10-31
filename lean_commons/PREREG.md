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
