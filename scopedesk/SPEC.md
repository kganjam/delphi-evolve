# Scope Desk interface contract (v0.1, director) — frozen unless the director amends it with a dated note

Selection and acceptance tests: `planning/rethink/DECISION.md`. This file only fixes interfaces so three workers can build in parallel in their own checkouts. Each worker writes ONLY its own subdirectory on its own branch; the director merges.

## Directory ownership
- `scopedesk/oracles/` — rethink-nca. Exact linear checker, nonlinear PDE solver, repair enumerator. Reuse `turing_scope/` (do not fork its arithmetic) and `experiments/rethink_nca/` solvers.
- `scopedesk/bench/` — rethink-critic. Instance generator, NL renderer, answer key, benign controls, deterministic baselines B0/retrieval.
- `scopedesk/arms/` — rethink-electric. Agent runner, accounting, commons, arms, stacker, analysis.
- `scopedesk/` root files, site, docs, results — director.

## Evidence kinds (every number carries one): `formal` (exact arithmetic/Lean), `simulated` (declared-model PDE solve), `observed` (measured data), `unknown`.

## Instance (bench → arms). Agents see ONLY `request_text` and their allowed tools.
```json
{"id":"ts-0001","family":"turing_finite_domain","stratum":"formal|simulated|descriptive",
 "request_text":"<natural-language request; may leave boundary condition or domain unstated>",
 "tools_allowed":["exact_modes","pde_solve","source_lookup","python"],
 "hidden":{"structured":{...}, "benign":false}}
```
`hidden` is stripped before any agent sees the item. The key file is `{"id","verdict","condition_ids","witness","expected_repairs"}` with `verdict ∈ applies | out_of_scope | underdetermined`. Key + generator source are sha256-hashed and committed before any agent run (`scopedesk/bench/KEY.sha256`).

## Agent answer (arms → scoring), frozen schema
```json
{"id":"ts-0001","verdict":"out_of_scope","p":{"applies":0.05,"out_of_scope":0.9,"underdetermined":0.05},
 "diagnosis":{"condition_ids":["DOMAIN_ADMISSIBLE_MODE"],"source_quote":"<verbatim from the pinned record>"},
 "missing_information":[], "repair":{"knob":"domain_length|reaction_scale|diffusion_ratio","value":"<exact rational or float>"} }
```
Scoring: verdict accuracy; Brier and log score on `p`; diagnosis correctness separate from flagging; false-alarm rate on `applies` items; repair success = oracle verdict on the proposed repair. Weakening a claim (declaring the request out of scope to dodge) is penalised because scoring is against the key, not the agent's declared scope.

## Condition IDs (shared taxonomy)
`BC_NEUMANN`, `BC_PERIODIC`, `BC_DIRICHLET`, `BC_UNSTATED`, `DOMAIN_ADMISSIBLE_MODE`, `NEAR_ONSET`, `LARGE_DOMAIN`, `WELLMIXED_STABLE`, `DIFFUSION_RATIO`, `LINEARIZATION_ONLY`, `ESTIMATOR_MEAN_VS_ENVELOPE`, `MECH_INPUTS_MISSING` (add with a dated note).

## Oracle API (Python, pure functions, exact where stated)
- `oracles.linear.check(structured) -> {"verdict","admissible_unstable_modes":[...],"witness":{...},"evidence":"formal"}` (Fractions; refuses with code on unsupported input).
- `oracles.pde.solve(structured, gamma=None) -> {"pattern":bool,"m_dom":int,"converged":bool,"evidence":"simulated"}`; convergence = dt halved and grid doubled agree; non-converged results are reported, never scored as success.
- `oracles.repair.enumerate(structured) -> [{"knob","value","linear_verdict","pde":{...}}]`.
- Gate with Delphi scope: `oracles.gate.decide(structured, records=..., pins=...)` with ablation flags `record_removed`, `record_hash_changed`, `continuum_only`.

## Arms (matched total input+output+tool tokens, counted by the runner and written to `arms/ledger.jsonl`)
B0 deterministic gate · R retrieval-only one-pass · S sequential single agent with tools + checker feedback · PL pooled single agent with all tools and union of evidence · P N parallel independent samples (vote/checker-select) · C guilds with different tool access via append-only `commons.jsonl`, pull-based claiming (each claim line records who chose what) · ST non-agent stacker on the same features. Optional model-family arm only with budget recorded and public data.

## Results files
`tasks/results/rethink-<role>.json` per role (status, commit, commands+exits, artifacts, limitations, next). Wall times from `date`, Seattle PDT; never guessed.
