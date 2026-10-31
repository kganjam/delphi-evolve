# Core: measured TrpB graph and matched-budget query-to-certify replay

Everything below was produced by code in `evolve/` from the CC0 Johnston et al. (PNAS 2024) TrpB four-site table (CaltechDATA 10.22002/h5rah-5z170). It is a **retrospective replay over already-assayed labels**: no new wet-lab measurement, no new variant, no biological-truth claim. Numbers here are copied from `replay/table_primary.csv`, `replay/table_paired.csv`, `replay/summary.json`; if they disagree, the CSV wins.

## What was built

| Piece | File | Notes |
|---|---|---|
| Reproducible fetch + hashes | `scripts/fetch_data.py`, `data/manifest.json` | Reads 3 members of the 3.3 GB `data.zip` by HTTP range (28 MB transferred, 10 requests); SHA256 verified; `--from-dir` for an existing cache |
| Audited loader | `evolve/data.py`, `artifacts/core/audit.json` | 193,170 source rows; 159,129 measured non-stop genotypes; 871 unmeasured = exactly the 871 KNN-imputed rows (overlap with measured = 0, never used as observations); 698 rows with min input count < 10 are flagged, not dropped; source declares 0 censored rows |
| Score definition | `evolve/data.py` | mean of replicate (raw growth rate `mu_k` − per-replicate mean `mu` of the 34,041 stop-containing control rows), integer micro-units. **No `/max` normalisation, no authors' row-specific `mu-bg`, no KNN labels.** |
| Interval model (ASSUMED) | `evolve/data.py` | `eps = ceil(kappa * sd_bin / 2 * 1e6)`; `sd_bin` = replicate-difference SD by min input-count bin (0.0150/0.0100/0.0059/0.0030), recomputed and checked by `python -m evolve audit`. **`kappa` (main = 2) is an assumed sensitivity multiplier, not a confidence level; there is no coverage claim.** |
| Graph | `evolve/graph.py` | Declared scope = measured subgraph of the 20^4 library, single substitutions (76 neighbours). Edge u→v admissible iff `Lo[v] >= Hi[u]` (integers). Memory is flat 160k-entry arrays plus a 76-neighbour arithmetic generator; no dense matrix |
| Truth | `evolve/graph.py::truth_bfs` | Forward admissible closure under *full* measured labels. Benchmark truth only |
| Policy-visible state | `evolve/graph.py::Ledger` | Incremental closure + unknown frontier from **revealed labels only**. `open` iff target ∈ closure; `blocked` iff the closure has no unknown neighbour (closed set/cut); else unresolved. Every certificate is re-verified against full data after the fact (`verified_by_full_data`) |
| Oracle + event log | `evolve/oracle.py` | Reveals the label of a queried genotype only; unmeasured genotypes cost an assay and reveal only "outside scope". Hash-chained (tamper-evident, **unsigned**) event log |
| Policies | `evolve/policies.py`, `evolve/collective.py` | random frontier, greedy walk, GP uncertainty, `directed` (deterministic single policy, no learned model), `q2c` (GP-priced open-route vs cut-completion), `q2c_nomodel`, collective shared/isolated |
| Replay | `evolve/replay.py` | 20 fixed seeds × 5 pairs = 100 episodes per policy, budget 1000 assays beyond 96 random initial observations (+start, target), same for all policies |
| Demo JSON | `evolve/demo.py` → `artifacts/demo.json` | CONTRACT fields; proof/compute/claims `unavailable` |
| Certificates for the Lean worker | `artifacts/core/certificates/*.json` | integer intervals, route or closed set + boundary, dataset hash, scope, assumptions (schema `delphi-evolve/core-certificate/v1`). Not Lean-checked here |

## Protocol (frozen before the first main run: `protocol.json`, panel sha256 `bb6c144e…`)

