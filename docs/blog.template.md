# Which experiment would justify the next step? A query-to-certify view of a measured enzyme landscape

*Darwin's Bridge / Delphi Evolve, ScienceClaw 2026 prototype. Every number below is filled from a saved artifact by `python -m evolve.evidence docs`; where an artifact is missing the text says so. This project performed no new wet-lab experiment; the source measurements were made by the cited study.*

## The question

A protein design is not a plan. Suppose you want to take the TrpB enzyme (tryptophan synthase β-subunit) from its parent sequence VFVS to the best variant in a published table, AIKG, by changing one amino acid at a time. Which mutation do you make first, which measurement does that choice rest on, and which experiment could prove the choice wrong?

The data are real: Johnston et al. (PNAS 2024) measured bacterial growth for essentially every combination of amino acids at four active-site positions (183, 184, 227, 228). Growth in that assay is a proxy for function, not a catalytic constant. The table is CC0 (CaltechDATA 10.22002/h5rah-5z170). Of {{landscape:counts.library_aa_genotypes}} possible four-residue genotypes, **{{landscape:counts.measured_non_stop}}** have replicate measurements in the file we used, **{{landscape:counts.unmeasured_cells}}** have none, and the source's KNN-imputed rows for those ({{landscape:counts.knn_imputed_rows_in_source_file}}) are never treated as observations (overlap with measured rows: {{landscape:counts.measured_imputed_overlap}}).

## What ran

| Item | State | Evidence |
|---|---|---|
| Landscape pack from the original CSV, with source SHA-256 | ran | `site/data/landscape.meta.json` (built {{landscape:built_seattle}}) |
| Delphi MCP queried live | {{delphi:n_ok}} calls succeeded, {{delphi:n_error}} failed | `artifacts/evidence/delphi_queries.json`, run {{delphi:run_utc}} |
| Nanopublication drafts, parsed with rdflib | all valid: {{nano:all_valid}}; unsigned, not published | `artifacts/evidence/nanopubs/` |
| Descriptive full-data route analysis | ran | `artifacts/evidence/route_summary.json` |
| Interactive site; browser logic cross-checked against a Python mirror | ran | `tests/test_evidence.py`; experience result: {{experience:status|not yet written}} |
| Core worker's audited loader, measured-graph truth, replay protocol | {{core:status|not integrated into this checkout}} | `tasks/results/core.json` |
| Lean conditional certificate (proof worker) | {{proof:status|not integrated into this checkout}} | `tasks/results/proof.json` |
| GPU foundation-model prior (BioNeMo / ESM2) | {{gpu:status|no result integrated; do not assume it ran}} | `tasks/results/gpu.json` |
| Retrospective assay-budget replay | benchmark status in demo.json: {{demo:benchmark.status|no demo.json integrated}} | `artifacts/core/replay/` |

Rows that say "not integrated" were not available to the experience worker when this page was rendered; they may exist on other branches. The integrator re-renders this file.

## What the measured data show (a descriptive analysis, not a benchmark)

We apply one rule to every single-substitution step: **a step is admitted only if the lower bound of the next genotype is at least the upper bound of the current one.** The bounds come from the measurements plus an *assumed* sensitivity κ (core's declared noise model: half-width = κ × replicate-difference SD for the genotype's read-count bin ÷ 2). κ is not a confidence level.

