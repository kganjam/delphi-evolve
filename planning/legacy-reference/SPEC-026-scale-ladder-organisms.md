# SPEC-026 — Scale Ladder, Model Organisms and Coverage

**Status:** Draft · **Version:** 0.1.1 · **Owner:** G2 (0.1.1, 2026-10-27: coverage round 21 task 0adcfda2, rule 14)

## Scope

Defines the coverage target and makes it measurable. Three parts:

1. **The scale ladder** — eleven organismal levels, each with its state variables, characteristic
   scales, model classes, measurement modalities and cross-scale ports.
2. **Model organisms** — the target species, their available atlases, which scales the registry
   currently covers, and the gaps.
3. **Coverage metrics** — the (taxon × scale) occupancy matrix and the rules for counting a cell.

Covers what "works for any organism, at any scale" means operationally and how progress toward it
is reported.

Does **not** cover: the assembly mechanics that implement cross-scale coupling (SPEC-003), the
ModelCard schema (SPEC-001), resource access (SPEC-023), or which model to use (SPEC-025).

## Motivation

The requirement is explicit: *work for model organisms; be able to model and design at all
organismal levels.* From flies to zebrafish to shells to frogs — everything; all scales of biology.

That ambition needs a yardstick, because the same ambition has already produced a cautionary
result in this project's own prior art. MorphoLib reports "100 / 100 (100%) cell occupancy across
the Aristotelian Taxonomic × Biophysical Cause Matrix" — a complete coverage matrix across 150
genera and 10 mechanisms. The matrix is filled by the ~1,000 generated slots, whose scripts contain
no model, whose "empirical" and "simulated" series are the same curve, and whose dataset
directories do not exist. The occupancy number is real; what it counts is not.

So the honest coverage matrix is the point of this spec. A filled cell must be backed by a
ModelCard that earned `independently-verified` or `source-only` under SPEC-014, and every coverage
claim must state which statuses it includes. A sparse matrix that is true is worth more than a full
one that is not, and it is also far more useful — the empty cells are the work queue.

The second motivation is compositional. "All scales" is not eleven independent modelling efforts;
it is the problem of making a cellular model drive a tissue model without the two contradicting
each other. ChatGPT conversation 2 §5.2 is blunt about this: one universal simulator is beyond
current capability, so the design is a federation with explicit interfaces, and the cross-scale
mappings are initially approximate and must carry uncertainty.

## Schema

### Part 1 — The scale ladder

| # | Level | Characteristic state variables | Length | Time | Model classes | Measurement modalities |
|---|---|---|---|---|---|---|
| 1 | **Molecular** | Conformation, binding occupancy, reaction rates | 0.1–10 nm | fs–µs | MD, docking, kinetic schemes | Crystallography, cryo-EM, AlphaFold, SPR |
| 2 | **Macromolecular** | Complex stoichiometry, polymer mechanics, filament state | 10–500 nm | µs–s | Coarse-grained MD, polymer physics, rule-based | Cryo-ET, FRET, single-molecule |
| 3 | **Subcellular** | Organelle geometry, ion channel state, motor flux, local [species] | 0.1–5 µm | ms–min | Spatial reaction-diffusion, PDE on realistic geometry | Super-resolution, electrophysiology, FRAP |
| 4 | **Cellular** | Gene expression, cell state, membrane potential, polarity, volume | 5–50 µm | min–h | ODE/SDE GRNs, Boolean networks, cell-state transitions, FSM | scRNA-seq, live reporters, voltage dyes, patch clamp |
| 5 | **Tissue** | Cell packing, adhesion, stress, strain, morphogen fields | 50 µm–1 mm | min–h | Cellular Potts, vertex models, continuum mechanics, reaction-diffusion | Light-sheet, confocal, laser ablation, traction force |
| 6 | **Organ** | Shape, chamber geometry, flow, branching topology | 0.1–10 mm | h–days | Continuum mechanics, growth laws, branching morphogenesis | µCT, OPT, histology, MRI |
| 7 | **Neural** | Spike trains, synaptic weights, circuit connectivity, population state | 1 µm–10 mm | ms–s | Compartmental models, spiking networks, connectome dynamics | Calcium imaging, EM connectomics, electrophysiology |
| 8 | **Whole-organism** | Body plan, size, allometry, physiology, behaviour | 0.1 mm–1 m | h–lifetime | Anatomy graphs, allometric scaling, sensorimotor control | Morphometrics, behavioural tracking, staging series |
| 9 | **Developmental** | Trajectory through 1–8 over time; fate maps, timing, regeneration | all | h–weeks | Clock-and-wavefront, positional information, bioelectric patterning, lineage trees | 3D+t imaging, lineage tracing, staged atlases |
| 10 | **Collective** | Group state, signalling fields, division of labour, colony form | 1 mm–10 m | h–years | Agent-based, stigmergy, active matter, biofilm mechanics | Colony imaging, tracking, time-lapse |
| 11 | **Ecological** | Population densities, interaction networks, environmental fields | 1 m–km | days–years | Population dynamics, spatial ecology, resource flow | Field survey, remote sensing, mesocosm |

