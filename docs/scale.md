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
