# NCA / amorphous inverse design: go/no-go memo

Author: `delphi-rethink-nca` (Claude Sonnet 5.5, subscription; no metered charge known). Seattle PDT, Oct 31 2026, 05:58 start, first push about 07:05. Branch `work/rethink-nca`. Everything below is **simulated** under one declared reaction–diffusion model. Nothing is observed, and no biology is claimed.

## Recommendation

| Question | Answer |
|---|---|
| Should NCA / amorphous inverse design be the headline entry? | **No-go.** |
| Why | In the frozen probe the NCA arm scored the same as a random choice of reaction scale (15% vs a 23% random baseline), and the NCA models diverged numerically when rolled forward. The strongest design tool was the plain analytic wavelength formula from an existing Delphi record. |
| Is any part worth keeping? | **Narrow, conditional go** for a claim-licensed Turing *check and repair* as one component of another entry. It is established theory with executable reuse. It is not a new scientific result. |
| Frozen NCA go rule | **Failed** on 3 of 4 conditions (details below). |
| Frozen claim-gated go rule | **Failed** (one of four conditions failed). |
| Validation target | **None measured.** The only intervention-labelled open dataset the scout found (Liu et al., Dryad `10.5061/dryad.2j9p4`) returns HTTP 401 "must have current bearer token" for every file. Metadata is public, files are not. Verified today by `curl` on file ids 18559–18563. |

A scientist could use the checker to avoid a futile design (16 of 16 equal-diffusivity requests) and to see a licensed repair. They would not use the NCA.

## Three narrow problems considered

