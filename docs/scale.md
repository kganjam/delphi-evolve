# Scaling the BioNeMo/ESM2 evidence (gpu_batch)

Owner: scale worker, branch `work/scale`. Written 2026-10-31 (Seattle PDT; the zone becomes PST on 2026-11-01 02:00).
The central contribution stays query-to-certify. This work answers one narrow question with spare compute:

> Does an ESM2 zero-shot prior, and which model size / scoring protocol, reduce the assays a query-to-certify policy needs to issue a correct certificate on the four-site TrpB landscape, relative to no prior and to a shuffled-prior control?

A negative answer is a valid result. GPU priors never discharge an empirical premise: certificates still use revealed measurements only.

## What exists (all code is in `gpu_batch/`)

| Piece | File | What it does |
|---|---|---|
| Shared-pool snapshot, ownership, yield policy | `pool.py` | Parses `nebius ai {job,endpoint} list --format json`; counts our H100s; decides how many shards may launch and which of OUR jobs to release when another team is waiting. Pure functions, fixture-tested. |
| Controller / monitor | `controller.py` | `status`; `monitor` polls at most every 60 s, appends `artifacts/scale/queue_log.jsonl`, launches queued specs by priority, releases lowest-priority owned jobs. |
| Nebius CLI wrappers | `nebius_cli.py` | create / get / cancel; no credential value is read. |
| Job side | `shard_runner.py`, `job_entry_scale.sh` | Scores fixed units of the 160,000-variant library with one ESM2 checkpoint. Imports the gpu worker's vendored `embed_trpb.py` for model loading, mapping and scoring. |
| Vendored payload | `vendor/` + `VENDOR.json` | gpu worker's `embed_trpb.py`, `trpb_ref.py`, FASTA, `recover_from_logs.py`, `fetch_job_logs.py` at a recorded commit with sha256. Not edited. |
| Assembly | `assemble.py` | Recovers units from job logs, places rows at the library index, derives label-free scalar priors. |
| Downstream use | `prior_replay.py` | Runs core's own `run_episode` with and without the prior, plus a shuffled control. |

## Facts established by running things (not assumptions)

* Nebius log API: **at most 1000 lines per query** (default 100). The CLI default silently truncates. Timestamps have 1 s resolution, so emitters must be paced; the gpu worker's `fetch_job_logs.py` pages by halving the time window. A 4 MB blob (889 lines) round-tripped with matching SHA-256.
* The bucket mounted at `/output` rejects `np.savez` (zipfile seeks): `OSError: [Errno 22]` killed the gpu worker's first main job `aijob-e00d27jgpd2n9kwva1` (FAILED, 07:29Z). Shard jobs here write to local disk and ship results through the log; nothing relies on the bucket. No object-store credentials are available to read a bucket back from this host anyway.
* NGC PyTorch image pull took about 7 minutes (job created 07:18Z, started 07:25Z). Short jobs are dominated by this, so shard jobs carry many units.
* Probe (gpu worker, `aijob-e00gqrf19pjdrbyat3`): H100 80GB, TE ESM2-650M bf16, 587 variants/s single pass at batch 32 (256 variants; tiny sample, not a sizing number).

## Ownership and yielding rules (implemented in `pool.py`, tested in `tests/test_gpu_batch_pool.py`)

