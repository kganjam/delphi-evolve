# Coordinator resolution — 2026-10-31 02:23 PDT

- [x] Replay completeness: all 700 original and 400 post-hoc rows recovered/re-run with exact panel guards; original traces archived.
- [x] Collective comparison: completed, no completion-rate uplift over the single planner; control and isolation limitations reported.
- [x] Novelty: established LazySP comparator implemented and independently audited, no Q2C superiority claimed.
- [x] Proof recovery: smaller generic and concrete proofs compiled; the larger OOM example remains explicitly unverified.
- [x] Resources: GPU, OpenResearch, Gemini and structure calls have receipts; low-confidence structures are not functional designs.
- [x] Presentation: final deck, PDF, notes, video and provenance exist.
- [x] Turing and five-size prior follow-ups complete and separately checked.
- [ ] Final Site deployment and downloadable submission bundle. Actual competition upload requires organizer access; no submission receipt exists.

Current handoff is `HANDOFF.md`; historical intermediate failures remain below for provenance, not as current blockers.

# Historical blocker list — Oct 31, 2026, 00:35 PDT

- [ ] **Replay completeness.** Coordinator independently counted 140 original shard files: 35 have five rows, 105 have ZERO rows (seeds 5–19), although each has five query logs. Current summary therefore covers only five seeds and 25 episodes per policy. Integrator independently found the same bug and committed the missing `rows.append(out)` fix as 4398fad on work/integration. Do not quote these summaries as 20-seed results. Recover complete outcomes from actual saved query logs, or rerun the affected shards with unchanged policy/seed/protocol; retain the original files and provenance. Gate final aggregation on exact expected keys/cardinality, including all 100 episodes per original policy. Timing of recovered runs is unknown unless retained; do not invent wall times. No optional-prior change may alter an already-running benchmark implementation unnoticed.
- [ ] **Controlled collective comparison.** Core is adding a shared round-robin follow-up. This is exploratory after seeing first results. Preserve original seven-policy protocol and results; do not silently update the preregistration. Distinguish evidence visibility from arbitration. Deterministic software specialists are not live LLM agents; their useful behavior can still be measured.
- [ ] **Novelty.** In addition to ALDE, acknowledge lazy path evaluation and Bayesian decision-region determination. Primary sources read by coordinator: Dellin & Srinivasa, LazySP (2016), https://www.ri.cmu.edu/pub_files/2016/3/paper-lazysp.pdf ; Choudhury et al., Bayesian Active Edge Evaluation on Expensive Graphs, IJCAI 2018, https://ijcai.org/proceedings/2018/679 . Selecting expensive evaluations to settle path feasibility is established. Our proposed contribution is the enzyme-assay/evidence/formal-checking system and its measured behavior, not inventing query-efficient path finding.
- [ ] **Proof recovery.** Original proof worker scope was OOM-killed at 00:25:41 PDT. Recovery worker owns the SAME proof worktree; retains all edits, uses smaller/sequential certificate checks. Existing smaller proofs remain recorded; do not call uncompleted larger certificate verified.
- [ ] **New resource worker.** work/resources owns Gemini independent reviews and at most two Nebius structure API calls. Do not conflate predicted structure with enzyme function. See tasks/resource-update.md.
- [ ] **Presentation worker.** work/presentation owns presentation/, docs/company-hypothesis.md and its receipt. Creates six-slide HTML/PDF and a recording harness; final deck must require complete benchmark and exact proof semantics. Integrator should merge after review; coordinator deploys Site only after final data export.

These are release criteria; each should be resolved by actual artifacts or clearly disclosed as a limitation. User-facing summary can explain the idea without claiming a benchmark win. No external collaboration bonus is earned merely by making a tool downloadable.
