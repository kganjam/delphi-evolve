

=================== 1. PROJECT SPEC (planning/PLAN.md excerpt, verbatim) ===================
## The bet

**Biology's next design tool should tell us which change to make, which claim that decision depends on, and which experiment could prove it wrong.**

Our first problem: can we improve an enzyme through a sequence of mutations without passing through a functionally broken intermediate? Build an interactive evolutionary route planner on a real, experimentally measured enzyme landscape. Give every route an evidence trail and a machine-checked conditional certificate. When the evidence cannot support a route, recommend the next measurement instead of inventing confidence.

The demo is a small, real step toward text-to-biological-function. It is not text-to-organism, a new organism, a wet-lab result, or a proof of Darwin. The initial system is **TrpB**, tryptophan synthase beta-subunit, using Johnston et al.'s published combinatorial measurements. Cellular growth in that assay is a proxy for function; it is not a purified-enzyme catalytic constant or a universal fitness measure.

## Why reset

MorphoSwarm's GOAL spans eleven biological scales, model extraction, CAD, inverse problems, formalization, distributed computation and a scientific publication platform. The specifications contain useful scientific discipline. They do not make those capabilities real. SPEC-079's historical demo record explicitly reported zero candidate solutions. The current repository has much more infrastructure than one person can communicate or independently validate in a three-minute pitch.

Keep the useful constraints: observation/simulation/assertion separation; content-addressed evidence; held-out tests; uncertainty; anti-vacuity; claim reuse. Replace the universal product with one experiment whose outputs fit on one screen. No general-purpose registry, task market, eleven-scale UI or new orchestration framework.

## What is new, and what is not

Directed evolution, epistasis, fitness landscapes, ESM, Bayesian optimization, graph reachability and nanopublications are established. Existing work already studies indirect adaptive paths and ML-guided enzyme optimization. We must cite Johnston 2024, Wu 2016, FLIP2 and relevant MLDE/active-learning work. Do not announce discovery of epistasis, a new fundamental law, or the first protein design agent.

The proposed contribution is **query-to-certify: assay selection aimed at settling a path/cut decision, with decision certificates linked to empirical scope and reusable claims**, evaluated on whether they prevent unsupported interventions and reduce the measurements needed for a justified decision. A route is accompanied by its weakest evidential step; uncertain steps become assay requests; an independent critic can supply a counterexample or a cut. All of that returns to Delphi as machine-readable evidence. This combination is a proposed systems contribution, not an established first-ever novelty claim.

An empirically useful negative result is possible: the collective may fail to beat a strong single policy; a foundation-model prior may degrade selection; no robust path may be supported at the chosen threshold. Report it. A measured answer to a narrow research question is stronger than a fabricated victory over a grand one.

## Scientific contract

1. Fetch the authors' original dataset. Record URL, retrieval date, SHA256, license, assay context, reference sequence and residue coordinates. Count observed, missing, censored and imputed rows separately. Never import a completed benchmark table and silently call its imputed rows measured.
2. Freeze a manifest before the main benchmark. Separate exploratory full-data route visualization from predictive/replay evaluation. The former is descriptive; it cannot demonstrate prediction.
3. Retrospective assay-budget replay: start each policy from the same admissible observations and seed; hold the same assay budget. An oracle alone exposes newly requested measured rows. Log every query. No hidden labels or global ranking in policy inputs, prompts, evidence caches or choice of favorable starting points.
4. Compare random search, greedy measured-neighbor walk, additive regression, an epistasis-aware baseline, and the proposed collective. Add foundation-model prior versus no prior. Aim for 20 fixed seeds; report paired outcomes, uncertainty and all seeds. Scale computation down before reducing scientific controls.
5. Primary outcome: assays needed to issue a correct open/blocked certificate for prespecified start/target pairs, with abstention and false-certification rates at a fixed budget. Use survival-style summaries or explicitly censored outcomes for unresolved cases, never exclude them. Secondary: best observed assay score, bottleneck score, route length, runtime and cost. Compare random, greedy and uncertainty acquisition as well as a strong non-agent query-to-certify policy. Fix targets using training information or published biology, never the held-out top percentile. The benchmark truth is finite measured-graph reachability under a declared assay/noise model, not biological truth.
6. Mathematical certificate: for genotype graph G and intervals [L(v), U(v)], accepting an edge only when L(v_next) >= U(v_current) implies nondecreasing fitness for every assignment inside all those intervals. Prove it for arbitrary routes, and connect a decidable checker to that property. Also prove that a separating cut with no admissible outgoing edge rules out a path in the declared graph.
7. Unknown nodes/edges stay possible in any negative certificate: absence of measurement is not evidence of no path. A certificate restricted to a measured subgraph says so prominently. Finite four-residue graph completeness never implies impossibility in the full protein sequence space. Two replicates alone do not justify simultaneous 95% bounds across 159,129 variants. This theorem assumes interval containment; it does not prove the empirical intervals contain reality. If assay replicates cannot support intervals, use point-value certificates labeled descriptive and a sensitivity parameter labeled assumed error bound. Do not manufacture confidence levels.
8. Formal status requires original compilation, no sorry/admit/unjustified axioms, a statement correspondence note, actual dataset-linked instance, and a mutation that changes the scientific condition and is rejected. Graph statements must not merely prove arithmetic constants.
9. Novel designs are proposals until measured. Retrospectively recovered variants were already assayed in the source study, not new discoveries. Sequence → assay growth spans a measured molecular/cellular bridge; organism and tissue predictions remain absent.
10. Unresolved historical claims stay unresolved. A Darwin statement about domestic breeds is motivation, not a theorem about four enzyme residues. Record the modern operationalization as a new claim linked by motivation/analogy, never equivalentTo without justification.




=================== 2. SCIENTIFIC/INTERFACE CONTRACT (specs/CONTRACT.md, verbatim) ===================
# Minimal scientific and interface contract

## Scope and stable artifacts

The only scientific system required is the four-site TrpB assay. Canonical source files currently exist at /data/artifacts/v2-scout/data/caltech/{simplified_AA,summary_AA,KNN_imputed_TrpB}.csv. They are primary CaltechDATA archive members. Copy them into ignored data/raw/ only as a cache; implement a reproducible source fetch and checksums. Never train/evaluate on the KNN labels as observations. Raw growth columns avoid max-normalization leakage.

Python package: evolve/. Core CLI: python -m evolve demo --output artifacts/demo.json, with documented additional commands. Demo JSON is the integration boundary. Site fetches ./data/demo.json and presents unavailable fields as unknown. Workers may implement richer APIs, but preserve this boundary.

Minimal demo JSON fields:

```
schema_version, generated_at, source {url, doi, sha256, license, assay, counts},
nodes [{id, genotype, observed_score, replicate_1, replicate_2, lower, upper, evidence_kind}],
edges [{source, target, status}],
routes [{id, nodes, status, assumptions, certificate_path}],
claims [{id, source_uri, statement, relation_to_test, status}],
benchmark {status, protocol, metrics, limitations},
proof {status, theorem, command, exit_code, mutation_exit_code, receipt},
compute {status, provider, model, job_id, artifacts},
limitations []
```

null is unknown, not zero. Empty results are not passes. Display source measurements as such; model outputs as predictions. Node layout is a projection, not physical geometry.

## Query-to-certify

Fix start/target pairs and graph scope before evaluation. Full finite graph consists of four-letter amino-acid genotypes, single-substitution adjacency. Missing labels leave edges possible. Restricting to measured or sampled nodes is permitted only with an explicit restricted-graph claim. A proof of no route in that graph is never a proof of no evolutionary route in biology.

An oracle exposes the same initial observations and bounded additional measurements to each policy. Record immutable query/reveal/proposal/challenge/decision events. Policy inputs contain no unseen labels. Use matched budgets/seeds and retain unresolved cases. Include a competent single-policy baseline, not only random. Centralized software orchestration and decentralized decision-making are different; explain actual boundaries.

Primary report: assays-to-correct-certificate, false certificates, abstentions, domain coverage. Best-score optimization is secondary. At least 20 fixed seeds if cheap enough, with paired uncertainty and an explicit reason if fewer. No significant-improvement claim without supporting analysis.

Two assay replicates do not supply rigorous simultaneous confidence bands. Use empirical sensitivity bounds explicitly assumed, or point-observation statements. Validate decisions against held-out replicate data; account for adaptive selection and multiple edges before claiming probability coverage. A GPU prior may guide measurement but never discharge a missing empirical premise.

## Lean

Generic interval path-soundness theorem and closed-set/cut no-path theorem; executable finite checker tied to theorem, not a parallel unproved Python checker. A certificate contains dataset hash, graph scope, exact rational or outward-rounded integer intervals, route/cut, assumptions and software versions. Kernel compile original, inspect axiom dependencies, reject meaningful mutant, and record correspondence. No sorry, admit, trusted native_decide shortcut, or proof by an unrelated constant identity. Invalidating the dominance inequality or opening a cut edge must change acceptance. No false certificates through rounding, missing vertices or NaN.

## Claims and nanopubs

Preserve Delphi IDs and source local/network. An operational enzyme hypothesis is not synonymous with a broad Darwin claim. Link as motivation unless justified. Distinguish observed finding, simulated selection replay, mathematical theorem, interpretation and proposal. Emit valid RDF nanopub named graphs with source/author provenance, mark unsigned drafts. Never invent a public trusty URI, verified network publication or an identified scientist's endorsement.

## Acceptance

