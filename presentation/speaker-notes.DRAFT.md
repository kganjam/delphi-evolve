# Speaker notes (DRAFT)

Built 2026-10-31 00:40 PDT from 4398fad02ecc242fd58cd48a8c0d8c7051aa700c.

**Slide 1** (0:00-0:25)

A protein design is not a plan. Which mutation do you make first, and what evidence says the next step still works? This is the TrpB enzyme. The parent is VFVS, the best measured variant is AIKG, four changes apart. There are 24 orders to make them in. Taking the measurements at face value, every one of them steps down at least once. The dashed ordering is the most tempting one; it still falls. The orange detour is 6 steps, and every step is certified under an assumption we state.

**Slide 2** (0:25-0:55)

Every pixel is a measured enzyme variant: 159,129 of 160,000 four-residue combinations, from the published CC0 dataset, scored by cellular growth. 871 were never measured. We keep them unknown, and we used none of the authors' imputed rows as observations. This is a map of measurements, not of molecular geometry.

**Slide 3** (0:55-1:25)

Now challenge the assumption. The slider is how distrustful we are of each measurement. At zero, the shortest route has 5 steps; at the default, 6; at three, 7. By kappa 6 no route can be certified. That is not a claim that none exists, only that this evidence cannot certify one at this bound. The weakest step, SFMS to SIMS, clears by 0.0013. Click it and you see the raw rows. That is where the system asks for a measurement.

**Slide 4** (1:25-2:05)

DRAFT: replay is not final; do not present this slide until the deck is rebuilt in final mode.

**Slide 5** (2:05-2:30)

A decision should be checkable. The theorem: if every true value is inside its interval, and each step's lower bound clears the previous upper bound, the route never goes down. The Lean kernel compiled the original, exit 0, and rejected the flipped-dominance and open-cut mutants. Axioms are only Quot.sound, propext. The intervals are assumptions; two replicates are not a confidence theorem. The replay's decisions are not Lean-checked; only the routes are.

**Slide 6** (2:30-3:00)

The wedge is a decision and evidence layer above existing protein models, for enzyme engineering teams. Today it is a retrospective engineering tool on public data. The next real experiment is a prospective pilot with one enzyme lab: pre-register the rule, spend equal assay budgets, and measure cost and days to a defensible decision over 120 days. We have no customers or market size. The ambition: biologic design starts with justified enzyme experiments, not text-to-organism.
