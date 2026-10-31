# Status

- [x] Read MorphoSwarm goals, core scientific/evidence specs, backlog and resource docs.
- [x] Consult three independent Claude Sonnet scouts.
- [x] Compare 20 ideas, narrow to 10, three and one: query-to-certify enzyme evolution.
- [x] Retrieve original CC0 TrpB data; coordinator independently counted 159,129 measured and 871 imputed non-stop variants, zero overlap.
- [x] Call Delphi MCP local overview and claim search; no epistasis hit in the limited search.
- [x] Check live judging rubric and competing ALDE work.
- [x] Implement audited loader, finite genotype graph and assay-budget replay.
- [x] Compile conditional Lean path/cut checker and kill meaningful mutants.
- [x] Run bounded Nebius BioNeMo inference and compare with simpler baselines.
- [x] Log an actual OpenResearch experiment.
- [x] Build interactive site, blog, three-minute pitch and video storyboard from measured outputs.
- [ ] Complete final fresh-checkout reproduction, deck/video, and final Site deployment (initial Site is deployed).
- [ ] Finish stronger LazySP baseline and model-size/prior ablations; publish actual outcomes.
- [ ] Finish bounded Turing domain/applicability example; do not conflate it with biological validation.
- [x] Produce reusable evidence/nanopub bundle. Public-network publication remains distinct from a local draft.

Data cache: /data/artifacts/v2-scout/data/caltech/ (uncommitted source artifacts, tracked download manifest required).
Scout records: planning/scouts/. These are leads; their usage of “verified” does not replace coordinator checks.
Kickoff planning observation: 2026-10-30 11:48pm PDT (UTC−7). Internal 24h freeze target: 2026-10-31 11:48pm PDT.

Worker logs: /data/artifacts/delphi-evolve-workers/. Workers have isolated worktrees.
Official slide deadline interpreted in Boston venue time: Nov 1, 2026, 10am PST in Seattle. Internal target: first complete build within 18h, freeze within 24h of kickoff.

Spend: Claude subscription capacity selected after Orchestra cached-usage inspection. Probe and scouts completed on Sonnet. CLI dollar estimates are list-price estimates, not actual subscription charges. No metered API charge or GPU charge has been established yet. Brev access is currently unavailable on this host; resource scout found no login/CLI/key.

User additionally authorized up to $69 of OpenAI API credits. Credential is excluded from repository and worker prompts. No OpenAI spend initiated.

Four implementation workers launched in tmux: delphi-v2-core, delphi-v2-proof, delphi-v2-gpu, delphi-v2-experience. Managed Orchestra allocation confirmed Max subscriptions. Each has a six-hour process-tree runtime bound and a three-round task limit; coordinator must check receipts and continue unfinished work.

Initial owner-private Site deployed: https://delphi-evolve.lefthill1.chatgpt.site (deployment appgdep_6ae596d12d608191a64d09796a68e7fb succeeded). Hosting checkout /data/worktrees/delphi-evolve/site-hosting. Final integrated update is pending; preserve owner-private access.

## Integration log
- 2026-10-31 00:08 PDT: independent recount reproduces 193,170 / 159,129 / 871 / overlap 0 (scripts/audit_data.py, exit 0). ALDE read: it already benchmarks on TrpB and GB1 in simulation; our claim is limited to query-to-certify. Workers have not committed yet.
- 2026-10-31 00:10 PDT: merged work/proof and work/experience into work/integration. lake build exit 0; axioms only propext/Quot.sound; 4/4 integrator mutants rejected; route table matches source CSV. Open: check_proofs.py missing, core/gpu not pushed. See tasks/results/integrator.json.
- 2026-10-31 00:27 PDT (integrator): merged proof 3960198, experience 3f41769, core bcc0729. Verified: 91 tests pass in a clean venv; check_proofs.py exit 0 in a fresh clone (26 instance + 8 Lean-source mutants rejected, axioms propext/Quot.sound); core kappa=2 route Lean-checked via bridge; independent recomputation of core's truth (8/8 kappa rows) and of route intervals (7/7). Open: core replay summary (117/140 shards at this time), GPU receipt, final docs re-render, fresh-checkout run of scripts/reproduce.sh. Blocked-semantics and collective-confound caveats are in planning/INTEGRATION-FINDINGS.md (F1, F6, F7).

## Release checkpoint — 2026-10-31 01:39 PDT

- Integrated the complete core replay (1100 episodes across 11 policies; 700 original, 400 post hoc), recovered original trace archive, Lean bridge, GPU sweep, source-pinned claim adapters and resource/research reports. Original q2c78/100 versus Directed32; shared78; posthoc no-GP96 at1000 but16 at250 versus43 for originalq2c. No collective completion-rate uplift.
- BioNeMo ESM2-650M on Nebius H100 completed160000 predictions; artifacts hashed and successful job tied to receipt. OpenResearch local CPU analysis completed. Gemini reviews and low-confidence Nebius OpenFold predictions have real receipts; neither is biological validation.
- Operational Kimura/Fisher claim traces now linked in the site. Same-context claim reuse equals ordinary caching; context mismatch gains are software-fixture results. Nanopublications remain unsigned drafts.
- Release checks: 18 passed, 1 skipped (optional network ESM2-8M test); another28 evidence/release checks passed. Desktop/mobile browser smoke passed with0 horizontal overflow,0 failed requests,0 page errors. Temporary demo generation now keeps audited repository certificates unchanged. These checks do not claim a full clean-host reproduction.
- Presentation worker was stalled after its final message on a stale background poll. Coordinator checked its clean/pushed tree, stopped only that owned scope, and restarted a bounded final-artifact task.
- Remaining: fresh checkout run, final deck/PDF/video, optional stronger comparisons and Turing example, final deployment and handoff. No competition submission receipt or prospective lab result exists.