1. Cancel only IDs in `artifacts/scale/job_manifest.json` under `owned`, whose live `job get` id and name both match and whose name starts `delphi-evolve-scale-`. Anything else is refused.
2. The gpu worker's jobs are `peers`: counted against our 10, never cancelled. An unlisted H100 workload named `kganjam-delphi-*` is counted as ours (we launch less) but never cancelled. No ownership is inferred from other names such as `kg-extract`.
3. Launch at most one job per 60 s cycle; only if no other team's H100 workload is waiting, our total (owned + peers + conservative prefix) is under 10, and at least 2 pool H100s would remain free (pool assumed 16; the quota itself is unreadable).
4. If another team's H100 workload is queued (state in PENDING/QUEUED/WAITING/SCHEDULING/CREATING/PROVISIONING, or an unrecognised state), release owned jobs, lowest priority first, only as many GPUs as the waiting demand exceeds free capacity.
5. If the pool cannot be listed (error or truncated listing): launch nothing; after 5 consecutive blind polls, release owned jobs by per-ID verified cancel down to a floor.
6. Every cycle is logged to `queue_log.jsonl`. Units are small and checkpointed (emitted to the log as they finish), so a release loses at most the unit in progress.

Limitation: the Nebius documentation does not enumerate job states for us. The WAITING/HOLDING sets above are a conservative reading; unknown states of other teams' jobs are treated as possible waiters.

## Predeclared design (frozen before any scale-job output existed)

