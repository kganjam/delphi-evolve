# Compute: ESM2 inference on one Nebius H100 (gpu worker)

All times Seattle PDT, 2026-10-31. Everything below is backed by files in `artifacts/gpu/`.
GPU outputs are **model predictions**. They guide measurement choice and never certify fitness.

## What ran

| Item | Value |
|---|---|
| Reference | TrpB Tm9D8s*, 397 aa (incl. C-terminal `LEHHHHHH` tag), numbering = 1-based index into the FASTA. Sites 183/184/227/228 = **V/F/V/S** (parent genotype `VFVS`). |
| Reference source | CaltechDATA record h5rah-5z170 (CC0 1.0), member `data/ftmlde_data/tm9d8s_AAs.fasta`, sha256 `d56ebe8d…c6c`. |
| Verification | `artifacts/gpu/reference_verification.json`: identical to `TARGET_b0.3.fa`; PDB `Tm9D8s_refine_19.pdb` has VAL/PHE/VAL/SER at the four numbers (chains A and B); all 3,199 reads in `118X_184X_pooled_culture_data.csv` match the reference numbering at 118 and 184; parent row `VFVS` is measured in `simplified_AA.csv`. |
| Model (BioNeMo) | `nvidia/esm2_t33_650M_UR50D` @ `118f470e7e96ba8741227ab898e54758850e9563`: NVIDIA BioNeMo-recipes TransformerEngine ESM2-650M, HF custom code (`NVEsmForMaskedLM`), bf16. |
| Model (plain) | `facebook/esm2_t33_650M_UR50D` @ `08e4846e537177426273712802403f7ba8261b6c`, plain PyTorch/Transformers (`EsmForMaskedLM`), fp32 and bf16. Never called BioNeMo. |
| Container | `nvcr.io/nvidia/pytorch:25.12-py3` (digest `sha256:1dc787f5c6264fcc1c99809f99b84823e73ed4588d5a581b94290fc2a8fecff8`), torch 2.10.0a0+nv25.12, CUDA 13.1, **transformer_engine 2.10.0**, transformers 5.5.0, Python 3.12.3. NVIDIA driver 580.173.02. |
| Hardware | 1× H100 80GB HBM3 (`gpu-h100-sxm`, `1gpu-16vcpu-200gb`), project `workshop-30-10`. |
| Variants | **All 160,000 = 20^4 genotypes**, defined combinatorially, with no outcome label involved. A seeded permutation (PCG64 seed 20261031, fixed before any output existed) fixes processing order so any prefix is label-free. |

## Jobs (Nebius `ai job`; all mine; none of others' touched)

| Job | Purpose | Run time (UTC) | State |
|---|---|---|---|
| `aijob-e00gqrf19pjdrbyat3` | probe: env, bucket, log transport, parity n=64 | 07:15:21–07:17:39 (2m18s) | COMPLETED, exit 0 |
| `aijob-e00d27jgpd2n9kwva1` | parity n=512 + main sweep | 07:25:57–07:29:19 | **FAILED** in main sweep: the bucket mount rejects `np.savez` (seek-back write, `OSError 22`). Parity completed first and is kept. |
| `aijob-e00whrj05xvrnbfxtx` | main sweep (fix: shards on local disk, sequential copy to bucket) | 07:41:48–08:02:11 (20m23s) = 00:41:48–01:02:11 PDT | COMPLETED, exit 0 |
| `aijob-e00n4wkfyqafsqby8w` | CPU-only check that the bucket copy matches (read-only mount) | short | COMPLETED; sha256 of the three compact files equal the log-recovered ones; 40 shards, 2.0 GB |

H100 container time ≈ 2.3 + 3.4 + 20.4 ≈ 26 min, plus 6–8 min of image pull per fresh node. Nebius is event-provided; no metered charge is known to me, and nothing was spent on Brev.

## What each variant gets (per genotype)

For every sequence the model runs 5 forward passes (one unmasked, four with a single library site masked):

* `lp_unmasked_obs[4]`: log p(observed aa at each site | full variant, nothing masked).
* `lp_masked_obs[4]`: log p(observed aa at site j | variant context with only site j masked). Full 33-token softmax. Summing over sites gives a context-aware 4-site pseudo-log-likelihood. The `VFVS` row minus the WT scalar is the delta.
* `wt_masked_table_20aa[4,20]`: WT-context masked marginals, which give the additive prior.
* Mean-pooled and per-site final hidden states (1280-d fp16) were stored to shards; PCA-64 projections (label-free, fit on all 160,000) are the portable embeddings.

## Results (single runs; numbers copied from receipts)

