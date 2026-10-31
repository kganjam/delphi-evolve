# lean_commons — verified-library experiment + multi-family adapter

What this is: a small, preregistered measurement of whether a **shared** library of kernel-verified Lean theorems
changes how many frozen targets are certified at a **matched budget of model calls**, against private libraries, one
sequential agent, no retention, and deterministic tactics. Plus the reusable pieces: a uniform model adapter with
per-call token accounting, and a sound checker.

Not a claim of novelty: shared/growing lemma libraries are published (LEGO-Prover, LeanAgent, Prove Together;
architecture credit Prove2Me arXiv 2608.28433); Berlot-Attwell arXiv 2504.03048 found no direct reuse after compute
adjustment in a LEGO-Prover re-evaluation. Read `PREREG.md` (with Addenda A–C) and `tasks/results/guilds.json`.

## Pieces
| File | Role |
|---|---|
| `adapters.py` | `make_adapter(family)`: claude (CLI, Max subscription), gpt (codex CLI, isolated CODEX_HOME), gemini (API), glm / minimax (Anthropic-compatible endpoints via managed key pool), grok (CLI; blocked while its account is rate-limited). One `complete()` returns text, provider-reported tokens, served model, account, cost basis. |
| `accounting.py` | Append-only token ledger with hard budgets; one JSONL row per call. |
| `lean_check.py` | Assembles frozen defs + verified library + agent helpers + the frozen target statement with the agent's proof; compiles with Lean 4.35.0 (core); audits `#print axioms`; rejects forbidden constructs. |
| `commons.py` | Append-only flock-serialised stores: `Commons` (verified lemmas with provenance) and `Board` (pull-based claims; no dispatcher). |
| `agent.py` / `experiment.py` | The prover loop and the arm runner. Arms differ only in which verified lemma text the prompt shows. |
| `deterministic.py` | Arm D: fixed tactic scripts, zero tokens. |
| `targets/`, `reference/` | 19 frozen statements + held-out reference proofs and rejected law mutants (`VALIDATION.json`). |

## Gotchas learned (each cost real time)
- Orchestra `acquire_credentials(preferred="glm"|"minimax"|"gemini"|"max_allen")` does **not** honour the name; it returns
  a Claude Max account. Record `creds.provider`; use the key pool for GLM/MiniMax; verify the served model from the response.
- Codex's own `~/.codex/AGENTS.md` and memories would reach the model; the adapter uses a throw-away `CODEX_HOME` with an
  auth symlink only.
- Gemini counts hidden thinking against `maxOutputTokens`; without headroom answers truncate (`MAX_TOKENS`).
- Core Lean has no `nlinarith`, `positivity`, `by_contra`, `ring`; the contract tells every prover so.
- For GLM/MiniMax the "served model" is the CLI's echo of the configured model name (label `cli_echo_of_configured_model`).

## Run
```
PATH=$HOME/.elan/bin:$PATH systemd-run --user --scope -p TasksMax=128 -p MemoryMax=4G -p MemorySwapMax=0 -p RuntimeMaxSec=1500 \
  python -m lean_commons.experiment --arm shared --family claude --agents 3 --max-calls 30 --budget 400000 --out OUT --run-id X
python -m lean_commons.run_registered      # all 12 same-model runs, fixed order (seed in ORDER.json)
python -m lean_commons.run_hetero          # heterogeneous arms
python -m lean_commons.analyze             # TABLE.json
```
