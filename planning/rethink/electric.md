# Bioelectric / electric fabrication / cellular computation: go/no-go memo

Author: `delphi-rethink-electric` (Claude Sonnet 5.5, subscription; metered spend unknown). Written 2026-10-31 06:3x PDT, branch `work/rethink-electric`. Code: `experiments/rethink_electric/`, tests `tests/test_rethink_electric.py`, machine-readable record `tasks/results/rethink-electric.json`.
Labels: **observed** = measured by the Allen Institute / Cello authors; **model-derived** = computed by us from stated assumptions; **unknown** = not tested.

## Recommendation

**NO-GO as the headline entry.** The one direction with a real measurement chain (intracellular current injection in Allen Institute patch-clamp data) works as a retrospective check but reproduces a century-old law (Lapicque strength-duration), is not bioelectric tissue control, not electric-field control and not fabrication. The tissue-patterning, electric-field fabrication and cellular-circuit arms have no open dataset on which a prediction of ours could be rejected within the deadline. Use at most the small result below as a supporting "retrospective intervention check" panel if the director wants one; do not pitch it as new science.

## What was actually run (CPU only, no GPU, no external messages)

**Target.** 101 mouse cortical neurons (pre-registered every-19th rule over 1,920 mouse cells with NWB files; 1 cell dropped for missing input resistance). Calibration data per cell: Long Square sweeps only. Held-out stimulus class: the same cell's 3 ms Short Square pulse; target = geometric midpoint of the bracket (highest non-firing amplitude, lowest firing amplitude). Cells are the unit of replication. All raw NWB are hash-pinned in `results/cell_features.json` and were never modified.

**Predictors (all model-derived).**
- P0 population ratio to rheobase, leave-one-cell-out (the "straightforward current rule").
- P1 Lapicque strength-duration `I_rh / (1 - exp(-T/tau))`, no fitted parameter.
- P2 same with one leave-one-out tau multiplier.
- P3 LIF from independently measured spike threshold voltage, input resistance, tau, no fit.
- P4 leave-one-out regression on log rheobase and log tau.
- P5 the **released Allen GLIF LIF model** for the 49 cells that have one (closed form, no allensdk import).

**Results** (mean |log2 fold error| with cell-bootstrap 95% interval; lower is better):

| predictor | n | mean abs log2 err | within 1.5x | note |
|---|---|---|---|---|
| P0 ratio to rheobase | 101 | 0.74 [0.65, 0.84] | 45% | baseline |
| P1 Lapicque, no fit | 101 | 0.43 [0.37, 0.50] | 75% | beats P0 in 73% of cells; paired diff -0.31 [-0.39, -0.23] |
| P2 Lapicque + kappa | 101 | 0.45 | 68% | kappa=1.21 in every fold |
| P3 LIF from Vth, Rin, tau | 101 | 0.59 | 50% | systematic +0.6 log2 bias |
| P4 LOO regression | 101 | 0.35 [0.30, 0.41] | 81% | best, but needs the other cells |
| P5 released GLIF LIF | 49 | 0.82 | 24% | over-predicts by about 1.8x; **not** better than P0 on common cells (+0.07 [-0.10, 0.25]) |

The repeat-disagreement floor is small (median log2 spread between lowest-any and lowest-all-repeat firing amplitude 0.02, p90 0.13); the amplitude grid floor is 0.016. So the errors above are not measurement-grid artifacts, but 62 of 101 cells show repeat disagreement at the threshold amplitude and 18 are non-monotone, so a "threshold" here is a noisy edge, not an exact value. On the 38 clean-ladder cells the ordering is unchanged (median abs log2: P0 0.75, P1 0.42, P4 0.25).

**Decision-relevant version (robust intervention under uncertain parameters).** Choose a pulse amplitude with a cross-fit 90% margin from training-fold residuals. Coverage was 0.90 for all predictors (Wilson 95% 0.83-0.95). The **median energy (I²·T) needed** was 4.8x the lowest observed firing amplitude for the ratio rule, 2.25x for Lapicque, 2.0x for LIF-from-parts, 2.1x for regression, 2.6x for released GLIF (49 cells). Across 30 random fold splits the ranges are 4.7-5.2 / 2.2-2.3 / 2.0-2.05 / 2.0-2.1 / 2.4-2.6. So a mechanistic model roughly halves the stimulation energy needed for a covering amplitude **on this panel**, using only long-square data of the same cell. The 90% margin is a cross-fit quantile, not a distribution-free guarantee on a heterogeneous panel.

