# Status

- [x] Read MorphoSwarm goals, core scientific/evidence specs, backlog and resource docs.
- [x] Consult three independent Claude Sonnet scouts.
- [x] Compare 20 ideas, narrow to 10, three and one: query-to-certify enzyme evolution.
- [x] Retrieve original CC0 TrpB data; coordinator independently counted 159,129 measured and 871 imputed non-stop variants, zero overlap.
- [x] Call Delphi MCP local overview and claim search; no epistasis hit in the limited search.
- [x] Check live judging rubric and competing ALDE work.
- [ ] Implement audited loader, finite genotype graph and assay-budget replay.
- [ ] Compile conditional Lean path/cut checker and kill meaningful mutants.
- [ ] Run bounded Nebius BioNeMo inference and compare with simpler baselines.
- [ ] Log an actual OpenResearch experiment.
- [ ] Build interactive site, blog, three-minute pitch and video storyboard from measured outputs.
- [ ] Integrate, reproduce, validate claims and deploy.
- [ ] Produce reusable evidence/nanopub bundle. Public-network publication remains distinct from a local draft.

Data cache: /data/artifacts/v2-scout/data/caltech/ (uncommitted source artifacts, tracked download manifest required).
Scout records: planning/scouts/. These are leads; their usage of “verified” does not replace coordinator checks.
Kickoff planning observation: 2026-10-30 11:48pm PDT (UTC−7). Internal 24h freeze target: 2026-10-31 11:48pm PDT.

Worker logs: /data/artifacts/delphi-evolve-workers/. Workers have isolated worktrees.
Official slide deadline interpreted in Boston venue time: Nov 1, 2026, 10am PST in Seattle. Internal target: first complete build within 18h, freeze within 24h of kickoff.

Spend: Claude subscription capacity selected after Orchestra cached-usage inspection. Probe and scouts completed on Sonnet. CLI dollar estimates are list-price estimates, not actual subscription charges. No metered API charge or GPU charge has been established yet. Brev access is currently unavailable on this host; resource scout found no login/CLI/key.

User additionally authorized up to $69 of OpenAI API credits. Credential is excluded from repository and worker prompts. No OpenAI spend initiated.

Four implementation workers launched in tmux: delphi-v2-core, delphi-v2-proof, delphi-v2-gpu, delphi-v2-experience. Managed Orchestra allocation confirmed Max subscriptions. Each has a six-hour process-tree runtime bound and a three-round task limit; coordinator must check receipts and continue unfinished work.

ChatGPT Site registered (not deployed yet): delphi-evolve. Hosting checkout /data/worktrees/delphi-evolve/site-hosting. Native registration is owner-private; expected URL is not proof of publication.

## Integration log
- 2026-10-31 00:08 PDT: independent recount reproduces 193,170 / 159,129 / 871 / overlap 0 (scripts/audit_data.py, exit 0). ALDE read: it already benchmarks on TrpB and GB1 in simulation; our claim is limited to query-to-certify. Workers have not committed yet.
