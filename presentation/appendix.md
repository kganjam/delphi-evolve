# Appendix — limitations, all arms and the LazySP follow-up (not slide material)

Built 2026-10-31 02:04 PDT from artifacts commit `fcbc98f9f6206a49fe36d89b0c080867437ef859`. Every number below is read from the files named in `deck.provenance.json`.

## Strong LazySP-style follow-up (complete, independently audited)

* Result files (read from `artifacts/lazysp/results/`): summary.json, table_primary.csv, episodes.csv, exploratory_post_hoc.json, audit.json. 3 variants x 100 episodes, none missing. Audit: 300 shards replayed from their saved assay logs against the source data and a fresh core ledger, 0 errors. This deck re-derived resolved@B, restricted-mean assays, status counts and the paired only-LazySP / only-Q2C / both counts from `episodes.csv` and the core replay before rendering; any mismatch rejects the build.
* Provenance of the idea: LazySP (Dellin & Srinivasa, ICAPS 2016) and Bayesian active edge evaluation (Choudhury et al., IJCAI 2018). The node-query adaptation (assaying a vertex instead of evaluating an edge) is an existing adaptation of that prior art, not our algorithmic invention. The original directed-Hamming frontier policy was a weak comparator to LazySP.
* Timing of the protocol: the follow-up was preregistered before its new baseline episodes ran, but after the original study (so the original panel's outcomes were known). Primary selector: alternate; forward and reverse were declared secondary. Post hoc rows are labelled as such.
* Paired alternate minus saved Q2C (100 episodes): resolved@1000 +18 pp [+14, +22] (preregistered seed-cluster bootstrap, 20 clusters); 18 episodes only LazySP, 0 only Q2C, 78 both, 4 neither. Restricted-mean assays -6.5 [-53, +49]: includes 0.
* Where the gain sits: the 18 LazySP-only episodes by endpoint pair are VFVS→AIKG: 1, VFVS→ALKG: 17. Four fixed published-parent targets recur across 20 seeds, so the panel behaves like about 24 independent problems. A POST HOC problem-cluster bootstrap (24 clusters; exploratory, not preregistered) gives resolved@1000 +18 pp [+0, +51] and restricted-mean assays -6.5 [-183, +209]. The completion advantage is not established at the problem level. Budget sensitivity: at 750 assays Q2C is ahead of the alternate selector, so quote any figure with its budget.
* Conclusion kept: the original Q2C planner is not demonstrated to beat a lazy path-search baseline; the old 78-versus-32 headline (Q2C versus our own directed frontier) lacked this baseline. No claim that LazySP is generally better, no calibrated confidence, no other landscape, no biological impossibility from a `blocked` result.

| follow-up arm | status | @100 | @250 | @500 | @750 | @1000 | restricted-mean assays | open / blocked / unresolved |
|---|---|---|---|---|---|---|---|---|
| lazysp_alternate | preregistered primary | 27% | 50% | 55% | 56% | 96% | 476.6 | 91 / 5 / 4 |
| lazysp_forward | preregistered secondary | 29% | 54% | 55% | 96% | 96% | 369.6 | 91 / 5 / 4 |
| lazysp_reverse | preregistered secondary | 26% | 27% | 49% | 49% | 49% | 593.9 | 49 / 0 / 51 |

## Not part of this release (no benefit claimed)

* **GPU-prior policy ablation** (replay with the ESM2 prior as input): not available in this release. The prior's agreement with the measured data was computed (weak Spearman) but its effect on assay decisions is untested; a model-size ablation is in progress on another branch and nothing from it is claimed here.
* **ALDE** (active-learning-assisted directed evolution) was not run; it is the closest prior art on this landscape.

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
* Not kernel-checked: the individual decisions of the 1,100 core replay episodes and the 300 LazySP follow-up episodes (the latter are audited by replay against a fresh ledger, which is not a Lean proof); source/nanopub claims do not become verified biology because Lean compiled.
* Turing-domain example (`artifacts/turing_scope/`): two existing Delphi records (turing-ddi, turing-wavelength), source-pinned by content hash, with a requester-declared Jacobian J = [['1', '-2'], ['2', '-3']], D_u = 1, D_v = 10, 1-D zero-flux (Neumann) domain. L = pi: stable, no admissible unstable mode although a continuum instability band exists; L = 2 pi: linearly_unstable at n = 1 (q = 1/4, determinant -1/8, negative). Exact rational check; 2001 modes cross-checked in floating point, modes beyond that covered by the analytic tail rule. Lean Lean (version 4.35.0 compiled the parameterised dispersion algebra, the infinite-mode tail and the instantiation; 4/4 witness mutants behaved as expected and 2/2 generic-law mutants were rejected. Lean does not show eigenvalue/Routh-Hurwitz equivalence, the PDE, or any biological pattern; the fixed point is declared, not measured. Evidence type: model-derived.

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
