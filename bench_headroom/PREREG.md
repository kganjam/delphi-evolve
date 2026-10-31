# Preregistration — Scope Desk bench v1.2 small headroom check (dx-guilds)

Written 2026-10-31 (Seattle PDT) before any model has seen a v1.2 item. Pushed on `work/guilds` before the run starts.
Requested by the director (director-to-dx-guilds.md item 4). Scoring requirements follow director-goals-scopedesk.md "ELECTRIC follow-up".

## Inputs (read-only; critic's tree is not touched)
Frozen bench read via `git show origin/work/rethink-critic:scopedesk/bench/v1_2/...` at critic commit 70c1254:
`model_payload.jsonl` sha256 `6c571db13a63d5dc8e8b5e5fadda601471f9a0a4fad6053f798395a48f78ee42` (127 items, id + prompt — the ONLY thing a
model sees), `key.jsonl` sha256 `28645a12f2f4c77fc1acedb10b23b4070832eefa381b88ca65a12b9e4ecdaa2f`, `split.json` for family roles.
The runner fails closed if either hash differs. The key is loaded only by the scorer after all responses are stored.

## Arms actually run
| Arm | What | Tokens |
|---|---|---|
| U unguarded | one model, prompt text only, no tools, one call per item, answer = one JSON object | counted per call |
| R always-refuse | answers `underdetermined`-free abstention on every item (coverage 0) — reference only, no model | 0 |
| B0 / constant policies | copied from the critic's committed `baseline_scores.json`, not recomputed | 0 |
**NOT RUN, stated in advance:** the "same model with the exact checker tool" arm. The salvaged tool server depends on the oracle layer
(`scopedesk/oracles`, not on this branch) and an MCP-enabled adapter path that this repository does not have; building and validating it
is out of this time-box. The host already measured two frontier models at 24/24 on scope traps with exact-count questions
(2026-10-31-LEAN-ENV message), so headroom for an unguarded model is expected to be small. A checker-tool arm remains open work.

## Models (two families, one fixed call each per item)
Claude Sonnet 5.5 (CLI, Max subscription) and Gemini 3.8 flash (event API key; thinking headroom per adapter). Account, served model and
tokens recorded per call via `lean_commons.adapters` (matched on number of calls: 127 per family; no retries on a wrong answer; up to 2
retries on transport failure, logged).

## Prompt (fixed, no tuning)
System text, hashed in the run record: "You answer one scoped-applicability question. Reply with ONLY a JSON object
{\"verdict\": \"applies\" | \"out_of_scope\" | \"underdetermined\"}. No other text." User text = the item's `prompt` verbatim.
A response that is not parseable to one allowed verdict is an ABSTENTION (not an error and not a refusal verdict).
No prompt tuning occurs. Dev families (turing_finite_domain, hawk_dove_ess) are reported separately only because the bench declares them dev.

## Metrics (all reported; per family and overall; exact Clopper-Pearson 95% intervals, item-level and descriptive)
coverage (answers issued / N); selective risk (errors / answers issued); accuracy counting abstention as wrong; false acceptance (answered
`applies` on gold out_of_scope or underdetermined / their count); false refusal (answered out_of_scope or underdetermined on gold applies /
gold-applies count); confusion matrix; tokens per call and per item. No utility figure is computed: costs were not preregistered.
Intervals treat items as independent, which they are not (families share generators): they are descriptive, not tests.
Effective n for generalisation is the 8 families, not 127 items; per-family tables are provided.

## Interpretation rules (written in advance)
If an arm answers >= 95% of items correctly overall, the headroom check says "no headroom for an unguarded model on this bench"
and nothing about agent collectives follows. A difference between the two model families is not a model ranking. Nothing here says a
pattern forms in any tissue: all items are declared-model, linear/closed-form checks. A null/ceiling result is reported as such.
