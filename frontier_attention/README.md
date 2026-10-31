# frontier_attention — attention and forecasting schema for the Frontier map

Library plus validators. **No persistence, no endpoint, no identity, no federation.** Everything is a pure function over
plain dicts; the transactional layer (Foundation worker, `kganjam/delphi-frontier`) owns storage, atomic leases and
authentication, and can test itself against the invariants fixed here. Review status: **single-reader, not Codex-reviewed, not independently reviewed**. Status: local, read-only pilot + unit tests; nothing
has been scored on real Frontier data because no decision models, signals, forecasts or ledgers exist yet.

**Premise.** An unguarded frontier model already scores ~95% on the frozen benchmark (Claude Sonnet 5.5 121/127, Gemini 3.8
flash 110/127). Nothing here assumes models are inaccurate. What an answer *unlocks* is a **decision** about reuse, scope or
allocation (the witness, the refusal, the repair), valued by how it would change that decision, including a negative answer.

## The five questions of a problem page → fields

| Question | Field (`schema.validate_profile`) | What the validator refuses |
|---|---|---|
| What do we know? | `known[]` `{statement, evidence_kind, source}` | an item without one of observed / predicted / simulated / formal / source_assessment, or without a source |
| What is open? | `open` `{question, open_kind, novelty_status, acceptance_criterion}` | no acceptance criterion; `searched` without scope+date (a failed search is not proof of novelty) |
| What would an answer unlock? | `unlocks[]` typed edges `{kind, decision_ref, independent_group, provenance}` | untyped edges; kinds are `logical_necessity`, `empirical_relevance`, `proposed_connection` |
| Who is working? | `working[]` leases `{operator, status, leased_at, expires_at, last_progress_at}` | missing times/operator. An empty list means *no recorded work*, not no work |
| Next bounded action? | `next_action` `{type, input_hashes, resource_estimate{basis:'estimate'}, stop_rule, acceptance_criterion, reviewer}` | unpinned inputs, no stop rule, no reviewer, an "estimate" labelled as measured |

## Value of information (`voi.py`) — what each answer would unlock

`EVPI = E_s[max_a U(a,s)] − max_a E_s[U(a,s)]`, `EVSI` for a real experiment with likelihood `L(o|s)`. Utilities, states and
the prior are **declared with a source**; the library invents none. Hand example (in the tests and `selftest`): reuse a result
(+10 if its assumption holds, −20 if not) vs skip (0), p(holds)=0.6 → EU(reuse)=−2, EU(skip)=0, EVPI=6; a test with
sensitivity 0.8 / specificity 0.9 → EVSI=4.0 ≤ EVPI. At p=0.9 the whole EVPI (=2) is the value of *finding the bad state*.

Rules that stop double counting: several routes to one decision count once; decisions that share an `independent_group`
(descendants of one result) are not additive — the group contributes its maximum; `proposed_connection` edges never enter the
headline; utilities in different units are not summed (value becomes `None`); decisions with no model are listed as
`unestimated` and the total is a stated lower bound.

## Signals (`schema.validate_signal`, `card.active_signals`) — four things, never merged

`following`, `can_contribute`, `resource_offer`, `blocked_by_this` (requires a concrete downstream link, otherwise it is just a
preference). Versioned and retractable, but only by the same operator. Counted by **operator**, not account. Never displayed
as a probability of truth. Resources: `offered → availability_checked → reserved → consumed | released`, with
`offered ≥ reserved ≥ consumed + released`, an unverified offer cannot be reserved, and a declared consumption is reported as
unverified (`credit.reconcile`). Attention credits (`credit.allocate_attention`) are bounded per operator and per problem,
merged per operator before the cap (splitting across rows does not help), verified operators only, and **there is no transfer
operation**. Credit for work (`credit.contribution_credit`) counts only independently accepted work; negative results,
replications, consolidation and corrections are first-class kinds; weights are a caller-declared policy, with none supplied
no total is invented.

## Priority cards and lenses (`card.py`, `policies.py`)

