# Nonlinear sweep result: where does exact linear theory mispredict the nonlinear outcome?

Preregistered in `scopedesk/oracles/nonlinear_sweep/PREREG.md` (committed `cb27cf2`, before any scored row). All 2,520 cells ran to completion (stop rule: completion; 10,055 s wall, 2 worker processes, CPU only, no GPU). Raw rows: `rows.jsonl` (sha256 `a32c2bf7dd3c10162317974ae6a0ecbefa06c1c180a6886dea1bcb8ea4d4c882`), full tables: `report.json`, analysis logged as a local orx run: `orx_receipt.json`. Evidence kind: simulated (two integrations by the same author of the same declared equations) plus formal (exact linear verdicts). Model class: Schnakenberg and Brusselator, 1-D, zero-flux ends, a stated prior for parameters (not published ranges), domains 2/4/8 critical wavelengths. Nothing here is observed or about a tissue. Subcritical Turing instability and amplitude equations are classical; this does not claim novelty.

## Headline counts (cells are NOT independent; intervals are exact but too narrow)

| Quantity (definition in PREREG) | Count | Rate | exact 95% (cells as independent) |
|---|---|---|---|
| R1: linear stable, nonlinear patterned | 30 / 1,080 | 2.8% | 1.9–3.9% |
| R2: linear unstable, nonlinear NO pattern by horizon | 0 / 1,440 | 0% | 0–0.26% |
| R3: linear unstable, patterned, dominant mode ≠ fastest linear mode | 461 / 1,440 (461 / 1,391 resolved patterned) | 32.0% (33.1%) | 29.6–34.5% |
| Unresolved mass (in every denominator) | 59 / 2,520 | 2.3% | 1.8–3.0% |

Unresolved reasons: 51 solver disagreement on dominant mode or amplitude, 2 on the patterned flag, 6 not settled. 56 of 59 are Brusselator.

## Where it happens
* **R1 (finite-amplitude patterns from a linearly stable state)** occurs only for the Brusselator (30 of 540 linear-stable Brusselator cells; 0 of 540 Schnakenberg), only at the largest perturbation (ε = 0.3), only just below onset (ρ = 0.9: 13, ρ = 0.97: 17; ρ = 0.7: none), in 4 of the 20 parameter draws (all Brusselator), roughly equally across domain lengths (9, 11, 10 for L/λ_c = 2, 4, 8). Within the ε = 0.3, ρ ∈ {0.9, 0.97} Brusselator cells, 30 of 120 patterned and 10 were unresolved. Amplitudes of those patterns were 0.22–0.80 (std of u). This is a finite-amplitude outcome of the declared Brusselator, not a proof of subcriticality.
* **R2** never occurred: every linearly unstable cell produced a pattern by the horizon, including ρ = 1.03 and the shortest domain. P3 (below) therefore cannot be confirmed.
* **R3 (wavelength mismatch)** occurs in every one of the 20 draws, grows with distance from onset (ρ = 1.03: 37; ρ = 1.1: 72; ρ = 1.5: 152; ρ = 3: 200, each out of 360 cells), is more frequent for the Brusselator (349 of 720) than the Schnakenberg (112 of 720), and is mostly toward longer wavelength: the nonlinear dominant mode is lower than the fastest linear mode in 84% of mismatches (offsets −1: 186, −2: 79, −3: 59, +1: 70).

## Preregistered predictions
| | Result |
|---|---|
| P1 R1 = 0 at ε = 0.01 | holds (0 events) |
| P2 R1 only at ρ ≥ 0.9 and ε ≥ 0.1 | holds (30 of 30 events at ε = 0.3, ρ ∈ {0.9, 0.97}) |
| P3 R2 concentrated at ρ = 1.03 or L = 2λ_c | cannot hold: zero R2 events (reported as failed as stated) |
| P4 R3 ≥ 0.2 and mostly lower mode | holds (0.32; 84% lower) |
| P5 unresolved < 5% | holds (2.3%) |

## Cautions
* The ensemble is mine (stated prior, three amplitudes, γ = 1, one family of initial perturbations, 1-D Neumann only). A different prior or perturbation family could give different rates; this is a sweep, not a claim about "realistic" parameters.
* Both solvers share equations. Solver disagreement (2.3%) is kept as unresolved mass, so the headline rates are bounded rates among all cells rather than among resolved ones.
* The analysis script was written after the sweep started (not after seeing results, with one exception: a smoke test of the analyzer on 14 partial rows printed provisional predictions; no design choice was changed afterwards). The PREREG text says "about 08:40"; the commit was made at 08:34 by `date`.
* The plain textbook formula (C0) is what predicts "pattern whenever the continuum band exists" regardless of domain; this sweep does not rank it against the gate, it asks about linear-theory limits only.
* No GPU or Nebius resources were used. The orx run logged only the analysis, locally.
