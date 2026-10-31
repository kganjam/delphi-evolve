# LazySP-style baseline for TrpB query-to-certify

Status: **complete.** Protocol preregistered before any panel episode was run (commit `1412a6f`); full preregistered
panel (3 variants x 100 episodes) run and independently audited. See "Results".

## What this is, and what it is not

Established prior art selects expensive evaluations to settle whether a feasible path exists:
* Dellin & Srinivasa, *LazySP* (ICAPS 2016): <https://www.ri.cmu.edu/pub_files/2016/3/paper-lazysp.pdf>
* Choudhury et al., *Bayesian Active Edge Evaluation on Expensive Graphs*, IJCAI 2018: <https://ijcai.org/proceedings/2018/679>

This package adds the direct lazy path-search baseline that the prior-art audit found missing from
the original comparison. It is a bounded extension, not a new method, not a claim of novelty, and
nothing here was tuned on benchmark results.

Existing core policies, stated precisely (read from `evolve/policies.py`):

| core policy | what it actually is | LazySP? |
|---|---|---|
| `random` | uniform over the **unknown frontier of the revealed admissible closure** (not global random) | no |
| `directed` | target-Hamming best-first over the same frontier (ties: parent score, index) | no: it ranks frontier vertices only, never searches the whole optimistic graph and never replans around observed blocked edges |
| `q2c` | GP-ranked candidate Hamming-monotone path permutations from closure members + a block-cost arbitration (route falsification vs cut completion) | no: candidate routes are monotone-in-Hamming permutations from closure members, not a shortest-path search over the full graph; the arbitration uses a surrogate |

## The baseline

