# Critic red-team 2 — candidate E "operationalization-fidelity audit"

Sat 31 Oct 2026, 06:20–06:45 PDT. Claude Sonnet 5.5. Responds to `director-to-critic-02.md` and `primary-operationalization-benchmark.md`. Prior-art statements below come from **search results plus two abstract fetches, not full-paper reads**; each is marked. Companion to `critic.md`.

## 0. Verdict in five lines

1. The idea is **better than "claims-as-tests"** because it converts today's real mistake into a measurable question and gives a genuine information asymmetry (auditor holds the primary source; proposer holds the test).
2. It is **not unprecedented in its parts**: NL↔formal fidelity benchmarks with controlled drift and benign variants exist for Lean (§1), and error-injection benchmarks exist for papers. The remaining gap is narrow and I could only partly verify it.
3. "By-construction labels" survive **only** if labels are tied to a machine-found *distinguishing instance* between a faithful base test and the mutant, with equivalent mutants as controls. Anything else is "known edit, unknown fault."
4. Realistic size: **≈12–20 independent claim families** (§3). That fixes the statistical resolution before anyone runs anything.
5. Versus polishing the baseline: E has a higher *ceiling* on the 45% multi-agent block and a higher *risk* on Execution and Impact; both can end in a second collective null (§4). Kill conditions in §5.

## 1. Prior art (what exists; what gap remains)