Fresh checkout can acquire/cache exact data, produce demo JSON, reproduce its summary, run targeted tests, compile proofs and reject mutants. Site works from static files and reports absent integrations honestly. All advertised scientific numbers are derived from saved artifacts. Each integration reports real run identifier/exit or an explicit blocker. Every worker owns its tests and run receipts. Coordinator reviews all receipts before pitch claims.



=================== 3. PRIOR ART as summarised by the project's own novelty note (the authors' reading; verify against sources) ===================
## What is already established (we claim none of it)

| Topic | Established work | Notes |
|---|---|---|
| The TrpB four-site landscape itself, epistasis, local optima, path accessibility, simulated directed-evolution strategies | Johnston et al., *PNAS* 121(32):e2400439121 (doi 10.1073/pnas.2400439121; data CC0 at doi 10.22002/h5rah-5z170) | The paper reports 520 local optima among active variants (5.3%), analyses how much fitness loss routes to the top variant must tolerate, and compares simulated directed-evolution approaches. **Route accessibility analysis on this exact table exists.** |
| Active-learning-assisted directed evolution | ALDE, *Nature Communications* 2025 (PMC11739421) | Wet-lab campaign on a protoglobin (five residues). Computational simulations on **both GB1 and TrpB** four-residue combinatorial datasets: 96 random starting variants, four rounds of 96, averaged over 70 random initialisations; compares encodings (one-hot, ESM2) and model classes with calibration analysis. It reports no path/reachability decision and no formal certificate. |
| Sequence-to-fitness benchmarks | FLIP and FLIP2 (flip.protein.properties) | FLIP2 adds TrpB sub-landscapes (about 228k variants over 10 sub-landscapes; a different table from the four-site set) and 16 splits. Evaluates predictors (Spearman, NDCG), not assay decisions. |
| Indirect adaptive paths and sign epistasis | Wu et al., eLife 2016 (e16965, GB1); Ribeca et al., arXiv:2604.22611 (April 2026): proof that simple sign epistasis is associated with evolutionary detours, plus analysis of experimental landscapes | Our 5/6/7-step detours are instances of this phenomenon, not a finding about it. Only the abstract-level statement of Ribeca et al. was read. |
| Embedding-space Bayesian optimisation for proteins | PELLM (github.com/soldatmat/PELLM) | Listed in planning/PLAN.md as adjacent; **not inspected by the experience worker**, so no comparison is made. |
| Nanopublications, PROV, interval arithmetic, graph reachability | standard | Used, not contributed. |




=================== 4. FROZEN REPLAY PROTOCOL (core artifacts/core/protocol.json; panel truncated) ===================
{
 "frozen_before_main_run": true,
 "graph_scope": "measured subgraph G_meas of 20^4 amino-acid library, single-substitution adjacency; 871 unmeasured genotypes are outside scope; stop-containing genotypes excluded",
 "edge_rule": "u->v admissible iff Lo[v] >= Hi[u]; Lo/Hi = round(mean of 2 replicates, micro-units) -/+ ceil(kappa*sd_bin/2*1e6)",
 "kappa_main": 2.0,
 "kappa_meaning": "assumed sensitivity multiplier, not a confidence level",
 "noise_bins_min_input_count_edges": [
  20,
  50,
  200
 ],
 "replicate_diff_sd": [
  0.014953,
  0.009995,
  0.005851,
  0.002992
 ],
 "truth": "forward admissible closure of start under full measured labels (benchmark truth under declared model, not biological truth)",
 "budget_assays_beyond_initial": 1000,
 "n_initial_random_observations": 96,
 "policies": [
  "random",
  "greedy",
  "uncertainty",
  "directed",
  "q2c",
  "collective_shared",
  "collective_isolated"
 ],
 "seeds": 20,
 "pair_rules": {
  "A": "target = best-scoring of the seed's 96 initial observations; start = random other initial observation with lower score, Hamming>=2",
  "B": "start VFVS; targets ['AIKG', 'CLKG', 'VLKG', 'ALKG'] (published top variants); initial set seeded by seed"
 },
 "censoring": "unresolved or stuck at budget is right-censored and retained",
 "dataset_sha256": {
  "simplified_AA.csv": "d7e3ab4bcb721819ddf79ac0c9d322046dcdc4ce7d0df7d5ccd423fee771cb76",
  "summary_AA.csv": "a631d8cf6c5b188a801555cc4117547a1bf8e294240e1757c2d2d78dcb25ee82",
  "KNN_imputed_TrpB.csv": "83b4db9f82fe8d09c4bf7006f3cc730d511eee12147e8fe2e9198281960f34c4"
 },
 "panel": [
  {
   "family": "A",
   "seed": 0,
   "start": "PAIL",
   "target": "ATSG",
   "initial_observations_sha256": "81ccea182cf5dd762a1654bde2be21fdb2befd4390491e7d747443abdda9e342"
  },
  {
   "family": "B",
   "seed": 0,
   "start": "VFVS",
   "target": "AIKG",
   "initial_observations_sha256": "32592d5ffd18a6ff1f7b16ea303dc6a89ec8297c421a6a3c0cf647c7f3e6e862"
  },
  {
   "family": "B",
   "seed": 0,
   "start": "VFVS",
   "target": "CLKG",
   "initial_observations_sha256": "32592d5ffd18a6ff1f7b16ea303dc6a89ec8297c421a6a3c0cf647c7f3e6e862"
  },
  {
   "family": "B",
   "seed": 0,
   "start": "VFVS",
   "target": "VLKG",
   "initial_observations_sha256": "32592d5ffd18a6ff1f7b16ea303dc6a89ec8297c421a6a3c0cf647c7f3e6e862"
  },
  {
   "family": "B",
   "seed": 0,
   "start": "VFVS",
   "target": "ALKG",
   "initial_observations_sha256": "32592d5ffd18a6ff1f7b16ea303dc6a89ec8297c421a6a3c0cf647c7f3e6e862"
  },
  "... 95 more panel rows omitted ..."
 ],
 "panel_sha256": "bb6c144e8f0eba1079d6353d9c7f612a02df30afa7770ce94a064a47ad9b9bcf"
}


