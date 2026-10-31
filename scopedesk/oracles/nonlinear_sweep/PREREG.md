# PREREG: where does exact linear theory mispredict the nonlinear outcome? (named ensemble, nonlinear sweep)

Author `delphi-rethink-nca` (Claude Sonnet 5.5). Written 2026-10-31 (Seattle PDT, from `date`: about 08:40) and committed BEFORE any scored cell is run. The only runs so far are an UNSCORED 24-cell pilot from a different ensemble seed (`results/nonlinear_sweep/pilot_unscored.json`), used for timing and for one definition fix noted below. Evidence kind of every number: `simulated` (declared models) plus `formal` (exact linear verdicts). Nothing is observed. This is an appendix result about a declared model class, not a claim about any tissue.

## Prior art (stated, not claimed as new)
Subcritical Turing instability, finite-amplitude patterning below the linear threshold, and amplitude/Landau-type expansions are classical weakly-nonlinear pattern-formation theory. This sweep neither discovers nor proves subcriticality: a nonlinear pattern from a linearly stable state under a large initial perturbation is a *finite-amplitude outcome of the declared equations*, reported as such.

## Question
Across a named ensemble of two kinetics models, how often does the exact linear verdict (does an admissible unstable diffusion-driven mode exist on the finite domain) disagree with the converged nonlinear outcome of the same equations, and how often does the dominant nonlinear wavelength differ from the fastest-growing linear mode?

## Ensemble (named; no claim that it is "realistic")
* Models: Schnakenberg (`f = a − u + u²v`, `g = b − u²v`) and Brusselator (`f = A − (B+1)u + u²v`, `g = Bu − u²v`); 1-D interval, zero-flux (Neumann) ends, γ = 1 (γ only rescales time and length), Du = 1, Dv = ρ·d_c.
* Parameter prior (a STATED PRIOR, not published ranges): Schnakenberg `a ~ logU[0.05, 0.4]`, `b ~ logU[0.4, 1.6]`; Brusselator `A ~ U[0.8, 2.5]`, `B = 1 + u·A²` with `u ~ U[0.15, 0.85]`; parameters rounded to small rationals (denominators ≤ 100 / 20). Rejection: well-mixed stable, finite onset ratio `1 < d_c < 400`. Textbook centres exist (Schnakenberg a = 0.1, b = 0.9, d = 10; example source arXiv 1903.05030, seen at search-snippet level only) and lie inside the prior, but the prior is mine. 10 draws per model, drawn with `random.Random(20261031)`.
* Distance from onset: `ρ = Dv/d_c ∈ {0.7, 0.9, 0.97, 1.03, 1.1, 1.5, 3.0}`, where `d_c` is the smallest Dv/Du satisfying the `turing-ddi` continuum inequality (computed in floats; Dv = ρ·d_c rounded to denominator ≤ 1000, exact thereafter).
* Domain: `L = x·λ_c`, `x ∈ {2, 4, 8}`. Basis: `λ_c = 2π/k_c` with the `turing-wavelength` record notation `k_c² = sqrt(det J/(Du Dv))` evaluated at the onset ratio Dv = d_c (so λ_c does not move with ρ). Basis is a modelling convention, not a cited "realistic" length; `r = L/π` rounded to denominator ≤ 50.
* Initial perturbation: band-limited cosine series `Σ_{k=1..K} c_k cos(kπx/L)` (K = max(8, min(N_A/4, 40))) with N(0,1) coefficients scaled so the ANALYTIC std equals `ε·|steady state|` for each species, `ε ∈ {0.01, 0.1, 0.3}`. The same continuous function is sampled by both solvers. Paired seeds `{101, 102}` index the coefficient draw; pairing is across ε, ρ, x and solvers. Design factors are crossed, not iid.
* Total grid: 2 models × 10 draws × 7 ρ × 3 x × 3 ε × 2 seeds = **2,520 cells**.

## Solvers (two integrations of the same equations; BOTH ARE MINE)
* A: spectral Strang splitting (exact cosine-mode diffusion, RK4 reaction), dt_τ = 0.02, N_A = ⌈L/min(π/4, λ_c/20)⌉ cells (`scopedesk/oracles/pde.py::_run`).
* B: scipy `solve_ivp` BDF method of lines, cell-centred second-order finite differences, sparse Jacobian, rtol 1e-6, atol 1e-9, N_B = ⌈1.5·N_A⌉ cells; no stepping or discretisation code shared with A.
* Horizon T_τ = 800; if the exact linear fastest growth rate σ > 0, T_τ = min(1500, max(800, 40/σ)). Same T for both solvers. Evaluate at 0.9 T and T.

