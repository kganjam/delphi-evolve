# SPEC-078 — Problem belief graphs: sensitivity, what-if and the next decision

**Status:** Draft · **Version:** 0.1.1 · **Owner:** G6 · 2026-10-26 (0.1.1, 2026-10-27: the
hypotheses schema gains `search_kind` and `split_artefact`, and §Concepts gains how a set was
searched and the refusal of a zero-`other` prior, from row M2497)

## Scope

For every attacked open problem that has at least two competing hypotheses, a SPEC-050 belief
graph compiled from the claim graph, and the three things a person or an agent does with it:

- **Sensitivity.** Find which evidence items, which sources and which assumptions the current
  weight of evidence rests on.
- **What-if.** Ask what would happen under a hypothetical result, without a source, or under an
  intervention.
- **The next decision.** Decide which action to take next, ranked by value of information and
  checked for whether that ranking depends on a prior nobody knows.

In scope:

- the problem's hypothesis set, and how it is drawn from recorded claims;
- compiling the graph from the claim graph with the existing compiler;
- the three analyses, their payloads and how they are persisted;
- routing the ranking into the SPEC-076 attack runner through SPEC-050's belief frontier;
- **the decision-model arm**, in which language models marketed for forecasting or decisions,
  and general models, give priors and rankings that are recorded as elicitations and compared with
  the graph, never substituted for it;
- the viewer at `/problems/<slug>/belief`.

Not in scope, and owned elsewhere:

- The calculus (decibans, independence classes, tiers): SPEC-019 and SPEC-049.
- Belief variables, factors, engines, `BeliefRun`, `blocked` and elicitation:
  [SPEC-050](SPEC-050-causal-factors-belief-graph.md). Nothing here adds an engine or a factor
  kind.
- The belief frontier's routing mechanics, the `belief_update` need and the complete denominator:
  SPEC-050 §Where updates matter most, built by M108 and M230. This spec gives the frontier its
  declared targets and its first consumer.
- Causal identification and do-queries: SPEC-021.
- The attack loop: SPEC-076 §The runner. This spec changes only how the runner chooses when a
  ranking exists.

## Motivation

The owner, 2026-10-26: *"we also want to show how we utilize a bayesian style, metaculus radiant
style … we want nice viz of the factor graphs, evidence for everything, sensitivity analysis,
what if analysis, how the evidence/causal/factor graphs help the engine in pursuing questions and
making decisions. we should also explore decision llm models (now all the rage) and how we
leverage and complement them to accelerate solving open problems."*

**The machinery exists. It has been aimed at one specimen.** All of the following are measured at
`origin/main` `c08420596`:

- The evidence and causal panels are phyllotaxis-specific. `studio/panels/evidence.py` builds "the
  competing mechanistic accounts of golden-angle phyllotaxis" and `causal.py` loads
  `studio/specimens/phyllotaxis-causal.yaml`.
- The engines exist (`evidence/belief/engines/`: exact, gibbs, loopy, compiled, crosscheck,
  withheld).
- So do the compiler (M102), elicitation (M106), the contingency map and what-would-change-my-mind
  (M97), decision journals (M228) and decision-conditional forecasts (M96). All are `passed`.
- The belief frontier (M108) and its denominator (M230) were pending when this account was
  written. Both subsequently passed and landed in `evidence/belief/frontier.py`.
- The attack runner chooses hypotheses by upper-confidence selection over *expected surprisal
  from elicited priors* (`attacks/runner.py`: `expected_surprisal`, `ucb_score`). So the only
  probabilities steering an attack today are the proposing model's own.

**Why most posteriors here must be `blocked`, and why that is the demonstration rather than a
defect.** SPEC-050 rule 15 forbids a probability for a variable with no reference-class prior of
enough resolved cases. "Source–sink versus shuttling for zebrafish BMP" has no such class. So a
compiled graph cannot honestly print "73% source–sink". It can print three things:

1. **How far the recorded evidence moves the odds between hypotheses, in decibans**, with every
   item accounted for by independence class.