A card shows `consequence` (summed EVPI, with caveats), `cost` (estimate), `ready` (bounded and all `depends_on` resolved),
`staffed` (needs matched exactly against `can_contribute`), active leases, signal counts by operator, and the calibration
record of any forecast-derived prior ("none supplied" by default). Lenses are deterministic predicates and each says why:
`newly_actionable`, `blocking_downstream`, `seeking_review`, `neglected_important`, `exploratory`. No single score.
Policies: curator order, round-robin first cycle, value/cost, and one disclosed `coordinated` heuristic (ready, unleased,
value/cost, plus an explicit exploration share). Items with no declared value are unranked, never given one.

## Forecasting frontier events (`forecasting.py`) — reuses the Scope Desk scoring code

A prediction spec needs a defined yes/no event, a resolution criterion and source, a resolver who is not a forecaster, a
horizon and void conditions (`schema.validate_prediction_spec`). Scoring reuses `market.scoring` (Brier, log), `market.aggregate`
(mean, median, log pool, extremised), `market.calibration` (reliability table, error correlation). Added: void and
expired-unresolved events are counted and the report says the scored subset may differ systematically; late forecasts and
resolver conflicts are excluded and listed; a **family-first mean** (a dependence-aware heuristic, not a correction) is printed
beside the plain aggregates; `calibrated_claim_allowed` is always `False` for a handful of events. The diversity decomposition is
in `market.diversity` and is not used here.

## Allocation evaluation (`evaluate.py`, `prereg_eval.json`) — the decisive test, as a harness

Does coordinated allocation resolve more *preregistered, decision-relevant* uncertainty than a persistent sequential agent,
independent parallel workers and simple deterministic scheduling at the same budget? Refused if budgets differ by >5%
(`market.arms.check_budgets`); value per problem is the EVPI frozen and hashed before any arm runs (a changed table aborts); an
accepted result later overturned does not resolve the problem; a policy is "better" only with exact p < 0.05 **and** no worse
incorrect-acceptance count; with fewer than 6 problems there is no verdict (the seed map has seven). Generated questions,
messages and leases are not outcomes. No run exists.

## Read-only pilot on the seed map

`python -m frontier_attention cards --problems frontier-problems.json [--now ISO] [--out DIR]` reads the seed map
(`frontier-problems-0.1`, source commit `5165177` on `work/frontier-curation`) and prints a card per problem. Result on the real
seven records: **0 bounded, 0 ready, 0 with a consequence estimate**. The seeds carry prose where this schema needs structure
(`unlocks` and `next_action` are strings; no evidence kind; no input hashes, resource estimate, stop rule or reviewer; no
decision models). The adapter deliberately does not turn prose into structure, so the issue list is exactly what curation must
add before anything can be ranked or funded. F001 is blocked on F004 and F006 on F005 via `depends_on`; F007 is resolved.

## Commands

```
python -m frontier_attention selftest
python -m frontier_attention cards --problems P.json [--now T] [--out DIR]
python -m frontier_attention score-events --specs S.json --forecasts F.jsonl --resolutions R.jsonl --now T
python -m frontier_attention evaluate --rows ROWS.jsonl --frozen FROZEN.json --arms a,b,c
python -m pytest tests/test_frontier_attention.py          # 33 tests, hand-worked expectations
```

## Conflicts with the store models

Three real conflicts with `kganjam/delphi-frontier` `frontier/models.py` @ `1d014d1` (problem kinds, resource verification states, and the store's
inability to hold a typed unlock or a bounded action) are recorded as findings, not fixed: `STORE-SCHEMA-CONFLICTS.md`,
`store_conflicts.json`. Host ruling: the validators are not changed to match the store.

## Not claimed

Not a database, search index, MCP server or API. No identity or federation. No probability that a hypothesis is true. No
claim that coordinated allocation beats any baseline (no run exists). Utilities and priors in tests are *illustrative fixtures*
invented to exercise the code, not estimates about any real problem. Field names are a proposal; they agree with the store on evidence kinds and signal kinds and conflict on three points (see above).
