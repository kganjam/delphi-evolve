# Frontier MCP pilot

An actual local stdio MCP server over the same 21 pinned records as `site/review/frontier.html`. Uses the installed official MCP Python SDK 1.27.0; no package installation was required in this workspace. This is not the deployed Delphi MCP and has no public URL or persistent database.

Run with Python in an environment containing `requirements.txt`:

```sh
python experiments/frontier_mcp/server.py
```

An MCP host can launch that command with an absolute script path. In this workspace, process-spawning invocations must use the prescribed bounded `systemd-run --user --scope` wrapper. Do not mistake raw terminal silence for failure: stdio transport expects JSON-RPC, not conversational input.

Available tools:

* `frontier_search`: lexical retrieval with review-state filtering and pagination. No embeddings, entity resolver or measured relevance claim.
* `frontier_get_claim`: exact source/version, scope, evidence and proposed next action. Optional expected-version check rejects drift.
* `frontier_contribution_contract`: contribution/resource-offer schemas and implemented capabilities.
* `frontier_prepare_contribution`: validates schema and pinned claim version, returns an unsigned draft and deterministic payload hash.
* `frontier_prepare_resource_offer`: prepares an unsigned offer of compute, model inference, data access, review or instrument time.
* `frontier_list_problems`: lists the six open project questions or the resolved correction.
* `frontier_get_problem`: reads a seed, acceptance criterion, dependencies and deterministic version hash.
* `frontier_prepare_interest`: prepares an interest/help/resource/blocking signal tied to the problem version; returns its coordination link. It does not register the signal or cast a vote.

Resources: `frontier://review-map`, `frontier://claim/{claim_id}` and `frontier://problems`.

All operations are read-only. Drafts are returned to the caller, not saved or submitted. Author identity and artifact content are unverified. A supplied artifact hash is checked for syntax only. No signing, publication, resource reservation, spending or execution occurs. The scientific acceptance and scalable service design is in `planning/rethink/FRONTIER-MCP-AND-DATA-CONTRACT.md`.

`scripts/check_frontier_interfaces.py` exercises the server through an actual MCP SDK client and the map through Chromium, with successful and rejected contribution envelopes. Receipts are in `artifacts/integration/codex-api/frontier-interfaces/`. No external agent reuse is claimed by those local tests.
