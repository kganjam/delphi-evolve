# LazySP-style baseline for TrpB query-to-certify

Status: **protocol preregistered before any panel episode was run** (see "Preregistration").
Results sections are appended below only after the preregistered run (see "Results", currently empty).

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
(not yet run)
