# Claim reuse: how existing Delphi claims change a decision

Written 2026-10-31 (Seattle PDT) by the claim-reuse worker (Claude Sonnet 5.5, subscription). Code: `claim_runtime/`. Receipts: `artifacts/claim_reuse/`. Goal persisted in `tasks/results/claim-reuse.json`.

## The question this answers

The earlier Darwin links in this project were decorative: deleting Delphi changed no planner decision. This service closes that gap for **two existing Delphi claims** and for **observed TrpB evidence**. It is a small systems prototype. It is not protein generation, agent orchestration, new epistasis, or query-efficient path search (LazySP and Bayesian active edge evaluation exist; ALDE is prior art for ML-guided directed evolution). Anthropic's Claude Science work and the Adaptyv wet-lab benchmark (1,320 designs, 354 binders, 26.8% hit rate, Adaptyv case study of 2026-08-20) show agent-driven design with real wet labs; we do none of that. Our narrow claim: **portable claims with executable applicability checks, and evidence whose reuse is gated by typed guards, so that removing or changing a claim changes a downstream decision.** No market traction is asserted.

## What is executable

| Existing Delphi claim | Adapter | What it computes | What it refuses |
|---|---|---|---|
| `kimura-fixation-probability` (network nanopub `RA76F4g6…`) | `claim_runtime/kimura.py` (hand-authored, v1.0.0) | `u(p) = (1-exp(-4 Ne s p))/(1-exp(-4 Ne s))`, neutral `u = p`, stable `expm1` form; declared hypothetical scenarios and an explicit hypothetical route trajectory (SIMULATED) | haploid models, non-genic selection, varying Ne, linkage, any `s` that is not a declared hypothetical or a cited estimate (so **TrpB growth scores are refused**), string/expression parameters |
| `fisher-ftns` (network nanopub `RAtLFqII…`) | `claim_runtime/fisher.py` (v1.0.0) | partial (selection-component) change `V_A / wbar` (or `V_A`, Malthusian) from a **declared** additive genetic variance; exact one-locus identity check | total fitness change, "Fisher proves every mutation step improves fitness", clonal/total/phenotypic/replicate/landscape variance, unmet conditions |

Nothing evals a math string. Only the two curated claims run; any other claim id gets `no_adapter`. The Fisher theorem is **not formalized here** (no new Lean); the generic conditional path-soundness theorem in `lean/` is a different statement and is cited only as such.

### Pinning, versions, and what cannot silently stay "verified"
`claim_runtime/pins.json` stores the sha256 of the record fields the adapter was reviewed against (label, description, source, `delphi:context`, notation, hypothesis type). The raw MCP responses (source network and local, with response sha256) and the two published nanopub TriGs are in `artifacts/claim_reuse/delphi_records/`; the local record is content-identical to the network one. A request is refused if the claim is deleted, withdrawn, unavailable, or its content hash differs (`claim_changed`). The verification receipt (`artifacts/claim_reuse/verification_receipt.json`) binds the adapter source hashes (numerics + `service.py` + `common.py`) to the claim content hashes and to test/mutation exit codes; any drift makes the service refuse as `unverified`.

### Exact assumptions and what was checked
Recorded by Delphi (Kimura): diffusion approximation to Wright–Fisher, genic (additive) selection with coefficient s, constant Ne, no linkage. Fisher: partial change with average effects and environment fixed; `V_A` is additive genetic variance in fitness; the total-change reading is false under dominance, epistasis, frequency dependence or a changing environment. **The primary Kimura 1962 PDF could not be retrieved** (PMC returns a bot challenge); the diploid reading (2N copies, genotype fitnesses 1 : 1+s : 1+2s) was instead verified against an exact Wright–Fisher chain that I wrote from its textbook definition. Adapter-added assumptions are listed separately in every response. The Fisher papers (Price 1972, Ewens 1989) were taken as cited by the record, not re-read.

## Results (all numbers from saved artifacts)

### Kimura numerics vs exact chains (`artifacts/claim_reuse/popgen_benchmark.json`) — SIMULATED hypothetical populations
Diploid WF, N ∈ {10,25,50,90} (≤181 states), s ∈ {−0.05…0.2}. Reference checks: neutral chain is an exact martingale (max dev 4e-15); rational solve vs float solve (3e-16); linear solve vs forward iteration (5e-14); Moran chain vs gambler's-ruin closed form (8e-15). Diffusion-formula error for a new mutant: |rel. error| ≤ 0.6% at s=0.01, ≤ 2.4% at s=−0.01, ≤ 8.5% at s=0.2, but up to **139% at s=−0.05** (small, deleterious: the approximation is poor, and the service warns for |s| ≥ 0.1 only by convention). Haploid WF check: applying the diploid formula with Ne=N is wrong by up to 99% relative error; the variance-effective mapping Ne=N/2 matches within 5% — but that mapping is *not* in the Delphi claim, so the adapter does not implement it. This benchmark does not establish any empirical biological result.