Level 9 (**Developmental**) is orthogonal to 1–8: it is the time-indexed trajectory through the
others, not a spatial scale of its own. It is listed as a level because morphogenesis models — the
corpus's centre of gravity — live there, and because the measurement modalities and model classes
that serve it are distinct.

### Cross-scale ports

Each level exposes typed ports (SPEC-003 vocabulary: `chemical_species`, `mechanical`,
`bioelectric`, `geometric`, `informational`, `thermal`). A coupling is a connection between a port
at level *n* and a port at level *n±1*, with a declared approximation.

```python
@dataclass(frozen=True)
class ScaleCoupling:
    id: EntityId
    version: VersionId
    lower_ref: EntityId                 # ModelCard at level n
    upper_ref: EntityId                 # ModelCard at level n+1
    direction: Literal["upward", "downward", "bidirectional"]
    port_lower: PortRef
    port_upper: PortRef
    mapping: str                        # SymPy srepr: how the quantity is transformed
    approximation: ApproximationClass   # REQUIRED — see below
    timescale_ratio: float              # τ_upper / τ_lower
    separation_satisfied: bool          # ratio ≥ threshold (default 10)
    conservation_checks: tuple[str, ...]
    uncertainty: UncertaintyPropagation # REQUIRED
    evidence_refs: tuple[EntityId, ...]
    validation_status: ValidationStatus # The coupling earns this in its own right
```

| `ApproximationClass` | Meaning | Validity condition that MUST be stated |
|---|---|---|
| `mean_field` | Upper level sees the average of lower-level state | Fluctuations small relative to the mean |
| `timescale_separation` | Lower level is at quasi-steady-state on the upper's timescale | `timescale_ratio ≥ threshold` |
| `homogenisation` | Periodic/statistical microstructure replaced by effective parameters | Scale separation in space; representative volume exists |
| `coarse_graining` | Explicit aggregation operator | Operator is stated and its kernel recorded |
| `phenomenological` | Fitted relation, no derivation | **Fit data and held-out validation required** |
| `direct` | Same quantity, unit conversion only | Units match after conversion |

`phenomenological` is the honest label for most couplings we will actually build at first, and it
carries the heaviest evidence burden — exactly as it should.

**Uncertainty propagation is mandatory.** A coupling that passes a point value upward without an
interval is invalid. The default is first-order propagation with an explicit statement that it is
first-order; Monte Carlo where the mapping is non-linear.

### Part 2 — Model organisms

Coverage targets. "Registry coverage" below reflects what the ~216 validated MorphoLib models
actually reach; everything else is gap.

