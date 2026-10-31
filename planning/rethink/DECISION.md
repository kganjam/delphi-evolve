# Selection decision

Criteria and gates below the line "Frozen criteria" were written before the scouts' reports and are unchanged. The selection section directly below was written after reading the critic memo + red-teams, the host's three memos, the primary's reviews, and the NCA frozen protocol (NCA/electric final reports still pending; they can change the *repair/PDE* stage, not the spine, unless a kill condition below fires).


Director, Claude Sonnet 5.5, Seattle PDT. Frozen 2026-10-31 06:04 PDT, commit recorded in git history. Scores and selection are filled in only after reading the reports in `planning/rethink/{nca,electric,critic}.md` and the pushed experiments. A candidate's score may not be edited after the selection commit without a dated note.


## SELECTION (director, recorded 06:24 Seattle PDT, Sonnet 5.5)

**Selected: "Scope Desk" — a scope-and-repair checker for mechanistic-biology claims, evaluated by a matched-budget agent comparison against deterministic and pooled-information baselines.** It is candidate E narrowed (critic ranking 1), absorbing the host's "market-mini" as the *scoring format* (calibrated verdict probabilities, Brier/log score, settled by non-LLM oracles) but not as a new platform, and absorbing the primary's "end with a repaired test" requirement.

One coherent story (end to end, one domain, one second example):
1. **Request.** A scientist/agent asks to design or test a classical claim in a stated situation, e.g. "produce a Turing pattern of wavelength lambda* on a 1-D domain of length L with these kinetics" (core domain, finite-domain reaction–diffusion) — plus, as the second worked example, "test Thompson's d~h^3/2".
2. **Source-linked verdict.** The hash-pinned Delphi record + its declared scope/assumptions decide: `applies` / `out-of-scope (with the violated condition and quoted source)` / `underdetermined (missing information named, e.g. boundary condition)`. Refusal is a graded verdict.
3. **Repair.** For out-of-scope requests, enumerate minimal declared interventions (domain length, reaction scale, diffusion ratio); accept only those the exact check licenses. For Thompson: a correctly labelled descriptive reanalysis (OLS/SMA/envelope kept separate) plus the list of missing mechanical measurements (modulus, density, taper) that blocks a buckling test.
4. **Independent settlement.** Exact rational linear-mode check (formal) then an independent nonlinear PDE solve with convergence checks (simulated). Observed (Tallo) stays a separate, descriptive stratum. Each level is labelled formal / simulated / observed / unknown.
5. **Evaluation (the collective measurement).** Frozen instance set, family-clustered; arms at matched total tokens/tool cost: B0 deterministic scope checker (the Delphi-scoped gate), one-pass retrieval baseline, S sequential single agent with tools and checker feedback, **pooled-information single agent given the union of all tools/evidence**, P N parallel samples, C guild collective with different tools/access coordinating through an append-only commons with pull-based claiming (assignment logged), and a non-agent stacker on the same features. Agents have headroom because instances are given as **natural-language requests** (boundary conditions unstated or ambiguous, kinetics described in prose, scope hidden) so extraction/scoping errors are real and refusal/missing-information is a correct answer.