### Boundary: TrpB growth score ≠ s
The default TrpB request (`examples/kimura_trpb_default_refused.json`) is refused as `unsupported_quantity_conversion` and names the missing mapping: growth score → relative fitness in the evolving environment; haploid *E. coli* vs the diploid claim; Ne; no-linkage/clonal-interference; and an uncertainty model for the conversion. Hypothetical trajectory mode runs only a declared scenario on route labels (route from `artifacts/integration/core_kappa2_route.input.json`); it reports `trpb_assay_scores_used: false`.

### Evidence reuse across recorded campaigns (`artifacts/claim_reuse/reuse_benchmark.json`)
Protocol pre-declared and committed before any count (`protocol.json`, commit c0a7c23): seeds 0–19, targets AIKG, CLKG, VLKG, ALKG then the family-A pair, 7 policies, 700 campaigns, 488,601 recorded paid requests from the original immutable core shards (tar sha256 `626a775a…`, from branch `work/replay-recovery`). Every query was re-verified against the Caltech CSVs (0 mismatches; 85 requests were for genotypes absent from the measured table and are typed as `absent_from_measured_table`).

| scope | requests | avoided by sequence cache | avoided by typed claim reuse |
|---|---|---|---|
| one pooled store | 488,601 | 465,564 (95.3%) | 465,564 |
| per-policy stores | 488,601 | 427,215 (87.4%) | 427,215 |

**Identical contexts: cache and claim reuse avoid exactly the same requests (asserted).** Plain caching gets the gain; the claim graph adds nothing there. These are recorded requests only: no adaptive-policy uplift (a policy handed free data would query differently), no wet-lab cost (the "assay" is a lookup of already-measured data), and the reuse value is identical to a fresh lookup by construction.

Fault injection (**SYNTHETIC software validation fixtures, not biological measurements**; 5% per attack chosen by a hash rule, four attacks: changed assay context, shifted coordinates, prediction formatted as observation, withdrawn). Pooled: the context-blind cache reuses 92,239 invalid facts (2,564 distinct) touching 681 campaigns, of which 289 had a recorded open/blocked certificate; typed reuse reuses 0, forced 2,564 re-assays and avoids 463,000. Disabling the matching guard makes each attack get through (negative controls 4/4); with guards on, 0.

### Falsifiable demo (`artifacts/claim_reuse/demo_receipt.json`, page `claim_runtime/demo/index.html`)
Covers: Kimura valid calculation; refused haploid transfer; refused TrpB score-as-s; Fisher valid partial change; Fisher refusals (every step improves, total change, clonal and landscape variance); real same-context reuse (genotype CFVS, first assayed by campaign `0/B:VFVS>AIKG/random` request 173, requested again by `…/greedy` request 2); changed-context, wrong-coordinate, prediction-masquerade, withdrawn and deleted evidence all return `assay_required`; a certificate over six observed same-context items is supported, becomes unsupported when one is a prediction, and an empty set supports nothing. Decision-change table: deleting, withdrawing, marking unavailable or editing the Kimura record flips `compute` → `refuse`; disabling the ploidy, assay-score or Fisher-inference guard flips a refusal to a (wrong) computation, which the negative controls detect. Unsigned TriG drafts in `artifacts/claim_reuse/nanopubs/` (rdflib-validated, no trusty URIs, nothing published) record the uses.

## Run it (no Delphi repo, no credentials)
```
python -m claim_runtime request claim_runtime/examples/kimura_valid.json          # exit 0 computed
python -m claim_runtime request claim_runtime/examples/kimura_trpb_default_refused.json   # exit 2 refused
python -m claim_runtime evidence claim_runtime/examples/evidence_lookup_prediction_refused.json
python -m claim_runtime verify        # tests + mutants, rewrites the verification receipt
python -m claim_runtime demo --shards <extracted original-shards dir>   # needs the Caltech CSVs and shards
```
Schemas: `claim_runtime/schemas.json`. `--records DIR` points at another set of Delphi MCP responses; requires numpy only for benchmarks; core request/evidence paths are standard library.
Bound every run: `systemd-run --user --scope -p TasksMax=128 -p MemoryMax=4G -p MemorySwapMax=0 -p RuntimeMaxSec=600 …`; `OMP_NUM_THREADS=2`.

## What the data cannot validate
No available data fixes a TrpB selection coefficient, an effective population size, or additive genetic variance for a real population; the intervals in the TrpB evidence are an assumed sensitivity model, not calibrated bounds; the Kimura formula's accuracy was checked only against idealised Wright–Fisher chains. Reuse "observed" here means reusing already-recorded source-table scores; no new assay was run. The review of the adapters was by the authoring model, not an independent scientist.