| Organism | NCBI taxid | Key atlases / data (SPEC-023) | Staging series | Registry coverage today | Principal gaps |
|---|---|---|---|---|---|
| *Drosophila melanogaster* | 7227 | DynamicAtlas, Flysta3D-v2, BDTNP, FlyEx, FlyBase, Fly Cell Atlas | Bownes stages | 5 tissue, 9 developmental (ventral furrow, wing-disc vertex, segmentation) | 1–4, 6, 7, 11 |
| *Danio rerio* | 7955 | Zebrahub, Daniocell, ZFIN, BioEmergences, weMERFISH | **Kimmel** | 9 developmental (segmentation clock, somitogenesis) | 1–4, 6, 7, 10, 11 |
| *Xenopus laevis* | 8355 | Xenbase; MorphoLib Ca²⁺ wave imaging | Nieuwkoop–Faber | 9 developmental (clock-and-wavefront), 3 subcellular (Ca²⁺ waves) | 1, 2, 4, 6, 7 |
| *C. elegans* | 6239 | WormGUIDES (360 frames, nuclear positions + lineage), OpenWorm c302 | Sulston lineage | 8 whole-organism, 9 developmental, 7 neural (connectome) | 1–3, 5, 6, 11 |
| *Schmidtea mediterranea* | 79327 | **PlanformDB** (372 morphologies as labelled graphs) | — | 8 whole-organism (anatomy graphs), 9 developmental (bioelectric regeneration) | 1–5, 7 |
| *Hydra vulgaris* | 6087 | — | — | 9 developmental (Gierer–Meinhardt activator-inhibitor, slot 001) | 1–8, 10, 11 |
| *Mus musculus* | 10090 | MGI, EMAGE, Allen Institute atlases | Theiler | 5 tissue (epithelial buckling), 6 organ (cortical gyrification) | 1–4, 7, 9, 11 |
| *Gallus gallus* | 9031 | GEISHA | **Hamburger–Hamilton** | 9 developmental (gastrulation streak, somite) | 1–7, 10, 11 |
| *Phallusia mammillata* | 59560 | **MorphoNet** — 180 timepoints at 2 min, full 3D segmentation. Distributed as figshare **8223890** (Phmamm-1, *ex* Astec-Pm1), **CC BY 4.0**, read 2026-10-26: 179 time points, 66,993 cell-instances with volume, barycenter, contact surfaces, lineage and fates ([report](../docs/research/third-organism-phallusia-morphonet.md)) | — | *none* yet — the third organism ([ADR-0029](../docs/decisions/ADR-0029-third-organism.md)); M2416 builds its pack | all |
| *Arabidopsis* / *Helianthus* | 3702 / 4232 | Swinton 2016 parastichy tables (768 counts, 657 capitula) | — | 9 developmental (phyllotaxis, leaf venation) | 1–7, 11 |
| *Conus textile*, *Turritella* | 6494 / — | Wikimedia specimens; Raup parameter sets | — | 8 whole-organism (shell geometry), 9 (pigmentation CA, accretion) | 1–7 |
| Diatoms (*Coscinodiscus*, *Thalassiosira*) | — | — | — | 2–3 (frustule phase separation, Cahn–Hilliard) | 4–11 |
| Corals (*Madracis*, *Acropora*) | — | — | — | 6 organ / 10 collective (flow-driven growth, colony geometry) | 1–5, 7 |
| Stromatolites | — | — | — | 10 collective (KPZ front) | — |
| *Dictyostelium discoideum* | 44689 | dictyBase | — | 10 collective (Schnakenberg, aggregation) | 1–8 |
| *Bacillus subtilis* | 1423 | SubtiWiki | — | 10 collective (biofilm wrinkling) | 1–8 |
| *Vibrio cholerae* | 666 | — | — | 10 collective (biofilm nematic ordering) | 1–8 |
| *Macrotermes* | — | — | — | 10 collective (stigmergic nest construction) | 1–9, 11 |

Two observations the matrix makes immediately visible, and which should drive early work:

- **Levels 1–4 are nearly empty across every organism.** The corpus is a morphogenesis corpus; it
  lives at 5, 8, 9 and 10. Molecular and cellular coverage must come from external resources
  (SPEC-023: BioModels, Reactome, UniProt, VCell) rather than from the existing scripts.
