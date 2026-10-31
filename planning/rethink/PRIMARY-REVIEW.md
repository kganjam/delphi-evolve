# Independent review during the stronger-entry search

This is a methods and source review, not a selection decision or an experimental result. The director owns selection and integration. Four standalone Claude tmux sessions have native goals; their launch receipt is `tasks/results/rethink-launch.json`. The stronger-entry goal remains active.

## Checks completed

- [x] Read all four session panes and confirm active goals and substantive work.
- [x] Read the director's Tallo probe and selection gates.
- [x] Read Thompson's original passage and the Tallo paper's analysis.
- [x] Read the binder probe and send methodological corrections before promoting its result.
- [x] Read the NCA protocol, solvers and training code; send implementation and evaluation findings.
- [x] Read the electrophysiology feature extractor and official model documentation; send interpretation and data-integrity findings.
- [ ] Independently reproduce final selected experimental results on the integration commit.
- [ ] Review final selection, useful output and matched-budget collective evaluation.

These findings were sent to the appropriate workers through files under `/data/artifacts/delphi-evolve-rethink/messages/` and queued tmux messages. A delivered message is not proof that its correction has been implemented.

## Tallo is a reproduction, and scope matters

Thompson's original 1917 discussion, pp.19–20, concerns bending under self-weight, assuming taper and a branch-area relationship. It gives a limiting-height example before the diameter/height scaling sentence. Thus a pooled ordinary-least-squares slope across living trees is an additional operationalization; it cannot by itself refute or validate the mechanical limit. Differences in material properties, architecture and growth regime matter. [Original text](https://www.gutenberg.org/files/55264/55264-h/55264-h.htm).

The Tallo paper already compares height–diameter scaling with a 2/3 exponent, using mixed-effects models across lineages and biomes, and reports systematic departures. The director's simpler regression therefore reproduces a known comparison. A useful claim-to-test workflow could still result, but the clade difference is not a new biological discovery. [Tallo paper, section 3.1](https://ris.utwente.nl/ws/portalfiles/portal/283467983/Global_Change_Biology_2022_Jucker_Tallo_A_global_tree_allometry_and_crown_architecture_database.pdf).

Access record: the original Gutenberg text and institution-hosted paper were read. PMC presented a browser challenge; the Jina fallback was inaccessible; the institution-hosted PDF succeeded.

## Collective evaluation needs independent task truth

Existing Delphi LLM assessments can prioritize or stratify tasks; they cannot serve as independent correctness labels. Exact arithmetic and Lean certify the supplied formal proposition, not the natural-language translation or its biological applicability. Record these separately. A corpus-wide board is coverage; it is not evidence that every displayed claim was resolved.

The expression `1-(1-p)^N` assumes independent attempts and compares N draws with one. It does not prove a collective advantage at equal compute. Include sequential repeated attempts, matched budgets and an independent checker. Preserve null results. A verifier must not reward an agent for weakening the requested claim until it becomes trivial.

