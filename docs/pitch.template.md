# Three-minute pitch — Darwin's Bridge / Delphi Evolve

Spoken text below targets 3:00. Bracketed directions and the Q&A are not spoken. Numbers are rendered from saved artifacts; a missing result must never be improvised.

**0:00–0:25 — [show the landscape]**

“A protein design is not a plan. Which mutation do you make first, and what evidence says the next step will still work?

We built Darwin's Bridge: a system that asks which experiment would justify the next step. Our test bed is a published enzyme landscape: {{landscape:counts.measured_non_stop}} measured variants, with {{landscape:counts.unmeasured_cells}} missing variants kept unknown.”

**0:25–1:00 — [draw the detour; increase the uncertainty assumption]**

“The parent and the best measured variant differ at four positions. There are {{route:direct_orderings.orderings}} direct mutation orders. Taking the measurements at face value, none avoids a drop in recorded growth. A detour does.

Now increase how much we distrust each measurement. The route lengthens, then cannot be certified. That does not mean evolution is impossible. It means these measurements and assumptions cannot justify this route. Every step opens its evidence; every unresolved question stays visible.”

**1:00–1:40 — [show the Results bars]**

“Does this change which experiments we ask for? In retrospective replay, each policy starts with the same observations and pays for additional measurements. At a budget of a thousand, query-to-certify resolves {{policies:q2c.all.1000.certified}} of {{results:episodes_per_policy}} cases; directed frontier search resolves {{policies:directed.all.1000.certified}}.

The uncomfortable results matter too. Sharing between agents did not beat one planner. Removing our model later reached {{policies:q2c_nomodel.all.1000.certified}}, but performed worse at small budgets. That was an exploratory follow-up. This is a benchmark on existing measurements, not a new wet-lab result.”

**1:40–2:20 — [Proof tab, then the claim trace]**

“Lean checks a precise conditional statement: if the true values lie inside the declared intervals, the certified route never steps down. It does not prove that our biological assumptions are true.

Delphi supplies reusable mathematical claims. Our hand-authored adapters use existing Kimura and Fisher records, check their assumptions, and either calculate or refuse. Withdraw the source and the decision changes. A bacterial growth score cannot silently become a population-genetic parameter. Same-context evidence reuse matches ordinary caching; the added value is checking when reuse is legitimate.”

**2:20–3:00 — [compute receipt; return to the route]**

“We scored all {{demo:compute.variants}} variants with NVIDIA BioNeMo on a Nebius H100. The prior was weak; we show that result too. OpenResearch ran the companion analysis locally.

Our ambition is biological inverse design where every proposed intervention carries its evidence, assumptions and next test. The first customer hypothesis is enzyme teams deciding which assay to fund. The next milestone is a prospective lab pilot measuring cost and time to a defensible decision.

From a promising design to an experiment we can justify.”

## Q&A — not spoken

- **Novel?** A systems contribution, not a new path-search algorithm. Johnston et al. analysed this landscape; ALDE, LazySP and Bayesian active edge evaluation are established. See `docs/novelty.md`. The direct LazySP-style comparison is a separate follow-up; do not invent its outcome.
- **Proved biology?** No. Conditional interval/path algebra and named finite certificates; not all replay episodes were Lean-checked. Error bins use all replicates and are a transductive sensitivity analysis, not held-out uncertainty validation.
- **Claims automatically extracted?** No. Existing Delphi source records feed hand-authored, source-pinned adapters. Kimura/Fisher calculations are separate from the TrpB route benchmark.
- **New proteins or organisms?** No. Retrospective decisions on already-assayed variants. Structure predictions are low confidence and do not validate a new design.
- **Nanopublications?** Valid unsigned drafts, not network publications. External reuse has not been observed.
- **Business?** A proposed pilot, no customer or revenue claim. See `docs/company-hypothesis.md`.