- ***Phallusia mammillata* has the best data and zero models.** MorphoNet's 180-timepoint
  full-segmentation ascidian dataset with invariant cell lineage is the single highest-value
  unexploited target in the catalogue, and ChatGPT conversation 1 §8 independently recommends it as
  possibly the best first system for recovering multicellular rules.

### Part 3 — Coverage metrics

```python
@dataclass(frozen=True)
class OccupancyMatrix:
    taxa: tuple[TaxonRef, ...]
    scales: tuple[int, ...]                      # 1..11
    cells: Mapping[tuple[TaxonRef, int], CellOccupancy]
    status_filter: frozenset[ValidationStatus]   # REQUIRED on every report
    generated_at: datetime
    registry_version: VersionId

@dataclass(frozen=True)
class CellOccupancy:
    model_refs: tuple[EntityId, ...]
    best_status: ValidationStatus
    weight: float                                # See table
    coupling_in: tuple[EntityId, ...]
    coupling_out: tuple[EntityId, ...]
```

Cell weight by best status:

| `validation_status` | Weight | Counts toward coverage? |
|---|---:|---|
| `independently-verified` | 1.0 | yes |
| `source-only` | 0.5 | yes, at half weight |
| `unverified` | 0.0 | **no** — reported separately as pipeline |
| `synthetic-rejected` | 0.0 | **never** |

Reported figures:

- **Occupancy** — fraction of cells with weight > 0, stated with its `status_filter`.
- **Weighted fill** — Σ weight / |cells|.
- **Connected coverage** — the fraction of occupied cells reachable from another occupied cell by a
  validated `ScaleCoupling`. This is the number that actually measures "can we model across
  scales", as opposed to "do we have models at several scales". Expect it to be near zero at first;
  that is the honest starting point.

## The second axis: interacting subsystems

Scale is one axis. It is not the only one, and treating it as the only one is a modelling error
this spec should name.

[`../docs/sources/chatgpt/01-developmental-biology-resources.md`](../docs/sources/chatgpt/01-developmental-biology-resources.md) §5
decomposes development into **six coupled dynamical systems** that each span several scales.
We carry **seven** — the source's six plus tissue geometry; see the note below the table:

| Subsystem | What it governs | **Candidate frameworks** | Measurable quantities |
|---|---|---|---|
| **Gene regulation** | GRNs, switches, attractors, bifurcations | Nonlinear dynamical systems; attractor and bifurcation analysis | Expression trajectories, response to regulatory perturbation |
| **Pattern formation** | Morphogen gradients, positional information, scaling | Reaction–diffusion; positional information; scaling laws | Stripe positions, boundary sharpness, concentration profiles |
| **Cell-state transitions** | Fate decisions, commitment, plasticity | Stochastic state-transition models; dynamical attractors | Fate probabilities and transition rates |
| **Cellular mechanics** | Forces, adhesion, active stress | Active matter; continuum mechanics; vertex-model dynamics | Velocity fields, strain, curvature, stress |
| **Lineage and growth** | Division, death, branching genealogies | **Branching processes; growth laws** | Division times, clone sizes, population structure |
| **Robustness** | Recovery from perturbation, canalisation, error correction | **Control theory; feedback; error correction** | Recovery after perturbation, variability across embryos |
| **Tissue geometry** | Shape, folding, topology | Differential geometry; topology of folded sheets | Morphometrics, curvature, connectivity |

The **candidate frameworks** column is not decoration: it is the hypothesis space
[SPEC-022](SPEC-022-equation-discovery.md) searches when asked *"what kind of law governs this?"*.
Dropping it, as an earlier draft of this spec did, turns subsystem identification into a label
rather than a constraint on model synthesis.

**Two corrections to an earlier draft, recorded rather than quietly applied**
([AGENTS.md](../AGENTS.md) §1.8 — preserve disagreement):