=================== 5. REPLAY RECEIPT SO FAR (aggregated by an independent script from core's shard files) ===================
Only replay shards whose per-episode `rows` were populated could be aggregated: these are seeds 0-4 for every policy (shards for seeds 5-19 exist but carry no per-episode rows). 'truth_open' = benchmark truth under the declared edge rule. Family A has 1 episode/seed, family B has 4 episodes/seed (VFVS -> 4 published targets).
[
{
"policy": "collective_isolated",
"family": "A",
"episodes": 5,
"truth_open": 3,
"cert_open": 3,
"cert_blocked": 1,
"censored_at_budget": 1,
"stuck": 0,
"false_certificates": 0,
"median_assays_among_certified": 140.0,
"max_assays": 1000,
"truth_open_and_censored": 0
},
{
"policy": "collective_isolated",
"family": "B",
"episodes": 20,
"truth_open": 20,
"cert_open": 19,
"cert_blocked": 0,
"censored_at_budget": 1,
"stuck": 0,
"false_certificates": 0,
"median_assays_among_certified": 428,
"max_assays": 1000,
"truth_open_and_censored": 1
},
{
"policy": "collective_shared",
"family": "A",
"episodes": 5,
"truth_open": 3,
"cert_open": 3,
"cert_blocked": 1,
"censored_at_budget": 1,
"stuck": 0,
"false_certificates": 0,
"median_assays_among_certified": 94.0,
"max_assays": 1000,
"truth_open_and_censored": 0
},
{
"policy": "collective_shared",
"family": "B",
"episodes": 20,
"truth_open": 20,
"cert_open": 15,
"cert_blocked": 0,
"censored_at_budget": 5,
"stuck": 0,
"false_certificates": 0,
"median_assays_among_certified": 569,
"max_assays": 1000,
"truth_open_and_censored": 5
},
{
"policy": "directed",
"family": "A",
"episodes": 5,
"truth_open": 3,
"cert_open": 2,
"cert_blocked": 1,
"censored_at_budget": 2,
"stuck": 0,
"false_certificates": 0,
"median_assays_among_certified": 599,
"max_assays": 1000,
"truth_open_and_censored": 1
},
{
"policy": "directed",
"family": "B",
"episodes": 20,
"truth_open": 20,
"cert_open": 5,
"cert_blocked": 0,
"censored_at_budget": 15,
"stuck": 0,
"false_certificates": 0,
"median_assays_among_certified": 34,
"max_assays": 1000,
"truth_open_and_censored": 15
},
{
"policy": "greedy",
"family": "A",
"episodes": 5,
"truth_open": 3,
"cert_open": 1,
"cert_blocked": 1,
"censored_at_budget": 3,
"stuck": 0,
"false_certificates": 0,
"median_assays_among_certified": 345.5,
"max_assays": 1000,
"truth_open_and_censored": 2
},
{
"policy": "greedy",
"family": "B",
"episodes": 20,
"truth_open": 20,
"cert_open": 0,
"cert_blocked": 0,
"censored_at_budget": 20,
"stuck": 0,
"false_certificates": 0,
"median_assays_among_certified": null,
"max_assays": 1000,
"truth_open_and_censored": 20
},
{
"policy": "q2c",
"family": "A",
"episodes": 5,
"truth_open": 3,
"cert_open": 3,
"cert_blocked": 1,
"censored_at_budget": 1,
"stuck": 0,
"false_certificates": 0,
"median_assays_among_certified": 127.5,
"max_assays": 1000,
"truth_open_and_censored": 0
},
{
"policy": "q2c",
"family": "B",
"episodes": 20,
"truth_open": 20,
"cert_open": 15,
"cert_blocked": 0,
"censored_at_budget": 5,
"stuck": 0,
"false_certificates": 0,
"median_assays_among_certified": 249,
"max_assays": 1000,
"truth_open_and_censored": 5
},
{
"policy": "random",
"family": "A",
"episodes": 5,
"truth_open": 3,
"cert_open": 0,
"cert_blocked": 1,
"censored_at_budget": 4,
"stuck": 0,
"false_certificates": 0,
"median_assays_among_certified": 189,
"max_assays": 1000,
"truth_open_and_censored": 3
},
{
"policy": "random",
"family": "B",
"episodes": 20,
"truth_open": 20,
"cert_open": 1,
"cert_blocked": 0,
"censored_at_budget": 19,
"stuck": 0,
"false_certificates": 0,
"median_assays_among_certified": 464,
"max_assays": 1000,
"truth_open_and_censored": 19
},
{
"policy": "uncertainty",
"family": "A",
"episodes": 5,
"truth_open": 3,
"cert_open": 0,
"cert_blocked": 1,
"censored_at_budget": 4,
"stuck": 0,
"false_certificates": 0,
"median_assays_among_certified": 189,
"max_assays": 1000,
"truth_open_and_censored": 3
},
{
"policy": "uncertainty",
"family": "B",
"episodes": 20,
"truth_open": 20,
"cert_open": 2,
"cert_blocked": 0,
"censored_at_budget": 18,
"stuck": 0,
"false_certificates": 0,
"median_assays_among_certified": 697.0,
"max_assays": 1000,
"truth_open_and_censored": 18
}
]


=================== 6. CORE IMPLEMENTATION (repo commit 8883518; line numbers added) ===================
----- core/evolve/data.py -----
   1| """Audited loader for the Johnston et al. TrpB four-site table (raw growth rates).
   2| 
   3| Design rules (see specs/CONTRACT.md):
   4| * labels are RAW growth rates mu_1, mu_2 minus the per-replicate mean over
   5|   stop-codon rows (a negative-control offset, constant per replicate).  The
   6|   source's `/max` columns are never used (they embed the global library maximum),
   7|   nor are the authors' row-specific `mu-bg` columns;
   8| * the KNN-imputed rows are never observations;
   9| * memory is compact: flat arrays indexed by base-20 genotype code (160,000
  10|   entries), never a pairwise matrix.
  11| All decision arithmetic uses int64 micro-units so a Lean checker can be exact.
  12| """
  13| from __future__ import annotations
  14| 
  15| import hashlib
  16| import json
  17| from dataclasses import dataclass
  18| from pathlib import Path
  19| 
  20| import numpy as np
  21| import pandas as pd
  22| 
  23| ROOT = Path(__file__).resolve().parents[1]
  24| RAW = ROOT / "data" / "raw"
  25| MANIFEST = ROOT / "data" / "manifest.json"
  26| 
  27| AA = "ACDEFGHIKLMNPQRSTVWY"
  28| POSITIONS = (183, 184, 227, 228)  # residue numbers in Tm9D8s* TrpB (source paper)
  29| N_GENO = 20 ** 4
  30| UNITS = 1_000_000  # integer micro-units of growth-rate score
  31| PARENT = "VFVS"
  32| 
  33| # --- Declared (assumed) noise model, frozen before any benchmark run ---------
  34| # Replicate-difference SD of (s1 - s2) by min(InputCount_1, InputCount_2) bin,
  35| # computed over the 159,129 measured genotypes (`python -m evolve audit` recomputes
  36| # and checks these).  Half-width of the interval on the 2-replicate mean is
  37| #   eps = KAPPA * sd_bin / 2 ,
  38| # KAPPA is an ASSUMED sensitivity multiplier, NOT a confidence level.
  39| COUNT_BIN_EDGES = (20, 50, 200)
  40| REPLICATE_DIFF_SD = (0.014953, 0.009995, 0.005851, 0.002992)
  41| DEFAULT_KAPPA = 2.0
  42| 
  43| 
  44| def encode(g: str) -> int:
  45|     a = AA.index
  46|     return ((a(g[0]) * 20 + a(g[1])) * 20 + a(g[2])) * 20 + a(g[3])
  47| 
  48| 
  49| def decode(i: int) -> str:
  50|     return AA[i // 8000] + AA[(i // 400) % 20] + AA[(i // 20) % 20] + AA[i % 20]
  51| 
  52| 
  53| def digits(idx):
  54|     idx = np.asarray(idx)
  55|     return np.stack([idx // 8000, (idx // 400) % 20, (idx // 20) % 20, idx % 20], axis=-1)
  56| 
  57| 
  58| # neighbor table pieces: 76 single substitutions = 4 positions x 19 other residues
  59| _POW = np.array([8000, 400, 20, 1])
  60| 
  61| 
  62| def neighbors(idx):
  63|     """Single-substitution neighbours; shape (..., 76)."""
  64|     idx = np.asarray(idx)
  65|     d = digits(idx)  # (...,4)
  66|     out = []
  67|     for p in range(4):
  68|         for k in range(1, 20):
  69|             nd = (d[..., p] + k) % 20
  70|             out.append(idx + (nd - d[..., p]) * _POW[p])
  71|     return np.stack(out, axis=-1)
  72| 
  73| 
  74| def hamming(a, b):
  75|     return (digits(a) != digits(b)).sum(-1)
  76| 
  77| 
  78| def sha256_file(p: Path) -> str:
  79|     h = hashlib.sha256()
  80|     with open(p, "rb") as f:
  81|         for c in iter(lambda: f.read(1 << 20), b""):
  82|             h.update(c)
  83|     return h.hexdigest()
  84| 
  85| 
  86| @dataclass
  87| class Landscape:
  88|     measured: np.ndarray   # bool (160000,)
  89|     s1: np.ndarray         # int64 micro-units, replicate 1 (0 where unmeasured)
  90|     s2: np.ndarray
  91|     s: np.ndarray          # int64, round(mean of replicates)
  92|     count_min: np.ndarray  # int32, min input count (0 where unmeasured)
  93|     raw_mu1: np.ndarray    # float64 raw growth rates (nan where unmeasured)
  94|     raw_mu2: np.ndarray
  95|     bg: tuple              # per-replicate stop-codon mean mu
  96|     counts: dict
  97|     sha: dict
  98|     kappa: float
  99| 
 100|     def eps(self, kappa=None) -> np.ndarray:
 101|         k = self.kappa if kappa is None else kappa
 102|         sd = np.array(REPLICATE_DIFF_SD)[np.searchsorted(COUNT_BIN_EDGES, self.count_min, side="right")]
 103|         return np.ceil(k * sd / 2 * UNITS).astype(np.int64)
 104| 
 105|     def intervals(self, kappa=None):
 106|         e = self.eps(kappa)
 107|         return self.s - e, self.s + e  # Lo, Hi (int64); meaningful only where measured
 108| 
 109|     def with_kappa(self, kappa):
 110|         import copy
 111|         c = copy.copy(self)
 112|         c.kappa = kappa
 113|         return c
 114| 
 115| 
 116| def load(raw_dir: Path = RAW, kappa: float = DEFAULT_KAPPA, verify: bool = True) -> Landscape:
 117|     man = json.loads(MANIFEST.read_text())
 118|     sha = {n: sha256_file(raw_dir / n) for n in man["files"]}
 119|     if verify:
 120|         bad = [n for n, m in man["files"].items() if sha[n] != m["sha256"]]
 121|         if bad:
 122|             raise RuntimeError(f"data hash mismatch vs data/manifest.json: {bad}; run scripts/fetch_data.py")
 123|     d = pd.read_csv(raw_dir / "summary_AA.csv")
 124|     stop = d["# Stop"] > 0
 125|     bg = (float(d.loc[stop, "mu_1"].mean()), float(d.loc[stop, "mu_2"].mean()))
 126|     ok = d[~stop]
 127|     idx = np.array([encode(g) for g in ok["AAs"]])
 128|     assert len(set(idx.tolist())) == len(idx)
 129|     meas = np.zeros(N_GENO, bool); meas[idx] = True
 130|     s1 = np.zeros(N_GENO, np.int64); s2 = np.zeros(N_GENO, np.int64)
 131|     s1[idx] = np.round((ok["mu_1"].to_numpy() - bg[0]) * UNITS)
 132|     s2[idx] = np.round((ok["mu_2"].to_numpy() - bg[1]) * UNITS)
 133|     s = np.zeros(N_GENO, np.int64); s[idx] = np.round((s1[idx] + s2[idx]) / 2).astype(np.int64)
 134|     cm = np.zeros(N_GENO, np.int32)
 135|     cm[idx] = np.minimum(ok["InputCount_1"], ok["InputCount_2"]).astype(np.int32)
 136|     m1 = np.full(N_GENO, np.nan); m2 = np.full(N_GENO, np.nan)
 137|     m1[idx] = ok["mu_1"].to_numpy(); m2[idx] = ok["mu_2"].to_numpy()
 138|     knn = pd.read_csv(raw_dir / "KNN_imputed_TrpB.csv")
 139|     kidx = np.array([encode(g) for g in knn["AAs"]])
 140|     counts = {
 141|         "source_rows_summary_AA": int(len(d)),
 142|         "stop_containing_rows": int(stop.sum()),
 143|         "measured_nonstop_genotypes": int(meas.sum()),
 144|         "library_nonstop_genotypes": N_GENO,
 145|         "unmeasured_nonstop_genotypes": int(N_GENO - meas.sum()),
 146|         "knn_imputed_rows_separate_file": int(len(knn)),
 147|         "knn_imputed_overlap_with_measured": int(meas[kidx].sum()),
 148|         "knn_imputed_equals_unmeasured_set": bool((~meas[kidx]).all() and len(kidx) == N_GENO - meas.sum()),
 149|         "source_declared_active_rows": int(ok["active"].sum()),
 150|         "source_declared_censored_rows": 0,
 151|         "low_count_rows_min_input_lt_10_flagged_not_dropped": int((cm[idx] < 10).sum()),
 152|         "imputed_rows_used_as_observations": 0,
 153|     }
 154|     return Landscape(meas, s1, s2, s, cm, m1, m2, bg, counts, sha, kappa)

----- core/evolve/graph.py -----
   1| """Admissible-edge reachability over the declared measured graph.
   2| 
   3| Edge rule (CONTRACT / PLAN 6): u -> v (single substitution) is ADMISSIBLE iff
   4| Lo[v] >= Hi[u], all integer micro-units.  Under interval containment this implies
   5| score(v) >= score(u).  Graph scope: the measured subgraph G_meas of the 20^4
   6| library (159,129 of 160,000 genotypes).  Unmeasured genotypes are outside the
   7| declared scope; certificates say nothing about paths through them.
   8| """
   9| from __future__ import annotations
  10| 
  11| import numpy as np
  12| 
  13| from .data import N_GENO, neighbors
  14| 
  15| 
  16| def truth_bfs(meas, Lo, Hi, start: int):
  17|     """Full-information forward admissible closure of `start`. Returns (reached bool,
  18|     parent int32, depth int16)."""
  19|     reached = np.zeros(N_GENO, bool); parent = np.full(N_GENO, -1, np.int32); depth = np.full(N_GENO, -1, np.int16)
  20|     reached[start] = True; depth[start] = 0
  21|     frontier = np.array([start]); d = 0
  22|     while frontier.size:
  23|         d += 1
  24|         nb = neighbors(frontier)                       # (F,76)
  25|         src = np.repeat(frontier, 76); dst = nb.ravel()
  26|         ok = meas[dst] & ~reached[dst] & (Lo[dst] >= Hi[src])
  27|         src, dst = src[ok], dst[ok]
  28|         if not dst.size:
  29|             break
  30|         uniq, first = np.unique(dst, return_index=True)
  31|         reached[uniq] = True; parent[uniq] = src[first]; depth[uniq] = d
  32|         frontier = uniq
  33|     return reached, parent, depth
  34| 
  35| 
  36| def path_to(parent, start, target):
  37|     p = [int(target)]
  38|     while p[-1] != start:
  39|         p.append(int(parent[p[-1]]))
  40|         if p[-1] < 0:
  41|             return None
  42|     return p[::-1]
  43| 
  44| 
  45| def edge_status(meas, Lo, Hi, u, v):
  46|     if not meas[u] or not meas[v]:
  47|         return "unknown"
  48|     return "admissible" if Lo[v] >= Hi[u] else "inadmissible"
  49| 
  50| 
  51| class Ledger:
  52|     """Policy-visible state: revealed observations only, plus an incrementally
  53|     maintained forward closure and its unknown frontier.
  54| 
  55|     obs: idx -> (lo, hi, s)  for measured nodes;  absent: idx set revealed as outside scope.
  56|     closure: nodes reachable from `start` via admissible edges between revealed nodes.
  57|     frontier: UNREVEALED neighbours of closure members (their status is unknown);
  58|         frontier_parents[w] = closure members adjacent to w.
  59|     status(): 'open' if target in closure; 'blocked' if frontier empty (closed set,
  60|     target outside); else 'unresolved'.
  61|     """
  62| 
  63|     def __init__(self, start: int, target: int):
  64|         self.start, self.target = start, target
  65|         self.obs: dict[int, tuple[int, int, int]] = {}
  66|         self.absent: set[int] = set()
  67|         self.closure: dict[int, int] = {}   # node -> parent (for route reconstruction)
  68|         self.frontier: dict[int, set[int]] = {}
  69|         self._nb: dict[int, list[int]] = {}
  70| 
  71|     def nbrs(self, u):
  72|         r = self._nb.get(u)
  73|         if r is None:
  74|             r = self._nb[u] = neighbors(np.int64(u)).tolist()
  75|         return r
  76| 
  77|     def known(self, v):
  78|         return v in self.obs or v in self.absent
  79| 
  80|     def reveal(self, v, rec):
  81|         """rec = (lo, hi, s) or None (absent from scope)."""
  82|         if rec is None:
  83|             self.absent.add(v)
  84|             self.frontier.pop(v, None)
  85|             return
  86|         self.obs[v] = rec
  87|         parents = self.frontier.pop(v, None)
  88|         if v == self.start and not self.closure:
  89|             self._join(v, -1)
  90|             return
  91|         if self.closure and parents:
  92|             for u in parents:
  93|                 if rec[0] >= self.obs[u][1]:
  94|                     self._join(v, u)
  95|                     break
  96|         elif self.closure:
  97|             # v may be adjacent to closure members only via frontier, which we popped; nothing
  98|             pass
  99| 
 100|     def _join(self, v, parent):
 101|         stack = [(v, parent)]
 102|         while stack:
 103|             x, p = stack.pop()
 104|             if x in self.closure:
 105|                 continue
 106|             self.closure[x] = p
 107|             hi = self.obs[x][1]
 108|             for w in self.nbrs(x):
 109|                 if w in self.closure or w in self.absent:
 110|                     continue
 111|                 if w in self.obs:
 112|                     if self.obs[w][0] >= hi:
 113|                         stack.append((w, x))
 114|                 else:
 115|                     self.frontier.setdefault(w, set()).add(x)
 116| 
 117|     def status(self):
 118|         if self.target in self.closure:
 119|             return "open"
 120|         if self.closure and not self.frontier:
 121|             return "blocked"
 122|         return "unresolved"
 123| 
 124|     def route(self):
 125|         if self.target not in self.closure:
 126|             return None
 127|         p = [self.target]
 128|         while self.closure[p[-1]] != -1:
 129|             p.append(self.closure[p[-1]])
 130|         return p[::-1]
 131| 
 132|     def cut(self):
 133|         """Closed set (closure) and boundary edges justifying a blocked status."""
 134|         assert self.status() == "blocked"
 135|         S = set(self.closure)
 136|         out = []
 137|         for u in S:
 138|             for w in self.nbrs(u):
 139|                 if w in S:
 140|                     continue
 141|                 out.append((u, w, "absent" if w in self.absent else "inadmissible"))
 142|         return S, out
 143| 
 144| 
 145| def verify_route(meas, Lo, Hi, route) -> bool:
 146|     from .data import hamming
 147|     if len(route) < 1 or any(not meas[v] for v in route):
 148|         return False
 149|     return all(int(hamming(route[i], route[i + 1])) == 1 and Lo[route[i + 1]] >= Hi[route[i]] for i in range(len(route) - 1))
 150| 
 151| 
 152| def verify_cut(meas, Lo, Hi, S, start, target) -> bool:
 153|     """Independent re-check of a closed set against FULL data (used by tests/audits only)."""
 154|     if start not in S or target in S:
 155|         return False
 156|     for u in S:
 157|         if not meas[u]:
 158|             return False
 159|         for w in neighbors(np.int64(u)).tolist():
 160|             if w in S or not meas[w]:
 161|                 continue
 162|             if Lo[w] >= Hi[u]:
 163|                 return False
 164|     return True

----- core/evolve/oracle.py -----
   1| """Assay oracle and immutable event log for the retrospective replay.
   2| 
   3| The oracle exposes ONLY observed labels (interval + score) for genotypes a policy
   4| explicitly queries; it never returns rankings, maxima, neighbours' labels or
   5| anything unqueried.  Each query costs one assay, including queries that reveal a
   6| genotype is outside the measured scope.
   7| """
   8| from __future__ import annotations
   9| 
  10| import hashlib
  11| import json
  12| 
  13| import numpy as np
  14| 
  15| 
  16| class EventLog:
  17|     """Append-only, hash-chained event list (tamper-evident, not signed)."""
  18| 
  19|     def __init__(self):
  20|         self.events: list[dict] = []
  21|         self._h = "0" * 64
  22| 
  23|     def emit(self, type_: str, actor: str, **payload):
  24|         ev = {"seq": len(self.events), "type": type_, "actor": actor, **payload}
  25|         ev["prev"] = self._h
  26|         self._h = hashlib.sha256(json.dumps(ev, sort_keys=True, default=int).encode()).hexdigest()
  27|         ev["hash"] = self._h
  28|         self.events.append(ev)
  29|         return ev
  30| 
  31|     def verify(self) -> bool:
  32|         h = "0" * 64
  33|         for ev in self.events:
  34|             body = {k: v for k, v in ev.items() if k != "hash"}
  35|             if body["prev"] != h:
  36|                 return False
  37|             h = hashlib.sha256(json.dumps(body, sort_keys=True, default=int).encode()).hexdigest()
  38|             if h != ev["hash"]:
  39|                 return False
  40|         return True
  41| 
  42| 
  43| class Oracle:
  44|     def __init__(self, land, kappa, log: EventLog | None = None):
  45|         self._meas = land.measured
  46|         self._Lo, self._Hi = land.intervals(kappa)
  47|         self._s = land.s
  48|         self.queried: set[int] = set()
  49|         self.log = log or EventLog()
  50|         self.n_queries = 0
  51| 
  52|     def reveal_free(self, idx, actor="data", why="initial"):
  53|         """Initial admissible observations (shared identically across policies)."""
  54|         rec = self._rec(int(idx))
  55|         self.log.emit("reveal", actor, node=int(idx), rec=rec, cost=0, why=why)
  56|         self.queried.add(int(idx))
  57|         return rec
  58| 
  59|     def query(self, idx, actor, why=""):
  60|         idx = int(idx)
  61|         if idx in self.queried:
  62|             raise ValueError("duplicate query " + str(idx))
  63|         self.queried.add(idx)
  64|         self.n_queries += 1
  65|         rec = self._rec(idx)
  66|         self.log.emit("reveal", actor, node=idx, rec=rec, cost=1, why=why, n_queries=self.n_queries)
  67|         return rec
  68| 
  69|     def _rec(self, idx):
  70|         if not self._meas[idx]:
  71|             return None
  72|         return (int(self._Lo[idx]), int(self._Hi[idx]), int(self._s[idx]))

----- core/evolve/policies.py -----
   1| """Query policies for matched-budget retrospective replay.
   2| 
   3| All policies share ONE soundness path: certificates are computed from revealed
   4| labels only (graph.Ledger).  Policies differ only in WHICH unrevealed genotype
   5| they spend the next assay on.  None sees unqueried labels.
   6| 
   7| random      uniform over the unknown frontier (competent random: global random
   8|             would almost never touch the closure)
   9| greedy      measured-neighbour walk: assay unknown neighbours of the highest-scoring
  10|             reachable genotype (target-agnostic hill climbing)
  11| uncertainty GP predictive-sd acquisition over the frontier
  12| directed    deterministic single policy, no learned model: best-first toward the
  13|             target by Hamming distance (ties: parent score, then index)
  14| q2c         single-brain query-to-certify: GP-predicted open-route vs cut cost
  15| collective_shared / collective_isolated   see collective.py
  16| """
  17| from __future__ import annotations
  18| 
  19| import itertools
  20| import math
  21| 
  22| import numpy as np
  23| from scipy.special import ndtr
  24| 
  25| from .data import UNITS, digits, hamming
  26| from .model import GPModel, LocalModel
  27| 
  28| REFIT = 16
  29| POOL = 400
  30| 
  31| 
  32| def phi(z):
  33|     return ndtr(z)
  34| 
  35| 
  36| class Base:
  37|     name = "base"
  38| 
  39|     def __init__(self, ctx, rng):
  40|         self.ctx, self.rng = ctx, rng
  41| 
  42|     def step(self, oracle, ledger) -> bool:  # perform one query; False => no admissible query
  43|         raise NotImplementedError
  44| 
  45|     def ask(self, oracle, ledger, v, why):
  46|         rec = oracle.query(v, self.name, why)
  47|         ledger.reveal(int(v), rec)
  48|         return rec
  49| 
  50| 
  51| def frontier_array(ledger):
  52|     return np.fromiter(ledger.frontier.keys(), np.int64, len(ledger.frontier))
  53| 
  54| 
  55| class RandomFrontier(Base):
  56|     name = "random"
  57| 
  58|     def step(self, oracle, ledger):
  59|         keys = list(ledger.frontier.keys())
  60|         if not keys:
  61|             return False
  62|         self.ask(oracle, ledger, keys[int(self.rng.integers(len(keys)))], "uniform frontier")
  63|         return True
  64| 
  65| 
  66| class _Pooled(Base):
  67|     """Pool of preferred frontier nodes refreshed every REFIT queries."""
  68| 
  69|     def __init__(self, ctx, rng):
  70|         super().__init__(ctx, rng)
  71|         self.pool, self.age = [], REFIT
  72| 
  73|     def rank(self, ledger, F):  # return ordered list of candidate nodes (best first)
  74|         raise NotImplementedError
  75| 
  76|     def step(self, oracle, ledger):
  77|         self.pool = [v for v in self.pool if v in ledger.frontier]
  78|         if not self.pool or self.age >= REFIT:
  79|             F = frontier_array(ledger)
  80|             if F.size == 0:
  81|                 return False
  82|             self.pool = list(self.rank(ledger, F))[:POOL]; self.age = 0
  83|         if not self.pool:
  84|             return False
  85|         v = self.pool.pop(0); self.age += 1
  86|         self.ask(oracle, ledger, v, self.why)
  87|         return True
  88| 
  89|     why = ""
  90| 
  91| 
  92| def _best_parent_hi(ledger, v):
  93|     return max(ledger.obs[u][2] for u in ledger.frontier[v])
  94| 
  95| 
  96| class Greedy(_Pooled):
  97|     name = "greedy"; why = "neighbour of highest-scoring reachable genotype"
  98| 
  99|     def rank(self, ledger, F):
 100|         sc = np.array([_best_parent_hi(ledger, int(v)) for v in F])
 101|         order = np.lexsort((F, -sc))
 102|         return F[order[:POOL]].tolist()
 103| 
 104| 
 105| class Directed(_Pooled):
 106|     name = "directed"; why = "Hamming-closest unknown neighbour to target"
 107| 
 108|     def rank(self, ledger, F):
 109|         h = hamming(F, self.ctx.target)
 110|         cut = np.argsort(h, kind="stable")[: 8 * POOL]
 111|         Fc, hc = F[cut], h[cut]
 112|         sc = np.array([_best_parent_hi(ledger, int(v)) for v in Fc])
 113|         order = np.lexsort((Fc, -sc, hc))
 114|         return Fc[order].tolist()
 115| 
 116| 
 117| class Uncertainty(_Pooled):
 118|     name = "uncertainty"; why = "max GP predictive sd on frontier"
 119| 
 120|     def __init__(self, ctx, rng):
 121|         super().__init__(ctx, rng)
 122|         self.gp = GPModel(prior=ctx.prior)
 123| 
 124|     def rank(self, ledger, F):
 125|         if len(F) > 3 * POOL:
 126|             F = self.rng.choice(F, 3 * POOL, replace=False)
 127|         nodes = list(ledger.obs)
 128|         self.gp.fit(nodes, [ledger.obs[v][2] for v in nodes])
 129|         _, sd = self.gp.predict(F)
 130|         order = np.lexsort((F, -sd))
 131|         return F[order].tolist()
 132| 
 133| 
 134| # ---------------------------------------------------------------- planners
 135| class Planner:
 136|     """Open-route and cut cost planning from a ledger and a surrogate model."""
 137| 
 138|     def __init__(self, ctx, ledger, model):
 139|         self.ctx, self.ledger, self.model = ctx, ledger, model
 140|         self.n_fit = -1
 141| 
 142|     def sync(self):
 143|         n = len(self.ledger.obs)
 144|         if self.n_fit < 0 or n - self.n_fit >= REFIT:
 145|             nodes = list(self.ledger.obs)
 146|             self.model.fit(nodes, [self.ledger.obs[v][2] for v in nodes])
 147|             self.n_fit = n
 148| 
 149|     # --- edge probability under model
 150|     def _stats(self, nodes, cache):
 151|         need = [v for v in nodes if v not in self.ledger.obs and v not in cache and v not in self.ledger.absent]
 152|         if need:
 153|             mu, sd = self.model.predict(np.array(need))
 154|             for v, a, b in zip(need, mu, sd):
 155|                 cache[v] = (a * UNITS, b * UNITS)
 156| 
 157|     def edge_p(self, u, w, cache):
 158|         L = self.ledger
 159|         if w in L.absent or u in L.absent:
 160|             return 0.0
 161|         eps = self.ctx.eps_typ
 162|         ku, kw = u in L.obs, w in L.obs
 163|         if ku and kw:
 164|             return 1.0 if L.obs[w][0] >= L.obs[u][1] else 0.0
 165|         if ku:
 166|             mu, sd = cache[w]; return float(phi((mu - eps - L.obs[u][1]) / sd))
 167|         if kw:
 168|             mu, sd = cache[u]; return float(phi((L.obs[w][0] - mu - eps) / sd))
 169|         (m1, s1), (m2, s2) = cache[u], cache[w]
 170|         return float(phi((m2 - m1 - 2 * eps) / math.hypot(s1, s2)))
 171| 
 172|     # --- open-route candidates
 173|     def open_routes(self, topk=5, members=40):
 174|         L = self.ledger; t = self.ctx.target
 175|         C = np.fromiter(L.closure.keys(), np.int64, len(L.closure))
 176|         h = hamming(C, t)
 177|         sc = np.array([L.obs[int(v)][2] for v in C])
 178|         order = np.lexsort((C, -sc, h))[:members]
 179|         routes, nodes = [], set()
 180|         for ci in order:
 181|             u = int(C[ci])
 182|             du, dt = digits(u), digits(t)
 183|             pos = [p for p in range(4) if du[p] != dt[p]]
 184|             for perm in itertools.permutations(pos):
 185|                 cur = du.copy(); path = [u]
 186|                 for p in perm:
 187|                     cur[p] = dt[p]
 188|                     path.append(int(((cur[0] * 20 + cur[1]) * 20 + cur[2]) * 20 + cur[3]))
 189|                 if path[-1] != t or any(x in L.absent for x in path):
 190|                     continue
 191|                 routes.append(path); nodes.update(path)
 192|         cache = {}
 193|         self._stats(nodes, cache)
 194|         scored = []
 195|         for path in routes:
 196|             ps = [self.edge_p(path[i], path[i + 1], cache) for i in range(len(path) - 1)]
 197|             P = float(np.prod(ps))
 198|             if P <= 0:
 199|                 continue
 200|             unk = [v for v in path if v not in L.obs]
 201|             if not unk:
 202|                 continue
 203|             scored.append({"nodes": path, "unknown": unk, "p_edges": ps, "p": P, "cost": len(unk), "score": len(unk) / P})
 204|         scored.sort(key=lambda r: (r["score"], r["nodes"]))
 205|         return scored[:topk], cache
 206| 
 207|     @staticmethod
 208|     def next_on_route(route, ledger):
 209|         """fail-fast: assay the unknown node adjacent to the weakest edge."""
 210|         path, ps = route["nodes"], route["p_edges"]
 211|         best = None
 212|         for i, p in enumerate(ps):
 213|             for v in (path[i], path[i + 1]):
 214|                 if v not in ledger.obs and (best is None or p < best[0]):
 215|                     best = (p, v)
 216|         return best[1] if best else None
 217| 
 218|     # --- cut planning
 219|     def frontier_probs(self, k=POOL):
 220|         L = self.ledger
 221|         F = frontier_array(L)
 222|         if F.size == 0:
 223|             return F, np.array([]), 0.0
 224|         h = hamming(F, self.ctx.target)
 225|         sel = F[np.argsort(h, kind="stable")[:k]] if F.size > k else F
 226|         cache = {}
 227|         self._stats(sel.tolist(), cache)
 228|         eps = self.ctx.eps_typ
 229|         P = np.array([max(phi((cache[int(w)][0] - eps - L.obs[u][1]) / cache[int(w)][1]) for u in L.frontier[int(w)]) for w in sel])
 230|         mean_p = float(P.mean())
 231|         return sel, P, mean_p
 232| 
 233|     def block_cost(self):
 234|         """Heuristic expected assays to close the cut: every frontier genotype must be
 235|         assayed, and each admissible one (prob. ~ mean_p) opens up to 75 new neighbours."""
 236|         F = len(self.ledger.frontier)
 237|         sel, P, mp = self.frontier_probs()
 238|         return F * (1.0 + 75.0 * mp), sel, P
 239| 
 240| 
 241| class Q2C(Base):
 242|     """Single-brain query-to-certify: choose the cheaper of open-route falsification
 243|     and cut completion under one GP surrogate sharing all revealed evidence."""
 244|     name = "q2c"
 245| 
 246|     def __init__(self, ctx, rng, model=None):
 247|         super().__init__(ctx, rng)
 248|         self.model = model or GPModel(prior=ctx.prior)
 249|         self.pl = None
 250| 
 251|     def step(self, oracle, ledger):
 252|         if self.pl is None:
 253|             self.pl = Planner(self.ctx, ledger, self.model)
 254|         pl = self.pl; pl.sync()
 255|         if not ledger.frontier:
 256|             return False
 257|         routes, _ = pl.open_routes()
 258|         bc, sel, P = pl.block_cost()
 259|         use_open = bool(routes) and routes[0]["score"] <= bc
 260|         if use_open:
 261|             v = pl.next_on_route(routes[0], ledger); why = f"open route p={routes[0]['p']:.3g} unknown={routes[0]['cost']}"
 262|         else:
 263|             v = int(sel[int(np.argmax(P))]); why = f"cut completion frontier={len(ledger.frontier)}"
 264|         if v is None or v in oracle.queried:
 265|             v = int(sel[int(np.argmax(P))])
 266|         self.ask(oracle, ledger, v, why)
 267|         return True

----- core/evolve/model.py -----
   1| """Small surrogate models used only to decide WHICH genotype to assay next.
   2| They never discharge an empirical premise: certificates use revealed labels only.
   3| 
   4| GPModel   : GP regression on sequence with additive + pairwise-site + Hamming
   5|             kernels (hyperparameters fixed a priori, no tuning on hidden labels).
   6| LocalModel: Hamming-neighbourhood smoother (different inductive bias).
   7| Both return (mean, sd) in score units (micro-units/1e6) and cache per fit.
   8| """
   9| from __future__ import annotations
  10| 
  11| import numpy as np
  12| from scipy.linalg import cho_factor, cho_solve, solve_triangular
  13| 
  14| from .data import UNITS, digits
  15| 
  16| PAIRS = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]
  17| 
  18| 
  19| def _eq(A, B):  # (m,4),(n,4) -> (m,n,4)
  20|     return A[:, None, :] == B[None, :, :]
  21| 
  22| 
  23| def kernel(A, B, w_add=0.35, w_pair=0.25, w_ham=0.40, rho=0.45):
  24|     eq = _eq(A, B)
  25|     k_add = eq.sum(-1) / 4.0
  26|     k_pair = sum((eq[..., i] & eq[..., j]) for i, j in PAIRS) / 6.0
  27|     k_ham = rho ** (4 - eq.sum(-1))
  28|     return w_add * k_add + w_pair * k_pair + w_ham * k_ham
  29| 
  30| 
  31| class GPModel:
  32|     name = "gp"
  33| 
  34|     def __init__(self, noise=0.15, prior=None):
  35|         self.noise, self.prior = noise, prior  # prior: optional (160000,) float array of external prior means (score units)
  36|         self.n = 0; self.cache = {}
  37| 
  38|     def fit(self, nodes, scores):
  39|         X = digits(np.asarray(nodes)); y = np.asarray(scores, float) / UNITS
  40|         self.X = X
  41|         pm = self._pm(nodes)
  42|         self.mean0 = float(np.mean(y - pm)) if len(y) else 0.0
  43|         self.sf2 = max(float(np.var(y)), 1e-4)
  44|         K = self.sf2 * kernel(X, X) + self.noise * self.sf2 * np.eye(len(y))
  45|         self.c = cho_factor(K, lower=True)
  46|         self.alpha = cho_solve(self.c, y - pm - self.mean0)
  47|         self.cache = {}; self.n = len(y)
  48| 
  49|     def _pm(self, nodes):
  50|         return 0.0 if self.prior is None else np.asarray(self.prior)[np.asarray(nodes)].astype(float)
  51| 
  52|     def predict(self, nodes):
  53|         nodes = np.asarray(nodes, np.int64)
  54|         miss = [int(v) for v in nodes if int(v) not in self.cache]
  55|         if miss:
  56|             m = np.array(miss)
  57|             Ks = self.sf2 * kernel(digits(m), self.X)
  58|             mu = Ks @ self.alpha + self.mean0 + self._pm(m)
  59|             V = solve_triangular(self.c[0], Ks.T, lower=True)
  60|             var = np.maximum(self.sf2 * 1.0 - (V ** 2).sum(0), 1e-8) + self.noise * self.sf2
  61|             for v, a, b in zip(miss, mu, np.sqrt(var)):
  62|                 self.cache[v] = (float(a), float(b))
  63|         r = np.array([self.cache[int(v)] for v in nodes])
  64|         return r[:, 0], r[:, 1]
  65| 
  66| 
  67| class LocalModel:
  68|     name = "local"
  69| 
  70|     def __init__(self, shrink=1.0, prior=None):
  71|         self.shrink, self.prior = shrink, prior
  72|         self.cache = {}
  73| 
  74|     def fit(self, nodes, scores):
  75|         self.X = digits(np.asarray(nodes)); self.y = np.asarray(scores, float) / UNITS
  76|         self.m0 = float(np.median(self.y)) if len(self.y) else 0.0
  77|         self.sd0 = max(float(np.std(self.y)), 1e-3)
  78|         self.cache = {}
  79| 
  80|     def predict(self, nodes):
  81|         nodes = np.asarray(nodes, np.int64)
  82|         miss = [int(v) for v in nodes if int(v) not in self.cache]
  83|         if miss:
  84|             m = np.array(miss)
  85|             d = (digits(m)[:, None, :] != self.X[None, :, :]).sum(-1)      # (m,n)
  86|             w = np.where(d == 1, 1.0, np.where(d == 2, 0.25, 0.0))
  87|             sw = w.sum(1)
  88|             base = self.m0 if self.prior is None else np.asarray(self.prior)[m]
  89|             mu = (w @ self.y + self.shrink * base) / (sw + self.shrink)
  90|             var = (self.sd0 ** 2) / (sw + self.shrink)
  91|             sd = np.sqrt(var + 0.25 * self.sd0 ** 2 * (sw > 0) * 0)  # shrinks with local evidence
  92|             for v, a, b in zip(miss, np.atleast_1d(mu), sd):
  93|                 self.cache[v] = (float(a), float(b))
  94|         r = np.array([self.cache[int(v)] for v in nodes])
  95|         return r[:, 0], r[:, 1]

----- core/evolve/replay.py -----
   1| """Matched-budget retrospective query-to-certify replay.
   2| 
   3| Protocol (frozen before the first run; see PANEL below and artifacts/core/protocol.json):
   4| * declared graph: measured subgraph G_meas (159,129 nodes), single substitutions;
   5| * declared edge rule: Lo[v] >= Hi[u] with eps = KAPPA * sd_bin / 2 (assumed);
   6| * truth: forward admissible closure under FULL measured labels (benchmark truth,
   7|   not biological truth);
   8| * every policy gets the same start, target, 96 random initial observations (+start,
   9|   target) and assay budget BMAX; one run yields the whole certificate-vs-assays curve
  10|   because no policy is told the budget;
  11| * certificates are issued only from revealed labels; unresolved runs are RIGHT-CENSORED
  12|   at BMAX and kept;
  13| * pair families (no hidden-label cherry-picking):
  14|     A "seeded-initial": target = best-scoring genotype among the seed's own 96
  15|        initial observations, start = random other initial observation with lower score
  16|        and Hamming >= 2.  Uses only admissible observations.
  17|     B "published-parent": start = parent VFVS, target in the published top variants
  18|        AIKG, CLKG, VLKG, ALKG (identified in the source paper / dataset).  Targets fixed
  19|        by published biology, not by held-out ranking performed here.
  20| """
  21| from __future__ import annotations
  22| 
  23| import gzip
  24| import json
  25| import time
  26| from dataclasses import dataclass, field
  27| from pathlib import Path
  28| 
  29| import numpy as np
  30| 
  31| from . import data
  32| from .collective import Collective
  33| from .graph import Ledger, path_to, truth_bfs, verify_cut, verify_route
  34| from .oracle import EventLog, Oracle
  35| from .policies import Directed, Greedy, Q2C, RandomFrontier, Uncertainty
  36| 
  37| BMAX = 1000
  38| N_INIT = 96
  39| SEED_BASE = 20261031
  40| PUBLISHED_START = "VFVS"
  41| PUBLISHED_TARGETS = ("AIKG", "CLKG", "VLKG", "ALKG")
  42| POLICIES = {
  43|     "random": RandomFrontier, "greedy": Greedy, "uncertainty": Uncertainty,
  44|     "directed": Directed, "q2c": Q2C,
  45|     "collective_shared": lambda c, r: Collective(c, r, True),
  46|     "collective_isolated": lambda c, r: Collective(c, r, False),
  47|     "collective_shared_rr": lambda c, r: Collective(c, r, True, "rr"),
  48| }
  49| 
  50| 
  51| @dataclass
  52| class Ctx:
  53|     start: int
  54|     target: int
  55|     eps_typ: float
  56|     prior: object = None
  57| 
  58| 
  59| def eps_typical(land):
  60|     return float(np.ceil(land.kappa * data.REPLICATE_DIFF_SD[2] / 2 * data.UNITS))
  61| 
  62| 
  63| def make_episodes(land, seeds):
  64|     """Deterministic pair + initial-set panel. Label use: only the seed's own initial observations."""
  65|     meas_idx = np.flatnonzero(land.measured)
  66|     eps = []
  67|     for seed in range(seeds):
  68|         rng = np.random.default_rng(SEED_BASE + seed)
  69|         init = [int(x) for x in rng.choice(meas_idx, N_INIT, replace=False)]
  70|         sc = land.s[init]
  71|         tgt = init[int(np.argmax(sc))]
  72|         cand = [x for x in init if x != tgt and land.s[x] <= land.s[tgt] and int(data.hamming(x, tgt)) >= 2]
  73|         st = int(rng.choice(cand))
  74|         eps.append({"family": "A", "seed": seed, "start": st, "target": tgt, "init": init})
  75|         s0 = data.encode(PUBLISHED_START)
  76|         for g in PUBLISHED_TARGETS:
  77|             r2 = np.random.default_rng(SEED_BASE + 10_000 + seed)
  78|             init2 = [int(x) for x in r2.choice(meas_idx, N_INIT, replace=False)]
  79|             eps.append({"family": "B", "seed": seed, "start": s0, "target": data.encode(g), "init": init2})
  80|     return eps
  81| 
  82| 
  83| _truth_cache = {}
  84| 
  85| 
  86| def truth(land, start, target):
  87|     k = (start, land.kappa)
  88|     if k not in _truth_cache:
  89|         Lo, Hi = land.intervals()
  90|         _truth_cache[k] = truth_bfs(land.measured, Lo, Hi, start)
  91|     r, p, d = _truth_cache[k]
  92|     return bool(r[target]), int(r.sum()), (path_to(p, start, target) if r[target] else None)
  93| 
  94| 
  95| def run_episode(land, ep, policy_name, bmax=BMAX, keep_events=False, prior=None):
  96|     Lo, Hi = land.intervals()
  97|     log = EventLog()
  98|     oracle = Oracle(land, land.kappa, log)
  99|     ledger = Ledger(ep["start"], ep["target"])
 100|     ctx = Ctx(ep["start"], ep["target"], eps_typical(land), prior)
 101|     # same admissible initial observations for every policy: start, target, then the 96 random
 102|     order = [ep["start"], ep["target"]] + [v for v in ep["init"] if v not in (ep["start"], ep["target"])]
 103|     for v in order:
 104|         ledger.reveal(v, oracle.reveal_free(v))
 105|     pol_seed = SEED_BASE + 77 * ep["seed"] + 5 * ep["target"] % 100003
 106|     pol = POLICIES[policy_name](ctx, np.random.default_rng(pol_seed))
 107|     t0 = time.time(); status = ledger.status(); stuck = False
 108|     qlog = []
 109|     while status == "unresolved" and oracle.n_queries < bmax:
 110|         n0 = oracle.n_queries
 111|         if not pol.step(oracle, ledger):
 112|             stuck = True; break
 113|         assert oracle.n_queries == n0 + 1
 114|         status = ledger.status()
 115|     wall = time.time() - t0
 116|     truth_open, closure_size, truth_route = truth(land, ep["start"], ep["target"])
 117|     out = {"family": ep["family"], "seed": ep["seed"], "start": data.decode(ep["start"]), "target": data.decode(ep["target"]),
 118|            "policy": policy_name, "truth_open": truth_open, "truth_closure_size": closure_size,
 119|            "truth_shortest_route_len": None if truth_route is None else len(truth_route) - 1,
 120|            "status": status, "assays": oracle.n_queries, "censored": status == "unresolved", "stuck": stuck,
 121|            "wall_s": round(wall, 3), "bmax": bmax,
 122|            "observed_max_score": int(max(v[2] for v in ledger.obs.values())), "n_observed": len(ledger.obs)}
 123|     out["certificate"] = None if status == "unresolved" else status
 124|     out["correct"] = None if status == "unresolved" else (status == "open") == truth_open
 125|     # independent re-verification against FULL data (audit only, never policy-visible)
 126|     if status == "open":
 127|         route = ledger.route()
 128|         out["verified_by_full_data"] = bool(verify_route(land.measured, Lo, Hi, route))
 129|         out["route"] = [data.decode(v) for v in route]
 130|         out["route_len"] = len(route) - 1
 131|         out["min_edge_margin"] = int(min(Lo[route[i + 1]] - Hi[route[i]] for i in range(len(route) - 1))) if len(route) > 1 else None
 132|         out["replicate_sign_agree_frac"] = float(np.mean([(land.s1[route[i + 1]] >= land.s1[route[i]]) and (land.s2[route[i + 1]] >= land.s2[route[i]]) for i in range(len(route) - 1)])) if len(route) > 1 else None
 133|     elif status == "blocked":
 134|         S, bnd = ledger.cut()
 135|         out["verified_by_full_data"] = bool(verify_cut(land.measured, Lo, Hi, S, ep["start"], ep["target"]))
 136|         out["cut_size"] = len(S); out["cut_boundary_edges"] = len(bnd)
 137|     events = [e for e in log.events if e["type"] == "reveal" and e["cost"] == 1]
 138|     qlog = [(e["n_queries"], e["actor"], e["node"], e["rec"], e["why"]) for e in events]
 139|     other = [e for e in log.events if e["type"] != "reveal"] if keep_events else []
 140|     return out, qlog, other, log
 141| 
 142| 
 143| def shard_path(outdir, policy, seed):
 144|     return Path(outdir) / "shards" / f"{policy}__seed{seed:02d}.json"
 145| 
 146| 
 147| def run_shard(args):
 148|     outdir, policy, seed, kappa, bmax = args
 149|     import os
 150|     os.environ.setdefault("OMP_NUM_THREADS", "1")
 151|     p = shard_path(outdir, policy, seed)
 152|     if p.exists():
 153|         return str(p), True
 154|     land = data.load(kappa=kappa)
 155|     rows, qlogs = [], {}
 156|     prior = None
 157|     if policy.endswith("+prior"):      # optional external prior: (160000,) float array of predicted scores, genotype order = evolve.data.encode
 158|         import os
 159|         prior = np.load(os.environ["EVOLVE_PRIOR_NPY"]); assert prior.shape == (data.N_GENO,) and np.isfinite(prior).all()
 160|         policy = policy[:-6]
 161|     for ep in [e for e in make_episodes(land, seed + 1) if e["seed"] == seed]:
 162|         out, qlog, other, log = run_episode(land, ep, policy, bmax=bmax, keep_events=(seed == 0 and policy.startswith("collective")), prior=prior)
 163|         if prior is not None:
 164|             out["policy"] = policy + "+prior"
 165|         qlogs[f'{out["family"]}:{out["start"]}>{out["target"]}'] = qlog
 166|         if seed == 0 and policy.startswith("collective"):
 167|             d = Path(outdir) / "events"; d.mkdir(parents=True, exist_ok=True)
 168|             with gzip.open(d / f'{policy}__{out["family"]}_{out["start"]}_{out["target"]}.jsonl.gz', "wt") as f:
 169|                 for e in log.events:
 170|                     f.write(json.dumps(e, default=int) + "\n")
 171|             out["event_chain_valid"] = log.verify()
 172|     p.parent.mkdir(parents=True, exist_ok=True)
 173|     p.write_text(json.dumps({"rows": rows, "qlogs": qlogs}, default=int))
 174|     return str(p), False
 175| 
 176| 
 177| def protocol(land, seeds=20):
 178|     import hashlib
 179|     panel = make_episodes(land, seeds)
 180|     pairs = [{"family": e["family"], "seed": e["seed"], "start": data.decode(e["start"]), "target": data.decode(e["target"]),
 181|               "initial_observations_sha256": hashlib.sha256(json.dumps(sorted(e["init"])).encode()).hexdigest()} for e in panel]
 182|     return {
 183|         "frozen_before_main_run": True,
 184|         "graph_scope": "measured subgraph G_meas of 20^4 amino-acid library, single-substitution adjacency; 871 unmeasured genotypes are outside scope; stop-containing genotypes excluded",
 185|         "edge_rule": "u->v admissible iff Lo[v] >= Hi[u]; Lo/Hi = round(mean of 2 replicates, micro-units) -/+ ceil(kappa*sd_bin/2*1e6)",
 186|         "kappa_main": land.kappa, "kappa_meaning": "assumed sensitivity multiplier, not a confidence level",
 187|         "noise_bins_min_input_count_edges": list(data.COUNT_BIN_EDGES), "replicate_diff_sd": list(data.REPLICATE_DIFF_SD),
 188|         "truth": "forward admissible closure of start under full measured labels (benchmark truth under declared model, not biological truth)",
 189|         "budget_assays_beyond_initial": BMAX, "n_initial_random_observations": N_INIT,
 190|         "policies": list(POLICIES), "seeds": seeds,
 191|         "pair_rules": {"A": "target = best-scoring of the seed's 96 initial observations; start = random other initial observation with lower score, Hamming>=2",
 192|                        "B": f"start {PUBLISHED_START}; targets {list(PUBLISHED_TARGETS)} (published top variants); initial set seeded by seed"},
 193|         "censoring": "unresolved or stuck at budget is right-censored and retained",
 194|         "dataset_sha256": land.sha, "panel": pairs,
 195|         "panel_sha256": hashlib.sha256(json.dumps(pairs, sort_keys=True).encode()).hexdigest(),
 196|     }

----- core/evolve/collective.py -----
   1| """Runtime specialist collective for query-to-certify.
   2| 
   3| Specialists (separate objects, each with its own surrogate and view of evidence):
   4|   data     gatekeeper: sole holder of the oracle, budget and the certificate ledger;
   5|            reveals only observed labels; refuses duplicate assays.
   6|   route    proposes the next assay to confirm/falsify the best open route (GP model A).
   7|   cut      proposes the next assay to complete a closed set (local model B).
   8|   critic   (shared mode only) re-prices the route specialist's candidate routes with the
   9|            cut specialist's model; a route that survives only under one model is
  10|            demoted ("challenge").  Its output changes which assay is bought.
  11|   arbiter  data specialist; compares open-route and cut cost estimates.
  12| 
  13| shared   : every specialist reads the one global ledger (all reveals) and posts
  14|            proposals/challenges visible to all.
  15| isolated : route and cut specialists keep PRIVATE ledgers + models fed only by assays
  16|            they themselves caused; they alternate turns; no cross-reading.  The data
  17|            specialist still pools all reveals for certification (a certificate needs the
  18|            union of facts), and a duplicate request is answered from that ledger for
  19|            free (logged) -- the only leak in the isolated arm.
  20| 
  21| This is a runtime decision protocol inside one Python process: the decisions are made
  22| by distinct specialist objects, but scheduling/arbitration is fixed software, not an
  23| independent-agent market.  See artifacts/core/README.md for what this does and does not show.
  24| """
  25| from __future__ import annotations
  26| 
  27| import numpy as np
  28| 
  29| from .graph import Ledger
  30| from .model import GPModel, LocalModel
  31| from .policies import Base, Planner
  32| 
  33| 
  34| class Collective(Base):
  35|     def __init__(self, ctx, rng, shared=True, arbiter="cost"):
  36|         super().__init__(ctx, rng)
  37|         self.shared, self.arbiter = shared, arbiter
  38|         self.name = ("collective_shared" if arbiter == "cost" else "collective_shared_rr") if shared else "collective_isolated"
  39|         self.pl = {}
  40|         self.turn = 0
  41|         self.priv = None
  42| 
  43|     # -- helpers
  44|     def _planner(self, role, ledger, model):
  45|         if role not in self.pl:
  46|             self.pl[role] = Planner(self.ctx, ledger, model)
  47|         return self.pl[role]
  48| 
  49|     def _post(self, oracle, type_, actor, visible_to, **kw):
  50|         oracle.log.emit(type_, actor, visible_to=visible_to, **kw)
  51| 
  52|     def _init_private(self, ledger):
  53|         if self.priv is None:
  54|             self.priv = {}
  55|             for role in ("route", "cut"):
  56|                 L = Ledger(self.ctx.start, self.ctx.target)
  57|                 for v, rec in ledger.obs.items():
  58|                     L.reveal(v, rec)
  59|                 self.priv[role] = L
  60| 
  61|     # -- main
  62|     def step(self, oracle, ledger):
  63|         if not ledger.frontier:
  64|             return False
  65|         return self._shared_step(oracle, ledger) if self.shared else self._isolated_step(oracle, ledger)
  66| 
  67|     def _shared_step(self, oracle, ledger):
  68|         plA = self._planner("route", ledger, GPModel(prior=self.ctx.prior))
  69|         plB = self._planner("cut", ledger, LocalModel(prior=self.ctx.prior))
  70|         plA.sync(); plB.sync()
  71|         routes, _ = plA.open_routes()
  72|         bcA, selA, PA = plA.block_cost()
  73|         bcB, selB, PB = plB.block_cost()
  74|         bc = 0.5 * (bcA + bcB)
  75|         route_pick = None
  76|         if routes:
  77|             r0 = routes[0]
  78|             self._post(oracle, "proposal", "route", "all", hyp="open", route=r0["nodes"], p=r0["p"], score=r0["score"])
  79|             cacheB = {}
  80|             plB._stats({v for r in routes for v in r["nodes"]}, cacheB)
  81|             best = None
  82|             for r in routes:
  83|                 pB = float(np.prod([plB.edge_p(r["nodes"][i], r["nodes"][i + 1], cacheB) for i in range(len(r["nodes"]) - 1)]))
  84|                 pess = min(r["p"], pB)
  85|                 sc = r["cost"] / pess if pess > 0 else float("inf")
  86|                 if best is None or sc < best[0]:
  87|                     best = (sc, r, pB)
  88|             route_pick = best
  89|             if best[1]["nodes"] != r0["nodes"]:
  90|                 self._post(oracle, "challenge", "critic", "all", target="route", reason="route survives only under one model; demoted by pessimistic (min over models) probability",
  91|                            demoted=r0["nodes"], preferred=best[1]["nodes"], p_route_model=r0["p"], p_cut_model=best[2])
  92|         self._post(oracle, "proposal", "cut", "all", hyp="blocked", frontier=len(ledger.frontier), cost=bcB, query=int(selB[int(np.argmax(PB))]))
  93|         use_open = route_pick is not None and route_pick[0] <= bc
  94|         if self.arbiter == "rr":      # control: same shared evidence, but alternate hypotheses instead of comparing costs
  95|             use_open = route_pick is not None and self.turn % 2 == 0
  96|             self.turn += 1
  97|         if use_open:
  98|             v = plA.next_on_route(route_pick[1], ledger)
  99|         else:
 100|             v = None
 101|         if v is None or v in oracle.queried:
 102|             comb = PA[: len(selA)]
 103|             v = int(selA[int(np.argmax(comb))]) if selA.size else int(selB[int(np.argmax(PB))])
 104|             use_open = False
 105|         self._post(oracle, "decision", "arbiter", "all", rule=self.arbiter, chose="open-route" if use_open else "cut", open_score=None if route_pick is None else route_pick[0], cut_cost=bc, query=int(v))
 106|         self.ask(oracle, ledger, v, "shared: " + ("open route" if use_open else "cut completion"))
 107|         return True
 108| 
 109|     def _isolated_step(self, oracle, ledger):
 110|         self._init_private(ledger)
 111|         role = "route" if self.turn % 2 == 0 else "cut"
 112|         self.turn += 1
 113|         mine = self.priv[role]
 114|         if not mine.frontier:
 115|             role = "cut" if role == "route" else "route"; mine = self.priv[role]
 116|             if not mine.frontier:
 117|                 return False
 118|         model = GPModel(prior=self.ctx.prior) if role == "route" else LocalModel(prior=self.ctx.prior)
 119|         pl = self._planner(role, mine, model); pl.sync()
 120|         v = None
 121|         if role == "route":
 122|             routes, _ = pl.open_routes()
 123|             if routes:
 124|                 v = pl.next_on_route(routes[0], mine)
 125|                 self._post(oracle, "proposal", "route", ["route"], hyp="open", route=routes[0]["nodes"], p=routes[0]["p"], query=v)
 126|         if v is None:
 127|             _, sel, P = pl.block_cost()
 128|             v = int(sel[int(np.argmax(P))])
 129|             self._post(oracle, "proposal", role, [role], hyp="blocked" if role == "cut" else "fallback-cut", query=v)
 130|         if v in oracle.queried:   # already revealed to the other specialist: gatekeeper answers from ledger, free
 131|             rec = ledger.obs[v] if v in ledger.obs else None
 132|             self._post(oracle, "duplicate_request", "data", [role], node=int(v), cost=0)
 133|             mine.reveal(v, rec)
 134|             # forced progress: avoid stalling when the proposer asks only for known nodes
 135|             self.stall = getattr(self, "stall", 0) + 1
 136|             if self.stall > 50:
 137|                 keys = [w for w in ledger.frontier]
 138|                 v = keys[int(self.rng.integers(len(keys)))]
 139|             else:
 140|                 return self._isolated_step(oracle, ledger)
 141|         self._post(oracle, "decision", "arbiter", "all", chose=role, query=int(v), rule="round-robin (no cost comparison across isolated models)")
 142|         rec = oracle.query(v, self.name + ":" + role, "isolated " + role)
 143|         ledger.reveal(int(v), rec); mine.reveal(int(v), rec)
 144|         return True
