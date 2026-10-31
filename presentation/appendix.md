# Appendix — long limitations and pending items (not slide material)

Built 2026-10-31 01:49 PDT from artifacts commit `fdf01b5efce38a327fadb078c4f8744c15363e82`. Every number below is read from the files named in `deck.provenance.json`.

## Pending at render time (no benefit claimed)

* **Current strong LazySP-style baseline** on the same 100 episodes per policy: pending, not complete at render time; no benefit is claimed. The worker's branch records a preregistration and a seed-0 smoke test only. Until it is complete, query-to-certify (Q2C) is **not** claimed to beat a LazySP-style policy; LazySP and BAEE are prior art for query-efficient path evaluation.
* **GPU-prior policy ablation** (replay with the ESM2 prior as input): pending, not complete at render time. The prior's agreement with the measured data was computed (weak Spearman) but its effect on assay decisions is untested.
* **Roadmap only:** an optional second-domain Lean example (Turing-model applicability check) is in progress on another branch; nothing from it is claimed here.

## All arms, certified fraction of 100 episodes (family: all)

| arm | status | @100 | @250 | @500 | @1000 | mean assays (restricted) @1000 | false certificates |
|---|---|---|---|---|---|---|---|
| random | original (pre-declared) | 4% | 7% | 14% | 21% | 877 | 0 |
| greedy | original (pre-declared) | 3% | 7% | 7% | 8% | 934 | 0 |
| uncertainty | original (pre-declared) | 2% | 5% | 8% | 13% | 931 | 0 |
| directed | original (pre-declared) | 27% | 30% | 30% | 32% | 709 | 0 |
| q2c | original (pre-declared) | 24% | 43% | 48% | 78% | 483 | 0 |
| collective_shared | original (pre-declared) | 24% | 47% | 49% | 78% | 467 | 0 |
| collective_isolated | original (pre-declared) | 19% | 39% | 58% | 77% | 485 | 0 |
| q2c_nomodel | POST HOC | 7% | 16% | 96% | 96% | 378 | 0 |
| collective_shared_c | POST HOC | 7% | 11% | 59% | 96% | 518 | 0 |
| collective_isolated_c | POST HOC | 11% | 40% | 54% | 65% | 525 | 0 |
| collective_shared_rr | POST HOC | 23% | 48% | 50% | 78% | 465 | 0 |

Arm names: `collective_shared_c` = shared specialists without the GP; `collective_isolated_c` = isolated specialists without the GP; `q2c_nomodel` = single planner without the GP; `collective_shared_rr` = shared evidence with round-robin proposals. The no-GP arms were selected after observing the original run and are not pre-registered winners.

## Replay limitations

* 20 seed clusters; 100 episodes per policy = 4 published-parent targets (AIKG, CLKG, VLKG, ALKG) repeated across 20 seeds (80 cases) + 20 seed-chosen family-A pairs. Not 100 independent biological targets. Bootstrap intervals resample seeds and are descriptive, not coverage claims.
* 0 false certificates is guaranteed by construction (certificates are computed only from revealed labels) and was re-checked against full data: structural consistency, not biological accuracy.
* Specialists are deterministic software objects in one process, not independent agents. Isolated arms are not fully isolated: a duplicate request is answered from the data specialist's ledger at zero cost. Shared vs isolated also differs in arbitration. No collective uplift over a single planner was found.
* Truth is reachability in the measured graph under the declared interval rule (benchmark truth), not biological truth. `blocked`/`no route certifiable` is not the Lean no-path theorem.
* Of the original 700 episodes, 175 intact rows were kept and 525 missing rows were recovered from saved assay histories without re-running policies (recovered rows have unknown wall time); the core worker separately re-ran the panel after a bug fix. The 400 post hoc episodes were run afterwards. Query traces are committed under `artifacts/core/replay/queries/`; each arm's per-episode paid-query count equals `assays` in `episodes.csv` (checked by `validate.py`).
* The noise-bin standard deviations are fit on all replicates: κ is a transductive sensitivity, not held-out validation.

## Lean scope

* Kernel-checked: generic route-soundness and cut theorems (conditional on assumed interval containment); one VFVS→AIKG κ=2 seven-node route with an exact raw-CSV recompute (7/7); a swapped-route mutant is rejected.
* Not kernel-checked: the individual decisions of the 1,100 replay episodes; source/nanopub claims do not become verified biology because Lean compiled.

## Claim runtime limits

* Two existing Delphi claims (Kimura, Fisher) with hand-authored, hash-pinned adapters; authored and reviewed by the same model, not by a population geneticist. The Kimura 1962 PDF could not be retrieved; the diploid reading was checked against an exact Wright–Fisher chain.
* Same-context reuse equals an ordinary cache (identical avoided requests). Fault-injection counts are synthetic software fixtures, not savings and not biology. The diffusion formula is up to 139% off for small deleterious mutants (s=-0.05) in the exact-chain benchmark.
* A recorded execution, not a live browser service. No claim that these adapters improve the TrpB route benchmark.

## GPU / compute

* Zero-shot ESM2 prior Spearman 0.17-0.18 vs measured growth (159,129 genotypes); adds no detectable value over one-hot site identity in a random-split ridge check. Model output, not measurement.
* Job aijob-e00whrj05xvrnbfxtx on Nebius AI Cloud (project workshop-30-10, eu-north1), 1x H100 80GB HBM3; wall 2026-10-31 00:41:48-01:02:11 PDT. Predictions never discharge an empirical premise.
* OpenResearch: a local CPU analysis actually ran (`artifacts/gpu/orx/receipt.json`); no hosted OpenResearch service and no biological experiment.

## Spend and model

* Deck authored with Claude Sonnet 5.5 on an existing subscription; metered API charge, if any, is unknown (CLI cost estimates are not subscription spend). No GPU used by this worker.
