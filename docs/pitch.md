# Three-minute pitch — Darwin's Bridge / Delphi Evolve

Spoken text below targets 3:00. Bracketed directions and the Q&A are not spoken. Numbers are rendered from saved artifacts; a missing result must never be improvised.

**0:00–0:25 — [show the landscape]**

“A protein design is not a plan. Which mutation do you make first, and what evidence says the next step will still work?

We built Darwin's Bridge: a system that asks which experiment would justify the next step. Our test bed is a published enzyme landscape: 159,129 measured variants, with 871 missing variants kept unknown.”

**0:25–1:00 — [draw the detour; increase the uncertainty assumption]**

“The parent and the best measured variant differ at four positions. There are 24 direct mutation orders. Taking the measurements at face value, none avoids a drop in recorded growth. A detour does.

Now increase how much we distrust each measurement. The route lengthens, then cannot be certified. That does not mean evolution is impossible. It means these measurements and assumptions cannot justify this route. Every step opens its evidence; every unresolved question stays visible.”

**1:00–1:40 — [show the Results bars]**

“Does this change which experiments we ask for? In retrospective replay, every policy starts with the same observations and pays for additional measurements. At a budget of a thousand, our model-assisted planner resolves 78 of 100 cases. A stronger baseline using established lazy path search resolves 96.

That result changed our pitch. Sharing between agents did not beat one planner. The contribution is an auditable decision process, not an algorithmic superiority claim. These are retrospective decisions on existing measurements, not new wet-lab results.”

**1:40–2:20 — [Proof tab, then the claim trace]**

“Lean checks a precise conditional statement: if the true values lie inside the declared intervals, the certified route never steps down. It does not prove that our biological assumptions are true.

Delphi supplies reusable mathematical claims. Our hand-authored adapters use existing Kimura and Fisher records, check their assumptions, and either calculate or refuse. Withdraw the source and the decision changes. A bacterial growth score cannot silently become a population-genetic parameter. A Turing-model example also checks whether the chosen domain admits an unstable mode. Reuse must preserve the assumptions that make a claim applicable.”

**2:20–3:00 — [compute receipt; return to the route]**

“We scored all 160,000 variants with NVIDIA BioNeMo on a Nebius H100. The prior was weak; we show that result too. OpenResearch ran the companion analysis locally.

Our ambition is biological inverse design where every proposed intervention carries its evidence, assumptions and next test. The first customer hypothesis is enzyme teams deciding which assay to fund. The next milestone is a prospective lab pilot measuring cost and time to a defensible decision.

From a promising design to an experiment we can justify.”

## Q&A — not spoken

- **Novel?** A systems contribution, not a new path-search algorithm. Johnston et al. analysed this landscape; ALDE, LazySP and Bayesian active edge evaluation are established. See `docs/novelty.md`. The completed LazySP-style follow-up reaches 96/100 with its primary selector, ahead of original Q2C78/100; its gain is concentrated in one repeated endpoint pair. A post-hoc no-GP arm also reaches96/100. This is not general superiority evidence.
- **Proved biology?** No. Conditional interval/path algebra and named finite certificates; not all replay episodes were Lean-checked. Error bins use all replicates and are a transductive sensitivity analysis, not held-out uncertainty validation.
- **Claims automatically extracted?** No. Existing Delphi source records feed hand-authored, source-pinned adapters. Kimura/Fisher calculations are separate from the TrpB route benchmark.
- **New proteins or organisms?** No. Retrospective decisions on already-assayed variants. Structure predictions are low confidence and do not validate a new design.
- **Nanopublications?** Valid unsigned drafts, not network publications. External reuse has not been observed.
- **Business?** A proposed pilot, no customer or revenue claim. See `docs/company-hypothesis.md`.


---
*Rendered 2026-10-31 02:18:04 PDT by `python -m evolve.evidence docs` from: claimcheck, claimreuse, core, delphi, demo, evsite, experience, gpu, integrator, landscape, lazysp, nano, policies, proof, results, route, scale. Edit `docs/pitch.template.md`, not this file.*
