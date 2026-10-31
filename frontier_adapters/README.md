# frontier_adapters

Reusable Claim and Evidence adapters plus an unsigned nanopub-draft exporter for the Frontier store.
Single-reader (corpus session, Claude Sonnet 5.5), **not Codex-reviewed**. Nothing here submits, accepts, signs or publishes.

| module | does |
|---|---|
| `delphi_claim.py` | Delphi claim -> Frontier `Claim` draft. Keeps the original claim id/IRI, nanopub URI and registry (production/test). Never copies quote text (digest + locator only). Carries Delphi's source hash only after re-verifying it. |
| `orx_evidence.py` | OpenResearch (`orx`) run -> `Evidence` draft. Refuses failed runs, tampered snapshots, and kinds other than simulated/predicted. Records, per field, whether orx, the adapter, the run author or nobody supplied it. |
| `orx_replay.py` | EXPLICIT re-execution of an exported run (`trust_code=True`), with a mutation control that must change the output. |
| `nanopub_draft.py` | Frontier record -> unsigned TriG draft (four named graphs). Deterministic. Refuses private records, unlicensed available content, stored quote text, malformed IRIs. No publish function. |
| `bundle.py` | Claim + Evidence pinned to the Claim's exact version -> `records.json`, two drafts, `manifest.json`. |
| `delphi_mcp.py`, `common.py` | keyless Delphi MCP client with 429 backoff; hashing; read-only loader for the Frontier models (`$FRONTIER_PATH`) used only to validate. |

Run the tests (bounded): `FRONTIER_PATH=<delphi-frontier checkout> systemd-run --user --scope -p MemoryMax=4G -p MemorySwapMax=0 -p TasksMax=128 -p RuntimeMaxSec=300 env PYTHONPATH=. python3 -m unittest frontier_adapters.tests.test_adapters -v`
(without `FRONTIER_PATH`, 3 tests that need the real Frontier models are skipped and reported as skipped).

`examples/orx_run_turing/` is a real, path-scrubbed export of one OpenResearch run; `examples/turing_bundle/` is the proposed
Claim + Evidence + drafts built from it and live Delphi data; `examples/delphi_snapshots/` are recorded Delphi snapshots (no quote text).