2. **What the posterior would be under any prior a person chooses, or under a named
   elicitation's prior** (a decision model's, or an expert's), labelled what-if (SPEC-050
   rule 30).
3. **Whether the next decision changes as the prior moves.** When the best action is the same at
   every prior in the range, the decision does not need the prior, and the page can say so.

That third point is where decision models fit. A model's forecast is a prior, recorded as an
elicitation, with the model named. The graph adds what the model cannot: likelihoods from
recorded evidence, independence accounting, and a check of whether the choice of action depends
on that model's prior at all. The research behind this framing, and what decision-tuned models
are measured to do, is in
[`docs/research/decision-llms-and-belief-engines.md`](../docs/research/decision-llms-and-belief-engines.md),
which deepens
[`docs/research/forecasting-and-belief-platforms.md`](../docs/research/forecasting-and-belief-platforms.md)
(Radiant, Metaculus).

## Concepts

- **Hypothesis set.** The competing answers to one problem, each a `claim_truth` variable. Each
  entry carries:
  - its statement;
  - its formalization id where one exists;
  - its source, one of: a `hypothesis` step, a register mechanism class, or the model classes of
    a statistical formalization.

  The set declares whether its members are mutually `exclusive` and always carries an explicit
  `other`, because biological mechanisms combine and a set is rarely exhaustive. It also records
  **how it was searched** (`search_kind`, added 2026-10-27): `sampled`, the only kind a search
  that cannot certify a closed set may claim, or `exhaustive-split`, which is admitted only
  beside a `split_artefact` that names the closed set. A file written before the field existed
  records no kind, and is read as `sampled` with that absence recorded rather than passed off as
  a statement about coverage.
- **A prior that gives `other` no mass** (added 2026-10-27). Where the prior first enters, a
  range that records mass 0 on the explicit `other` is refused on a sampled set, because sampled
  search cannot show that the set is closed: a set is rarely exhaustive, and the search that
  produced it cannot prove otherwise. An `exhaustive-split` set may carry such a prior, but only
  beside an artefact that resolves, and only for a problem the register places outside biology:
  biological mechanisms combine, so `other` keeps mass above 0 whatever the search kind. How a
  problem is classed comes from its register entry's domain, never from its slug.
- **Credal range.** The set of priors under analysis. For a blocked target it is either a declared
  interval for each hypothesis or a set of named elicitations. Uniform over the hypothesis set is
  allowed only as a labelled convention. It is never presented as "no prior".
- **Robust action.** An action whose rank-1 position holds at every prior in the credal range.
- **Decision model.** Any language model asked for a prior over a hypothesis set or for a ranking
  of candidate actions. That includes models trained or marketed for forecasting or decisions. Its
  answer is a SPEC-050 elicitation by a named model and prompt hash, at a temperature and a date.

## Schema

```yaml
# data/problems/belief/<problem-slug>/hypotheses.yaml   (written by the compiler, reviewable)
problem: zebrafish-bmp-gradient-formation-mechanism
exclusive: true
search_kind: sampled          # sampled | exhaustive-split; added 2026-10-27
hypotheses:
  - id: h-source-sink
    statement: "..."
    formalization: sha256:…            # optional
    from: [step:<attack>/<NNNN>, register:mechanism-class:<name>]
  - id: other
    statement: "none of the listed mechanisms, or a combination"
compiled_from_commit: <sha>
uncompiled:                              # recorded and NOT in the graph, each with a reason
  - item: <evidence or step iri>
    reason: "null without recorded detection power"   # rule 4
```