* Library: all 20^4 = 160,000 variants on the Tm9D8s* background (397 aa, positions 183/184/227/228, parent VFVS), mapping from the gpu worker's checked `trpb_ref.py`. Verified again here: tokenising the genotype string and masking the four sites reproduces the runner's `lp_all` and `lp_un` exactly for 3 variants (8M model, CPU).
* Units: unit k = positions `[5000k, 5000(k+1))` of the seeded permutation (seed 20261031, from the gpu worker). A partial run is a random, label-free subset.
* Per-variant outputs: `lp_un`, `lp_mask` (the gpu worker's protocols), `lp_all` (all four sites masked at once), seeded Gaussian random projections of site embeddings (4 x 32) and mean-pool embeddings (32) in fp16.
* Scalar priors relative to the parent, z-scored over the library: `mm_wt` (additive WT-context table), `mm_ctx` (context-aware single-site-masked pseudo-LLR), `unmasked`, `allmask`.
* Model ablation: ESM2 TE checkpoints 8M, 35M, 150M, 650M (gpu worker), 3B, optionally 15B, with fixed revisions in `shard_runner.REGISTRY`.
* Primary prior for the policy replay: `mm_ctx`, chosen now for every model. Others are descriptive.
* Replay: `q2c` and `collective_shared` at core's frozen 20-seed panel, 1000-assay budget; baselines `none`, `shuf_*` control, `esm_*`. Per-episode OLS calibration uses only the free initial observations (see `prior_replay.py`). Paired differences use a seed-cluster bootstrap and are descriptive, not coverage claims.

## Results (2026-10-31, run 00:44-02:13 PDT; all numbers from saved artifacts)

### Compute actually used
Ten owned single-H100 jobs, 2.63 H100-hours of job wall time (`artifacts/scale/library_receipts.json`; from recorded started_at to finished_at; not a billing measurement). Peak concurrent own H100s counted by the monitor: 8 (cap 10; the gpu worker's 650M job had finished). 57 monitor cycles, 0 failed listings, **0 cycles with another team's job waiting, 0 releases**: the yield path ran live only as a no-op; it is verified by fixtures, not by a real eviction. Metered charge: unknown (the event covers Nebius; no invoice seen), not zero.

Measured throughput (variants/s, six passes per variant incl. random projection, batch 64, H100): 8M and 35M not logged separately here, 150M 217, 650M 126, 3B 36.7. A 3B unit of 5,000 variants took 136 s plus 7 s of paced log emission; model load 227 s (12 GB download); NGC image pull about 7 min. Peak GPU memory 7.7 GB for 3B at batch 64. Each unit ships as ~1.6 MB (354 log lines). 15B was NOT run: the size curve below is flat from 150M to 3B, so a 61 GB-checkpoint, ~7 GPU-hour run had no evidence behind it.

### Reproducibility cross-check against the gpu worker (independent job, batch 128 vs 64)
650M TE, all 160,000 variants: `lp_masked_obs` mean |diff| 1.5e-5, max 0.078 (bf16); `lp_unmasked_obs` mean 6.8e-7, max 0.031; WT table identical; correlation of summed scores 0.99999996. Their job `aijob-e00whrj05xvrnbfxtx`, mine `aijob-e00bz2z168xhb8sqj0`.

### Descriptive size/protocol ablation vs measured TrpB growth (`artifacts/scale/ablation_descriptive.json`)
159,129 measured genotypes, y = core's bg-subtracted two-replicate mean. Spearman rho of the label-free prior (variant-resampling bootstrap 95% interval is descriptive, variants are not independent draws):

| model | mm_wt | mm_ctx | unmasked | allmask | top-1% overlap (mm_ctx) |
|---|---|---|---|---|---|
| 8M | 0.194 | 0.182 | 0.158 | 0.192 | 0.12 |
| 35M | 0.187 | 0.176 | 0.129 | 0.182 | 0.22 |
| 150M | 0.202 | 0.196 | 0.172 | 0.207 | 0.28 |
| 650M | 0.170 | 0.173 | 0.183 | 0.175 | 0.35 |
| 3B | 0.171 | 0.170 | 0.182 | 0.171 | 0.34 |

Reading: weak positive rank association (rho about 0.17-0.21) that does not grow with model size; top-1% enrichment (chance 0.01) rises from 0.12 to about 0.35 and plateaus at 650M. The cheapest protocol (additive WT-context table, 4 forward passes) is as good as the context-aware ones. This is evaluation only; it chose nothing.

### Does the prior help query-to-certify? (`artifacts/scale/replay_summary.csv`, `replay_rows.jsonl.gz`)
Core commit 8883518, core's frozen 20-seed panel (100 episodes per row), budget 1000, prior `mm_ctx` calibrated per episode from free initial observations. Mean assays-or-1000-if-uncertified (RMST@1000); difference vs the same policy with no prior, paired by episode, seed-cluster bootstrap interval (descriptive):

| policy | prior | RMST@1000 | diff vs none [interval] | certified@1000 | false certificates |
|---|---|---|---|---|---|
| q2c | none | 483.1 | | 78 | 0 |
| q2c | 8M | 464.5 | -18.6 [-46.6, +7.6] | 79 | 0 |
| q2c | 35M | 486.2 | +3.2 [-20.7, +29.3] | 78 | 0 |
| q2c | 150M | 453.2 | -29.9 [-86.3, +21.2] | 80 | 0 |
| q2c | 650M | 490.1 | +7.0 [-20.3, +36.4] | 78 | 0 |
| q2c | 3B | 475.5 | -7.6 [-34.2, +14.9] | 77 | 0 |
| q2c | shuffled 150M (control) | 463.6 | -19.5 [-60.3, +19.1] | 77 | 0 |
| q2c | shuffled 3B (control) | 463.5 | -19.6 [-42.2, +2.2] | 80 | 0 |
| collective_shared | none | 466.9 | | 78 | 0 |
| collective_shared | 3B | 466.9 | -0.0 [-39.1, +39.7] | 78 | 0 |
| collective_shared | shuffled 3B | 460.5 | -6.5 [-32.3, +25.0] | 78 | 0 |

**Result: no clear benefit under this integration.** Every interval contains zero, no size shows a trend, and the shuffled-prior controls move RMST as much as the real priors (-19.5, -19.6), so the differences are within what perturbing the surrogate does. No false certificates in any configuration (certification still rests on revealed measurements). The honest statement is "an ESM2 zero-shot prior of 8M-3B parameters did not measurably reduce assays-to-certificate for core's q2c or shared-collective policies at this budget on this landscape". Not tested: a supervised/embedding kernel, other priors, other budgets, 650M with collective_shared, and the other three scoring protocols in the replay.

## Reuse contract (exact IDs)

Durable (untracked, this host): `/data/artifacts/delphi-evolve-scale/arrays/{te8m,te35m,te150m,te650m,te3b}_library.npz` with sha256 in `artifacts/scale/library_receipts.json`. Keys: `have` (160000 bool, all True), `lp_un`, `lp_mask`, `lp_all` (160000,4) f32, `site_rp` (160000,4,32) f16, `mean_rp` (160000,32) f16, `raw_<protocol>`, `z_<protocol>`, `meta_json` (repo, revision, rp seed). Row i is the genotype `trpb_ref.all_genotypes()[i]` (= `evolve.data.encode` order, site 183 slowest; asserted in tests). Tracked: `artifacts/scale/priors_z.npz` (keys `<model>__mm_ctx`, `<model>__mm_wt`, z-scored, float32; NOT score units). Raw per-unit blobs and job logs: `/data/artifacts/delphi-evolve-scale/recovered/<job-id>/`.

| model | repo @ revision | jobs |
|---|---|---|
| te8m | nvidia/esm2_t6_8M_UR50D @ 3674a6ac | aijob-e00j9xfkkz9rpeakz6 |
| te35m | nvidia/esm2_t12_35M_UR50D @ ca13c2d4 | aijob-e00cgjqnrbdeeybnj5 |
| te150m | nvidia/esm2_t30_150M_UR50D @ a2e82bef | aijob-e00db00w7bzzp973r0 |
| te650m | nvidia/esm2_t33_650M_UR50D @ 118f470e | aijob-e00bz2z168xhb8sqj0 (gpu worker: aijob-e00whrj05xvrnbfxtx) |
| te3b | nvidia/esm2_t36_3B_UR50D @ 0850cbdf | aijob-e00kejm199cp3hq1nt, -e00hsqc8eyxhaps2rw, -e00nga5q6vjqbbee30, -e00y49t1xsfxm7cmqf, -e00zv8gre71k3mxt1s, -e00msfjf9v25bjzb2w |

To use a prior in a core policy: take `z`, then per episode fit `prior = a + b z` by OLS on that episode's free initial observations (`gpu_batch.prior_replay.episode_prior`) and pass it as `prior=` to `run_episode`. Do not use a shared slope fitted on all labels. For the demo `compute` block: provider Nebius, models above (BioNeMo TransformerEngine checkpoints, bf16), job IDs above; state the null replay result with it. All fields are `predicted`, never `observed`.

To run new GPU jobs (consumes shared capacity): `python -m gpu_batch.controller monitor --launch` with the queue in `artifacts/scale/launch_queue.json` (needs the Nebius `hackathon` profile), then `gpu_batch.assemble recover|library`, `gpu_batch.ablation`, `gpu_batch.prior_replay run|summarize`.

## Limitations
* The yield-to-other-teams path was never triggered live. Job state names are inferred; unknown states are treated as waiting.
* One landscape, one enzyme, four sites; cell-growth proxy, not catalysis.
* Replay uses 20 seeds (core's panel); intervals are descriptive resampling summaries, not coverage claims, and the surrogate/policy randomness makes a +/-20-assay swing unremarkable (see shuffled controls).
* Random-projection embeddings (`site_rp`, `mean_rp`) were produced and shipped but not yet evaluated downstream; no claim is made about them.
* Nebius LLM inference was not used: only a cloud IAM token is configured, no AI Studio API key. Brev, OpenAI: not touched.
* Actual metered charges: unknown.

## Coordinator audit

The coordinator independently checked all five full-library file hashes and 160,000-row coverage, recomputed ten correlations from source measurements, recounted all 1,100 episode summaries and their paired seed bootstrap intervals, and queried all ten owned jobs live as COMPLETED. See `artifacts/integration/scale-coordinator-audit.json`. The scale replay did not retain per-query logs; it does not have the query-by-query audit of the core and LazySP studies. This limits independent reconstruction of its certificate histories. Compact scalar priors and episode rows are committed; full projected embeddings remain on this host.