**Why this over the alternatives**
- A (hardened TrpB baseline): floor; LazySP-style comparator wins 96/100 vs 78/100, collective null, no repair output. Retained as the Execution evidence and honest-negative opening, not the headline.
- B (NCA inverse design): its frozen probe is model-only and simulator-vs-simulator; its value here is the *gated claim + repair stage and independent-solver check*, which Scope Desk reuses. NCA-as-tool stands or falls on its own pre-registered rule; no NCA superiority is claimed.
- C (bioelectric/cellular logic): electric report pending; critic found no measured benchmark path in the time; not selected unless its report shows a settled, data-backed repair story (kill-condition reversal below).
- D (binder triage): fusion failed its frozen rule (AUROC fused 0.61 vs best single 0.68, CI includes 0); pilot only.
- Evidence market as specified by the host: **rejected as specified** (critic six objections, primary review): tier-3 DMS thresholding is ProteinGym-style, LLM contamination of the public TrpB paper, the "orthogonal modality ceiling" is untested (ESM rho 0.17–0.21, fusion null), GPU use would be decorative (100 nonlinear PDE solves to T=1000 = 20.4 s on one CPU thread in the critic's unrefined run; 1e7 Turing screens = 15.5 s), formal tier decidable in ms, information asymmetry without a pooled baseline rewards withholding data from the control. Its reusable parts are kept (Brier/log scoring, frozen claims, matched budgets, null reporting).
- Operationalization-fidelity benchmark as *generic* contribution: rejected as novelty. Primary prior-art review: DriftBench (arXiv 2606.16541), ShadowBench (2608.29270), Benchmarking Agentic Review Systems (2606.19749) already cover drift probes, scope-deletion mutants, bidirectional Lean checks and multi-model complementary detection. Our only claimed gap is narrow: **executable scientific-test repair with checked witnesses tied to a pinned claim's scope**, graded by exact and independent-simulation oracles. Exhaustive novelty search not done; slide text must say so.

**Delphi requirement and the user's direction (verbatim quotes, host-relayed; full page `/data/artifacts/delphi-evolve-rethink/messages/2026-10-31-user-quotes-verbatim.md`, times are when the host session received them, bracketed, not exact).** The user said: *"i dont overly trust the delphi results so far, but they are something at least"* [~06:00]; *"but we might want to use the ideas in delphi in some way. can also look at some of the claims."* [~06:10]; *"just use delphi for inspiration and to help with a fraction of the narrative; we still need something compelling"* [~06:20]; *"lean for bio resonated with some people; the federeate evidence graph, metaculus for bio; notsure how to make these real. now that we have nebius/google we should expand the idea space. leveraging bionemo, openresearch, nvidia, nebius gets us some bonus points as well."* [~06:30]. Reconciliation: Delphi claims are material and scope source, not the headline and not trusted for correctness (the gate cites a record's declared assumptions and verifies the *computation*, never the record's truth); the earlier release requirement for operational reuse is met by the removal/hash-change/misapplication ablation (AT5) as one measured line. The user has low confidence in the market spine ("notsure how to make these real") and an external positive signal for **Lean for biology**: Scope Desk's formal tier is exactly Lean/exact-arithmetic scope certificates with law mutants, and the visible reveal is Lean-checked. **Sponsor bonus:** the user believes BioNeMo/OpenResearch/NVIDIA/Nebius use earns bonus points; the live page lists none (verified twice). We will use Nebius/Gemini/orx where they do real work (model-family arms, CPU/GPU batch if a pilot shows need, orx logging of the evaluation) and report them as used, not as scored.

### Track L (Lean-verified scope certificates + commons experiment) — accepted as a PARALLEL track, not a respin of the spine (director, 06:26 PDT)
Host proposal `2026-10-31-REFINEMENT-verified-commons.md`: formalization subproblems with a sound verifier (Lean), and a clean collective control — same agents, same model, matched tokens, WITH vs WITHOUT read/write access to a shared verified commons. Director's assessment: a cleaner collective test than information asymmetry (the mechanism is lemma reuse, the control is not a strawman) and it carries the one audience signal we have ("lean for bio resonated"). Not novel (growing skill-library provers exist; checking prior art is a condition) and it is the highest-execution-risk item. Therefore:
- Scope Desk stays the spine and the demo. Track L supplies (i) Lean-checked, parameterized scope statements with rejected law mutants for the Scope Desk families (formal tier certificates) and (ii) a second, preregistered collective experiment. Which collective result the pitch leads with is decided at the K-B checkpoint from executed results; both stay in the appendix whatever they show.
- Owner: host `morphoswarm-8c` fleet, in its own worktree/branch, not my three workers. Conditions: statements frozen and hashed BEFORE any agent runs and written by a different party than the provers (agents may not choose or weaken statements); every accepted proof compiled by the Lean kernel with `#print axioms` clean (no sorry/unexpected axioms) and a statement-fidelity review by someone who did not write it; law mutants of each statement must fail to compile or fail the check; counts of attempted/proved/failed theorems reported with tokens; the no-commons arm must not be starved (same retrieval of core library, only lemma sharing differs); a null is a result.
- Mathlib: try `lake exe cache get` (prebuilt oleans) on this host or a worker checkout FIRST; building Mathlib from source on 128 vCPU only if the cache is unavailable for the pinned version; any Nebius job needs gpuops, a live price/stop bound, and a CPU-time estimate from a pilot.
- Time-box: by the K-A checkpoint (12:30) at least 6 families have a frozen Lean statement set and >= 1 compiled certificate each; otherwise Track L is reported as an unfinished appendix and not claimed.

### Headline supported now vs intended
- Supported now: exact linear check (turing_scope: pi vs 2pi flip, Lean-checked algebra); Tallo descriptive probes (OLS 0.588, SMA 0.780, q99-bin 0.632 — critic); TrpB baseline results; NCA frozen protocol (no scored result yet).
- Intended (must be measured, otherwise not said): that the Delphi-scoped gate refuses/repairs correctly on a frozen family-clustered set; that every accepted repair passes the independent nonlinear solve at a stated rate; where LLM agents help (NL→contract extraction, missing-information detection) and where deterministic B0 or the pooled agent ties or wins.

### Exact acceptance tests (all must hold to keep Scope Desk as the headline)
- AT1 Frozen instance set: >= 8 formal/simulated families (Turing finite domain with Neumann vs periodic vs Dirichlet; wavelength-formula licence; Rayleigh–Plateau pinned vs periodic; Kimura regime; Hawk–Dove; Greenhill uniform vs tapered; Hamilton rule form; KPP speed), >= 120 items, >= 30% benign/in-scope controls, ambiguous items excluded and listed, family-held-out prompt tuning, key + generator hashed and committed before any agent run.
- AT2 Every labelled `out-of-scope` item has a machine-found distinguishing witness; labelled `applies` items have none within the stated search and are not claimed equivalent by finite search.
- AT3 Independent audit (a session that did not write the generator/oracle) of keys and oracle outputs, results committed.
- AT4 Repair: for >= 10 refused requests a repair is produced and both the exact check and the independent solver verdicts reported; failures kept.
- AT5 Delphi ablation on >= 3 decisions: gate with record vs record removed vs record hash changed vs continuum-only misapplication; decision and independent-solver success measured.
- AT6 Matched-budget arms executed once from a frozen protocol, with the pooled agent and B0 baseline, family-clustered exact intervals; collective superiority claimed only if the interval supports it; otherwise stated as null.
- AT7 Fresh-checkout reproduction of the whole pipeline under the process caps; public CLI that fails closed on a mutated request.
- AT8 Pitch/site/blog numbers each trace to a committed artifact.

### Kill conditions (check at the times shown; Seattle PDT)
- K-A 12:30: fewer than 8 families with witnesses or fewer than 80 items → shrink to the Turing + Thompson pair as a worked case study, keep matched-budget comparison on whatever exists, say so.
- K-B 14:00: B0 deterministic gate equals or beats every agent arm on all strata AND the NL-extraction stratum shows no headroom → headline becomes "the deterministic Delphi-scoped gate with repair is the product; agents add nothing measured on this task" (honest null on 45% of the rubric; do not add arms until one wins).
- K-C 14:00: independent solver disagrees with the exact linear check on > 20% of accepted repairs → report the mismatch as the finding (linear theory vs nonlinear outcome), do not hide.
- K-D 16:00: no repaired test that a scientist could run → fall back to candidate A story with the Scope Desk as an appendix.

### Four-hour build plan (to ~11:00 PDT; then evaluate, then present)
| Owner (own worktree) | Deliverable |
|---|---|
| nca (`rethink-nca`) | Finish current frozen probe; then own `scopedesk/oracles/`: exact linear-mode + nonlinear CPU PDE oracle with convergence, repair enumerator, reuse its gate/ablation arms |
| electric (`rethink-electric`) | After its memo: own `scopedesk/arms/`: headless-agent runner with token/tool accounting, guild roles, append-only commons, pull-based claiming, sequential/pooled/parallel arms, stacker baseline, analysis |
| critic (`rethink-critic`) | Own `scopedesk/bench/`: instance generator, NL request renderer, answer key hash, benign controls, B0 + retrieval baselines; then independent audit of the oracle (not its own) |
| director (`rethink-director`) | Interface contract (`scopedesk/SPEC.md`), integration branch, acceptance runner, site/pitch/blog/video, tasks/results |
| host `morphoswarm-8c` | Submission channel and +10 service packet only; no worker writes in other trees; outside use observed, not claimed |
GPU: none until a CPU pilot shows a preregistered workload exceeding it. Zero GPU use is acceptable and will be reported plainly.

### Excluded scope
New market platform; DMS/fitness regression leaderboards; claims of novelty in fidelity benchmarking; biological validation from simulation; wet-lab claims; any contact with other teams without user instruction; a corpus-wide 880-claim resolution count.

---
## Frozen criteria (unchanged from before the reports)

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

## Note on host PITCH v2 "operationalization gap" (read 06:12 PDT)
Leading direction E now = *operationalization-fidelity audit*: detect when a test or computation addresses a different proposition than the source claim (envelope→mean, dropped scope, changed estimator/population/units, conditional→universal). Director conditions for this to count as ground truth (not LLM opinion):
1. For claims with a formal core, a mutant is labelled unfaithful only if an exact **distinguishing instance** exists and is machine-checked (the same discipline as the Lean law mutants); an *equivalent* mutant (provably the same proposition) is labelled faithful and included as a harmless-change control. A mutation is not unfaithful merely because we changed text.
2. Empirical-claim pairs (e.g. Thompson/Tallo) cannot have by-construction labels beyond the source passage; they are reported as a separate, human-reviewed set and not mixed into the accuracy figure.
3. Faithful pairs are authored and fixed before any agent sees them; false-alarm rate on faithful pairs is a headline number alongside detection rate; exact binomial intervals are computed, no invented statistics. With ~40 pairs, collective-vs-single differences will likely be inconclusive; the design must say so in advance and the pitch may not claim collective superiority unless the interval supports it.
4. Authors of mutants must be different sessions from the reviewers; reviewers must not see labels; the answer key is hashed and committed before reviewer runs.
Closest-work caveat: LLM-as-judge faithfulness/specification-checking and mutation testing exist; the gap, if any, is applying mutation-labelled checking to *scientific claim → operational test* with sound verifiers. Not yet source-checked for prior art — the critic is asked to do this.