* **Family A (20 pairs, "seeded-initial")**: target = best-scoring genotype among the seed's own 96 initial observations; start = random other initial observation with lower score and Hamming ≥ 2. Uses only admissible observations; the open/blocked outcome is not looked at. Result: 12 open, 8 blocked.
* **Family B (80 pairs, "published-parent")**: start = parent VFVS; targets AIKG, CLKG, VLKG, ALKG, the published top variants. All 80 are open at kappa = 2. Seeds vary only the 96 initial observations and tie-breaks, so the 4 targets × 20 seeds are **not 80 independent pairs**.
* Unresolved or stuck runs are **right-censored at 1000 and kept**. A policy is not told the budget, so one run gives the whole certificate-vs-assays curve.
* Uncertainty: paired differences on identical episodes; bootstrap over the 20 **seeds** (clusters), percentile 95%. Descriptive resampling, not a coverage claim.

## Results (20 seeds, kappa = 2, budget 1000)

Fraction of the 100 episodes with a sound certificate (open or blocked); the rest abstain/censored. **0 false certificates and 0 full-data verification failures for every policy**. That is guaranteed by construction (certificates use only revealed labels), so it is a check, not a finding.

| policy | 250 assays | 500 | 1000 | restricted-mean assays @1000 |
|---|---|---|---|---|
| random frontier | 0.07 | 0.14 | 0.21 | 877 |
| greedy walk | 0.07 | 0.07 | 0.08 | 934 |
| GP uncertainty | 0.05 | 0.08 | 0.13 | 931 |
| directed best-first (single deterministic baseline) | 0.30 | 0.30 | 0.32 | 709 |
| **q2c (GP-priced)** | 0.43 | 0.48 | 0.78 | 483 |
| q2c, no learned model *(post hoc)* | 0.16 | 0.96 | **0.96** | 378 |
| collective, shared evidence | 0.47 | 0.49 | 0.78 | 467 |
| collective, isolated evidence | 0.39 | 0.58 | 0.77 | 485 |
| collective, shared, no GP *(post hoc)* | 0.11 | 0.59 | 0.96 | 518 |
| collective, isolated, no GP *(post hoc)* | 0.40 | 0.54 | 0.65 | 525 |

Paired differences in certified fraction at 1000 assays (a − b; seed-cluster bootstrap 95%; episodes a-better/b-better/tied):

* q2c − directed: **+0.46 [0.40, 0.53]**, 46/0/54. q2c − random: +0.57 [0.49, 0.64].
* q2c_nomodel − q2c: **+0.18 [0.14, 0.22]**, 18/0/82 (but −0.27 [−0.34, −0.21] at 250 assays: the GP helps early and hurts later).
* **collective shared − q2c: 0.00 [0.00, 0.00], 0/0/100.** The shared-evidence collective is indistinguishable from a single brain at 1000 assays; at 250/500 assays differences are small and the intervals include 0. **No collective advantage over one policy was found.**
* collective shared − isolated (GP): +0.01 [−0.07, 0.10] at 1000; isolated is *better* at 500 (−0.09 [−0.16, −0.02]). With a shared-evidence **round-robin** control (`collective_shared_rr`, same evidence, no cost arbitration) the shared arm matches `collective_shared`, so that effect is not due to arbitration.
* collective shared − isolated (no GP): **+0.31 [0.24, 0.37]**, 31/0/69. When the planner is the better one, cutting specialists off from each other's reveals costs certificates.

Blocked (cut) certification is **policy-independent**: all 11 policies certify the same 62% (5/8) of blocked family-A pairs, because a cut needs every neighbour of a small closed set assayed (76 assays for a 1-genotype set) and the 3 blocked pairs with closed sets of 1,800+ genotypes are infeasible in 1000 assays for any policy. The measurable gains are all in **open** certification.

## How to read the collective comparison

Specialists (data gatekeeper, route, cut, critic, arbiter) are separate Python objects with their own surrogate models and, in the isolated arm, private ledgers; proposals/challenges/decisions are logged with `visible_to` (see `replay/events/*.jsonl.gz`, seed 0, hash-chain valid). The critic demonstrably changes the purchased assay in the shared arm (it logs a challenge and demotes a route). But scheduling and arbitration are **fixed software in one process**, not independent agents, and a shared-evidence collective is exactly as capable as one planner using the same facts. The one leak in the isolated arm: a specialist that proposes an already-revealed genotype is answered from the data specialist's ledger at zero cost (logged as `duplicate_request`).

## Post-hoc disclosure and caveats (read before quoting)