| # | Problem | Closest primary prior art (read level) | Result here |
|---|---|---|---|
| P1 | Target-wavelength inverse design for a learned local rule (NCA) vs direct design, checked by a *different* solver on held-out domain length and scale | Richardson et al., PLoS Comput Biol 2024 ([link](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1011589); arXiv 2310.14809): NCA on Gray–Scott, new initial condition and longer horizon. Mordvintsev et al. arXiv 2107.06862: RD as NCA, gradient design. Kho et al., arXiv 2211.13464: physics-informed networks for Turing-system design. Allen et al., arXiv 2202.00728: differentiable learned simulators for inverse design. *Read level: search-result snippets and abstracts only, not full texts.* | Tested: **no-go** |
| P2 | Domain-aware Turing design with claim-licensed applicability and repair | Finite-domain Turing analysis is classical ([PMC9884266](https://pmc.ncbi.nlm.nih.gov/articles/PMC9884266/)); Turing 1952. | Tested: works, but textbook. The contribution would be executable, hash-pinned reuse of existing Delphi records, not the mathematics. |
| P3 | Predict held-out Bicoid-dose gap-gene profiles with a mass-action circuit vs a black-box local rule | Gap-gene circuit models predict mutants already (scout cites Shen et al., arXiv 1807.08414, abstract level). | **Blocked** by the data-access result above. Not run. |

The scout's cross-solver, hidden-state-exploitation gap is **not shown to be unoccupied**. One search found no paper doing it, and that is not evidence of absence.

## Experiment (frozen before scoring)

Protocol: `experiments/rethink_nca/protocol.json`. Code frozen at commits `8fcefde`, `e7838b3`, `7ee95dc`. Scored run at `237f85b`. Bug fixes after the freeze, all before any output was read: a train-script syntax error, a fraction-string parse in the continuum arm, and a KeyError in the summarizer. Two protocol edits before scoring, both recorded in the protocol: NCA training 3000 → 1000 iterations (measured about 4 iterations/s), and NCA scan 48 → 16 γ values after a throughput pilot (23 ms per step for a 144-row, r=40 batch under load).

**System (declared).** Schnakenberg kinetics, a=1/10, b=9/10, Du=1, Dv=d, reaction scale γ; 1-D Neumann interval of length rπ; steady state (1, 0.9). Time is τ=γt; length unit has Du=1.

**Task.** For a request (d, r, target wavelength λ*) choose γ so the *dominant* cosine mode has wavelength within 15% of λ*. 32 treatment requests (d ∈ {10, 20}, r ∈ {10, 20, 30, 40}, λ* ∈ {8, 11, 15, 22}) plus 16 equal-diffusivity controls (d=1).

**Independent evaluator.** Spectral Strang splitting with exact cosine-mode diffusion and RK4 reaction, dt_τ=0.02, horizon τ=400, noise 1e-2, seeds {11, 12, 13}. Success needs std(u) ≥ 0.1, wavelength within tolerance and the same dominant mode at τ=360 and 400. Design-time world is explicit Euler (dt_τ=0.005, horizon τ=200, seed 0). Both are the same equations under different code; this is a numerical cross-check, not validation against nature.

**Arms.**
- C0: closed-form γ = √d (2π/λ*)² from the `turing-wavelength` record notation. Never refuses.
- D: black box. 12 γ simulated, pick the closest.
- G: claim-gated hybrid using `turing_scope.analyze` (exact rationals, hash-pinned records).
- Gmis: continuum band only, ignoring admissible modes (claim misapplied).
- N: NCA, 3 training seeds.
- Nshuf: NCA trained with shuffled conditioning.

### Results (independent-solver success, mean over requests of the fraction of 3 seeds)

| Arm | All 32 | Held-out 24 (r ∈ {30, 40} or formula γ outside [0.7, 2]) | d=10 (near onset) | d=20 | Design simulations (32 requests) |
|---|---|---|---|---|---|
| C0 formula | **0.958** | **0.972** | 1.000 | 0.917 | 0 |
| D black box | 0.698 | 0.667 | 0.750 | 0.646 | 384 |
| G claim-gated | 0.635 | 0.556 | 0.750 | 0.521 | 263 (8 requests solved analytically with 0) |
| Gmis continuum only | 0.677 | 0.653 | 0.729 | 0.625 | 336 |
| N NCA (3 seeds: 0.000, 0.208, 0.240) | 0.149 | 0.171 | 0.146 | 0.153 | 0 (16 NCA queries per request) |
| Nshuf control | 0.000 | 0.000 | 0.000 | 0.000 | 0 |
| *Post hoc: random γ from the 16-point grid* | *0.229* | *0.193* | — | — | — |

Raw counts and per-request rows: `artifacts/rethink_nca/summary.json`, `evaluated.json`. Only 3 noise seeds and 3 NCA seeds; no confidence interval is claimed. Treat differences below about 0.1 as unresolved: see the noise baseline below.

Reading it plainly:
- **The analytic formula wins.** C0 failed on 3 of 32 requests. D, G and Gmis spend simulations and do worse, partly because selecting γ on one design-world seed does not transfer to other seeds and the other solver (D's own-world success 0.78 vs independent 0.70).
- **The claim's licence is conservative here.** `turing-wavelength` licenses the formula only near onset. Only d=10 qualifies, and G used the formula with zero simulations on 8 of those requests (success 8/8). Using the formula outside the licence (C0, d=20) still succeeded 0.917 for this kinetics and a 15% tolerance. That says the licence is cautious for this system, not that it is wrong in general.
- **The finite-domain admissibility check did not improve outcomes.** G changed γ relative to Gmis on 23 of 32 requests, with independent success 0.72 (G) vs 0.78 (Gmis) on those 23. The two refusals by G (d=10, r ∈ {10, 20}, λ*=22) were caused by my declared design bound γ ≥ 0.5, not by domain physics: C0 used γ=0.37 and succeeded. This is a limitation of the declared range.
- **Where the claim clearly changed a decision: the controls.** For d=1 the `turing-ddi` inequality fails (no unstable band). G refused 16 of 16; C0 accepted 16 of 16 and succeeded on 0. D and N also produced no accepted design, but D spent 192 simulations to find that.

### Decision rules (frozen in the protocol)

NCA go required all of:

| Condition | Value | Pass |
|---|---|---|
| N ≥ D − 0.05, all requests | 0.149 vs 0.698 | no |
| N ≥ D − 0.05, held-out | 0.171 vs 0.667 | no |
| Self-consistent minus independent ≤ 0.10 | 0.063 vs 0.224 among accepted | yes, vacuously: the NCA's own world rarely formed the target pattern |
| Nshuf ≤ N − 0.20 | 0.000 vs 0.149 | no (the shuffled model abstained or diverged, so this contrast is uninformative) |

Gated claim go required all of:

| Condition | Value | Pass |
|---|---|---|
| Controls: G refuses all, C0 accepts all, C0 success 0 | 16/16, 16/16, 0 | yes |
| G coverage ≥ 50% of treatment (added after primary review) | 30/32 | yes |
| G ≥ D − 0.05 on accepted with ≤ half of D's simulations | 0.678 vs 0.744; 263 vs 360 sims (73%) | **no** |
| Changed pinned record refuses everything | 48/48 | yes |

The last row shows provenance dependence only, not scientific dependence. The scientific ablations are the removed (D, C0 vs G) and misapplied (Gmis) rows above.

### Why the NCA failed (measured, with caveats)

- All four v1 NCAs (hidden channels, 16-step windows, 1000 iterations) blow up in long rollouts. At τ=20 the maximum |u| is already 1e16 for seed 0 and about 200 for seed 1 in-distribution (d=10 and 20, training domain), reaching 1e22 by τ=200. Seed 0 and the shuffled model produced non-finite values on every row and therefore abstained; seeds 1 and 2 accepted all 32 requests but their own world formed the target pattern on 12.5% and 0% of them.
- Their independent success (0.208 and 0.240) is statistically indistinguishable in size from picking γ at random (0.229). Interpretation: no usable design signal.
- This is a failure of **this** short-window, hidden-channel training recipe on a stiff reaction–diffusion system, not evidence that no NCA can do the task. Richardson et al. trained successfully on Gray–Scott with different settings. A post-hoc fair-chance variant is reported below.
- Throughput measured under load: explicit-Euler-equivalent NCA rollouts cost about 23 ms per step for a 144-row r=40 batch (40,000 steps ≈ 15 minutes), 7 ms for r=10. A fused implementation (`nca.fast_rollout`, verified equal to the module to 1.9e-6) roughly halved this. A CPU bound is why the scan was cut; it is not a result.

### Evaluator trust

- Time step halved: success flag and dominant mode agreed on 33 of 33 (subset: every 6th accepted D/G design, 11 designs × 3 seeds).
- Resolution doubled (new noise field at 2N cells): success-flag agreement 0.818 and dominant-mode agreement 0.455. This is **below the 0.90 bar I set**, so I do not trust the evaluator at the single (request, seed) level.
- Post-hoc diagnostic: the same resolution with new noise seeds agreed only 0.758 (flag) and 0.576 (mode). The doubling disagreement is within what noise realization alone produces: nonlinear mode selection depends on the initial noise. Aggregate success was identical (0.697) in the baseline and both variants. Consequence: per-request success from 3 seeds is noisy; only large arm differences (C0 vs the rest, NCA vs C0) are safe to read.

### The repair (actual intervention, independently checked)

Request: target wavelength with Dv/Du=1 (no admissible instability). Gate output: refused by `turing-ddi` (band absent). Minimal declared repair: raise Dv/Du to the smallest integer for which the exact adapter check licenses an unstable mode near the target (9), set γ at the log-midpoint of that mode's instability interval, then simulate in the independent solver.

| Result | Value |
|---|---|
| Repairs that succeeded, 16 controls | 0.708 mean (11 of 16 requests succeeded on all 3 seeds; the 5 others are the four λ*=22 requests, which need γ near or below my 0.5 bound, and one partial λ*=15 case at r=10 with 1 of 3 seeds) |
| Same requests, formula design without repair (C0) | 0.000 |
| Domain-length repair for d=1 controls | none found within r ∈ [5, 60] (as expected: domain changes cannot create a band) |
| Repairs for the two λ*=22 refusals | 0 of 2: the dominant mode was 4 or 9, not the licensed 3 or 7. Repairs near onset (d between 9 and 11) have amplitude 0.15–0.38 and the nonlinear mode differs from the linear prediction. |

Near-onset repaired patterns are marginal (amplitude 0.15–0.18 against a 0.10 threshold). The repair is checked by linear theory plus a nonlinear independent solver, never by experiment. Details: `artifacts/rethink_nca/repair.json`.

## Operational Delphi reuse

**Records.** `turing-ddi` (content sha256 `43de1d39496e0d2a8df133d0e537bed158bf3c68d23c28a764c2356715aa4f66`), `turing-wavelength` (`e0d541383aa5d6334d794b60753e371dc781b01f0bc1b45e3d0ec337208a7559`), retrieved from Delphi MCP 2026-10-31 01:32 PDT; unsigned local nanopubs, not network publications.

**Kept separate.** (1) The record text and its stated context (two species, linearization at a homogeneous state, fixed domain without growth or mechanics, near onset and large domain for the wavelength). (2) `turing_scope`'s added assumptions (1-D Neumann, declared Jacobian). (3) This experiment's own additions: Schnakenberg kinetics treated as exactly known, 15% tolerance, near-onset threshold 1/2, domain ≥ 5 wavelengths, γ ∈ [0.5, 3]. The near-onset and domain thresholds are requester-declared operationalizations; the record gives no numbers.

**What the records did.** Gated: refuse when no unstable band exists (controls 16/16), computed the exact admissible-mode set per request, licensed the closed-form wavelength for 8 requests (no simulation), restricted search intervals for 22, and fixed the repair (which knob, which value). Removed or misapplied: D and Gmis did comparably or slightly better on this task's outcome, so **the records did not improve the success rate here**; they saved simulations and changed which requests were refused. A changed pinned hash turned all 48 computations into refusals.

## Multi-agent contribution

None claimed. This was one Claude Sonnet session. Rubric weight on multi-agent organization is 45%; a measured contribution for this line would be an independent replicate solver or an independent critique agent whose disagreement changes a reported result (for example, a second agent reimplementing the evaluator and finding the disagreement in the resolution check). That was not run. Other model families are not authorized.

## Limits that matter

- Model-only. No measurement, wet-lab link or biological claim. Do not present as biology.
- One kinetics, one boundary condition, one dimension, loose 15% tolerance, 3 noise seeds, 3 NCA seeds. Fifteen requests per condition give coarse resolution.
- NCA training was short (1000 iterations, 16-step windows) and CPU-bound. This is a feasibility probe, not an optimized NCA.
- Evaluator resolution check missed the preregistered 0.90 bar (above).
- Gate refusals partly reflect my γ range.
- No GPU was used. No data request was sent to anyone; no outside contact.

## Next decisive test (only if the director wants this line)

Give the NCA a fair chance on a task where no closed form exists: a non-uniform or growing domain, or kinetics outside the two-species theory, with a held-out solver and a real or independently specified target. The question would be whether any NCA beats black-box search at equal simulation cost there. The measured result here says the analytic baseline dominates on the case where theory exists, so the justification for NCA must come from cases where it does not.

## Resources and commands

Commands actually run, exits, artifacts and commits are in `tasks/results/rethink-nca.json`. CPU only, 2 threads, every process under `systemd-run --user --scope` caps. Seattle wall: training 4 models about 13 min; design stage about 20 min under load average 12–20; independent evaluation under 2 min; convergence, repair and diagnostics a few minutes. Actual metered charges: none known.