```yaml
# the same file when the set was closed by an artefact (added 2026-10-27). The artefact is the
# record: nothing here is compiled to check it, and the `lean-split` path is resolved against
# the tree the resolver is pointed at.
search_kind: exhaustive-split
split_artefact:
  kind: lean-split                       # lean-split | language-coverage
  path: splits/<problem-slug>.lean       # relative to the resolver root
  receipt:                               # a VerificationResult (SPEC-009 §Proof receipt)
    subject_kind: claim
    subject_ref: ms:claim/<problem-slug>-split
    level: L2
    verdict: pass
    engine: <the engine that checked it>
    detail: {sorry_count: 0}
#   or a language-coverage record, which names the closed set it certifies:
#   kind: language-coverage
#   problems: [<id>, <id>]
```

> **The kind a file records (added 2026-10-27).** A file written before `search_kind` existed
> records no kind at all: it is read as `sampled`, with the absence recorded rather than passed
> off as a statement about coverage, and it is written back without the key, so the committed
> files stay byte-identical under an idempotent recompile. A third value is refused, an
> `exhaustive-split` without an artefact that resolves is refused, and a `sampled` set that names
> a `split_artefact` is refused: the kind that cannot certify a closed set does not point at a
> proof of one.

```yaml
# a BeliefAnalysis record (persisted, immutable; SPEC-049 rule 16 applies)
problem: str
belief_run: str                    # the SPEC-050 BeliefRun id it analyses
weight: {h_id: {decibans, independence_classes, items}}    # relative to `other`
posterior: {h_id: p} | {blocked: reason}
what_if_posterior: [{prior: {source: elicitation:<id> | person | convention:uniform, values}, posterior}]
sensitivity:
  items:   [{item, delta_decibans: {h_id: d}}]        # leave-one-out, sorted by |d|
  sources: [{latent, delta_decibans: {h_id: d}}]      # clamp a shared source to `systematic`
  prior:   {range, posterior_band: {h_id: [lo, hi]}}
what_if:
  outcomes: [{action, outcome, p_outcome | null, delta_decibans}]    # preposterior
  clamps:   [{latent, state, delta_decibans}]
  do:       [{query, result | non_estimable_reason}]                 # SPEC-021, where identified
decision:
  candidates: [{action, voi_by_prior: {prior_id: v}, cost_lines, robust_rank1: bool}]
  routed: [action]                  # via the SPEC-050 frontier; SelectionRecord id
  decision_models: [{elicitation, prior, ranking, agrees_with_robust_rank1: bool | null}]
```

## Rules

1. **A problem's belief graph is compiled, never drawn.** The SPEC-050 compiler (M102) builds it
   from recorded claims: hypothesis variables, evidence factors from SPEC-019 items, shared-source
   latents, logical edges as hard constraints, and `other`. A factor typed by hand is refused.
   Recompiling at the same commit gives the same graph hash.
2. **Only evidence enters as evidence.**
   - A `lead` (SPEC-077) never enters.
   - An elicitation enters only as a prior.
   - A simulation result enters as mechanistic support for model adequacy (SPEC-050
     §Mechanistic support), never as an observation of the organism.
   - An extracted literature claim enters at its tier, with its `extracted_by` visible, and its
     correspondence state bounds the tier it may carry (SPEC-019).
3. **Shared sources are latents.** Items sharing an author group, a code commit or a dataset get
   one SPEC-050 `source_error` latent. An agent's several results from one run of one model on
   one prompt share a latent too, because they are one source.
4. **A null result enters only with its detection power.** A null contributes a likelihood factor
   only if its attack recorded the probability that the method would have found a positive in
   the covered region (a recall, measured on planted positives). Otherwise it is listed under
   `uncompiled` with that reason, and it is still shown. Coverage without power says where nobody
   needs to look again. It does not say how unlikely the answer is.
5. **Every published number follows SPEC-050 rules 7, 15 and 30.** Every number carries an
   engine, an exactness flag, diagnostics and a run id. A target with no reference-class prior is
   `blocked`, and its decibans are shown. A posterior for a blocked target appears only as a
   what-if under a named prior, labelled what-if.
6. **Sensitivity is computed by the same engine on the same graph, and it is complete over what
   it names.**
   - Leave-one-out covers every compiled item, not a sample.
   - Every shared-source latent is clamped once.
   - The prior band spans the whole credal range.

   The page draws the top items, and the record holds all of them. An analysis whose run id
   differs from the graph's current run is shown as stale.
