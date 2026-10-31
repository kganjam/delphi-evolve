# Speaker notes

Built 2026-10-31 02:19 PDT from 6cbbd9da0eacfdb0c07c4e8736b95723e2f44a86.

**Slide 1** (0:00-0:20)

A protein design is not a plan. Parent VFVS, best measured variant AIKG: four changes, 24 possible orders. At face value, every direct order steps down at least once. The orange detour takes 6 steps, each certified under an assumption we state.

**Slide 2** (0:20-0:40)

Every pixel is a measured enzyme variant: 159,129 of 160,000 four-residue combinations, from the published CC0 dataset, scored by cellular growth. 871 were never measured. We keep them unknown, and we used none of the authors' imputed rows as observations. This is a map of measurements, not of molecular geometry.

**Slide 3** (0:40-1:05)

Challenge the assumption. Kappa is how much we distrust each measurement. The shortest route has 5 steps at zero, 6 at the default, 7 at three; by kappa 6, none can be certified. That does not mean none exists. The weakest step, SFMS to SIMS, clears by 0.0013: that is where the tool asks for a measurement.

**Slide 4** (1:05-1:50)

Does asking for the decisive assay save measurements? We added a stronger baseline from the literature: lazy path search, adapted to assay queries. At 1000 assays it certifies 96 of 100; our model-assisted planner 78; specialists sharing evidence 78, so no collective uplift. A post hoc arm without the learned model also reaches 96, but only 16 versus 43 at 250 assays. The gain over our planner sits mostly in one repeated endpoint pair, so we claim no superiority. One enzyme, assumed intervals, retrospective.

**Slide 5** (1:50-2:30)

Delphi claims become executable. Kimura and Fisher run through hand-authored, hash-pinned adapters with an applicability guard. A valid diploid calculation computes; a haploid E. coli transfer, or a TrpB score used as a selection coefficient, is refused. Withdraw or edit the source and the answer flips to refuse. Ordinary caching already captures same-context reuse. A Turing example is model-derived: the domain decides whether an unstable mode is admissible. Bounded knowledge execution, not theorem extraction; it does not improve the TrpB route benchmark.

**Slide 6** (2:30-3:00)

Lean checks the generic route and cut theorems, plus one seven-node route recomputed exactly from raw data, conditional on assumed intervals. The ESM2 prior is predicted, weakly correlated, not measured, and its use in policy replay is tested without a clear benefit. The contribution is compact: assay decisions with machine-checkable conditional certificates and typed reusable evidence. Not the first query-efficient pathfinding. Next: one lab, one prior campaign, one prospective round.
