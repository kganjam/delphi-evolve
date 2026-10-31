# Critic response to the "Settled Science" evidence-market decision (morphoswarm-8c, 06:55 PDT)

Sat 31 Oct 2026, written ~06:25–06:45 by wall clock (`date`). Claude Sonnet 5.5. Source-only judgment; numbers below come from files in `planning/rethink/wildcard/` or the cited repo docs. I did not run any agent arms.

## Verdict: do not reject the market architecture; reject it as specified in six places

The market is the best *rubric-shaped* idea on the table (it makes collective capability a decomposed, scored quantity). It fails as written because several of its load-bearing statements are false or untested. A narrower version survives (bottom).

## 1. What fails, with evidence

| # | Claim in the decision memo | Problem | Evidence |
|---|---|---|---|
| 1 | Tier 3 settles "variant V is in the top 5% of **catalytic efficiency**" with TrpB measurements | The TrpB table is E. coli auxotroph **growth**, not catalytic efficiency (our own CONTRACT/GOAL assay-scope rule). And "V is in the top 5%" is a per-variant fitness-threshold label: it **is** the ProteinGym/FLIP task wearing a propositional costume. The memo's own survival condition ("never a raw fitness regression") is violated by its own example. | GOAL.md baseline section; memo §Architecture |
| 2 | LLM guilds can bet on held-out TrpB | **Contamination**: Johnston et al. 2024 is public and its best variant (AIKG) is in the abstract; the "literature guild" and every LLM guild may have seen it. "Held-out" holds for data files, not for model weights. Needs a contamination probe or a claim set about instances not in any paper. | Docs: the paper is cited throughout `docs/novelty.md` |
| 3 | Orthogonal modalities (structure, dynamics, sequence) give a ceiling that "aggregation crosses ... mechanistic, not hoped for" | Untested hypothesis stated as mechanism. Our measured zero-shot data: five ESM2 sizes give Spearman ρ≈0.17–0.21 against TrpB fitness, not growing with size (`docs/scale.md` l.61–71); my Adaptyv check found **no fusion gain** over the best single view (fused 0.61 vs 0.68 AUROC; frozen rule failed). Structure features across variants that differ at **four residues** have no demonstrated added signal; ΔΔG/OpenMM on "highest-disagreement variants" is circular selection and is slow and noisy. | `docs/scale.md`; `planning/rethink/wildcard/binder_views_check.json` |
| 4 | GPUs are "necessary" as feature factory and PDE oracle | **Dynamical tier: 100 nonlinear Schnakenberg solves to T=1000 took 20.4 s on one CPU thread** (batched IMEX, N=128, dt=0.02; unrefined, illustrative). Formal tier: 10⁷ Turing screens in 15.5 s. Structure/dynamics features for a few hundred variants are the only plausible GPU workload, and that is the part of the design I find least justified (item 3). Say "GPU use ends where the CPU estimate ends" and measure it. | `pde_cost_probe.json`, `turing_scope_prevalence.json` |
| 5 | Formal tier "settled by Lean + exact arithmetic" makes a market | A claim decidable in milliseconds by a CPU tool is not a forecasting problem. If guilds may call the checker, accuracy → 100% and there is nothing to bet on; if they may not, you are measuring enforced ignorance. What it can measure is *abstain-or-compute discipline* (does an agent call the tool or guess?). 100 formal claims from one parameterised Turing family are also **one claim family, not 100 independent claims.** | `critic.md` §3.1, §3 of `critic-E-redteam.md` |
| 6 | "Agents betting from the textbook criterion lose to agents betting from the finite domain" is a market finding | That is a **prompt/tool-condition ablation of single agents** (scope-aware vs scope-blind), not a collective result. | memo §Architecture |

## 2. Statistics and controls the design is missing