7. **What-if is three operations, each labelled, none of them a credence.**
   - **Hypothetical outcomes** (preposterior) for a candidate action. They use the action's
     recorded outcome model, or show `p_outcome: null` with the reason.
   - **Clamping** a source latent.
   - **A do-query**, only where SPEC-021 identifies it. Otherwise the record names the
     `NonEstimable` reason.

   No what-if result ranks an action except through rule 8.
8. **The next decision is ranked by M97's single VOI implementation, at every prior in the credal
   range, and ordered by Pareto dominance over VOI and each cost line** (SPEC-050 rule 32).
   - An action is `robust_rank1` only when it is first at every prior.
   - When no action is robust, the page says that the choice depends on the prior and shows the
     prior at which the order changes.
   - Every ranking run writes its SPEC-025 `SelectionRecord` (M230).
9. **The runner follows a ranking when one exists, and says when it did.** If the problem has a
   current ranking, the SPEC-076 runner chooses the robust rank-1 action. If none is robust, it
   chooses the rank-1 action under the convention prior and records that the choice depends on the
   prior. With no ranking it falls back to its UCB selection. Each step records which of the three
   decided it (`chosen_by: robust-voi | convention-voi | ucb`), so the comparison in SPEC-079 can
   count them.
10. **Decision models give priors and rankings, recorded as elicitations, beside the graph and
    never in place of it.**
    - At least two models are asked: one marketed or trained for forecasting or decisions where
      one is available through the fleet's providers, and one general model. If no
      forecasting-trained model is available, that is recorded as a gap. A general model is not
      substituted under the other label.
    - The question shows the hypothesis set and the evidence bundle's summary. It never shows the
      graph's own ranking.
    - Each answer is stored with its model, prompt hash, temperature and date (SPEC-050
      §Elicitation).
    - The page shows each model's prior as a labelled point in the credal range. It shows each
      model's top action and whether it matches the robust rank-1.
    - Agreement is reported as a count with its denominator.
    - **A model's probability is an instrument reading, not a credence.** The one independent
      audit of a decision model
      ([`decision-llms-and-belief-engines.md`](../docs/research/decision-llms-and-belief-engines.md))
      found its calibration error moving by 0.071 between two phrasings of one question, and
      71.6% of its answers at exactly 1.00. So before an answer is recorded:
      - the model's version is pinned;
      - the question is asked in two wordings, and the option order is swapped once;
      - an invalid option is refused;
      - an answer of exactly 0.00 or 1.00 is kept as given and flagged. It is never used as a
        prior until a recalibration on a labelled set has been recorded.

      The spread across wordings is shown beside the point.
11. **No claim that a decision model or the graph decides better without the pre-registered
    comparison.** The comparison is a secondary analysis in SPEC-079's pre-registration, scored on
    realized evidence weight. It asks whether the actions each ranking put first moved the
    decibans more once they ran. It is reported with its N and interval, or as "not enough
    resolved actions" when that is the truth.
12. **The viewer is generic.** It reads only the BeliefAnalysis record and the graph. It names no
    problem and no organism, which the domain-neutrality check (SPEC-076 rule 15) enforces. What it
    shows:
    - variables as circles, factors as squares coloured by evidence origin (SPEC-077), latents as
      diamonds, and constraints as bars;
    - blocked targets distinct from estimated ones;
    - the prior control with the posterior band and the decision models' points;
    - the tornado chart, the what-if controls and the VOI table, with each action's robustness;
    - for every node, the SPEC-077 evidence bundle one click away.
