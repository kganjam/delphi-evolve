# Required integration correction: two different no-path claims

Coordinator source review, 2026-10-31 00:20 PDT. The core/browser and strong Lean cut theorem answer different questions. Keep both; do not conflate them.

- core graph.py and browser lib.js declare an admissible edge when L(next) >= U(current). Their blocked cut proves NO PATH OF GUARANTEED-ASCENDING EDGES under that fixed conservative rule. It does not imply no actual ascending path for all assignments inside the intervals.
- Lean blocked_cut_sound requires U(next) < L(current) across every outgoing edge. This is stronger: every boundary edge is certainly descending, so no actual nondecreasing path is possible under any assignment inside the declared intervals.
- Counterexample: A interval [0,2], B [1,3]. The first rule rejects A->B, so the conservative graph is blocked; the assignment f(A)=0, f(B)=3 permits ascent. This must be a named test and user-visible distinction.

Required UX: label the core/browser negative verdict 'No guaranteed route' or 'No route certifiable at this bound', with 'an actual ascending route may still exist'. Only show 'all ascending routes ruled out under the assumptions' when the STRONG cut has its own actual checked certificate. The site's current 'Blocked' wording is ambiguous even with graph-scope caveats. A closed set in the conservative graph can still be shown, but label its meaning precisely. Unknown genotype handling is a separate issue and does not fix overlapping measured intervals.

Required proof integration: map each receipt to its EXACT relation/score definition/interval policy/graph scope. Do not attach the strong cut theorem to the benchmark's weaker cuts. Generic closed_no_reach could certify the conservative relation too, but must state that relation. Keep the stronger real-data local-peak instance as a separate proof result. Rounding/micro-unit conversion must also match or be declared as separate instance rather than a live slider proof.

Benchmark protocol need not be changed: it measures query-to-decide reachability in its fixed declared conservative graph. Name it precisely in results/blog/pitch and don't claim impossibility of evolution. Do NOT rerun merely to alter the labels. If a model-training result uses both replicates and noise parameters estimated over the full dataset, call it retrospective/transductive sensitivity calibration, not an independently held-out replicate validation.