1. The source lists **Robustness** — control theory, feedback, error correction — as one of its
   six. An earlier draft of this spec dropped it and put **Tissue geometry** in its place. Both
   belong, so there are **seven** here, not six, and the divergence from the source count is
   stated rather than hidden. Robustness is not optional for us: it is precisely what
   [SPEC-006](SPEC-006-morphobench.md)'s primary evaluation dimension, perturbation
   generalisation, measures. A system that can reproduce a wild-type pattern but not its recovery
   after a perturbation has matched a picture, not a mechanism.
2. The framework column was dropped entirely. Restored above.

These are **not** levels. Gene regulation operates from molecular to tissue scale; cellular
mechanics from subcellular to organ. A model occupies a *(scale × subsystem)* cell, and the
coupling that is hardest to get right is usually between subsystems at the same scale rather than
between scales — mechanics feeding back onto gene regulation is the canonical example, and a
scale-only decomposition cannot even express it.

**Consequence for coverage.** The occupancy matrix is reported on both axes. A corpus covering
eleven scales entirely within *tissue geometry* has broad scale coverage and a single-subsystem
blind spot, and a one-axis metric would score it well. Many morphogenesis corpora — including the
one we build on — are exactly that shape.

## Rules

1. A `ScaleCoupling` **MUST** declare an `ApproximationClass` and the validity condition for it.
2. A `ScaleCoupling` **MUST** propagate uncertainty; passing a point value upward is invalid.
3. A coupling claiming `timescale_separation` **MUST** record `timescale_ratio` and
   `separation_satisfied`; a ratio below the stated threshold **MUST** fail validation.
4. A `phenomenological` coupling **MUST** cite its fit data and a held-out validation (SPEC-020).
5. An occupancy cell **MUST NOT** be counted unless backed by a ModelCard whose
   `validation_status` is `independently-verified` or `source-only`.
6. A `synthetic-rejected` ModelCard **MUST NOT** contribute to any coverage figure, at any weight.
7. Every coverage claim **MUST** be published with its `status_filter` and `registry_version`.
   A bare percentage is not a valid coverage claim.
8. Reports **MUST** publish occupancy, weighted fill and connected coverage together. Occupancy
   alone overstates capability.
9. Empty cells **MUST** be enumerable as a work queue; coverage reporting that hides gaps is a
   defect.
10. MorphoLib's "100/100 cell occupancy" figure **MUST NOT** be reproduced, cited as achievement,
    or used as a baseline. Its construction is documented in `docs/prior-art/morpholib.md` §3.
11. A model **MUST** declare the scale level(s) it operates at; a card without a level cannot be
    placed in the matrix and **MUST** fail validation.
12. Cross-scale couplings are versioned entities (SPEC-015) and earn their own
    `validation_status` under SPEC-014 — a coupling between two verified models is not thereby
    verified.
13. Where a level is covered only by an external resource rather than a registry ModelCard, the
    cell **MUST** be marked `external` and reported separately from native coverage.
14. A developmental model **MUST** declare the subsystem or subsystems it advances from §The
    second axis and **MUST** predict forward from a declared initial embryo state. A reconstruction
    not advanced from that initial state **MUST NOT** be described as a generative or predictive
    theory of development. Transcript 01 requires a program that *"starts from an initial embryo
    state"* (`docs/sources/chatgpt/01-developmental-biology-resources.md`, line 353). The existing
    seven-subsystem axis already covers the source's six-subsystem decomposition.

## Acceptance