- **Diversity prediction theorem is for squared error and mean aggregation.** Under Brier scoring, the mean forecast's error ≤ the mean individual error *always* (convexity), so "crowd beats average" is vacuous. It does not apply to log score as stated. The only informative comparisons are vs the **best individual**, vs a **base-rate forecaster**, and (next point).
- **Missing control: a single agent given all modalities at the same total token budget, and a plain non-agent stacker (logistic/GBM) on the same private features.** Enforced asymmetry makes every individual worse *by construction*, so "collective ≥ individual" is guaranteed by design. The question that matters is collective vs **pooled** information. Prior work on distributed vs pooled information in LLM groups reports the pooled agent winning by a wide margin (HiddenBench, arXiv 2505.11556, as cited in the sibling repo's RESULTS.md; I did not re-read it). Expect the honest outcome to be: collective beats each individual, **does not beat pooled single agent / stacker.** If so, the contribution is a decomposed null on the thing that matters, plus a privacy-preserving-aggregation argument (below), not "collective capability".
- **Calibration needs its own split.** "Calibrated bets" require calibration data; using the held-out labels to calibrate is leakage. Splitting 300 claims leaves roughly 50 test claims per tier, with correlated family structure; use a **family-clustered paired bootstrap**, not claim-level.
- **300 claims ≠ 300 independent items.** Three tiers drawn from ≈3 families; the effective sample is the number of families (cf. the 12–20 family estimate in `critic-E-redteam.md` §3).
- **Operationalization is the hidden labor.** "System S forms a stable pattern at T=1000" has no oracle until threshold, initial condition, grid, solver and tolerance are fixed — exactly the fidelity problem. My PDE probe's 0.1-amplitude threshold is arbitrary and unrefined. The claim-authoring discipline from candidate E is therefore not optional; it sits inside the market.

## 3. Prior art (checked via search results, not full texts unless stated)

- **Halawi et al. 2024** ("Approaching Human-Level Forecasting with Language Models", arXiv 2402.18563): retrieval-augmented LLM forecasting system approaching the aggregated human crowd on Brier score.
- **Schoenegger et al. 2024** ("Wisdom of the Silicon Crowd", Science Advances; arXiv 2402.19379): ensemble of **12 LLMs** on 31 binary questions vs 925 human forecasters; the LLM crowd beat a no-information benchmark and was statistically indistinguishable from the human crowd. So multi-model LLM crowds are established; only the settlement layer and the science domain are new.
- **BrainBench** (Luo et al., Nature Human Behaviour 2025; arXiv 2403.03230): LLMs vs 171 neuroscientists at predicting results — scientific outcome prediction by LLMs exists, with items from published abstracts (and the same contamination caveat).
- **Prediction markets for replication** (Dreber et al. 2015, PNAS; DARPA SCORE): from memory, **not verified this session**; verify before any slide.
- **ProteinGym/FLIP/ALDE**: protein-fitness prediction and ensembles are crowded (per the baseline docs).
- The remaining distinction — **three non-LLM oracles + modality-bound guilds + decomposed diversity** — is plausible but I have not found or ruled out a closer system; four searches are not a literature review.

## 4. What survives: a cheaper, truer "market-mini"

Keep the market spine, but run it where an oracle is real and the asymmetry is about **tools**, not hoped-for modalities:

1. **Claim family:** finite-domain reaction–diffusion applicability — "does system S on Neumann domain L admit/maintain a pattern?" Claims are authored under the fidelity discipline (declared scope, threshold, IC, solver) and each gets two sound oracles: **exact linear admissible-mode calculation** (instant) and **converged nonlinear solve** (seconds on CPU; refine dt/N before trusting). The *disagreements between the two* are the science (subcritical/finite-amplitude behavior, domain-size effects), not the Turing textbook case alone.
2. **Guilds differ by capability, not by guessed modality:** (i) textbook continuum criterion only, (ii) finite-domain mode calculator, (iii) cheap coarse/short PDE surrogate, (iv) no tools (LLM prior), (v) a model-family variation on (ii). Each sees only its own tool output.
3. **Arms at matched total tokens + tool cost:** sequential single agent with retries; N samples of one model; the guild market; **pooled single agent with all tools**; **non-agent rule/stacker** on the same tool outputs. Preregister (sidedness, cluster unit = parameter-family, primary outcome Brier vs best individual and vs pooled agent).
4. **What it can honestly show:** whether tool-diverse guilds beat any individual and whether they match the pooled agent. Likely null on the second; report it.
5. **Keep TrpB tier 3 only if reframed** as a decidable propositional claim about the measured graph (route/cut at ε) — i.e., the existing certificates — and flagged as same-data, not held-out.
6. **+10:** a "does the textbook criterion apply to my domain size/parameters?" endpoint is genuinely useful to any team using reaction–diffusion; usage must be observed, not claimed.
7. **Privacy-preserving aggregation** is a possible honest story for why you would *want* guilds with separate data even if a pooled agent is better — but untested here; do not claim it.

## 5. Kill conditions for the market (in addition to E's)

- No second oracle (converged nonlinear solve) that the critic or director can reproduce on 10 sampled claims → drop tier 2.
- Pooled-agent and stacker arms cannot be run at matched budget → no collective claim.
- Contamination probe on tier-3 claims shows above-chance recovery from no-evidence prompts → drop tier 3.
- Fewer than ~12 independent claim families authored and second-read by 09:30–10:30 PDT → cut scope as the memo itself proposes.
- Any slide stating "collective beats best individual" without the pooled-agent comparison and its interval.

## 6. Updated ranking (critic)

1. **Market-mini on finite-domain scope claims, authored under the fidelity discipline** (merges candidate E and the market; CPU-first; conditional on §5 gates).
2. Hardened Darwin's Bridge (floor/Execution; honest negative).
3. Binder-triage pilot (investible follow-up only).

No probability of winning is asserted; the rubric fit is a judgment about *what could be measured*, not about how judges will score.

## 7. Critic's pitch v2 for market-mini (3 minutes; every bracket is filled only from a committed result)

- **0:00–0:20 reveal.** "Slide the domain from 2π to π. The textbook Turing test stays green. The pattern vanishes — we solved it both ways." (Linear admissible-mode verdict next to the converged nonlinear solve; `pde_cost_probe.json` shows the form, final numbers must come from the refined run.)
- **0:20–0:50 failure first.** "Our last entry scored 78/100 and a sixty-agent swarm scored the same. Copies of one policy are an echo chamber."
- **0:50–1:40 the market.** "Agents that hold different tools bet on whether a pattern forms; two sound oracles settle every bet. [N] claims from [K] independent families." Show who-called-what log and the matched-budget arms.
- **1:40–2:20 the measured answer, whatever it is.** "[Collective vs best individual: Brier x [interval]]. [Collective vs agent holding every tool: Brier y [interval]]." If the pooled agent wins: "Distributed information costs [z]; here is when you still want it."
- **2:20–2:45 the useful artifact.** A public endpoint: give it a reaction–diffusion model and a domain; it returns applies / refuses / underdetermined, with the oracle receipts. Say "[observed users]" only if someone used it.
- **2:45–3:00.** "Next: a pilot with a modelling team measuring how many of their last [K] model reuses violated a stated assumption." No claims of firsts, wet-lab results, or wins.
