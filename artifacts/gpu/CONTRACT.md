# GPU → core integration contract

Files (all in `artifacts/gpu/main/`, hashes in `main_summary.json`; produced by H100 job `aijob-e00whrj05xvrnbfxtx`):

| File | Keys | Notes |
|---|---|---|
| `zeroshot_prior.npz` | `variant_index` int32 (160000), `lp_masked_obs` f32 (N,4), `lp_unmasked_obs` f32 (N,4), `wt_masked_table_20aa` f32 (4,20), `wt_lp_masked_obs` (4), `wt_lp_unmasked_obs` (4), `aa_order` (`ACDEFGHIKLMNPQRSTVWY`), `sites` (183,184,227,228) | model log-probabilities |
| `embedding_meanpool_pca64.npz` | `variant_index`, `mean`(1280), `components`(64,1280), `explained_variance_ratio`, `projection` f16 (N,64) | label-free PCA, 98.0 % variance |
| `embedding_sites_pca64.npz` | same with 5120-d (4 sites × 1280) | 93.5 % variance |

`variant_index` is the position in lexicographic order of `trpb_ref.all_genotypes()` (alphabet `ACDEFGHIKLMNPQRSTVWY`, site 183 slowest). The genotype key is the same 4-letter string as the `AAs` column of `simplified_AA.csv`.

Python: `from gpu.load_prior import load_prior` (add `gpu/` to `sys.path`) returns `{genotype: {additive_wt_marginal_delta, pll4_delta, unmasked_delta, emb_sites_pca64, emb_meanpool_pca64, evidence_kind:"predicted"}}`. Scores are log-prob **deltas versus the parent VFVS**; higher = model considers the substitution more natural, not higher fitness.

Rules for core:
1. Treat every field as `evidence_kind: "predicted"`. A node's `observed_score` comes only from the measured rows; the prior may rank or guide queries and **never discharges an empirical premise** (CONTRACT.md).
2. The prior covers all 160,000 genotypes, including the 871 non-stop genotypes with no measurement (KNN-imputed in the source; never observations). Whether a node is measured is the data loader's decision.
3. Prior information carries no outcome leakage: it was computed from sequence only. The post-hoc comparison in `artifacts/gpu/orx/analysis.json` used outcomes for evaluation only.
4. `compute` block for `demo.json` (fill from `artifacts/gpu/compute_block.json`): provider Nebius, model `nvidia/esm2_t33_650M_UR50D` (BioNeMo TE checkpoint), job id, artifacts with sha256. Strong caveat to show: weak prior (Spearman 0.17–0.18 vs measured), no added value over one-hot in the random-split ridge check.
5. Never name the plain Meta checkpoint "BioNeMo".

Recovery of the arrays from a fresh checkout needs no GPU: they are committed. Regeneration needs the Nebius profile `hackathon`; see `docs/compute.md`.
