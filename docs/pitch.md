# Three-minute pitch — Darwin's Bridge / Delphi Evolve

Target length 3:00 at about 140 words per minute (about 420 spoken words). Numbers are rendered from saved artifacts; **do not say any number that this file marks as unavailable.** Demo: `site/index.html` served over HTTP. Fallback if the live page fails: the recording described in `docs/video-storyboard.md`.

**0:00–0:25 — hook (show the map, route drawn)**
"A protein design is not a plan. Which mutation do you make first — and what evidence says the next step will still work? This is the TrpB enzyme. Every pixel is a real measured variant: 159,129 of the 160,000 four-residue combinations, from a published CC0 dataset. The parent is VFVS; the best measured variant is AIKG."

**0:25–1:15 — the route breaks (drag the slider)**
"The obvious plan is to make the four changes in some order. There are 24 orderings; taking measurements at face value, 0 survive — each passes through a variant measurably worse than where it started. The shortest route that never steps down is a detour of 5 mutations. Now I say how much I distrust each measurement — an assumption, not a confidence level. The route lengthens, then no route can be certified. The tool says *no route certifiable in this measured graph* — not 'impossible': an actual ascending route may still exist,: 871 genotypes were never measured and stay possible. Click any step for its raw replicate rows; when the answer is undetermined, it names the assay to run."

**1:15–1:50 — does asking the right assay save experiments? (Results section, 1000-assay bars)**
"Retrospectively, on real labels: every policy starts from the same observations, pays for each new measurement, and unresolved cases stay in the denominator. 20 seeds, zero false certificates by construction. At 1000 assays, random search certifies 0.21, our best-first policy 0.32, query-to-certify 0.78. Two negatives: the shared-evidence collective is no better than one policy — difference 0 — and the top arm, 0.96, was added after seeing results. Specialists are deterministic software, not live agents. We did not run ALDE."

**1:50–2:20 — certificate and evidence (Proof tab, Claims tab)**
"A decision should be checkable. In Lean: if true values lie inside their intervals, an admitted route never goes down; and a closed set whose every exit is certified lower rules out any non-decreasing path. The compiled original passes, and mutants that break the inequality or open a cut edge are rejected. The intervals remain assumptions. We queried Delphi live and link Darwin's 'slight modifications' only as motivation."

**2:20–2:45 — reuse**
"Everything is an evidence bundle: unsigned nanopublication drafts that parse in rdflib — yes — a JSON demo file, and a static page. We have not published them to any network, and we have not yet seen another team reuse them; that remains to be observed."

**2:45–3:00 — close**
"From scientific claims to experiments we can justify. Enzymes first; biological design next. The wedge is evidence-backed assay decisions for enzyme labs — a hypothesis we have not yet tested with a single customer."

## Likely questions (answer from the artifacts)

* *Is this new?* Route accessibility on this table is in Johnston et al.; ALDE simulates active learning on it. The proposal is the decision-and-evidence framing; the replay is what could support it. See `docs/novelty.md`.
* *Is ε/κ a confidence level?* No. It is an assumed sensitivity; the slider exists so the audience sees the decision depend on it.
* *Did you design or test an enzyme?* No. Retrospective, already-assayed variants; no wet-lab work.
* *Did a GPU model help?* GPU status in saved artifacts: none integrated.


---
*Rendered 2026-10-31 01:29:03 PDT by `python -m evolve.evidence docs` from: delphi, demo, evsite, experience, integrator, landscape, nano, proof, results, route. Edit `docs/pitch.template.md`, not this file.*
