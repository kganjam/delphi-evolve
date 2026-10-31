# Research-electric: bioelectric fields, electrobiofabrication, ion-channel actuators

Author: research worker, model = subscription Claude Sonnet 5.5 (repo-required). Metered spend: unknown, not inferred from CLI.
Run: first pass 2026-10-31 00:56 to 01:03 PDT, second pass 01:04 to 01:14 PDT, Seattle (clock-read, not estimated). Branch `work/research-electric`. No GPU, no paid service, no messages sent, no agents spawned.
Machine-readable companion: `artifacts/research/research-electric.json` (every source with how far I read it).

Labels: **[READ]** I read the body or raw data. **[ABS]** abstract or search snippet only. **[INF]** my inference. **[PILOT]** my quick count on a real file; descriptive, not a benchmark result.

## 1. Bottom line

1. **The headline result you pointed at is real but is not what the title suggests.** Sano, Rojas, Gatenholm and Davalos (Ann Biomed Eng 38:2475, 2010) used an externally applied DC field of about 0.15 to 0.45 V/cm to push whole *Acetobacter xylinum* cells by electrokinetic drift while they spun cellulose. The cells do the weaving. Nothing there is nanoscale field patterning, and nothing is endogenous bioelectricity. The alignment evidence in the thesis version is SEM images; I found no orientation statistics (§2).
2. **Strongest bounded project: a held-out-position benchmark for "does the variant still reach the surface but fail as an actuator?" on ion-channel deep mutational scans** (KCNE1, Kir2.1/KCNJ2, optionally KCNH2 and SCN5A fragments), with a conditional Lean certificate on the physical readout. Real data are public and CC0 or MIT. A built-in negative control exists: the same variants were assayed for surface expression and for function.
3. **Honest weakness.** The existing readouts are proxies (membrane-potential dye, a cell-depletion assay), not voltage-gating curves. Nobody should call the result "predicts voltage gating". A held-out result would be modest and incremental; ProteinGym already hosts these assays (§4).
4. **Field-control (electrotaxis) is the only real applied-field perturbation data I found, and it is too thin and already contested prior art** for a headline (§3). I rank it second, as a small experiment-design panel.

## 2. Strongest existing result and what it does and does not show

**Sano et al. 2010.** Chalmers record read [READ: abstract, no data links]. The journal PDF is paywalled (Springer sent an auth redirect), so the numbers below come from Sano's Virginia Tech master's thesis `hdl.handle.net/10919/76975` [READ: full text, 53 pp; "In Copyright"; thesis, not the paper, and the two may differ].

- Fields: DC, 0.15, 0.303 and 0.45 V/cm in micro-growth chambers (thesis Figs 17 to 19). Culture medium conductivity about 7.5 mS/cm.
- Mechanism evidence: measured electrokinetic cell velocity 1.37 to 7.47 µm/min over 2 to 30 V/cm (thesis Fig 13, which is non-monotonic with large error bars). Above about 400 V/cm dielectrophoresis traps cells and **cellulose production stops**. Native extrusion is quoted as about 2 µm/min.
- The medium makes oxygen by electrolysis; above about 1 V (0.67 V/cm) cellulose forms at the anode. That is a second, chemical channel by which the field acts, separate from cell drift.
- Alignment evidence: SEM images at three fields. Text: aligned groups at 0.303 V/cm, "stranded" network at 0.45 V/cm, nothing visible at 0.15 V/cm. A keyword search of the thesis found no histogram, FFT, orientation distribution or replicate count. The author himself says the effective window is narrow and a 20% electrode-spacing error changes the field by a similar amount as the 0.33 to 0.45 V/cm step.
- **Unreconciled inconsistency [READ + INF].** The thesis text quotes a *calculated* electrokinetic velocity of 4.2 to 12.6 µm/min for 0.15 to 0.45 V/cm. Linear scaling of its own measured values (1.37 µm/min at 2 V/cm) gives roughly 0.1 to 0.3 µm/min, about 40 times smaller; Fig 13's two panels also carry different axis exponents (x10^-8 vs x10^-6 m/s). The mobility formula is an image I could not read in the text layer. The mechanism story "drift speed approaches extrusion rate" therefore is not supported by the thesis's own measured mobility. This could be a typo or a different medium; it should be checked against the journal paper before anyone cites the mechanism.