| Check | Command / criterion |
|---|---|
| Level declaration | `uv run pytest tests/test_scale.py -q` — a ModelCard without a scale level fails validation |
| Matrix generation | `uv run python -m morphoswarm.coverage matrix --status independently-verified,source-only` emits occupancy, weighted fill and connected coverage with `registry_version` |
| Status filter required | Generating a matrix without `--status` fails with a message requiring it |
| Synthetic excluded | Injecting 1,000 `synthetic-rejected` cards leaves every coverage figure unchanged |
| Unverified excluded | `unverified` cards appear in the pipeline report, not in occupancy |
| Bare percentage blocked | A report rendering a coverage figure without its filter fails the docs lint |
| Coupling approximation | A `ScaleCoupling` without `ApproximationClass` is rejected |
| Uncertainty required | A coupling passing a point value upward is rejected |
| Timescale gate | A coupling claiming separation with ratio 2.0 against threshold 10 fails |
| Phenomenological gate | A phenomenological coupling without held-out validation is rejected |
| Coupling status independent | Two verified models joined by an unvalidated coupling yield `connected coverage` 0 for that pair |
| Gap queue | `uv run python -m morphoswarm.coverage gaps` lists empty cells ranked by available data (SPEC-023), with *Phallusia* × levels 4–5 ranked highly |
| Known-coverage regression | The matrix reproduces the Part 2 table for the current corpus; drift fails CI |

*Measured 2026-10-28 by the host session.* Neither command in the table above exists as written.
`morphoswarm.coverage` is not a module; the matrix is `python -m morphoswarm.mechanisms.coverage
--status …`, with no `matrix` or `gaps` subcommand. On `main` that command refuses the
repository's own inputs, twice over. A symlinked card is read twice, which M2568 fixes. Then the
segmentation clock's module and use disagree about levels, which is SPEC-060 open question 11.
The *Status filter required* row holds as written. The criteria are unchanged, and the commands
are recorded here as not yet built rather than rewritten to match the code.

## Open questions

- **Is "developmental" a level or an axis?** Treating it as level 9 is pragmatic — the models live
  there — but it is formally a trajectory through 1–8. Does the matrix need a third dimension
  (taxon × scale × time), and does that make it too sparse to report usefully?
- **Taxon granularity.** Species is right for model organisms, but "corals" and "diatoms" are not
  species. Should the matrix index NCBI taxids at mixed ranks, and how is coverage aggregated up a
  clade without double-counting?
- **Connected-coverage threshold.** What ratio of connected to occupied cells constitutes a
  credible claim of multi-scale capability? Setting this *before* measuring it is the honest order.
- **External vs native coverage.** If BioModels supplies a molecular model that a coupling reaches,
  is the cell covered? Current position: yes, but marked `external` and reported separately.
- **Design coverage vs modelling coverage.** A cell may be modellable but not designable
  (SPEC-005). Does the matrix need a second occupancy layer for design capability?
- **Ecological interaction simulation** *(coverage round 21, 2026-10-27).* Must an ecological-rung
  model simulate an organism's interaction with its declared environment, or is an environmental
  field or population model sufficient? **Recommended (coverage round 21):** require the
  interaction when a design claims ecological behaviour; keep environment-only models as narrower
  coverage. The source asks to simulate organisms interacting with the virtual world
  (`docs/sources/screenshots/01-whatsapp-joel-dietz-organism-cad.png`, Image 01; binary image,
  no textual line number).

## References

- `docs/prior-art/morpholib.md` §3 — the generated slots, and §3.6 for the real ~216-model corpus;
  the "100/100 occupancy" construction
- `docs/sources/chatgpt/01-developmental-biology-resources.md` §5 (six interacting dynamical
  systems), §6 (which organism and process to start with), §8 (*Phallusia mammillata* / MorphoNet
  as possibly the best first system)
- `docs/sources/chatgpt/02-organism-design-questions-morphoswarm.md` — the multiscale design table
  (atomic → ecological); §5.2 federation of models rather than one universal simulator
- SPEC-001 (ModelCard scale fields), SPEC-003 (assembly ports and interference), SPEC-014
  (validation status), SPEC-015 (versioning), SPEC-019 (evidence), SPEC-020 (held-out validation),
  SPEC-023 (atlases and external models), SPEC-025 (gap-driven selection)
- MorphoNet <https://morphonet.org/> · Kimmel et al. 1995 (zebrafish staging) ·
  Hamburger & Hamilton 1951 (chick staging) · Guignard et al., *Science* 2020 (ascidian)
