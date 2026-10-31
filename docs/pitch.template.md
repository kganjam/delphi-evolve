# Three-minute pitch — Darwin's Bridge / Delphi Evolve

Target length 3:00 at about 140 words per minute (about 420 spoken words). Numbers are rendered from saved artifacts; **do not say any number that this file marks as unavailable.** Demo: `site/index.html` served over HTTP. Fallback if the live page fails: the recording described in `docs/video-storyboard.md`.

**0:00–0:25 — hook (show the map, route drawn)**
"A protein design is not a plan. Which mutation do you make first — and what evidence says the next step will still work? This is the TrpB enzyme. Every pixel is a real measured variant: {{landscape:counts.measured_non_stop}} of the {{landscape:counts.library_aa_genotypes}} four-residue combinations, from a published CC0 dataset. The parent is VFVS; the best measured variant is AIKG."

**0:25–1:15 — the route breaks (drag the slider)**
"The obvious plan is to make the four changes in some order. There are {{route:direct_orderings.orderings}} orderings. With the measurements taken at face value, {{route:direct_orderings.admitted_at_parameter_0}} survive: every one passes through a variant measurably worse than where it started. The shortest route that never steps down takes {{route:rows.0.measured_only_distance}} mutations, a detour. Now I tell the tool how much I distrust each measurement — this slider is an assumption, not a confidence level. At the planner's default the route lengthens to {{route:rows.2.measured_only_distance}} steps; at three it takes {{route:rows.3.measured_only_distance}}. Past about {{route:break_points.readnoise_kappa}} no route is left, and the tool says *blocked in this measured graph* — not 'impossible', because {{landscape:counts.unmeasured_cells}} genotypes were never measured and stay possible. Click any step: raw replicate rows, read counts, the margin that failed. When the answer is undetermined, it names the assay to run."

**1:15–1:50 — does asking the right assay save experiments? (replay table)**
"We tested that retrospectively: each policy starts from the same observed variants and pays an oracle for each new measurement; unresolved cases stay in the denominator. Replay status in our artifacts: {{demo:benchmark.status|not available in the saved artifacts — say so, do not quote results}}. Read the primary table from artifacts/core/replay/table_primary.csv, including where the simple baselines win. ALDE already studies active learning on this landscape; we have not run it, so we make no claim against it."

**1:50–2:20 — certificate and evidence (Proof tab, Claims tab)**
"A decision should be checkable. The Lean statement is: if every true value lies inside its interval, a route of admitted steps never goes down, and a closed set with no admitted exit rules out a path in the declared graph. Whether it compiled and rejected a mutant is what the receipt says — proof status in our artifacts: {{proof:status|none integrated — show the Proof tab's empty state, which is the honest state}}. The intervals themselves are assumptions; two replicates are not a confidence theorem. The claim links to Delphi: we queried it live, kept local and network sources separate, and tied our narrow question to Darwin's 'numerous, successive, slight modifications' only as motivation."

**2:20–2:45 — reuse**
"Everything is an evidence bundle: unsigned nanopublication drafts that parse in rdflib — {{nano:all_valid}} — a JSON demo file, and a static page. We have not published them to any network, and we have not yet seen another team reuse them; that remains to be observed."

**2:45–3:00 — close**
"From scientific claims to experiments we can justify. Enzymes first; biological design next. The wedge is evidence-backed assay decisions for enzyme labs — a hypothesis we have not yet tested with a single customer."

## Likely questions (answer from the artifacts)

* *Is this new?* Route accessibility on this table is in Johnston et al.; ALDE simulates active learning on it. The proposal is the decision-and-evidence framing; the replay is what could support it. See `docs/novelty.md`.
* *Is ε/κ a confidence level?* No. It is an assumed sensitivity; the slider exists so the audience sees the decision depend on it.
* *Did you design or test an enzyme?* No. Retrospective, already-assayed variants; no wet-lab work.
* *Did a GPU model help?* GPU status in saved artifacts: {{gpu:status|none integrated}}.