The live rubric gives 20% to decentralized agency and 25% to collective capability. Its explicit bonus concerns capabilities materially helping other teams; it does not list automatic sponsor-tool bonus points. [ScienceClaw judging criteria](https://scienceclawhack.ai/).

## Binder probe

Read-only review of `experiments/rethink_wildcard/binder_views_check.py` in the critic's worktree identified:

- Grouped five-fold validation is not leave-one-designer-out validation. Unknown designers assigned distinct groups can hide dependence; examine sequence identity and duplicate families across splits.
- Permuting labels against fixed out-of-fold predictions trained with the true labels is not a full-pipeline permutation test. Refit under a justified null or label the calculation descriptive.
- Bootstrapping fixed out-of-fold predictions conditions on the fitted models and split; it does not capture training uncertainty. Selecting the best of several views adds exploratory selection.
- A confidence interval including chance does not establish that the dataset is unusable. Preserve the original criterion and explicitly correct the interpretation.
- Excluding failed-expression designs makes the target conditional on expression. Report that denominator if discussing laboratory yield.

Adaptyv already analyzes computational metrics against measured binding in this dataset; a generic metric-fusion claim needs a closer prior-art comparison. [Adaptyv BenchBB report](https://www.adaptyvbio.com/blog/benchbb). The worker reported an initial fusion null; that number has not been independently reproduced by this reviewer.

## Bioelectric probe

The official GLIF documentation provides released models and recordings, but model training stimuli must be checked before labeling a stimulus held out. Intracellular current injection is not extracellular electric-field control or a new ion-channel intervention. A newly optimized pulse is a prediction unless a corresponding experimental measurement exists.

The documentation's command example can overwrite experimental response traces when input and output use the same NWB file. Keep downloaded files immutable and hash-pinned; simulate into a distinct output. [Official GLIF documentation](https://alleninstitute.github.io/AllenSDK/glif_models.html).

The worker's extractor counted Long Square spikes for 50 ms after pulse end. This can include rebound responses and misclassify rheobase; inspect negative-current cases and define the intended response window. Repeated identical currents may disagree about spiking, so finite stimulus grids do not necessarily establish deterministic threshold brackets. Report censoring, repeat variability, source QC and unit conversions. The worker caught a sampling-rate assumption and was rerunning extraction; final results need to reflect the correction.

## NCA probe

The frozen protocol uses a declared Schnakenberg system and an independently implemented spectral evaluator. This is model-only evidence, not biological measurement.

Read-only review flagged a conditional dictionary-unpacking syntax issue in the training script and the need to check the actual launch exit. Before a large scan of 40,000-step rollouts, measure throughput and peak memory, then assign useful GPU work if warranted. Separate training cost from amortized design cost.

Conditional success over accepted requests must include a minimum nonzero coverage and report the refused fraction. Hash-change refusal proves provenance dependence; law-removal and misapplication arms test scientific dependence. Check evaluator convergence on a fixed representative subset when discretizations disagree. A second implementation is helpful but does not guarantee numerical accuracy.

## Authorization correction

The Sonnet-only launch configuration selects the requested worker harness. The user also authorized other available model resources and specified budgets. The working contract now states this explicitly. Standalone Claude tmux sessions remain the execution mechanism; no Orchestra task queue or supervisor is authorized for this phase.

## Follow-up source checks

The official AllenSDK reader explains the inconsistent NWB conversion attributes: early pipeline versions already store SI values despite incorrect attributes; versions 1.1 and later apply the conversion. The version is read from `general/generated_by`. This supplies a documented rule instead of choosing units from physiological plausibility. The electric worker received the source and was asked to record the version-dependent decision. [Reader implementation](https://raw.githubusercontent.com/AllenInstitute/AllenSDK/master/allensdk/core/nwb_data_set.py).

The proposed semantic-checking benchmark has close prior art. Relevant full-text sections were read:

- *Benchmarking Agentic Review Systems*, Appendix C, already injects dropped scope restrictions, incorrect implications and experimental misinterpretations; it compares review harnesses and model families. Its perturbation validation includes an LLM checklist. An executed distinguishing witness could provide a more concrete grading mechanism for our narrower task. [Paper](https://arxiv.org/html/2606.19749v1).
- *ShadowBench*, sections 3.1–3.3, uses forward and backward Lean implications with complete shadow sets, referencing intended formal statements. A failed search for counterexamples does not establish this kind of equivalence. [Paper](https://arxiv.org/html/2608.29270v3).
- *The Faithfulness Gap*, sections 1–5, proposes counterfactual probes and bidirectional provability fingerprints for natural-language/formal-statement drift. Generic mutation-based fidelity checking is not a new contribution. The possible applied contribution is a source-scoped scientific-test repair pipeline with useful design consequences. [Paper](https://arxiv.org/html/2606.16541).

These checks narrow the novelty claim; they are not an exhaustive literature review or a reproduction of published performance.

## Executed service edge cases, before publication

At 06:18:50 PDT on October 31, an independent bounded probe of the collaboration worker's in-progress `falsify` service reproduced three issues. This was an uncommitted implementation, not the released baseline. The receipt records file hashes sampled after execution, input requests and returned results; it does not establish the state of later edits. [Raw receipt](../../artifacts/integration/rethink-service-initial-review.json).

1. Arbitrary caller claim text was attached to a `survived` verdict even though the calculation only adjudicated linear instability. The requested text must remain separate from the proposition actually checked.
2. A very narrow instability band produced `bracket_verified=false` with no unstable mode at either proposed endpoint, while the prose still claimed an unstable mode at the upper endpoint. A proposed intervention must be withheld or refined until its check succeeds.
3. A software fault injection returning `source_pin_ok=false` left the claim verdict unchanged. A generic calculation can remain available, but source-authorized claim reuse must be distinguished or refused.

Command executed: `systemd-run --user --scope -q -p TasksMax=128 -p MemoryMax=1G -p MemorySwapMax=0 -p RuntimeMaxSec=60 env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 /data/artifacts/delphi-evolve-rethink/primary-audit/service_probe.py`; exit 0 means the probe recorded the above behaviors, not that they passed acceptance. The service owner received the inputs and was asked to add regression tests. Independent retesting of the committed fixes remains pending.