**What this implies physically [INF].** Applied DC fields work by (a) moving charged cells, (b) electrolysis and pH or oxygen gradients at electrodes, and (c) dielectrophoresis near geometry. In ionic medium the field is screened over roughly a nanometre of the membrane (Debye length about 1 nm at physiological ionic strength). Transmembrane voltage therefore does not imply long-range nanoscale patterning. The achieved resolution is the cell's path, micrometres, not molecular organisation.

**Comparison of routes** (what sets the pattern, resolution, and what is measurable):

| Route | Pattern set by | Length scale | Closest evidence |
|---|---|---|---|
| Electrochemical deposition (electrobiofabrication, chitosan pH gradient at an electrode) | Electrode geometry and local pH | µm to mm | Payne, Bentley, Rubloff groups; 2020 *Biofabrication* review [ABS, search excerpts] |
| Dielectrophoresis | Field gradient and particle polarisability | µm | Sano thesis; DEP traps cells above about 400 V/cm [READ] |
| Cell alignment / secretion (electrotaxis, contact guidance) | Cell migration bias | cell size | Sano 2010; electrotaxis data §3 |
| Actual ion channels | Membrane potential and ion flux inside a cell | nm to µm for the channel, cell for the effect | §4 |

## 3. Electrical control of living cells: what exists

- **Electrotaxis with real data.** Prescott, Zhu, Zhao, Baker, bioRxiv 2021.01.22.427762 v2 [READ via r.jina.ai, 429 on direct]. Stochastic single-cell model, four hypothesised field effects, Bayesian sequential calibration, and a **held-out prediction of the field-reversal window (180 to 300 min)**. It names model-predictive control of fields as future work. Code `github.com/tpprescott/electro` (GPL-3.0). Data: Zenodo 10.5281/zenodo.4749429 [READ: metadata and two CSVs], licence **CC BY-NC-ND 4.0**, 2.9 GB.
  - **[PILOT]** `Ctrl-1.csv`: 27 tracks x 61 points (5 min interval, 5 h). `200mV-1.csv`: 26 tracks x 61. Columns `TID,PID,x,y`, pixel units. sha256 in the JSON.
  - The deposit's notes file lists 50 mV/mm fields as well, but the file list holds only Control and 200 mV: **one nonzero field magnitude**, two replicates each. No dose-response, so choosing a field magnitude cannot be validated on it.
- **Closed-loop and predictive work already exists** [ABS]: deep-learning directedness predictor (Sci Rep 2022, s41598-022-13925-4); neural-network feedback controller steering macrophages, in silico then in vitro (Bioengineering 2025, PMC12292985). An electrotaxis controller is not novel.
- **Ciliate dose-response data.** Daul, Lemloh, Hörning, New J Phys 24:053040 (2022); DaRUS 10.18419/darus-2827 (CC BY 4.0) with raw `.czi` videos per field strength [ABS; record not opened]. Multi-field, but a protist, raw video, and needs a tracker.
- **DART electrogenetics.** Huang, Xue, Buchmann, Teixeira, Fussenegger, Nature Metabolism 2023 [ABS: ETH record and press only; full paper not read]. DC at 4.5 V for 10 s per day through needle electrodes produces reactive oxygen species, which activate an NRF2 promoter. That is **electrochemistry at electrodes, not a transmembrane-voltage actuator**, and the outcome data are mouse data I would not reuse beyond citation.
- **Engineered excitable tissue.** Kirkton and Bursac, Nat Commun 2011; Nguyen et al. 2016; Zhang, McNamara, Werley, Cohen, Phys Rev X 2016 [ABS]. **"SHREAD": two searches returned nothing under that name. Unresolved; I did not make it up.** Public raw wave data not located.
- **Simulators.** BETSE (Pietak and Levin 2016, Front Bioeng Biotechnol; BSD-2-Clause per GitHub API). Brodsky and Levin (ALIFE 2018) search simulator space with a genetic algorithm [ABS]; I found no differentiable BETSE. Jaxley (Deistler et al., Nat Methods 22, 2025; Apache-2.0 [READ]) is a differentiable, GPU-parallel simulator that already reproduces NEURON on Allen Cell Types Database neurons and fits electrophysiology.
  - **I found no measured bioelectric-pattern dataset that BETSE has been inverted against.** Inverting BETSE on simulated patterns would be generated data posing as measurements, so it is out.

## 4. Ion channels as actuators: the dataset that works

