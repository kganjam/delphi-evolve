# Selection decision (DRAFT — criteria frozen before scout reports were read)

Director, Claude Sonnet 5.5, Seattle PDT. Frozen 2026-10-31 06:04 PDT, commit recorded in git history. Scores and selection are filled in only after reading the reports in `planning/rethink/{nca,electric,critic}.md` and the pushed experiments. A candidate's score may not be edited after the selection commit without a dated note.

## Judging frame (live page, re-fetched about 06:00 PDT)

Significance 20 · Scientific/technical impact 25 · Decentralized agency 20 · Collective capability 25 · Execution 10 · +10 for capabilities that materially help other teams. Slides due Sun Nov 1 1:00 PM Boston = 10:00 AM PST. 45% of the score concerns multi-agent organization; the released baseline measured a null there (shared specialists 78/100 = single planner 78/100).

## Hard gates (fail any → candidate cannot be the headline)

- **G1 Independent check.** The headline output is checked by something other than the model/solver that produced it (held-out measured data, independent solver, exact arithmetic or compiled proof).
- **G2 Delphi changes a decision.** At least one existing Delphi claim (hash-pinned) changes a constraint, inference, refusal or experiment choice; a removal/context-change ablation shows the dependence. A citation graph does not count.
- **G3 Collective is measured or not claimed.** Any multi-agent claim has a matched single-agent/ordinary-budget control and a recorded result, including a null. Otherwise the pitch says nothing about collective advantage.
- **G4 Authorized resources only (amended 06:11 PDT after the primary review).** Claude Sonnet tmux sessions are the worker harness. Other model families and credits the user authorized (Codex/GPT, GLM, Grok, MiniMax, Gemini, Nebius LLMs, API keys) may be *measured subjects* of a preregistered comparison, free/subscription capacity first, per-arm tokens and any metered charge recorded, no secret exposure, public data only. GPUs only under the shared-capacity rules and only if they do work a CPU could not do in time.
- **G5 Honesty.** Observed / predicted / simulated / unknown separated; no fabricated measurements or statistics; a simulator is not biological validation.

## Scored criteria (0–3 each; weight in brackets reflects the rubric, not a win probability)

| Criterion | Weight | 0 | 3 |
|---|---|---|---|
| Scientific utility: would a scientist use the output | 3 | cosmetic | changes a design/experiment decision a domain scientist cares about |
| Evidence strength | 3 | self-validating | held-out/independent check passed with controls and negatives retained |
| Novelty vs closest prior work | 2 | reimplements | clear, source-checked gap, honestly bounded |
| Visible result in 20 seconds | 2 | table | one figure/interaction that shows the finding |
| Measurable collective capability | 3 | none/null only | matched-control gain, or a decisively informative measured null with design reason |
| Feasible by 11:48 PM PDT today | 3 | needs unavailable data/credentials | data in hand, probe already run |
| Company/pilot plausibility | 1 | none | specific buyer, workflow and measurable pilot metric (no invented market) |

## Candidates under consideration (status at freeze)

| ID | Candidate | Source | Evidence at freeze |
|---|---|---|---|
| A | Released TrpB query-to-certify, polished (fallback) | baseline | Complete; LazySP-style baseline wins 96/100 vs 78/100; no collective gain; ESM priors no benefit |
| B | NCA / amorphous inverse design with independent-solver evaluation | `rethink-nca` | pending report |
| C | Bioelectric / electrical fabrication / cellular logic | `rethink-electric` | pending report |
| D | Critic's wildcard (Adaptyv/binder data direction observed in pane) | `rethink-critic` | pending report |
| E | **Claims-as-tests / scope-and-falsification**: Delphi math claims (Thompson 18+ shown, pop-gen 18, Turing 3) become operational predictions with declared scope, adjudicated by exact arithmetic/Lean where model-internal and by open data where empirical; geometry/boundary conditions decide applicability (Turing π vs 2π, Rayleigh–Plateau finite length, tree buckling) | director + host memo `2026-10-31-rubric-strategy-from-morphoswarm-8c.md` | Probe run: Thompson ch02-02 vs Tallo (n=496,827; `artifacts/rethink_director/thompson_tallo_probe.json`): pooled log-log slope 0.588, gymnosperm 0.665, angiosperm 0.563, per-study median 0.624 against the claim's 2/3. Data is reachable; the claim splits by clade. |

## Director's pre-commitments about candidate E (so it cannot be favoured silently)

- Known allometry results (McMahon/Niklas-type) mean E has limited novelty as biology; its defensible contribution is an operational, reproducible claim→scope→check pipeline over an existing corpus. Say so.
- The host memo proposes model-family diversity. The primary review corrected my initial reading: other families are permitted as measured subjects (see G4). The comparison must be matched in total tokens/cost against a sequential multi-attempt single-agent baseline.
- Verification asymmetry (1−(1−p)^N) is arithmetic, not a finding. Only an executed comparison counts toward Collective Capability.
- GPUs are justified only for a workload a CPU cannot do in time; exact-math counterexample search is CPU-cheap. Do not launch GPU jobs for optics.
- Decision is not made until the three scout reports have been read.

## Output of this document when completed

Selected concept; headline supported now vs intended; acceptance tests; kill conditions; four-hour build plan; excluded scope; preserved negative results for every rejected candidate.

## Notes added after reading incoming reviews (06:11 PDT)
- Primary review: Thompson ch02-02 is embedded in a self-weight buckling / limiting-height argument; pooled OLS is only a descriptive operationalization. Tallo 2022 already tests the H–D slope against 2/3 with mixed models, so the probe is a reproduction, not new biology. It is retained as an example of an operational-fidelity mismatch.
- Delphi's LLM dataset-resolvability assessments are not ground truth. An 880-row board is coverage, not 880 resolved claims.
- 1−(1−p)^N is not evidence; the comparison must match compute against a sequential single agent.

## Note on host PITCH v2 "operationalization gap" (read 06:16 PDT)
Leading direction E now = *operationalization-fidelity audit*: detect when a test or computation addresses a different proposition than the source claim (envelope→mean, dropped scope, changed estimator/population/units, conditional→universal). Director conditions for this to count as ground truth (not LLM opinion):
1. For claims with a formal core, a mutant is labelled unfaithful only if an exact **distinguishing instance** exists and is machine-checked (the same discipline as the Lean law mutants); an *equivalent* mutant (provably the same proposition) is labelled faithful and included as a harmless-change control. A mutation is not unfaithful merely because we changed text.
2. Empirical-claim pairs (e.g. Thompson/Tallo) cannot have by-construction labels beyond the source passage; they are reported as a separate, human-reviewed set and not mixed into the accuracy figure.
3. Faithful pairs are authored and fixed before any agent sees them; false-alarm rate on faithful pairs is a headline number alongside detection rate; exact binomial intervals are computed, no invented statistics. With ~40 pairs, collective-vs-single differences will likely be inconclusive; the design must say so in advance and the pitch may not claim collective superiority unless the interval supports it.
4. Authors of mutants must be different sessions from the reviewers; reviewers must not see labels; the answer key is hashed and committed before reviewer runs.
Closest-work caveat: LLM-as-judge faithfulness/specification-checking and mutation testing exist; the gap, if any, is applying mutation-labelled checking to *scientific claim → operational test* with sound verifiers. Not yet source-checked for prior art — the critic is asked to do this.
