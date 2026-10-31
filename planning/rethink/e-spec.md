# Candidate E working spec — source-to-test mismatch audit with applicability scope

Status: DRAFT proposal, not selected. Author: director. Combines host PITCH v2, critic memo 1 §7 (kill gates), and primary reviews (`primary-selection-review.md`, `primary-operationalization-benchmark.md`). Nothing here is a result.

## The task, stated precisely

Input: a source claim (Delphi record hash + the original passage's assumptions) and a proposed test or computation of it (a *proposed operationalization*: estimator, population, scope, units, quantifier, data/model).
Output (frozen schema): `verdict ∈ {faithful, mismatch, underdetermined}`; for `mismatch`, the **source-supported diagnosis** (which element differs and quoted source text), and a **repaired test or a specific missing-information request**. Diagnosis correctness is scored separately from merely flagging a mismatch.

This is *not* judging whether the biological claim is true, and a changed estimator is not automatically a fault.

## Ground-truth rules (binding)

1. **Faithful base pairs:** author-written, each justified against the source passage in a one-line rationale, reviewed by a second session before the key is hashed.
2. **Consequential mutations only:** a mutant is labelled `mismatch` only if a *distinguishing instance* exists (exact arithmetic / counterexample / independent solver) where the base and mutant propositions disagree. For non-formal claims, mutants need two-reviewer agreement and are reported in a separate stratum, not mixed into the headline accuracy.
3. **Benign controls:** provably equivalent edits (reparametrisation, units, notation, ordering) labelled `faithful`; minimum count ≥ 30% of items. Report false-alarm rate on faithful items as a headline number.
4. **Ambiguous items** are excluded from accuracy and listed with reasons.
5. **No shortcuts:** randomised position, matched length and formatting, no label-bearing filenames/words; a deterministic "length/format/position" baseline must score at chance.
6. **Split by claim family** (not by variant). Whole families held out for any prompt tuning. The key and mutation code are hashed and committed before any agent run; agents never see them.
7. A local synthetic-fault benchmark does **not** establish field false-positive/negative rates; slides say "benchmark of N items across F families".

## Baselines and arms (matched total input+output+tool tokens, checker cost counted)

- B0 deterministic scope checker (rule/regex + exact check where a formal verifier exists) and a one-pass retrieval baseline.
- S: one agent, sequential attempts with checker feedback.
- P: N independent parallel samples, majority/checker select.
- C: role-separated agents with different access (source reader / formalizer / adversarial mutator / data prober) pulling tasks from a shared append-only log; assignment recorded to show no dispatcher chose it.
- Optional D: model-family arm (measured subjects; authorization per primary review; budget and public-data constraints in DECISION G4).
Report accuracy, false-alarm rate, diagnosis correctness, repair usefulness, and error correlation between arms with exact binomial intervals. No claim of collective superiority unless the interval supports it; a null is reported as a null.

## Minimum content before selection holds (kill gates, from the critic and primary)

K1. ≥ 8 non-trivial formal families (Turing finite-domain, Rayleigh–Plateau, Kimura regime, Hawk–Dove, Greenhill uniform vs tapered, Hamilton's rule form, KPP speed, LMC sex ratio, …) each with a verified distinguishing instance for every labelled mutant.
K2. ≥ 120 labelled items, ≥ 30% benign, family-held-out split, ambiguous exclusions listed.
K3. A Delphi-record ablation (remove/alter the scope record or its hash) that changes a decision on ≥ 3 instances, measured — not only a refusal-by-hash.
K4. A matched-budget S/P/C comparison executed once, protocol frozen first.
K5. At least one *repaired test* that a scientist could use, with the descriptive vs mechanical operationalizations kept separate (Thompson/Tallo is the worked example: pooled OLS, SMA, 99th-percentile envelope, Greenhill bound with assumed E/ρ).
K6. Public CLI/service that fails closed on a mutated request (the +10 packet); outside use is observed, not claimed.

If K1–K3 are not met by the review gate, fall back to candidate A (hardened baseline) and say why.

## Ownership if selected (one writer per checkout)

- `rethink-critic` worktree: independent audit of every base pair and key; red-team; deterministic baselines.
- `rethink-nca` worktree: formal verifier layer (exact-arithmetic distinguishing-instance generators; Lean for Turing/Hawk–Dove/Kimura where tractable).
- `rethink-electric` worktree: agent-arm runner, token accounting, shared commons log, analysis.
- Director: integration branch, spec/key freeze, final artifacts and site/pitch.
- Host (`morphoswarm-8c`): dx-corpus pair authoring in its own worktree and the submission-channel/+10 logistics; fleet capacity only under written briefs.