Prior notes (binder-bioelectric-actuator.md and voltage-gated-channel-binder-candidates.md) say designed binders against channels are already published (ELIXIR, NB5, NB1.3, Depiv2). I took that as a lead only and did **not** re-verify those papers. I avoid de novo design entirely.

Paired expression and function assays exist, listed in ProteinGym's `reference_files/DMS_substitutions.csv` [READ; ProteinGym code MIT]:

| Assay | Variants | Readout (as stated by authors) |
|---|---|---|
| KCNE1 Muhammad 2023 expression / function | 2339 / 2315 | HA-tag surface level / cell depletion with gain-of-function KCNQ1 |
| KCNJ2 (Kir2.1) Coyote-Maestas 2022 surface / function | 6917 / 6963 | antibody surface / FLIPR membrane-potential dye on steady-state resting potential |
| KCNH2 Kozek 2020 | 200 (residues 545 to 555) | trafficking (ProteinGym label says "Voltage"; check) |
| SCN5A Glazer 2019 | 224 (residues 1621 to 1632) | triple-drug survival, a surrogate for dysfunction |

[READ] KCNE1: Genome Med 2024 (PMC11138074), MaveDB `urn:mavedb:00000674-a-2` (trafficking) and `-b-1` (function), **CC0**, per-variant score, SD, SE, CI and category. Code BSD-3-Clause. Functional scores correlate with prior electrophysiology at rho = -0.64 and with AlphaMissense at rho = -0.62 (authors' numbers). [READ] Kir2.1: eLife 76903 (PMC9273215). Authors say function fitness "is the combination of surface expression … and functional properties", that function is unimodal because the dye has lower dynamic range, and that the assay measures steady-state resting potential. Data SRA PRJNA791691, source data and code on GitHub (MIT). Replicate Pearson 0.85 to 0.94 (surface).

**[PILOT] real-data check on the KCNE1 MaveDB files** (CSV sha256 in the JSON; missense only; MaveDB categories as supplied; not a benchmark):

- 2415 missense variants have both a trafficking and a function score.
- **Spearman(surface score, function score) = 0.062.** Surface expression carries almost no rank information about function for this protein.
- Cross-tab (trafficking category vs function category, as supplied): of 173 variants with function "Loss", 96 have reduced trafficking (Loss, PartialLoss or PossibleLoss), 19 "Normal", 58 gain-type (42 "Gain", 16 "PossibleGain"). Of 406 with function "PartialLoss", 138 have reduced trafficking, 100 "Normal", 168 gain-type. Combined (Loss plus PartialLoss, 579 variants), 345 are not trafficking-impaired by these labels, but for strict "Loss" a slight majority (96 of 173) are. That is directionally compatible with the authors' statement that most deleterious variants act through gating rather than trafficking, but the split depends on how categories are lumped. My category lumping differs from theirs (they report 152 of 574 loss or partial loss with reduced surface expression), so do not compare the percentages.
- Leave-one-variant-out position-mean for function (uses the same position's other variants): **Spearman 0.695, n = 2413.** This is a ceiling for "position matters", not a held-out-position baseline.
- **Cheap held-out-position baseline** (mean function of variants at neighbouring positions within +/-1, 2, 3 residues, excluding the held-out position; 127 positions): **Spearman 0.576, 0.597, 0.604** with position-bootstrap 2.5 to 97.5 percentile spreads of about 0.51 to 0.64, 0.54 to 0.64 and 0.55 to 0.65 (200 resamples, seed 0; an empirical spread, not a formal confidence level). For scale, the KCNE1 authors report AlphaMissense at |rho| = 0.62 against function. **A language model therefore has to beat roughly 0.60 under position holdout, which is a hard bar and makes a null result likely.** Caveat: KCNE1 is only 129 residues, so neighbours are dense; Kir2.1 (428 residues) may differ.
- Reproduce: `artifacts/research/research-electric-kcne1-pilot.py` (stdlib only, run under the systemd-run caps) writes `artifacts/research/research-electric-kcne1-pilot.json`.

### 4b. Prior art found in the second pass (changes the ranking of novelty)

- **KCNQ1 landscape, medRxiv 2025 (PMC12724399)** [READ: body of the PMC mirror]. Four multiplexed assays, 13,403 variants, separating trafficking, gating and dominant-negative effects; surface abundance and function in variant-only and heterozygous conditions; AlphaMissense vs function rho = -0.49 with a set of discordant variants; licence CC BY 4.0. Data are "in the supplemental files and will be deposited in MaveDB … upon paper publication"; analysis code `github.com/GlazerLab/KCNQ1_MAVE` (no licence reported by the GitHub API). **This is a larger and more mechanism-resolved dataset than KCNE1, and the authors already compare function scores with AlphaMissense. It is also the only set I found that pairs multiplexed scores with measured V1/2 shifts, so it should be the primary Channel Bridge dataset instead of KCNE1.** The Europe PMC supplement archive (11 MB, second attempt completed) holds `media-2.xlsx` [READ: sha256 `ed94af00...3c73e45`]: **File S1** = 13,403 variants (12,223 missense, 544 synonymous, 636 nonsense) with trafficking, function, heterozygous trafficking and heterozygous function scores plus SEMs; **File S2** = 378 literature patch-clamp rows from 49 papers (281 distinct mutations; Xenopus, CHO, HEK293, mixed) with V1/2 of activation, shift from wild type in mV, normalised peak current and trafficking; **File S3** = 121 patient-linked rows. Preprint licence CC BY 4.0; I did not check the supplement's own licence line.
  **[PILOT, `artifacts/research/research-electric-kcnq1-pilot.py`]** 178 mutations have both a literature delta-V1/2act and MAVE scores (one median per mutation). Spearman of signed delta-V1/2act against the MAVE function score is -0.18 (n = 165) and against trafficking -0.01 (n = 174); using absolute shift, -0.09 and -0.09. Of 51 mutations with |delta-V1/2act| of at least 10 mV, 26 have a function score of at least 0.75 (WT-like by my arbitrary illustration cut). **Descriptively, the multiplexed function score is a weak and noisy proxy for measured activation voltage shift**, which is exactly the "structure or MAVE confidence is not voltage-gating function" distinction. Caveats: literature rows are heterogeneous in cell type, protocol and KCNE1 co-expression (not controlled here); 10 mV and 0.75 are not validated thresholds; no held-out evaluation; n = 178 is small.
- **PNAS 2026 "Classification models for KCNQ1 variants distinguish functional and trafficking effects"** (doi 10.1073/pnas.2537217123) [ABS only; PNAS returned 403 and the r.jina.ai route returned a Cloudflare challenge; no preprint copy found]. By title and search snippet it builds classifiers for electrophysiology-derived and trafficking properties of KCNQ1. **This is close prior art for the Channel Bridge question; I could not read it.** Until it is read, Channel Bridge must not claim to be the first to separate function from trafficking in a predictor.
- **Huang-lab benchmark of 61 KCNQ1 variants** [ABS]: trafficking loss is the most common cause of loss of function, and predictor accuracy depends on mechanism with a reliance on conservation.
- **IonBench** (Owen and Mirams, PLOS Comput Biol 2025) [ABS] benchmarks optimisers for ion-channel current models on simulated data; it does not address protocol selection. The research-synthesis branch's `bioelectrics` MIT package (read there, not by me) covers tissue-level intervention optimisation.
- **Baddam et al. 2025** (*Komagataeibacter xylinus* in AC fields, Oxford Open Materials Science itaf007) [READ: first 100k characters]. DEP trapping at 5 Vpp, 250 kHz to 10 MHz; cellulose at 750 kHz with 1, 2, 5 Vpp (modeled maxima 11.6, 21.5, 54 kV/m), fluorescence up more than 35% at 2 and 5 Vpp, n = 3; a 7 Vpp condition lysed cells. **Fibril alignment was not measured** (imaging inside the microreactor was not possible) and **data are only "on reasonable request"**. It does not rescue candidate 4 as a data source.
- Licence checks: AlphaMissense predictions are described as CC BY 4.0 in the project README per a search result [ABS]; the Zenodo licence text was not confirmed. Allen Cell Types data licence still unverified (the AllenSDK code carries a BSD-style licence with a no-commercial-redistribution clause; that is code, not data).

## 5. Candidate projects, ranked

Confidence is in the evidence base, not in the outcome.

| # | Candidate | Real data | Novelty beyond demo | Fit to 24 h | Evidence confidence |
|---|---|---|---|---|---|
| 1 | Channel function-beyond-expression benchmark and certificate | KCNE1 (CC0), KCNJ2 (MIT), +2 fragments; KCNQ1 (CC BY preprint; S1 and S2 inspected) | Low: ProteinGym lists these assays and KCNQ1 work (one paper unread) already separates function from trafficking | High | High on data, low on novelty |
| 2 | Electrotaxis field-program discrimination | One field magnitude, 53 tracks in two files (4 files total) | Low; 3 papers | Medium | Medium-low |
| 3 | Jaxley conductance inversion, held-out stimulus classes (Allen Cell Types) | Allen DB; licence not verified | Low; Gouwens 2018, Jaxley | Medium, GPU useful | Medium |
| 4 | Drift-to-extrusion alignment window for bacterial cellulose | SEM images only, qualitative | Would be new, but needs experiments | Low | High that data are insufficient |
| 5 | DART / electrochemical gene-switch dose-response | Not located | Unknown | Low | Low |
| 6 | BETSE inverse pattern design | None measured | n/a | Kill | High |

## 6. Top candidate, specified

**Name:** Channel Bridge. **Question:** among variants that reach the cell surface at a normal level, which ones are functionally dead as a potassium channel, and can any model beat position-level baselines when the position is held out?

- **Input.** Channel sequence, position, substituted residue. Optional: the measured surface score (for the conditional version). **Output.** P(function category in {Loss, PartialLoss}) given surface-normal, plus an abstain flag and, for the budget variant, which positions to assay next.
- **Units.** Dimensionless normalised MAVE scores (about 0 = null-like, about 1 = wild-type-like in the KCNE1 files; confirm for each dataset). Per-variant SD and SE come from the source; I would not label any interval "95%" unless MaveDB defines it so.
- **Held-out evaluation.** Leave-position-out and leave-region-out folds (KCNE1: transmembrane versus flanks; Kir2.1: pore versus cytoplasmic domain). Intervals by bootstrap over positions. All seeds reported. Surface-normal cutoff fixed before looking at results (ProteinGym uses 0.75 for KCNE1 expression; use that, not a tuned value).
- **Baselines.** (a) global mean; (b) BLOSUM or Grantham plus hydrophobicity; (c) window mean of neighbouring positions excluding the held-out one; (d) surface-score only; (e) ESM2 zero-shot at 650M, 3B and, if it fits, 15B; (f) AlphaMissense (licence to be verified before use); (g) LoRA-fine-tuned ESM2 under grouped cross-validation. Reference ceiling: the leave-variant-out position mean above.
- **Negative controls.** Shuffled labels within folds; scrambled input sequence; surface-trained model scored on function (cross-assay); train on KCNE1 and test on KCNJ2; nonsense variants as source-defined controls (KCNE1 nonsense at 56 to 104 reportedly traffic normally but lose function).
- **Falsifier, stated before running.** If no model beats the neighbour-window baseline in Spearman and AUPRC by more than the position-bootstrap spread on surface-normal variants, "structure or language-model confidence predicts channel function beyond trafficking" is rejected for these channels. A null is the expected outcome as likely as a win.
- **Query-to-certify arm (secondary).** Replay assay-budget policies (random, position-diverse, uncertainty, PLM-prior) on the real table, as in the core project's protocol but on a different protein family. **Do not duplicate or import core code.**
- **GPU versus CPU.** CPU (<=2 threads): data audit, baselines, folds, bootstrap, Lean. One H100 is enough: ESM2 scoring of about 10k variants is minutes; LoRA grouped-CV is the largest job, order of 1 to 2 hours. Planned bound: 2 GPU-hours, 1 GPU. **More GPUs buy nothing here beyond larger ESM variants; do not scale out for show.** What GPU time measurably buys: model size and fine-tuning versus the cheap baselines, which is exactly the comparison.
- **Conditional Lean statement.** Let `I(V,a)` be net membrane current at voltage `V` for actuator level `a`. Assume (H1) `V -> I(V,a)` strictly increasing for every `a` (a single stable rest potential) and (H2) the actuator change raises net current at the old rest: `I(V*(a), a') >= 0` where `I(V*(a),a)=0` and `I(V*(a'),a')=0`. Then `V*(a') <= V*(a)`. One-line proof by monotonicity. For the chord-conductance form `I = sum g_i (V - E_i)` with `g_i > 0`, H1 holds automatically, and H2 holds when a K+ conductance is added at `V* >= E_K`. **A mutant must be rejected:** drop H1 and exhibit an N-shaped I-V with three roots where the conclusion fails (inward rectifier plus leak can be bistable [INF; to be checked in the literature]). The statement is arithmetic. It does not prove that the dye score is a monotone function of conductance; that stays an explicit assumption `A_map`, and the Kir2.1 authors' own remark about dye dynamic range is the reason to doubt it.
- **Why it may fail.** (1) Position-mean information dominates, so models may not add anything. (2) KCNE1 "function" is a depletion assay and Kir "function" is a saturating dye; both blur voltage gating, and the KCNQ1 pilot shows the multiplexed function score only weakly tracks measured V1/2 shifts (rho -0.18, n = 165). (3) HEK293 overexpression need not match native cells. (4) Four assays, two real channels with n > 1000; fragment datasets are too small to say anything alone. (5) KCNQ1 papers (one unread) and ProteinGym may already contain the equivalent split; I did not search their supplements. (6) A neighbour-window baseline already reaches about 0.60 Spearman on KCNE1 under position holdout, close to the AlphaMissense figure the authors quote, so a language-model win is far from guaranteed.
- **Cannot be verified without new experiments.** Voltage-dependence (V1/2, kinetics) of any variant; native-cell effect; any designed channel's function; field or tissue consequences; bistability of the readout.

## 7. Delphi claims and what they would change

MCP `https://delphisci-mcp.fly.dev/mcp` (stateless; `tools/list` returned six tools: overview, search_claims, get_claim, rank_claims, graph, sparql). Local source: 2600 files, 880 claims over five domains. Searches for "bioelectric", "membrane potential", "ion channel", "voltage", "gap junction", "cellulose" returned **zero** local claims. No claim bears on channels. Network source was queried once ("electric"): same Darwin hit; no further network use.

Claims that change a design or test:

- `turing-ddi` (Turing 1952). Its proposed test says to measure the Jacobian and the diffusivities independently and then perturb the diffusivity ratio. **Changes** the electrobiofabrication test: before any "alignment window" claim, the independently measured pair (electrokinetic mobility, extrusion rate) must be in hand and consistent. In the thesis they are not (§2).
- `turing-wavelength` and `turing-morphogen-hypothesis`. A matching pattern does not identify the mechanism. For any bioelectric pattern simulator this means a size-invariance or parameter-scaling prediction is required, not a visual match. Not used in the top project.
- `thompson1917-ch04-08` (potential differences in cell division). Both assessors rate it needs-new-data or partial (scores 0.40 and 0.47) and note that clamping experiments are sparse. **Changes** scope: applied-field datasets (§3) cannot test an endogenous-potential claim. Keep them in separate claims.
- `wolfram2002-ch12-29` and `ch12-27` (inverse harder than forward). **Changes** the benchmark framing: inverse control is run as bounded forward-simulate-and-select over a finite candidate set, with forward checks as the certificate, and the cost axis is the number of assays or forward runs. No general-inversion claim.
- Decorative here, not used: `thompson1917-ch04-02`, `ch04-04` (spindle as a field of force), `wolfram2002-ch06-11`, `darwin1859-ch06-10`.

## 8. Failures and gaps

- Springer PDF (Sano 2010 journal version): auth redirect; the r.jina.ai copy returned only the reference list. Not read. Used the thesis.
- PNAS KCNQ1 classifier paper: 403, then Cloudflare challenge. Not read.
- KCNQ1 supplement: first download truncated; the retry succeeded and S1/S2 were read. MaveDB deposit still pending.
- bioRxiv direct fetch: HTTP 429; used r.jina.ai, worked.
- "SHREAD", differentiable BETSE, Kozek and Glazer details: not found or only metadata.
- Allen Cell Types data licence and ProteinGym data licence: not verified. AlphaMissense: README per search result only.
- Search results alone (marked [ABS]) are leads; prior notes were not treated as authority.
- Only two of four electrotaxis CSVs were opened.

## 9. Recommendation

Run Channel Bridge as a bounded side vertical only if the core owner agrees, and only after reading the PNAS KCNQ1 paper, which could change or kill the framing; use KCNQ1 (S1 plus the S2 voltage-shift rows) as the primary dataset and KCNE1/Kir2.1 as replication. The S2 overlap is only 178 mutations, so any claim about gating prediction must be framed as exploratory. It is a falsifiable benchmark on real open data, not a physical electrofabrication result, and the cheap-baseline number in §4 says a null is the likelier outcome. Do not claim voltage-gating prediction, nanoscale field patterning, or novelty over ProteinGym or the KCNQ1 work. If a field-control panel is wanted for the pitch, use the Prescott data as a described, cited experiment-design example, and say plainly that one field magnitude cannot validate a field-selection policy.