BioNeMo TE checkpoint vs plain ESM2 (`artifacts/gpu/parity/…n512…json`, 512 label-free variants, reference = plain fp32):

* TE bf16 vs plain fp32: mean-pool cosine min 0.99998; site-embedding cosine min 0.9987; summed 4-site log-prob Pearson 0.99976; mean |Δlog-prob| 0.051 (max 0.30); WT table argmax agreement 4/4.
* Noise floor, plain bf16 vs plain fp32: cosine min 0.99999 / 0.9981; Pearson 0.99969; mean |Δ| 0.057 (max 0.38). So the TE checkpoint differs from the original by about as much as bf16 itself.
* Throughput, one unmasked pass, 4,096 variants, batch 128, one measurement each: **TE bf16 772 seq/s**, plain bf16 453, plain fp32 236 (1.7× and 3.3×). Single run on a shared host. This is not a benchmark of the checkpoint in general.
* Batch-size effect: the `VFVS` row inside a 128-batch gives pll4 −2.565 vs −2.580 for the standalone batch-1 WT pass (bf16 numerical noise).

Prior vs measured assay (`artifacts/gpu/orx/analysis.json`, 159,129 measured non-stop genotypes, none imputed; outcome = mean of unnormalised `mu_1-bg`, `mu_2-bg`; replicate Spearman 0.708):

| Label-free score | Spearman | AUROC(active flag) | top-1000 overlap |
|---|---|---|---|
| ESM2 additive WT-marginal | 0.170 | 0.828 | 0.316 |
| ESM2 4-site context PLL | 0.173 | 0.822 | 0.309 |
| ESM2 unmasked ratio | 0.183 | 0.811 | 0.302 |
| BLOSUM62 sum | 0.100 | 0.714 | 0.067 |
| −Hamming to parent | 0.095 | 0.599 | 0.062 |

Random 80/20 ridge, 10 split seeds (optimistic split; SD is across seeds, not a CI): one-hot additive 0.2568 ± 0.0041; one-hot + pairwise 0.3013 ± 0.0067; ESM2 sites-PCA64 alone 0.2277 ± 0.0032; ESM2 PCA64 + one-hot 0.2579 (paired Δ vs additive +0.0011, range −0.0006…+0.0037); one-hot + 3 ESM2 scores 0.2565 (Δ −0.0002).

**Reading:** the zero-shot prior has weak but real rank information and beats BLOSUM62/Hamming, but as an added feature on top of one-hot site identity it adds nothing detectable here, while pairwise (epistatic) terms add +0.044. The bootstrap resamples variants and is descriptive only. This is a null-to-weak result for the sponsor model on this task and is reported as such. Nothing here tests the query-to-certify claim.

## Recovery and reproduction

* Compact results are emitted into the job log as checksummed base64 chunks (every chunk and every file has a SHA-256). The Nebius log API returns at most 1,000 lines per query and timestamps have 1 s resolution, so `gpu/fetch_job_logs.py` pages recursively by time.
* `scripts/run_gpu_recover.sh <job> <start> <end> <outdir>` rebuilt the committed arrays; the whole-file hashes match the job's own manifest. A 4 MB random blob also round-tripped byte-exact through the log in the probe.
* Full-fidelity per-shard embeddings (mean-pool + 4 sites, 1280-d, fp16; 2.0 GB, 40 shards) are only in bucket `kganjam-delphi-evolve-gpu-20261031` (`storagebucket-e003992510513182731464`, 8 GiB cap, project `workshop-30-10`) under `main/shards/`. I could not set an anonymous-read policy (`PermissionDenied`) and did not create an access key, so they cannot be pulled to this host without another job. The bucket is left in place on purpose. Delete it when no longer needed: `nebius --profile hackathon storage bucket delete --id storagebucket-e003992510513182731464`.
* Relaunch: `GPU_BUCKET_ID=<bucket> scripts/run_gpu_job.sh <name> 2h --stage main --out /output/main`. Public files only; no credential value is read or passed.

## Limitations

* The reference is the construct used for the assay (with His tag). No mapping to wild-type *T. maritima* numbering is claimed. FASTA header says `Tm9D8*` while the archive files are named `tm9d8s`; the archive treats them as one background.
* The model scores sequences in the full-length Tm9D8s* context, which approximates but need not equal the assay's expression context.
* bf16 inference; scores are reproducible only up to ~0.05 nats mean (batch/kernel noise).
* Throughput figures are one measurement each on a shared cluster.
* The OpenResearch run (`artifacts/gpu/orx/receipt.json`) is a local CPU analysis, not hosted compute.
