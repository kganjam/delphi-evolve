# EvoRoute feasibility audit — TrpB four-site landscape (Johnston 2024)
Written 2026-10-30 ~11:55pm PDT. Everything under "Findings" was fetched/computed in this session; code in `analysis/`.

## Verdict
**Data: real, open, retrieved. Science wedge: moderate, not universal-biology. Build it, but only as "a calibrated, leakage-aware decision certificate for the next assay batch" — not as generic protein design.** GFP fallback not needed.

## Findings (verified)
- Paper: Johnston et al., PNAS 121(32):e2400439121, "A combinatorially complete epistatic fitness landscape in an enzyme active site". PMC11317637 (https://www.ebi.ac.uk/europepmc/webservices/rest/PMC11317637/fullTextXML). Article license CC BY-NC-ND 4.0 (Crossref).
- Data: CaltechDATA https://doi.org/10.22002/h5rah-5z170 → https://data.caltech.edu/records/h5rah-5z170 . **License: CC0 1.0** (record API `rights`, https://data.caltech.edu/api/records/h5rah-5z170). Published 2024-01-19. Files: `data.zip` 3.32 GB, `code.zip` 413 MB. Raw reads: SRA PRJNA1127511.
- I did NOT download the 3.3 GB zip. I read its central directory by HTTP range and extracted 3 files (63 MB total) into `caltech/`; `analysis/zget.py` does this. Python urllib gets 403 from the host; curl works.
- Files used (paths inside data.zip):
  - `data/figure_data/4-site_merged_replicates/20230827/four-site_simplified_AA_data.csv` → `caltech/simplified_AA.csv`. Columns: `AAs,AA1..AA4,# Stop,fitness,active`. 193,170 rows (stop-containing included).
  - `.../four-site_summary_AA_data.csv` → `caltech/summary_AA.csv`. Per-replicate columns: `InputCount_1/2, enrich_1/2, mu_1/2, mu_k-bg, mu_k-bg/max, avg_mu-bg/max, # Stop, active`.
  - `data/figure_data/4-site_imputed/20230828_KNN_imputed_TrpB.csv` → `caltech/KNN_imputed_TrpB.csv`. 871 rows.
  - Not fetched but useful: `4-site_outputs/20230828_local_optima.csv`, `DE_simulations/top9783.csv`, `ftmlde_data/ZeroShotPreds_EVmutation.csv` (4 MB), codon-level replicate tables (4-site_codon_replicates, 10 MB each).
- Counts: library 20^4 = 160,000. **Measured, no stop codon: 159,129 (99.45%)**, matching the paper. **Imputed (KNN): 871, kept in a separate file, none in the measured file** (verified zero overlap). Active (above stop-codon mean + 1.96 SD): 9,783 (6.11%). Stop-containing rows: 34,041, mean fitness ≈ 0, SD 0.025.
- Genotype coordinates: TrpB (Tm9D8s*) positions 183, 184, 227, 228; parent VFVS, fitness 0.408 (normalised so top variant AIKG = 1.000). Next top: CLKG 0.932, VLKG 0.923, ALKG 0.917.
- Assay semantics: E. coli Trp-auxotroph growth selection, two replicate flasks, 36–44 h timepoints, fitness from a growth-rate fit (Kowalsky et al.) normalised to max. Proxy for native Trp-synthesis activity in a non-native environment, not kcat/KM. Paper measured kinetics separately for a few variants (xlsx in `data/kinetics/`).
- **Assay noise (computed from `summary_AA.csv`, 159,129 non-stop):** replicate Pearson 0.961, Spearman 0.714 (bulk is near-zero noise-dominated). Among active variants Pearson 0.997. Replicate-difference SD by input count: <20 reads 0.044; 20–50 0.030; 50–200 0.017; ≥200 0.0085. So per-variant noise is heteroscedastic and read-count-driven, which is usable as a per-variant error bar.
- Baselines (one random 80/20 split, seed 0, `analysis/audit.py`): one-hot additive ridge Spearman 0.27; HistGradientBoosting on categorical 4 positions Spearman 0.385, top-100 recall 0.85. Holding out all AA3=K variants (an extrapolation split), ridge Spearman 0.28. Honest read: **the global rank is weak because ~94% of variants are inactive near zero; the top end is learnable.**
- Active-learning toy (5 seeds, 96 init + 4×96 batches, HGB greedy vs random): best found 0.79 vs 0.62; fraction of the true top-100 found 2.1% vs 0.08%. Greedy is better but does not find AIKG reliably in 480 assays. Single config, 5 seeds; no CIs; not a result to quote.
- Delphi (network source, queried live): domains = darwin-origin-1859 (247 claims), thompson-growth-form-1917 (104), math-population-genetics-and-evolutionary-theory (18, all with math), morphogenesis (3), reaction-diffusion/Turing (3). Text search for "epistasis" and "fitness landscape" returned **zero** claims. Relevant existing claims: Fisher FTNS `…/claim/fisher-ftns` (nanopub RAtLFqIIyu4r-GlMcBEfmDtbV-CHwWxQ49gVMtHIX6r48), Fisher infinitesimal, Kimura fixation probability, Kimura neutral theory, Maynard Smith hitchhiking, Darwin ch.1 accumulative selection (darwin1859-ch01-11/-17). So the real hook is: Delphi has *no* epistasis claim, and the TrpB data can test a Fisher/Darwin-style "additive selection response" claim. Counts and claims above are from this session's live MCP calls.

## Honest assessment
- Strengths: CC0, complete, replicate-level data with read counts, a landscape where additivity demonstrably fails (paper: ~35% sign epistasis, 9% reciprocal sign), published local optima for ground truth, and the paper's own zero-shot (EVmutation/Triad) comparison for baselines. Exact "oracle lookup" means the active-learning simulator needs no wet lab and the GPU is optional.
- Weaknesses: (1) this is a well-trodden benchmark (FLIP/ProteinGym-like, ftMLDE by Li/Arnold used this data); novelty must come from the certificate, not the regressor. (2) The fitness is a selection proxy, so "intervention" means choosing which variants to assay. (3) 4 positions only — not "universal", which is good, but the story must stay at four sites.
- Versus generic protein design: stronger because every claim is checkable against measured ground truth and noise is quantified. Weaker if the pitch promises new enzymes.

## Leakage / split rules to adopt
1. Never impute-then-split: use only the 159,129 measured rows as labels; the 871 imputed ones are held out, never evaluation targets.
2. Splits: random (optimistic), leave-one-residue-out per position, and "no-shared-pair" (hold out all variants containing a chosen pair at 227/228). Report all three.
3. Normalisation (`/max`) uses the max over the whole library — a leak if the max variant is in test; recompute scale from the train set or report the raw `mu` columns.
4. `active` threshold derives from stop codons over both replicates: fine, but fix it before looking at test.
5. Use replicate 1 to train and replicate 2 as the independent test label — gives a noise ceiling for free.

## Lean (suggested, small and genuinely decision-relevant)
Lean 4.35.0 is at `~/.elan/bin/lean` (not on PATH). Theorem to prove, no Mathlib needed beyond `Int`/`Rat`:
*Interval-dominance certificate:* given per-variant estimates ŷᵢ with |ŷᵢ − yᵢ| ≤ εᵢ, if ŷₐ − εₐ > ŷⱼ + εⱼ for all j ≠ a, then a is the true argmax; and a top-k version (k variants whose lower bounds exceed all others' upper bounds are exactly the true top-k set). Use ε from the read-count bins above. The Lean file is the checker the demo calls on the data: it says "certified"/"cannot certify, assay N more". Weak spots to say aloud: the bound ε is an empirical assumption (replicate SD), not a proven fact.

## 24h deliverables
1. (3h) `evoroute/` repo: `fetch.sh` (range-extract the 3 files, SHA256s), `audit.py`, README with license + counts. Starting from `analysis/` here.
2. (4h) Evaluation harness: 3 split protocols, ridge/HGB/EVmutation-ZS baselines, noise ceiling from replicate 2.
3. (5h) Active-learning simulator: batch-wise, ε-aware acquisition vs random vs greedy, 20+ seeds, CIs. Optional H100 for a small ESM embedding baseline — not required.
4. (3h) Lean certificate + a Python emitter of certificate instances checked by `lake build`.
5. (4h) Visual: 4-position grid / path map (183-184 × 227-228 heatmap), click a variant → show its replicate error bar, what the certificate can/can't claim, and how many assays buy certainty. Intervention = "choose next batch".
6. (1h) One Delphi nanopub-style claim draft: "At TrpB 183/184/227/228, additive models rank-explain X% (Spearman 0.27 single split) of fitness; epistasis dominates" — only after the multi-seed numbers exist.

## Unverified / speculation
- Lean 4.35.0 is installed at ~/.elan/bin/lean (verified `--version`); I did not test a build or check for Mathlib.
- No GPU on this host (nvidia-smi absent); torch present. Nebius job not attempted.
- The 0.27/0.385 baselines are single-seed, untuned. Active-learning numbers are 5 seeds.
- Not checked: whether codon-level data shows additional noise (synonymous codons) beyond AA-level.
- GFP (Sarkisyan 2016) not fetched. GB1 4-site (Wu 2016) fitness is in the same zip (`data/figure_data/GB1_data/GB1_Fitness.csv`, 4.7 MB) and would be a safe second dataset for a generalisation check.