13. **Export to Radiant is optional and lossy by declaration.** The existing crosswalk
    (`evidence/crosswalks/radiant.py`) exports the graph as a qualitative map, and every term it
    cannot carry (decibans, latents, blocked) is listed as a loss.
    - What crosses is structure only. Radiant's own adapter in Metaculus's
      `map-forecasting-research` repository carries no numbers either way. It writes an `unknown`
      edge as `causal`, and it types every imported edge `causal`. So our export never sends an
      edge as `causal` that is not causal here.
    - Radiant documents no sensitivity, what-if or conditioning feature in the pages read on
      2026-10-26. Nothing here claims that it has them, or that it lacks them.
    - **Metaculus's terms bound what we do.** Its Terms of Use and its AI Products Terms (in
      force from 2026-09-21) restrict scraping and automated access other than through its API or
      MCP. They also forbid using its content or Radiant's output to train or evaluate AI models
      without written permission. So:
      - no Metaculus question or forecast data enters an evaluation here;
      - the reader route stays at documentation-reading scale;
      - anything systematic goes through the official API or MCP.

## Acceptance

| id | what | test |
|---|---|---|
| M2456 | Hypothesis sets and the problem belief compiler over the claim graph, for at least three attacked problems; `uncompiled` with reasons; same commit gives the same graph hash | `uv run pytest tests/test_problem_belief.py -q` |
| M2457 | Sensitivity: complete leave-one-out, every source latent clamped, the prior band over the credal range; persisted BeliefAnalysis | `uv run pytest tests/test_belief_sensitivity.py -q` |
| M2458 | What-if: preposterior outcomes, source clamps, do-queries where identified, each labelled and none ranking | `uv run pytest tests/test_belief_whatif.py -q` |
| M2459 | The next decision: VOI at every prior in the range, robust rank-1, Pareto over cost lines, SelectionRecord; the runner's `chosen_by` | `uv run pytest tests/test_problem_next_decision.py -q` |
| M2460 | The decision-model arm: at least two models' priors and rankings as elicitations, shown beside the graph, with agreement counted | `uv run pytest tests/test_decision_model_arm.py -q` |
| M2461 | The belief viewer at `/problems/<slug>/belief`, generic, with factor graph, prior control, tornado, what-if controls and VOI table | `uv run pytest tests/test_studio_problem_belief.py -q` |

## Open questions

1. **How wide the credal range should be by default.** Proposed: the hull of the named
   elicitations, widened to [0.05, 0.95] per hypothesis when fewer than two exist. The width is
   shown on the page, because a robust action under a narrow range proves little.
2. **Whether register mechanism classes are enough to seed a hypothesis set.** Some problems are
   questions of "how many" or "whether at all" (Lotka–Volterra limit cycles, Rule 30). For these
   the hypothesis set is a partition of the answer space, written in the formalization. A problem
   with no such partition is not compiled, and the page says why.
3. **Whether a decision model may see the evidence bundle.** Showing it tests the model as a
   reasoner over our evidence. Hiding it tests the model's prior knowledge. Proposed: both, as two
   elicitation questions, so that the difference between them is measurable.

## References

- [SPEC-050](SPEC-050-causal-factors-belief-graph.md) (rules 7, 15, 30, 32; §Belief frontier;
  §Elicitation; §Mechanistic support), [SPEC-049](SPEC-049-evidence-calculus.md) (M97, rule 16),
  [SPEC-019](SPEC-019-evidence-accumulation.md), [SPEC-021](SPEC-021-causal-graphs.md),
  [SPEC-025](SPEC-025-active-learning.md), [SPEC-076](SPEC-076-open-problem-attacks.md) §The runner,
  [SPEC-077](SPEC-077-claim-search-and-evidence-api.md) (origins and the evidence bundle).
- Existing rows this one builds on: M97, M102, M106, M108, M228, M230.
- Research: [`decision-llms-and-belief-engines.md`](../docs/research/decision-llms-and-belief-engines.md),
  [`forecasting-and-belief-platforms.md`](../docs/research/forecasting-and-belief-platforms.md),
  [`belief-inference-methods.md`](../docs/research/belief-inference-methods.md).
- The demonstration that uses it: [SPEC-079](SPEC-079-compounding-demonstration.md).