Figure: `experiments/rethink_electric/results/strength_duration.png`.

## Protocol amendments and data-quality findings (all made before any prediction was computed)

1. Sampling rate was hard-coded at 50 kHz; 44 of the first 102 files are 200 kHz. Now read per sweep.
2. Primary-session review: long-square rheobase had counted spikes up to 50 ms after step end. Now only positive steps with an on-step spike; rebound spikes are logged separately (5 cells have rebound; 0 cells had on-step spikes at non-positive current). Short-square window = pulse + 20 ms.
3. Threshold bracket made repeat-aware (see above); no cell is censored.
4. NWB units: 18 of 102 files carry conversion attributes 1e-3 (V) / 1e-12 (A) although the stored values are already SI. My first fix inferred scale from plausibility; the primary session then pointed to the official rule (AllenSDK `nwb_data_set.py`: apply `conversion` only for pipeline version >= 1.1 from `general/generated_by`; earlier files are already SI). **All 102 files are pipeline version 1.0, so no conversion is applied.** The >= 1.1 branch is implemented but not exercised by this sample, and was not cross-checked against the SDK (allensdk not installed). Plausibility is now only a flag; all 102 pass. Cross-check against the Allen API feature table: resting potential differs by median -0.004 mV, rheobase equal, input resistance median ratio 1.09 (p10-p90 0.95-1.43), and **my tau is about 0.84x the API tau** (different fit window; reported, not corrected).
5. Per-sweep QC flags (`ephys_sweeps.json`) were **not applied**: a limitation.

## Prior art and honest scope

- Strength-duration (Lapicque 1907; Weiss) is textbook. Our contribution would be a retrospective, per-cell, held-out-stimulus check on the Allen panel: a sanity result, not discovery.
- **Released GLIF training sweeps are unverified.** The released `neuron_config.json` carries no sweep list and the technical white paper was not retrieved, so P5 is a reference comparator and **not** claimed held-out. P0-P4 use only long-square features of the same cell and are held-out in stimulus class, but cell-level fits (P2, P4) are leave-one-cell-out.
- JAXLEY (Nature Methods 2025, doi 10.1038/s41592-025-02895-w; abstract read) already fits biophysical models to voltage recordings by gradient descent. A 2026 preprint, **jaxon** (doi 10.64898/2026.07.30.741846; abstract only) optimizes extracellular stimulation amplitude, waveform and electrode position through nerve-fibre cable models and checks against NEURON thresholds. bioelectrics (GitHub tlcdv, read by the coordinator) and BETSE (BSD-2) cover tissue-level simulators. Differentiable inverse stimulation design is therefore **not** novel.
- Our test is intracellular current injection in slices. It says nothing about extracellular electric-field control, ion-channel actuators in tissue, or fabricated material. Optimized waveforms beyond existing stimulus classes would remain predictions: no matching measurement exists.

## Three problems compared

| | Bioelectric control | Electric-field material organization | Cellular computation |
|---|---|---|---|
| Open data actually touched | Allen Institute Cell Types NWB (n=101 used; licence terms not retrieved); Prescott electrotaxis (CC BY-NC-ND, one field magnitude, not used here) | Sano 2010 thesis (SEM, qualitative, internal velocity inconsistency); 2025 AC-cellulose data only on request | Cello UCF `Eco1C1G1T1` (BSD-2): 20 NOR gates, 12-level cytometry histograms |
| Open model code | Jaxley (Apache-2.0), BETSE (BSD-2), AllenSDK GLIF | none validated | Cello (BSD-2) |
| Observable | spike threshold / firing (done); tissue pattern: none located | fibre orientation statistics: none quantitative | gate output per input; circuit output not retrieved |
| Comparator | rheobase ratio, released GLIF (done) | none possible | constant, refit Hill |
| Compute | about 20 CPU-minutes, no GPU | n/a | seconds |
| Experiment that could reject | done for stimulus-class transfer (Lapicque could have lost to the ratio rule; it did not). Tissue patterns: wet lab | wet lab: aligned fraction vs field, with replicate statistics | measured circuit outputs vs composed gates in new contexts: data not retrieved |
| Verdict | works but old law; no-go as headline | no-go, nothing computable | no-go, only trivial interpolation tested |