* `q2c_nomodel`, `collective_shared_rr`, `collective_shared_c`, `collective_isolated_c` were added **after** looking at the 7-policy results (`protocol.json` lists 7). They are exploratory; selecting the best of several variants after the fact makes their margins optimistic. A first run of the main replay silently produced empty shards for seeds 5–19 (a code edit dropped `rows.append`); those shards were deleted and re-run, and `tests/test_core_replay.py::test_run_shard_writes_all_five_episodes` now guards it.
* The GP surrogate hyperparameters were fixed a priori and not tuned; the GP-priced planner being worse than a constant surrogate after ~250 assays is a property of **this** untuned implementation, not of learned models in general.
* The noise bins use replicate differences over all 159,129 rows (a population-level calibration, frozen before replay). kappa sensitivity (10 seeds, 5 policies, `replay_kappa1.0/`, `replay_kappa3.0/`): q2c and the collectives remain far above directed and random at kappa 1 (0.98/0.98/0.96 vs 0.34 and 0.38) and kappa 3 (0.78 vs 0.30 and 0.20), while directed vs random flips (directed < random at kappa 1); absolute rates change as truth changes (open fraction of family A: 0.8 at kappa 1, 0.6 at 2, 0.4 at 3).
* Open routes: for all 587 open certificates issued across the 11 policies in the main replay every edge is also nondecreasing in each replicate individually (`replicate_sign_agree_frac = 1.0`). This is a descriptive consistency check, **not** an independent held-out validation (the replicates are the source of the interval), and not a probability of correctness.
* Truth is finite measured-graph reachability under an *assumed* interval model, not biology. A blocked certificate says nothing about sequence space beyond this graph, nor about the 871 unmeasured genotypes.
* Family B reuses one start and four targets; family A has 20 pairs. Sample sizes for blocked pairs are small (8).
* No foundation-model prior has been run: `evolve.replay` accepts `policy+prior` with `EVOLVE_PRIOR_NPY` (a (160000,) array of predicted scores in `evolve.data.encode` order) for the GPU worker; until a real file exists this comparison is **not done**.
* Compute: CPU only (pinned to 1 BLAS thread per process, ≤2 processes). Wall time per episode (loaded shared host): ≤0.4 s for random/greedy/directed, up to 5–20 s for the GP-based and collective policies.

## Prior art

ALDE (Active Learning-assisted Directed Evolution; Nature Communications 2025, https://pmc.ncbi.nlm.nih.gov/articles/PMC11739421/) already benchmarks active-learning MLDE on this same TrpB and on GB1 (96 random initial variants + 4 rounds of 96; greedy/UCB/Thompson acquisition; DE walks and random sampling as baselines) and optimises the best variant found. It provides no formal certificate and no path/cut reasoning. This work asks a different question (assays needed to settle an open/blocked route decision for a fixed pair) and should not be described as a better optimiser than ALDE. We did not implement or compare against ALDE; the "single-policy baseline" here is `directed`, our own deterministic best-first.

## Reproduce

```
python scripts/fetch_data.py                       # or --from-dir DIR; verifies SHA256
python -m evolve audit                             # counts, hashes, noise-bin check
python -m evolve replay --seed-start 0 --seed-end 20 [--policies a,b] # resumable shards in artifacts/core/replay/shards
python -m evolve summarize                         # CSV tables, plots, query logs
python -m evolve demo --output artifacts/demo.json
python -m pytest tests/test_core_data_graph.py tests/test_core_replay.py
```
Wrap long runs as `systemd-run --user --scope -p TasksMax=128 -p MemoryMax=4G -p MemorySwapMax=0 -p RuntimeMaxSec=600 …` (the replay is chunked 5 seeds per scope).

## Files

`audit.json`, `protocol.json`, `certificates/`, `replay/{episodes,table_primary,table_paired}.csv`, `replay/summary.json`, `replay/{cert_vs_assays,outcomes_at_budget,ablation_*}.png`, `replay/queries/queries__<policy>.tsv.gz` (every assay of every episode), `replay/events/` (specialist event logs, seed 0), `replay_kappa{1.0,3.0}/` (sensitivity tables). `replay/shards/` is git-ignored and regenerated by `python -m evolve replay`.