* Parent VFVS → highest measured variant AIKG differ at four positions, so there are {{route:direct_orderings.orderings}} direct orderings of the four substitutions. At κ = 0 — trusting every replicate mean exactly — **{{route:direct_orderings.admitted_at_parameter_0}}** are admitted: every direct ordering passes through a genotype measurably worse than where it came from.
* The shortest admitted route is not direct. It has **{{route:rows.0.measured_only_distance}}** steps at κ = 0, **{{route:rows.2.measured_only_distance}}** at κ = 2 (core's default) and **{{route:rows.3.measured_only_distance}}** at κ = 3.
* Some route exists only up to κ ≈ **{{route:break_points.readnoise_kappa}}** (bisection, measured genotypes only). Beyond that the answer is *no route certifiable in this declared graph at this bound* — an actual ascending route may still exist. Two simpler error models give the same qualitative break: replicate range ± ε breaks beyond ε ≈ {{route:break_points.envelope_eps}}, replicate mean ± ε beyond ε ≈ {{route:break_points.point_eps}} (growth-rate units).
* “No route certifiable” (the benchmark's and the browser's negative verdict) means no chain of steps with `lower(next) ≥ upper(current)` exists **in the measured four-residue graph under these assumptions**; overlapping intervals are not admitted, so an actual ascending route may still exist. The stronger statement — every ascending route ruled out — needs every exit certified lower and is checked only by the separate Lean strong-cut certificates. It says nothing about full sequence space, other assays, or biology. Unmeasured genotypes stay *possible* in any negative statement; the site reports "blocked" only if the route is blocked even when every unmeasured genotype is allowed to be perfect.

The same story in the browser: move the κ slider and the "tempting" route turns red at its failing step; the planner either reroutes through a different genotype or names the assay it would need.

Related work already analyses route accessibility on this table (Johnston et al.), and the ALDE paper simulates active learning on it. These results are descriptive instances of known phenomena (sign epistasis and detours), not a discovery. See `docs/novelty.md`.

## Query-to-certify, and what is not yet shown

The proposed contribution is not the regressor. It is to pose the engineering decision (is a route open, or cut?) as the object to certify, to choose assays that settle *that* decision, and to attach the decision to its evidence and scope. Evidence that this saves assays comes only from the retrospective replay, where each policy starts from the same observations and pays for measurements from an oracle: {{results:seeds}} fixed seeds, 100 episodes per policy, budget 1000 assays beyond the initial observations, unresolved episodes kept in the denominator. Fraction of episodes with a sound certificate at 1000 assays: random frontier {{demo:benchmark.metrics.primary_at_1000_family_all.random.cert_rate}}, greedy walk {{demo:benchmark.metrics.primary_at_1000_family_all.greedy.cert_rate}}, GP uncertainty {{demo:benchmark.metrics.primary_at_1000_family_all.uncertainty.cert_rate}}, our single deterministic best-first policy {{demo:benchmark.metrics.primary_at_1000_family_all.directed.cert_rate}}, query-to-certify (GP-priced) {{demo:benchmark.metrics.primary_at_1000_family_all.q2c.cert_rate}}, collective with shared evidence {{demo:benchmark.metrics.primary_at_1000_family_all.collective_shared.cert_rate}}, collective with isolated evidence {{demo:benchmark.metrics.primary_at_1000_family_all.collective_isolated.cert_rate}}. Paired against the best-first policy, query-to-certify differs by {{results:paired_contrasts.2.mean_diff}} (seed-cluster bootstrap {{results:paired_contrasts.2.ci_low}} to {{results:paired_contrasts.2.ci_high}}). The collective with shared evidence differs from the single query-to-certify policy by {{results:paired_contrasts.11.mean_diff}} at 1000 assays: no collective advantage was found. A no-model variant added after the first results certifies {{demo:benchmark.metrics.primary_at_1000_family_all.q2c_nomodel.cert_rate}} and is exploratory. The specialists are deterministic software objects in one process, not live language-model agents, and the shared and isolated arms differ in arbitration as well as evidence (a round-robin control for the shared arm matches it). False certificates are zero by construction, so that is a check, not a finding. All comparators are this repository's own policies; ALDE was not implemented or run. A closed (blocked) answer here means no route can be certified from the measurements and the assumed bound — not that no true route exists.

## The stronger baseline changed the conclusion

We subsequently implemented a node-query adaptation of established LazySP with exact optimistic A* search, the same paid-query oracle, initial observations and certificate rule. Its selectors were fixed before this follow-up, after the original experiment. The primary alternating selector resolves **{{lazysp:primary.certified}}/{{lazysp:primary.episodes}}** cases at1,000 additional assays; the original model-assisted Q2C resolves {{policies:q2c.all.1000.certified}}. The saved300 follow-up traces were re-read against the raw measurements and a fresh ledger with no discrepancies. Our model-assisted policy is **not demonstrated to beat established lazy path search**.

This is not broad superiority evidence for LazySP either: much of the completion-rate gap is one repeatedly tested endpoint pair, and the primary comparison's restricted-mean assay difference has an uncertainty interval including zero. The secondary forward selector used fewer assays on this panel. See [the complete follow-up and its exploratory analyses](lazysp.md). The value of this experiment is a decision benchmark that makes such corrections visible.

## Machine-checked certificate

The Lean project states interval-path soundness and separate weak and strong cut theorems, checks named dataset-linked certificates, and rejects meaningful mutants. The bridged VFVS→AIKG route has seven nodes; all seven integer intervals were independently re-derived from the raw CSVs exactly. The individual replay decisions were checked in Python, not each compiled in Lean. Status as rendered: {{proof:status|not available in saved artifacts}}; the original compiles, the axioms used are only propext and Quot.sound, and mutants that break the dominance inequality or open a cut edge are rejected by the kernel. The in-browser check on the site is *not* the Lean-checked object; the Proof tab shows nothing green unless `demo.json` carries a receipt with kernel exit 0 and a non-zero mutant exit.

## Delphi and Darwin

We queried the Delphi MCP live. Its local source reports {{evsite:overview.local.claims_total}} claims and its network source {{evsite:overview.network.claims_total}}; both are kept and labelled. Text searches for "epistasis" and "fitness landscape" returned no claims in either source — a limited text match, not proof that Delphi lacks related knowledge. We link our operational hypothesis ("on this finite measured graph, does a route with every step admitted exist?") to Darwin's chapter VI claim `darwin1859-ch06-08` as *motivation by analogy only*; it does not test, support or refute that statement, and Delphi's own LLM assessors rated it largely not empirically resolvable. The drafts (`artifacts/evidence/nanopubs/*.trig`) carry temporary URIs, no signature and no trusty URI; they are **not published** to any network.

## Existing claims now change execution

Historical Darwin links are context. They do not make the benchmark a test of Darwin. The separate `claim_runtime` demonstration uses existing Delphi **Kimura fixation-probability** and **Fisher fundamental-theorem** records operationally. A hand-authored adapter checks declared assumptions and the pinned source before it runs. An appropriate hypothetical diploid model computes; an attempt to reinterpret haploid E. coli growth as a selection coefficient refuses. A Fisher request that confuses a selection component with total change also refuses. Withdrawing or changing the source changes an otherwise valid decision to refusal.

This is not automatic theorem extraction. The source records and the additional assumptions introduced by the adapter remain separately visible. The recorded verification rejected {{claimcheck:mutation.guard_mutants_killed}} guard mutants and {{claimcheck:mutation.source_mutants_killed}} source mutants. The browser trace displays recorded executions; the Python CLI performs the calculation.

For evidence reuse, we replayed actual recorded measurement requests through ordinary caching and typed evidence reuse. In the same context they save the **same** repeated lookups: the graph's incremental count advantage is {{claimreuse:baseline.pooled.claim_gain_over_cache}}. The additional contribution is refusing deliberately mismatched contexts in software fixtures. Those tests do not establish adaptive-policy improvement or a wet-lab saving. See [the claim-reuse methods](claim-reuse.md).

## What the GPUs actually contributed

NVIDIA BioNeMo ESM2-650M produced a label-free prior for {{demo:compute.variants}} variants on a Nebius H100, with the successful job and artifact hashes saved. The companion analysis found weak zero-shot association with growth (Spearman about 0.17–0.18) and almost no added predictive value over one-hot identity in an optimistic random-split ridge comparison. The completed embedding run is not evidence that the prior improves the assay policy; that requires a separate matched replay. OpenResearch ran the companion analysis locally on CPU. See [the compute receipt and methods](compute.md).

[Anthropic's biomolecular-modeling study](https://www.anthropic.com/research/claude-uplifts-biomolecular-modeling) and [Adaptyv's experimental binder report](https://www.adaptyvbio.com/blog/anthropic-1) set a higher bar than an attractive generated sequence. We do not compete with their experimental binding results. Our narrower question is how a design decision acquires checkable evidence, and when a scientific model or measurement may legitimately be reused.

## From this prototype to inverse design

The long-term interface is a desired biological function, a proposed intervention, and the evidence needed to justify it. Neural cellular automata, bioelectric control and morphogenetic computation are possible future domains, but they already have substantial inverse-design prior art. A trained simulator matching its own targets is not independent biological validation. The reviewed [research synthesis](research/inverse-design-synthesis.md) keeps those directions separate from the completed enzyme experiment.

The immediate next study should use a prospectively frozen protocol and an independent assay context, retain the lazy path-search comparator and add an established active-learning baseline, and measure cost and time to a decision. Current error bins were fitted to all replicates; our uncertainty sweep is transductive sensitivity analysis, not held-out uncertainty validation. The panel repeats four endpoint pairs across initial observations, so its 100 episodes are not 100 independent biological targets.

## What this is not

Not a new enzyme, not a wet-lab result, not text-to-organism, not a proof of Darwin, not evidence that the approach beats ALDE (it was not run), and not a market claim. The commercial hypothesis — enzyme-engineering teams and CROs paying for fewer wasted assays and auditable experiment choices — is untested: no customer, market size or willingness to pay has been measured.

## Reproduce

```
python -m venv .venv && .venv/bin/pip install pandas numpy rdflib pytest
.venv/bin/python -m evolve.evidence landscape      # packs the original CSVs; needs the cached data
.venv/bin/python -m evolve.evidence delphi         # live MCP query
.venv/bin/python -m evolve.evidence nanopubs       # drafts + rdflib validation
.venv/bin/python -m evolve.evidence route-summary
.venv/bin/python -m evolve.evidence site-data
.venv/bin/python -m pytest tests/test_evidence.py
(cd site && python -m http.server)                 # then open http://localhost:8000
```