| Area | Found (confidence) | Consequence |
|---|---|---|
| NL→Lean autoformalization fidelity | **DriftBench** (2,183 NL/Lean 4 pairs, controlled drift labels, six mathlib4 subfields; reported 89.6% detection at 3.0% FPR — search snippet, not read); **FormalAlign** (ICLR 2025; misalignment strategies over four benchmarks; shows misaligned statements still compile — snippet); **ConsistencyCheck** (all statements compile so only semantics differ — snippet); **FormalRx** (ICML 2026 AI4Math shared task, 28-category error taxonomy, localization + repair — snippet); **ShadowBench** (arXiv 2608.29270, **abstract read**: forward/backward implication against "shadow" statements, 178 research-level Lean problems, 98.8% agreement with experts for the metric; compile rate 61.8% vs SA-Pass 11.2% for the best agent) | The mutation + benign-variant + fidelity-vs-compile idea is **established for math→Lean**. Do not call mutation-labelled fidelity checking new. The forward/backward implication test (ShadowBench) is the nearest design to our "distinguishing instance" idea. |
| Paper-level flaw detection | **FLAWS** (713 LLM-inserted claim-invalidating errors; best 39.1% at k=10), **SPOT** (83 papers, 91 confirmed real errors; ~21% best), **PaperAudit-Bench**, **SciReview** (ICML 2026; recall 62% falls to 10% once one false positive disqualifies a run), **"Auditing AI peer reviewers"** (NeurIPS 2026 poster; 177 injected errors, false-positive audit), **Benchmarking Agentic Review Systems** (arXiv 2606.19749, abstract read: four injected error categories, best 71.6% recall, complaints dominated by false positives; categories not named in the abstract) | Injected-error benchmarks exist and report that **false positives are the dominant practical failure**. Our false-alarm number is therefore a headline requirement, not a footnote. Caveat noted by commentators: LLM-inserted errors are not natural errors. |
| Hypothesis-vs-analysis fidelity in data analysis | **DiscoveryBench** (abstract-level via search): scores whether an agent's *hypothesis* matches the reference using an LLM judge — it does not check that the analysis tests the stated hypothesis. ScienceAgentBench scores programs. | This is where a gap plausibly remains: **NL scientific claim → executable data test, graded by a witness rather than an LLM judge.** My search found no benchmark doing that; four searches are not an exhaustive sweep. |
| Analytic-choice variance | **Many analysts / multiverse / specification curve** (Silberzahn et al. 2018: 29 teams, 20 significant vs 9 not, same data and question; Schweinsberg et al. 2021: operationalization freedom produced opposite-direction effects; multiverse analysis and specification curves proposed as remedies — search summaries, secondary sources) | Our four-verdict Thompson/Tallo table **is a small specification curve.** Credit that tradition; do not present it as a new idea. |
| Scientific claim verification | SciFact (evidence retrieval + verdict; not re-read) | Verifies claims against text, not tests against claims. |
| Our own domain | Tallo (Jucker et al. 2022) already compared the H–D exponent to 2/3 (primary's read). | The worked example is a reproduction, as already recorded. |

**Gap remaining (my best statement):** a *witness-graded* benchmark for whether an executable scientific test is faithful to a source claim, spanning the faithful/consequential/equivalent trichotomy, with an independent-auditor vs self-audit comparison. It is real but small, and Lean-side prior art is close enough that a knowledgeable judge could call it "DriftBench for science". Frame it as an applied extension, not a new field.

## 2. Attack on the by-construction label argument

1. **A mutation is an edit, not a fault.** "Envelope → mean" is consequential only if some instance within the claim's declared scope gives different verdicts. Otherwise it is an equivalent change (harmless control). Labels must come from that instance search, not from the mutation's name.
2. **The Thompson/Tallo pair itself is not by-construction.** Whether OLS, SMA, a quantile envelope or the Greenhill bound is "the" test depends on reading the source; Tallo's authors and Thompson's text read it differently (mean allometry vs buckling limit; McMahon-type elastic similarity sits between). Under the director's rule 2 it correctly stays in a separate, human-adjudicated set. Expect disagreement among the adjudicators too; report it.
3. **The base test must itself be faithful**, and nobody certified that. A second reader must verify each base pair against the primary source (Thompson's text, Kimura's model statement) before mutants exist; unreadable or ambiguous bases are excluded and the exclusions counted.
4. **Mutator leakage.** Sonnet-authored mutants carry Sonnet style; reviewers may detect "edited text" rather than a changed proposition. Prefer **rule-based mutation operators on executable tests** (swap max→mean, drop a scope guard, change units constant, swap estimator, quantifier ∃↔∀), apply them mechanically, and test label inferability with a trivial classifier on length/tokens/formatting before any agent runs (primary's point).
5. **Detection of injected edits ≠ detection of natural drift.** The Tallo error was a *natural* drift by an agent under task pressure. The more convincing measurement is the **natural drift rate**: blind agents operationalize N claims; independent adjudication (distinguishing instance where possible) labels them. Injected mutants are the secondary, controlled set.
6. **Harmless-mutation control must be nonempty and adversarial:** paraphrase; algebraic rearrangement; unit change with correct conversion; reordered but equivalent guard; estimator swap that is provably equivalent on the claim's scope (e.g., OLS vs SMA when the claim is invariant to slope scaling — rare). A reviewer that flags these is wrong; report the false-alarm rate with an exact binomial interval.
7. **Grade with a witness, not a judge.** Count a detection only if the reviewer submits an instance in the claim's declared scope on which base and mutant tests disagree, verified by running both. This removes LLM-as-judge from the label and the score, and it makes "diagnosis correct" distinct from "flagged". Flagged-without-valid-witness is counted separately (candidate false alarm or a real fault outside the generated search).
8. **Only exactly-computable claims qualify**, which brings us back to the triage in `critic.md` §3.1: 33 D1 claims (15 non-trivial), plus those D2 claims where an author-and-second-reader formalization is possible.

## 3. How many independent items? (statistical resolution, computed not guessed)

- Independent units are claim **families**, not mutants (primary's family-held-out requirement). From the single-reader triage (not independently confirmed), about **15 non-trivial D1 plus a handful of D2** ⇒ plan for **12–20 families** after exclusions; mutants multiply rows but not independence.
- Exact two-sided 95% Clopper–Pearson lower bounds for a perfect score: 12/12 → 0.735; 15/15 → 0.782; 20/20 → 0.832. A detector that catches 9/12 has a lower bound far below that. Differences between two arms on the same families need **≥6 discordant families all in one direction** to reach exact two-sided p<0.05 (6/0: two-sided 0.031, one-sided 0.016; 5/0: two-sided 0.063, one-sided 0.031; preregister sidedness). With 12–20 families, only a large effect is detectable.
- Therefore the pitch may report detection/false-alarm rates with intervals, and a collective comparison **only as exploratory** unless the intervals separate. This is a limit of the task, not of the effort.

## 4. Does it beat polishing the baseline? (rubric, honest)

| Rubric item | E | Polished baseline | Comment |
|---|---|---|---|
| Significance 20 | plausible (AI-for-science verification) but abstract | modest ("which assay next") | E reads bigger; do not oversell |
| Impact 25 | small benchmark, nearby prior art; helped by a witness-graded design and a real caught error | weak (lost to LazySP) | depends on novelty claim surviving §1 |
| Decentralized agency 20 | real info asymmetry (source vs test); must show non-dispatched task choice | weak | E better *if* agents self-select work and logs show it |
| Collective capability 25 | measurable independent-auditor vs self-audit at matched cost; may be null | measured null | E has headroom; a second null is possible |
| Execution 10 | new, unproven in <24h | banked | the real cost of switching |
| +10 | a "check your operationalization" service is useful in principle; needs observed use | similar | cannot be claimed |

Judgement: E is the stronger **expected story** *only if* a witness-graded detection result with false-alarm control exists by ~16:00 PDT; otherwise it is a weaker story than an honestly polished baseline. I give no probability of winning.

**What multiple agents actually add here (hypothesis, to be measured):** context separation. Self-audit by the agent that wrote the test is anchored on its own framing; an independent agent re-reading only the primary source and the test may flag mismatches the author cannot. Matched-budget arms: (S1) author self-audit with sequential retries; (S2) single agent given both artifacts in one context; (C) independent auditor(s) who see source and test, never the author's rationale; total tokens/tool calls and checker cost equal. A deterministic scope-guard checker (does the test's quantifier/estimator type match a declared claim type?) must be kept as a non-LLM baseline.

## 5. Kill conditions (E stops being the headline if any is true)

1. By **09:30 PDT**, fewer than **12 families** have a base test verified faithful to the primary source by a second reader (Thompson, Kimura, Hawk–Dove, log-spiral, Rayleigh–Plateau, Turing, Greenhill qualify first).
2. By **10:30 PDT**, mutant generation is not mechanical/hidden-key (hash committed before any reviewer runs), or a trivial surface classifier (length/format/one token) recovers the labels above chance.
3. The equivalent-mutant control set has **zero** items, or every control is trivially paraphrase-only.
4. No reviewer arm can be run at matched total budget with a sequential single-agent control, all attempts logged.
5. Witness grading cannot be automated for at least two thirds of families.
6. At freeze, false-alarm rate on faithful pairs has an upper interval bound that makes the headline "catches drift" meaningless (e.g. detection interval overlaps false-alarm interval).
7. Prior-art check by a second reader finds a benchmark that already does witness-graded NL-claim→executable-test fidelity (my search did not; it was not exhaustive).

**Fallback:** polished baseline (A) plus the Thompson/Tallo + Turing worked examples as an honest "scope and operationalization" appendix, with the family-level result reported as a pilot without a collective claim.

## 6. Smallest decisive probe (do first, ≈1 hour)

Take 3 families with exact tests already in the repo (Turing, Kimura limit, Hawk–Dove). Mechanically produce 3 consequential + 1 equivalent mutant each (12 items). Run a single blind reviewer with the witness protocol. If it cannot distinguish consequential from equivalent on 12 items, scale-up is pointless; if it does so trivially (all 12), the task has no headroom and the family set must include harder (D2) items.
