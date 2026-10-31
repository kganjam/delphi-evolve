# Integration findings (integrator, work/integration)

Evidence for each item is in tasks/results/integrator.json. Times Seattle PDT, 2026-10-31.

## F1 "blocked" means two different things (must not be conflated)
* core (`evolve/replay.py`, `evolve/demo.py`): blocked = no *certifiable* route in the measured subgraph, i.e. no chain of edges with `lower[v] >= upper[u]`. Edges whose intervals merely overlap are dropped. Example shipped in `artifacts/core/certificates/cut_HTGR_GTVN_kappa2.json`: closed set {HTGR}; of 76 neighbours only 6 are certified lower, 70 overlap or exceed. A non-decreasing route *could* exist inside those intervals.
* proof (`lean/DarwinBridge/Core.lean` `blocked_cut_sound`): blocked = every neighbour of every set member is in the set or `hi v < lo u`; unmeasured neighbours reopen the cut. Soundness: no non-decreasing path exists for every assignment inside the intervals.
* Consequence: core's "blocked" is "not certifiable as open", compatible with benchmark truth under the declared edge rule, but it is NOT covered by the Lean no-path theorem. Pitch, blog and site must say "no certified route" for core results and reserve "Lean-certified blocked" for proof's certificates. Do not call HTGR->GTVN certified impossible.

## F2 core and proof use different interval models
core: mean of two replicates +/- ceil(kappa*sd_bin/2) with kappa=2 (read-count bins). proof: replicate envelope +/- uniform delta (0 or 0.005). Lean's `obsBounds` takes min/max of two table values, so any integer [lo, hi] is expressible as a table row with delta=0. The core kappa=2 open route can therefore be Lean-checked unchanged; until that is done, say the benchmark's decision rule is not the Lean-checked one.

## F3 packaging
pyproject.toml did not declare rdflib (evidence tests) or scipy (core models); fixed in integration. Clean venv: 40 passed.

## F4 privacy
scripts/fetch_data.py sent a personal contact email in its User-Agent; replaced by the repo URL. Do not reintroduce.

## F5 site
Mobile (390 px) overflows by 21 px because `section.map-card` is 411 px wide; site requests data/demo.json and logs a console 404 when absent.

## F6 wording that must follow F1 (docs/pitch*, docs/blog*, docs/video-storyboard*, site Decision panel)
* docs/pitch.template.md says "a closed set with no admitted exit rules out a path in the declared graph". The Lean theorem requires every exit edge to be *certified descending* (`hi v < lo u`), and unmeasured neighbours must be inside the set. "No admitted exit" (overlapping intervals count as not admitted) is weaker and is NOT what Lean proves. Say: "a closed set whose every exit is certified lower rules out any non-decreasing path, for every assignment inside the intervals".
* Site/pitch "BLOCKED" from the browser or core replay = "no route can be certified from the measurements and the assumed bound". Use that phrase, or "Lean-certified blocked" only for artifacts/proof/trpb_blocked*.json (and bridge receipts).
* The Lean-checked artifacts are: proof's three/four certificates (delta 0, 0.005, replicate envelope) and integrator's bridged core kappa=2 route (artifacts/integration/). Do not say the replay benchmark's decisions are Lean-checked; only the open route certificates are.

## F7 collective: what the shared-vs-isolated comparison can and cannot say
* Specialists (`evolve/collective.py`) are deterministic software objects in one Python process, not live LLM agents; scheduling is fixed code. Say so every time "collective" or "agents" is used for runtime behaviour.
* Shared and isolated arms differ in TWO ways, not one: evidence visibility (global ledger vs private ledgers) AND arbitration (cost comparison between open-route and cut plus a critic re-pricing step in shared; strict round-robin turns with no cost comparison in isolated). A shared-vs-isolated difference therefore cannot be attributed to evidence sharing alone. The isolated arm also leaks: a duplicate request is answered free from the pooled ledger. The compared quantity is assays-to-certificate under matched oracle budget.
* No decentralised-agency or "collective beats single policy" claim is made unless the paired table (table_paired.csv, seed-cluster bootstrap) supports it, and even then only against core's own `q2c`/`directed` baselines, not ALDE.

## F8 independent verification of the benchmark truth
`scripts/independent_truth.py` (no evolve/ import) reproduces core's kappa sweep VFVS->AIKG at all 8 kappa values (open flag, closure size, shortest route length).

## F9 URGENT (core): replay shards for seeds 5-19 have EMPTY `rows`; tables built from them are 5-seed, not 20-seed
Found 2026-10-31 00:3x PDT by the integrator.
* `evolve/replay.py::run_shard` at bcc0729 (and the uncommitted working copy of the core tree at the time) builds `out` for each episode but never executes `rows.append(out)` (lost when the `+prior` hook was added). Shards written after that edit have `"rows": []` but keep `qlogs`.
* Evidence: of 140 shards in `artifacts/core/replay/shards/`, 35 (seeds 0-4, all 7 policies) have 5 rows each; 105 (seeds 5-19) have 0 rows. `python -m evolve summarize` on them gives `episodes: 175`, `seeds: 5` in `summary.json` and 25 episodes per policy in `episodes.csv`, although the protocol says 20 seeds / 100 episodes per policy. Any quoted rate such as "0.76 / 0.92 / 0.95 vs 0.75" is a 5-seed number (family A n=5, family B n=20 episodes from 5 seeds), and the seed-cluster bootstrap is over 5 clusters.
* Fix (one line, applied on work/integration): insert `rows.append(out)` right after `out, qlog, other, log = run_episode(...)` in `run_shard`. Verification: with the fix, `run_shard(("/tmp/rs","random",3,2.0,1000))` reproduces the existing seed-3 shard exactly (5 rows equal ignoring `wall_s`, query logs equal), so the pipeline is deterministic and nothing else is wrong.
* Required: delete the 105 empty shards (rows == []) and re-run seeds 5-19 for every policy including any new control (e.g. `collective_shared_rr`) with the fix, then re-summarize. Do not publish numbers while `summary.json` says `seeds` < 20. Add a guard in `summarize.run`: raise if any shard has zero rows or if episodes != policies x seeds x 5.