**Cello probe result** (`results/cello_gate_probe.json`, observed histograms + Hill refit): refitting a Hill function on even input levels predicts the held-out odd levels of the same gate to a median 0.066 log2 (about 5%), far better than a constant (1.98). That is within-ladder interpolation of a smooth function and tests nothing about circuit composition or new host/medium conditions. The UCF's published Hill parameters disagree with the raw histogram means by about 1.6 log2; this is almost certainly a unit/normalization mismatch I did **not** resolve, so that comparator was not used. Circuit-level measured outputs (Nielsen et al. 2016 SI) were not retrieved.

## Delphi claim reuse (actual, and its limits)

- Searches of Delphi (`results/delphi_search_log.json`, 18 queries on local source) found **no claim on membrane potential, ion channels, excitability or strength-duration**. No Delphi claim touched the patch-clamp experiment above.
- The only operational reuse is `turing-ddi` through the existing source-pinned `turing_scope` adapter as a scope gate for a "gap-junction voltage patterning" arm: for each of the 101 cells, `a = -1/tau_m` (measured, rounded to 0.01 ms) is the voltage self-derivative at rest; the partner's relaxation (3 values), cross-coupling (3 values) and diffusivity ratio (3 values) are declared and swept. Result (model-derived): **2,727 of 2,727 requests stable**, because the claim's inequality needs `S = a D_w + d D_V > 0`, impossible with a<0 and d<0. Ablation: a hypothetical regenerative `a > 0` (not measured) gives `linearly_unstable` in 101 of 101 requests (modes 3-7); a strictly voltage-only coupling (D_w = 0) is refused by the adapter's own precondition (`both > 0`). Decision changed: do not build a Turing-from-voltage patterning module around resting passive membranes; a self-activating partner or a second diffusing species must be declared.
- Honest weakness: the conclusion follows from the sign of two diagonal entries and a one-line algebra step you can do without Delphi; no counterfactual claim-free pipeline was run; single-cell tau is not tissue coupling; 1-D Neumann linear analysis only. This is scope-checking, not a decision that depends on Delphi.

## Multi-agent contribution

For this candidate a **measured** contribution would be seeded-defect detection: inject known defects into the feature extractor (wrong sampling rate, rebound counted as rheobase, ignoring repeats, wrong unit rule) and measure detection rate of a single Sonnet author vs author plus an independent Sonnet reviewer without access to the author's reasoning, on the same code. Everything needs only Claude Sonnet. What actually happened here is only an anecdote (n=3, not controlled): independent notes from the primary session caught the rebound window, repeat disagreement/censoring, and the official conversion rule, and my own check caught the sampling-rate bug. All were found before any prediction was computed; no benefit is claimed.

## Claims-as-tests (director's new candidate), from this vantage

It addresses the weakness of every electric arm: Delphi has no claims about channels, membrane or excitability (searches above), whereas Thompson/pop-gen math claims exist in volume and have open data (Tallo). Ranking for the "existing claims change a decision" criterion: Claims-as-tests > electric. Whether it is only known allometry and what a collective adds is the critic's question; I did not test it.

## Limitations and next steps

- Panel is one lab's mouse cortex slice recordings; the stimulus classes of 101 cells are not independent biological targets in the sense of different experiments.
- P4/P2 use the other cells to fit; P1/P3 use none.
- Raw NWB licence/terms not retrieved; committing derived per-cell feature tables is flagged for review before any public release.
- If the director wants this panel: apply per-sweep QC flags, add a cross-check against the SDK on a version >= 1.1 file, and extend to the ramp and noise classes (not done).
- If not: nothing here blocks the core. Available for an independent-validation `/goal` on the selected candidate.