**Optimistic graph.** Vertices: all 20^4 genotypes of the declared library. Edges: single
substitutions, directed. Every unevaluated edge has estimated weight 1 (LazySP's `w_est`). An edge
`u->v` is *evaluated* once both endpoints are revealed; its weight is 1 if ADMISSIBLE
(`Lo[v] >= Hi[u]`, the core ledger rule, integer micro-units) and infinite otherwise. A vertex that
an assay reported as outside the measured scope (absent) is removed. Unrevealed vertices are always
optimistic: the baseline is NOT told the measured mask. Overlapping intervals are inadmissible
(the core rule is conservative; see `tasks/semantics-review.md`).

**Loop (LazySP Algorithm 1).** Exact shortest candidate path from `start` to `target` under the lazy
weights (A* with the Hamming-distance lower bound, which is consistent for single-substitution
unit edges; no cap, no pruning). If the path has an unrevealed vertex, an edge selector picks which
one to assay through the **same paid-query oracle** used by every policy; the observation updates
the ledger; repeat. The replay loop stops as soon as the shared ledger certifies (`open` or
`blocked`); a path whose vertices are all revealed with admissible edges is exactly an `open` ledger.

**Selectors (Algorithm 2 of the paper).** Forward = first unevaluated edge, Reverse = last,
Alternate = Forward on odd iterations and Reverse on even iterations.

**Node-query adaptation (ours, not in the source papers).** The papers price edge evaluations; here
the paid action is a genotype assay that reveals a vertex. A path starts and ends at revealed
vertices, so the first unevaluated edge has a revealed tail and unrevealed head (Forward assays the
first unrevealed path vertex) and the last unevaluated edge has an unrevealed tail and revealed head
(Reverse assays the last unrevealed path vertex). One assay can evaluate two edges at once. The
paper's edge-equivalence and optimality theorems are about edge evaluations and are NOT claimed to
transfer to assay counts.

**Candidate-path caching.** The optimistic edge set only shrinks as vertices are revealed, so a
still-valid candidate path remains a shortest path; we keep it and re-search only when an
observation invalidates it. LazySP allows arbitrary tie-breaking among shortest paths and keeping
the incumbent is one such tie-break. Search tie-break: A* heap key `(f, h, node index)`, neighbours
expanded in ascending index, parent changed only on strict improvement of g.

**Native infeasibility.** If the optimistic graph itself disconnects `start` from `target` while the
ledger is unresolved, the baseline has proved no admissible route exists; the policy records the
assay count (`native_infeasible_at`) and then spends assays only on the ledger's unknown frontier
(ordered by Hamming distance to target, then index) until the ledger certifies, so that primary
results use the identical ledger certificate for every policy. Such queries are labelled
`fallback_after_native_infeasible` and counted.

**Objective.** The ledger certificate: `open` = a route of conservatively admissible edges among
revealed vertices; `blocked` = the revealed admissible closure of `start` is closed and omits
`target`. `blocked` means *no conservatively-admissible route in the declared measured graph*. It is
neither biological impossibility nor "no ascending route exists for any assignment inside the
intervals".

**Information.** The policy receives `(oracle, ledger, ctx{start,target,eps_typ})`. It never touches the
landscape; the only label access is `Oracle.query`. A unit test scrambles every never-assayed label and
requires an identical query sequence.

**Budget / abstention.** Identical to the original: 96 random initial observations plus start and target
revealed free, then at most 1000 paid assays. Reaching the budget, or a per-episode wall-clock bound,
produces `unresolved` with an explicit `abstain_reason` (`assay_budget` or `runtime_bound`). Neither is
ever represented as `blocked`.

## Preregistration

Written and committed before the first panel episode was run. Machine-readable copy:
`artifacts/lazysp/preregistration.json`.

* Panel: the frozen original panel, `panel_sha256 = bb6c144e8f0eba1079d6353d9c7f612a02df30afa7770ce94a064a47ad9b9bcf`
  (20 seeds x 5 episodes = 100 episodes; family A seeded-initial, family B published-parent), kappa = 2.0,
  budget 1000 paid assays, identical initial observations. The driver recomputes the panel hash and refuses
  to run on mismatch.
* Primary policy: `lazysp_alternate` (the paper's recommended simple selector compromise). Secondary,
  declared in advance: `lazysp_forward`, `lazysp_reverse`. All are reported; no best-of-three selection.
* Comparator: the **saved** original `q2c` rows (100 episodes) in `artifacts/recovery/episodes.csv`
  (recovered from actual query histories; no policy is re-run). `directed`, `random`, `greedy`,
  `uncertainty`, `collective_*` rows from the same file are reported descriptively.
* Primary metrics: resolved@B (ledger certificate within B assays, unresolved kept in the denominator)
  for B in {100,250,500,750,1000}; restricted mean assays-to-certificate at tau=1000 with unresolved counted
  as tau; false certificates; full-data verification failures; abstentions by reason.
* Paired analysis: difference LazySP - q2c per episode; 95% percentile interval from a paired seed-cluster
  bootstrap (20 seed clusters, 10,000 draws, `numpy.default_rng(20261031)`); raw discordant counts. The
  interval is descriptive (one panel, 20 clusters) and not a coverage guarantee.
* Allowed to change after the seed-0 smoke run (resource only): the per-episode wall-clock bound
  (<= 450 s), process parallelism (<= 2) and which secondary variants fit in the 2 h budget.
  NOT allowed: selector definitions, tie-breaks, heuristic, graph rule, budgets, panel, analysis.
  Any later code fix is reported as an amendment with both results.
* A null result or a defeat of q2c is a valid, reportable result. A win is not claimed unless the paired
  interval supports it. No no-feedback-repair claim; no new landscape.

## Reproduce

```
ln -s <downloaded Caltech files> data/raw           # or: python scripts/fetch_data.py
python -m pytest tests/test_lazysp_search.py tests/test_lazysp_policy.py      # fixture tests
python -m baselines.lazysp run-task --variant alternate --seed 0 --k 1 --out runs/x --cap 450
bash baselines/run_panel.sh <outdir> <variants> <cap>                          # bounded sharded full panel
python -m baselines.lazysp analyze --dir <outdir> --out artifacts/lazysp/<name> --variants alternate,forward,reverse
```
Each task runs in `systemd-run --user --scope -p TasksMax=128 -p MemoryMax=4G -p MemorySwapMax=0 -p RuntimeMaxSec=600`.

## Results

All numbers come from saved files: shards `artifacts/lazysp/panel/shards/` (300 gzip JSON files, one per variant x
episode, each with the full assay log), aggregated by `python -m baselines.lazysp analyze` into
`artifacts/lazysp/results/` (`summary.json`, `table_primary.csv`, `table_paired.csv`, `episodes.csv`,
`episodes_with_original.csv`, `exploratory_post_hoc.json`, `cert_vs_assays.png`). Comparator rows are the saved
original episodes in `artifacts/recovery/episodes.csv`. The panel is COMPLETE: 100 episodes per variant, none missing,
no empty shard, zero runtime-bound hits, zero failed tasks. Unresolved episodes stay in every denominator.

### Preregistered primary results (100 episodes, 1000 paid assays, kappa 2)

| policy | open | blocked | unresolved | false cert. | resolved@100 | @250 | @500 | @750 | @1000 | RMST assays (tau=1000) |
|---|---|---|---|---|---|---|---|---|---|---|
| **lazysp_alternate (primary)** | 91 | 5 | 4 | 0 | 0.27 | 0.50 | 0.55 | 0.56 | **0.96** | 476.6 |
| lazysp_forward (secondary) | 91 | 5 | 4 | 0 | 0.29 | 0.54 | 0.55 | 0.96 | 0.96 | 369.6 |
| lazysp_reverse (secondary) | 49 | 0 | 51 | 0 | 0.26 | 0.27 | 0.49 | 0.49 | 0.49 | 593.9 |
| q2c (saved original) | 73 | 5 | 22 | 0 | 0.24 | 0.43 | 0.48 | 0.70 | 0.78 | 483.1 |
| directed (saved) | | | | 0 | | | | | 0.32 | 709.2 |
| random (saved) | | | | 0 | | | | | 0.21 | 877.4 |

Paired difference LazySP - q2c (preregistered seed-cluster bootstrap, 95% percentile interval, descriptive):

| variant | resolved@1000 diff | RMST diff (assays, negative = LazySP faster) | resolved only by LazySP / only by q2c / both / neither |
|---|---|---|---|
| alternate | +0.18 [+0.14, +0.22] | -6.5 [-53.5, +48.9] | 18 / 0 / 78 / 4 |
| forward | +0.18 [+0.14, +0.22] | -113.5 [-159.3, -59.0] | 18 / 0 / 78 / 4 |
| reverse | -0.29 [-0.35, -0.24] | +110.8 [+52.8, +181.8] | 0 / 29 / 49 / 22 |

Audit: `python -m baselines.lazysp audit` replays every shard from its saved assay log against the hashed source data
and a fresh core ledger: 300/300 shards, 0 errors (record equals source data, unique and contiguous assays, no assay after
the certificate, replayed status equals recorded status, routes and cuts pass full-data verification). Tampering
tests confirm the audit rejects an altered interval and a truncated log. Zero false certificates under the declared
conservative rule is a software-consistency fact, not empirical validation of enzyme behaviour.

### How to read this (important)

1. **The completion-rate gap is concentrated in a single problem.** All 18 episodes that only LazySP (alternate or
   forward) resolves are family B: 17 are VFVS->ALKG (saved q2c resolves 3/20 of them, LazySP 20/20) and 1 is VFVS->AIKG.
   On the 20 family-A pairs LazySP and q2c both resolve the same 16 and abstain on the same 4. Family B reuses four
   fixed targets across all 20 seeds, and LazySP's assay counts for them are nearly identical across seeds
   (e.g. AIKG 899-905, ALKG 816-820 for alternate), so the panel behaves like about 24 independent problems, not 100.
   The preregistered seed-cluster bootstrap does not account for this and its interval is too narrow. A
   **post hoc** repeat with 24 problem clusters (20 A seeds + 4 B targets; `exploratory_post_hoc.json`) gives
   resolved@1000 difference +0.18 with 95% interval [0.00, 0.51] and RMST difference -6.5 [-183, +209] (alternate); the
   completion advantage is not statistically established at the problem level.
2. **Assays-to-certificate is mixed, not uniformly better.** Per-problem medians (resolved episodes only, assays):
   VFVS->AIKG LazySP-alternate 905 vs q2c 557 (q2c faster); VFVS->ALKG 820 vs 675 on only the 3 q2c-resolved episodes;
   VFVS->CLKG 219 vs 660 and VFVS->VLKG 94 vs 148 (LazySP faster). Among episodes both resolved, alternate used fewer
   assays in 32, more in 44, tied in 2. The primary result is thus "no demonstrated assays-to-certificate advantage for
   alternate, and a completion-rate gain at the 1000-assay budget that comes from one hard target".
3. **Budget sensitivity.** The curves are step functions because most family-B episodes of a target resolve at the same
   count. At 750 assays q2c (0.70) is ahead of alternate (0.56); at 850 they are level; the +0.18 appears only for
   budgets >= ~950 (alternate); alternate is ahead at 100-500, behind at 750-800 and level at 850-900. Forward is
   ahead at every listed budget. Do not quote a single number without the budget.
4. **Selector matters, and Reverse is poor under this certificate.** Reverse spends assays next to the target, which
   likely need not join the forward closure that the shared ledger certifies (mechanism not separately tested); it resolved 0/20 of VFVS->AIKG and VFVS->ALKG and
   0 blocked cases. Forward (secondary, not the preregistered primary) needs fewer assays than alternate on most
   problems. We report all three and select none post hoc.
5. **Blocked cases.** Truth-blocked episodes are 8/100; LazySP alternate/forward and saved q2c each closed the same 5 of them (8 truth-closed). LazySP's
   native optimistic-infeasibility path (target side sealed first) was never triggered in the panel (0/300), so the
   fallback code is exercised only by fixture tests.
6. **Why q2c fails on ALKG is not established here.** A hypothesis (its GP surrogate and block-cost arbitration misrank
   the needed route) was not tested.

### What this does and does not show

* A plain, exact, preregistered LazySP-style baseline on the same oracle, panel and certificate matches or exceeds the
  saved q2c on every episode in resolved/unresolved terms (0 episodes resolved only by q2c for alternate/forward), at ~1 s of
  policy compute per episode. The original Q2C planner is therefore **not demonstrated to beat** a lazy path-search
  baseline; the original comparison lacked this baseline.
* It does not show LazySP is better in general: the evidence is 24 problems on one landscape and one budget, with one
  problem carrying the completion gap.
* The original claim "collective evidence arbitration helps" is separately untested here; collective rows are shown only as comparators.
* Not claimed: biological impossibility from `blocked`, a calibrated confidence level, GB1/other landscapes, ALDE
  comparison, GPU/LLM benefit, any prior-art novelty.

## Limitations and provenance

* Objective is the core conservative-interval route / no-such-route in the measured 20^4 graph (CONTRACT, semantics review).
* Node-query adaptation of edge-evaluation prior art; the papers' optimality/equivalence theorems are not claimed to transfer.
* Candidate-path caching is an admissible tie-break; informational check: forcing a re-search every iteration gave
  identical assay sequences on 9 real episodes (`baselines/replan_check.py`; tests cover 2).
* Saved q2c comparator = recovered original rows. Core's later rerun of q2c (`origin/work/core` 7f722cd) matches them on
  status and assays for 100/100 episodes (`artifacts/lazysp/results/crosschecks.json`).
* Seed-0 outcomes were visible at the runtime smoke test before the full run (seed 0 is part of the panel; smoke and panel
  shards are bit-identical in assay logs). No parameter changed after the smoke test (cap 450 s, never reached).
* `search.py`/`policy.py` are byte-identical to the preregistered commit `1412a6f` that produced the panel; later
  edits only added the audit, analysis extras and tests. Shard metadata records `code_commit` and a hash of `baselines/`.
* Core quirk to know when testing: `evolve.replay._truth_cache` is keyed by (start, kappa), so synthetic fixtures must
  clear it between landscapes (our tests do).
* Wall time: panel run 2026-10-31 01:28:45-01:39:38 PDT (before the Nov 1 DST change), 2 parallel scopes; summed task wall
  423 s. No GPU, no paid API, no messages sent. Model: Claude Sonnet 5.5 on the existing subscription; no metered charge known
  (CLI cost estimates are not subscription spend). Cost: unknown/none metered.