## Outcome definitions (fixed now)
* `pattern` for a solver: std(u) at T ≥ 0.1·|u*| (u* the steady state of u). Dominant mode = index of the largest nonzero DCT-II coefficient of `u − mean(u)`.
* `settled` for a solver: if pattern, the dominant mode at 0.9 T equals that at T and std changed by ≤ 5%; if no pattern, std(T) ≤ 0.02·|u*| or std(T) ≤ 1.05·std(0.9 T). (The no-pattern clause originally read only the 1.05 ratio; the pilot showed a decaying 1e-17 noise floor failing it, so the 0.02·|u*| floor was added BEFORE scoring.)
* Cell outcome: `unresolved` if either solver diverged (non-finite or |u| > 1e3); else `unresolved` if the pattern flags differ; else `unresolved` if both patterned but dominant modes differ or std differs by > 15%; else `unresolved` if either solver is not settled; else `pattern` or `no_pattern`. Reasons recorded (`diverged`, `solver_disagree_flag`, `solver_disagree_mode_or_amp`, `not_settled`, `exception:*`). **Unresolved cells stay in every denominator** and are reported as unresolved mass.
* Linear verdict per cell: `linear.check` exact (`applies` = an admissible unstable mode exists; `out_of_scope` = none; well-mixed-unstable cannot occur after the prior's rejection). Fastest linear mode = the admissible mode with the largest real eigenvalue.

## Quantities reported (definitions fixed now)
* R1 = (linear `out_of_scope` ∧ nonlinear `pattern`) / (linear `out_of_scope` cells). Finite-amplitude outcome of the declared model; NOT proof of subcriticality.
* R2 = (linear `applies` ∧ nonlinear `no_pattern`) / (linear `applies` cells). "Unstable but no pattern by horizon".
* R3 = (linear `applies` ∧ `pattern` ∧ dominant mode ≠ fastest linear mode) / (linear `applies` cells); also the same restricted to resolved patterned cells, and the mode-offset distribution.
* Unresolved mass per stratum. Strata: model; ρ; x (L/λ_c bin); ε; and the ρ × ε table. Draw-level counts (number of parameter draws with at least one occurrence) are reported beside cell-level counts.
* Intervals: exact (Clopper–Pearson) 95% on cell counts, stated to treat cells as independent and therefore to be too narrow (cells share parameter draws and paired seeds). No p-values, no hypothesis tests, no effect-size claims beyond the counts.

## Predictions registered before scoring (each can fail)
* P1: at ε = 0.01, R1 = 0 in every ρ stratum (a linearly stable state with a tiny perturbation should decay).
* P2: any nonzero R1 occurs only at ρ ≥ 0.9 and ε ≥ 0.1.
* P3: R2 concentrates at ρ = 1.03 and/or x = 2 (slow growth or too-short domain), not at ρ ≥ 1.5.
* P4: R3 (wavelength mismatch among linear-unstable cells) is at least 0.2 overall, with the nonlinear mode lower than the linear mode in most mismatches (an earlier 82-config grid showed 18 of 61 mismatches, 15 of 16 lower in 1-D).
* P5: solver disagreement mass is below 5% of cells.

## Cost, pilot and stop rule
* Pilot (24 unscored cells, 1 thread, loaded host load average about 4–5): mean 6.1 s per cell (A 6.0 s, B 0.09 s), max 12.1 s. Extrapolation: 2,520 cells × 6.1 s = 15,400 CPU-seconds; with 2 worker processes (1 thread each) about 2.1 h wall; stage 1 alone (1,260 cells) about 1.1 h. Decision: **CPU is feasible; no GPU or Nebius job will be requested.** The solver is a sequential time-stepper on 100–1000 cell vectors, not GPU-suited at this size.
* Order: stage 1 = the 1,260 cells with seed 101 in a fixed random permutation (`random.Random(20261032)`), then stage 2 = seed 102 in a fixed random permutation. Rows appended to `rows.jsonl`; resumable.
* Stop rule: stop at completion or at a wall budget of 3.5 h, whichever is first. If the budget stops stage 2, the executed cells are an unbiased random subset of the seed-102 cells and the report states the executed fraction. Not extended, not cherry-picked, no cell dropped except by exceptions, which are counted as unresolved.
* Hard deadline for committed results: 15:00 PDT, 2026-10-31.

## Reproduction
`PYTHONPATH=. python3 -m scopedesk.oracles.nonlinear_sweep.run sweep scopedesk/oracles/results/nonlinear_sweep --workers 2 --budget-seconds 12600 --draws 10` under `systemd-run --user --scope -p TasksMax=64 -p MemoryMax=4G -p MemorySwapMax=0`, then `python3 -m scopedesk.oracles.nonlinear_sweep.analyze scopedesk/oracles/results/nonlinear_sweep`. Raw rows and a sha256 of `rows.jsonl` are committed.

## Non-claims and limits
Two models, one dimension, one boundary condition, γ = 1, one family of initial perturbations, a prior chosen by me, three amplitudes, two seeds. Both solvers are by the same author and share the equations (an equation error would be shared). Dominant mode is a single-number summary of the final state. No statement about any real tissue, chemistry or NCA.
