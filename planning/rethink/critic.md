# Critic decision memo 1 — strongest achievable idea, pitch, and kill criteria

Written Sat 31 Oct 2026, 06:00–06:20 PDT (wall clock from `date`) (UTC−7; zone changes to PST at 02:00 Sun 1 Nov). Model: Claude Sonnet 5.5 (subscription; no metered spend known). Branch `work/rethink-critic`. Machine-readable receipt: `tasks/results/rethink-critic.json`. Everything here is a **judgment by one reader**, source-only until the director or another worker checks it. No win probability is given and none can be defended.

---

## 0. Bottom line (read this if nothing else)

1. **No candidate I examined has a measured collective advantage today, and the rubric puts 45% on exactly that.** Our baseline measured a null (shared specialists 78/100 = single planner 78/100). Only a *new, preregistered* collective-vs-single experiment can change this, and it may also come out null. Plan the pitch so a null is still a coherent talk.
2. **Ranking (conditional, with kill gates in §7):**
   1. **Claims-as-tests, *narrowed* to an "applicability desk"** — GO conditional on gate K1 at ~09:30 PDT. Highest ceiling, but the headline must be about *scope-dependence of verdicts*, not new biology. Real size of the machine-decidable pool is **smaller than the pitch assumes** (§3).
   2. **Darwin's Bridge, hardened and re-told as an honest negative + decision layer** — the floor. Banked Execution; weak on Impact/Collective as the existing release stands.
   3. **Binder-triage on Adaptyv measured data** — *not for today's demo*; kept as the investible wet-lab pilot (§6). My wildcard check found usable public data and a weak, non-fusing signal.
   - **NCA / bioelectric inverse design: rank 4+, not for the entry.** I judge from the scouts' reports and primary sources cited there; I did not run them. Their own workers may overturn this with a measured result.
3. **The host memo (`morphoswarm-8c`) is half right.** Verifier-grounded adjudication is the right *kind* of design; its guaranteed-advantage arithmetic, its "free ground truth" scale, its GPU role, and its "decentralized via claim graph" claim all fail stress tests (§4). The decidability question it asked for: **partly collapses** — 33 of 92 math-bearing claims are machine-decidable as stated, only 15 non-trivially (§3).
4. **Tell the user plainly:** the event page says in-person only with all team members attending, and the only listed deliverable is final slides at 1:00 PM Sunday. I could not determine whether we are physically present or where slides are submitted. This is a gating fact for everything, and I cannot resolve it.

---

## 1. Live rubric, schedule, sponsors (fetched 06:00–06:10 PDT from https://scienceclawhack.ai)

**Listed on the page:** Problem Significance & Complexity 20; Scientific/Technical Impact 25; Decentralized Agency 20; Collective Capability 25; Execution & Validation 10; collaboration bonus up to +10 for "capabilities that materially strengthen other teams" ("not part of the core judging score"). Decentralized Agency asks whether agents have distinct information/resources/capabilities and coordinate "without a central planner prescribing the entire trajectory". Collective Capability names multi-agent vs single-agent, collaborative vs isolated, decentralized vs centralized comparisons.

**What to build (FAQ):** "a working decentralized agent system that makes measurable progress on a scientific or technical problem, with evidence or benchmarks". Teams may define their own challenge. Challenge areas: Biology & Protein Design; Physical Agency; Manufacturing & Materials; Open Scientific Challenge.

**Schedule (no time zone on page):** Sunday Nov 1 — "End of hacking – final slides due" 1:00 PM; Presentations & Judging 2:30 PM; Awards 4:30 PM. Venue MIT Media Lab (Cambridge, MA) → Eastern; 1:00 PM EST = **10:00 AM PST Seattle** (inference from venue, not stated). Presentation length not stated. **The "three-minute" length is our requirement, not the page's.** No submission link is on the page.

**Prizes/sponsors:** E14 Fund $50K SAFE (on incorporation of a backable startup), 3 NVIDIA DGX Sparks, Formlabs printer, $500 OpenResearch credits, "more to be announced". Organizer lab is Buehler's LAMM (MIT). **Not on the page:** Adaptyv, Delphi, FutureHouse (Edison Scientific is a sponsor/breakfast presenter), any Nebius/BioNeMo bonus points. Using those tools is our choice, not rubric points.

**Unverified:** whether the live judges use the page's text verbatim; whether an in-person-only rule is enforced for remote teams; any rubric detail not on the page.

---

## 2. Ideas (≥10), narrowing, reasons for rejection

Judgment criteria: (a) real measured or exactly checkable ground truth reachable today, (b) a baseline that could beat us, (c) a real decision that changes, (d) a collective measurement that is *possible* (not promised), (e) not already published.

| # | Idea | Outside TrpB/NCA/bio-electric? | Fate and reason |
|---|---|---|---|
| 1 | Darwin's Bridge (TrpB route certification) | no | Floor. LazySP-style 96/100 vs our 78/100; ALDE/BAEE not run; collective null. |
| 2 | Cross-landscape (GB1/DHFR) held-out certification | no | Extension of #1; adds replication, not a new idea; GB1 table not opened by anyone (scout `[UNV]`). Do only if #1 is the headline. |
| 3 | **Claims-as-tests applicability desk** (Delphi math claims → scoped test → exact check/open data) | yes (trees, shells, game theory, reaction–diffusion) | **Top 3 — rank 1.** |
| 4 | **Binder-triage collective on Adaptyv measured SPR outcomes** | yes | **Top 3 — rank 3 (pilot, not demo).** Wildcard check §5. |
| 5 | Rubisco threshold ledger (FutureHouse Problem 4) | yes | Reject for today: threshold auditing, not solving; one table with a no-licence repo; Flamholz 2019 plotted the same trade-off; weak collective story. Keep as outreach artifact. |
| 6 | Intervention-tested NCA | yes | Reject for the entry: scouts found no measured damage/regeneration benchmark; evaluation would be simulator-vs-simulator; inverse NCA is established. |
| 7 | Bioelectric control under uncertainty | yes | Reject for the entry: nearest work (`tlcdv/bioelectrics`, Jaxley, Manicka–Levin) already covers the machinery; ensemble ≠ calibrated biology. |
| 8 | Design-metric Goodhart audit on Adaptyv competition data (do designers who optimise iPTM/PAE get more binders?) | yes | Interesting, cheap, on the same CSV; organisers selected 400 of 1,131 designs so selection effects confound. Fold into #4 as an analysis. |
| 9 | Hidden-profile test for science agents (info asymmetry) | yes | Reject: HiddenBench (arXiv 2505.11556) already measures it (distributed 30.1% vs pooled 80.7%); only a coverage-mismatch distinction survives. |
| 10 | Mechanical-metamaterial/lattice inverse design with FEM check (Formlabs/LAMM fit) | yes (materials) | Reject: crowded; no printed specimen possible today; solver-vs-solver validation. Strong fit to the judges' lab — which means they have seen better. |
| 11 | Single-cell perturbation counterfactuals (public Perturb-seq) | yes | Reject: heavy data, crowded benchmark with strong linear baselines, hours of preprocessing. |
| 12 | Cloud-lab "physical agency" (order assays through a provider API) | yes | Reject: no credentials, spend or turnaround inside the window; do not fabricate integration. |

---

## 3. Red team: "Claims-as-tests" (the director asked for the hardest attack)

### 3.1 How many Delphi math claims are really machine-decidable? (host-memo falsifier, answered)

Fetched live from the hosted keyless MCP (`delphi_search_claims`, `mathOnly`, local source, 2026-10-31 ~06:05): **92 claims carry LaTeX** (Thompson 71, population genetics 18, Turing 3). **Wolfram (321) and Darwin (247) claims carry none, and 220 of 291 Thompson claims carry none** — 788 of 880 local claims have no math field; the "880" is coverage, not 880 testable propositions. Raw response saved: `planning/rethink/wildcard/delphi_math_claims_raw.json`.

I triaged all 92 by hand (**single reader — source-only; an independent second labeller has not confirmed scope or tier**; `experiments/rethink_wildcard/claim_decidability_labels.py`, output `planning/rethink/wildcard/claim_decidability.json`):

| Tier | Meaning | Count |
|---|---|---|
| D1 | decidable from the displayed math + trivial premises (exact arithmetic, limits, force balance, enumeration) | **33** (of which **18 trivial**: one-line algebra or definitions; **15 non-trivial**) |
| D2 | decidable only after the agent *authors a model/theorem the claim doesn't state* (PDE, ESS, variational, Laplace law) | 29 |
| E | empirical value/measurement; only data can adjudicate | 12 |
| P | prose/definition/heuristic, no decidable proposition as written | 18 |

Consequences, which the host memo does not state:
- **Free ground truth covers ≤33/92 (36%) of the math claims, 15 non-trivially.** The non-trivial D1 items are largely textbook geometry/limits (cos θ = −1/3, whorl ratio ↔ pitch angle, Hawk–Dove ESS, Kimura limits). A Sonnet will get most of those right on the first draw → **ceiling effect, no headroom for a collective to show a gain.**
- **Where there is headroom (D2), the verifier certifies the formalization the agent wrote, not that it is faithful to the claim.** Fidelity needs an independent check (human/other model rubric) that is itself unsound. This is the precise place a "verifier-grounded" story overreaches.
- The "prose with LaTeX decoration" worry is **true for 30 of 92** (E+P); false for the rest. The plan does not wholly collapse, but it shrinks to a pilot-sized benchmark.
- 92 claims is also too few instances for a clean paired comparison: an exact McNemar test needs ≥6 all-one-directional discordant pairs to reach two-sided p<0.05 (6-for-0: two-sided 0.031, one-sided 0.016; 5-for-0: two-sided 0.0625, one-sided 0.031 — the sibling `scienceclaw-hackathon-ideas` repo recorded the same power trap). Choose and preregister sidedness before running. Parameterised instances (Turing parameter sets, Kimura N_e/s, game payoffs) can be generated by the thousands with exact truth, **but they are not independent scientific claims** — the same caveat our 20-pair panel already carries.

### 3.2 The Thompson/Tallo probe (director's example) — what it does and does not show

**Which of these tests the original claim?** Per primary's read of Thompson pp. 19–20, the 3/2 power sits inside a self-weight buckling / limiting-height argument (uniform taper, branch-area law). Only the **bound-shaped** test (heights vs a buckling limit, bottom table) is aimed at that proposition, and even it is conditional on assumed E, ρ and a uniform-cylinder constant. The OLS, SMA, per-study and quantile-envelope slopes are **descriptive probes of related, different propositions (mean or upper-percentile allometry)**; they do not equally test the buckling claim and none confirms or refutes it.

I downloaded Tallo.csv (Zenodo 6637599, CC-BY 4.0; sha256 `bcd908a6…c8cd` matches the director's) and ran `experiments/rethink_wildcard/greenhill_envelope.py` (bounded, exit 0; output `planning/rethink/wildcard/greenhill_envelope.json`), n = 496,827:

| Operationalisation of "d ∝ h^{3/2}" (slope of log h on log d; claim implies 0.667) | Slope |
|---|---|
| pooled OLS (director's probe) | 0.588 |
| pooled SMA (errors-in-variables; OLS/\|r\|, r = 0.754) | 0.780 |
| gymnosperm OLS / SMA | 0.665 / 0.891 |
| upper envelope: slope of per-bin 99th-percentile height (14 log-d bins, all) | 0.632 |
| upper envelope, 90th percentile | 0.639 |
| per-study OLS median (52 studies, p10–p90) | 0.624 (0.499–0.737) |

And the bound-shaped test: Greenhill's critical height for a *uniform* cylinder, H_cr = 0.788 (E/ρg)^{1/3} d^{2/3}, vs measured heights. **With an assumed E/ρ grid, 0.09%–20.5% of trees exceed H_cr** (e.g. 2.8% at E = 6 GPa, ρ = 800 kg/m³; 0.6% at 10 GPa, 800), max ratio 2.3–4.7×. E and ρ are *assumed inputs, not Tallo measurements*; real trees taper and carry branch mass, which Thompson's text (pp. 19–20, per primary's read) also discusses — so exceeding a uniform-cylinder limit is not a refutation.

What this means for the pitch:
- **Different operationalisations of the Delphi claim's surface string give different numbers** (OLS below 2/3, SMA above, 99th-percentile envelope slightly below, the buckling bound violated by an amount that depends entirely on assumed E, ρ). They are **not four equal tests**: the source passage selects the bound-shaped statement as the one aimed at Thompson's argument; the slopes are labelled descriptive and kept separate. The honest product output is *"the source-faithful test needs inputs we lack (E, ρ, taper); the descriptive regressions are reported separately and do not decide the claim"* — not a confirm/refute. This is a scope-gating illustration, a **methods point, not biology**, and is a small specification curve in the many-analysts tradition.
- **It is prior art.** Tallo's own paper (Jucker et al. 2022) already compares the H–D exponent to 2/3 with mixed-effects models and reports lineage differences (primary's check), and McMahon's elastic-similarity literature long predates it. **Do not headline any slope.**
- The OLS-vs-envelope distinction was the right call by primary; the probe is a reproduction.

### 3.3 Is it "just known allometry"? What do Delphi claims change?

Yes for the biology. What can be new is *operational*: a claim is only reusable when it carries (i) the source passage's assumptions, (ii) an operationalisation, (iii) a checker, (iv) a refusal when the context lacks the assumptions. That exists partly (`claim_runtime`, `turing_scope`: Kimura/Fisher/Turing adapters; same-context reuse = ordinary caching, zero incremental gain). **The required ablation — remove/alter the Delphi scope record and show a *decision* changes — is demonstrable only for the few claims with non-trivial scope** (Turing finite domain; Kimura small-s/large-N_e regime; Rayleigh–Plateau length threshold; Greenhill uniform-vs-tapered; Hamilton's rule regression form). My estimate of that set from the triage is under ten claims; that is a number from reading, not a measurement.

### 3.4 What a multi-agent collective could add here (measured, not claimed)

Only these comparisons could be meaningful, each at **matched token/cost budget** with a **sequential single-agent with retries** control (primary's point):
- (S) single Sonnet, sequential attempts with checker feedback;
- (P) N independent parallel draws + checker selection;
- (C) role-separated agents with *different access* (formalizer / adversarial mutation-injector / data fetcher) coordinating through a shared append-only commons, pulling work themselves.

Outcome: fraction of frozen instances reaching a *verified-correct, faithful* verdict (faithfulness audited by someone other than the formalizer), and false-accept rate on mutated claims. **Prediction (a hypothesis I expect to be mostly null on D1 claims, possibly positive on D2 faithfulness/adversary tasks).** Needs only Claude Sonnet for the core. A model-family arm is an optional extra and the authorization is contradictory between the director note (Sonnet-only) and primary's review (other resources authorised; launcher limit is about worker auth). **Update 06:30: the user relays that PR5 clarifies experimental model authorization in `AGENTS.md`; I treat this conflict as resolved (not re-read by me).**

---

## 4. Stress test of the host memo `2026-10-31-rubric-strategy-from-morphoswarm-8c.md`

| Claim | Verdict |
|---|---|
| "45% is multi-agent and that's where we're weakest" | **Correct** (page verbatim). Best point in the memo. |
| "A collective *provably* wins under verification asymmetry; 1−(1−p)^N" | **Overstated.** Holds only for independent draws with constant p across claims, vs *one* draw; a fair comparison is equal-compute sequential retry with checker feedback. Draws from one model are correlated, p is heterogeneous (≈1 on D1-trivial, ≈0 on D2 until the model is authored). It is also a pass@k effect known from theorem-proving and code; not a collective-intelligence result. |
| "Machine-checked math is free, sound ground truth" | **Partly.** Sound for the *formal statement*, not for translation fidelity or biological applicability; covers ≤36% of the 92 math claims (§3.1). |
| "Model diversity vs sampling diversity is the novel headline" | **Worth one arm, not the headline.** A null is plausible and must be kept; results will be dominated by per-model skill differences unless budget-matched. Authorization unresolved. |
| "Plannerless coordination through the claim graph" | **Not by itself.** A shared log with roles is an orchestrated protocol unless agents choose their own next task (pull-based claiming) and the log shows assignment was not prescribed. Measure who picked what. |
| "H100s sweep millions of parameter points for counterexamples" | **Fails a direct test.** `experiments/rethink_wildcard/turing_scope_prevalence.py`: 10,000,000 random 2×2 Jacobians screened on **one CPU thread in 15.5 s** (exit 0). GPUs are decorative for closed-form/2×2 checks. The one number it surfaces — under an *arbitrary* sampling prior, 98.1% of continuum-Turing-passing systems have no admissible mode at L = π, 33.0% at 2π, 5.0% at 5π, 0.33% at 20π — is a scale-dependence illustration, not a prevalence of misapplied real models. |
| "The +10 is cheap" | **Cheap to build, hard to observe.** It needs an actual other team to call the service; outreach is not authorised without the user's say-so. Build the endpoint and the packet; do not count it. |
| "Six model families idle" | Out of my scope; authorization conflict above. |

---

## 5. The wildcard feasibility check (Adaptyv binder triage), with the methods fixes

**Question.** Using the public Adaptyv EGFR round-2 measured outcomes, does fusing independent computational "views" (structure confidence, protein-LM likelihood, sequence biophysics, novelty, length) beat the best single view for predicting measured SPR binding? This is a stand-in for "does a collective of heterogeneous scorers add capability?" **It is a statistical fusion of precomputed features, not an LLM-agent test.**

**Data.** https://github.com/adaptyvbio/egfr_competition_2 (`results/result_summary.csv`, sha256 `b98dd231…bd3`; repo licence field `NOASSERTION`; competition data public). 402 designs, 380 with a binding label (55 binders), 22 unexpressed/unknown excluded in the primary analysis. 110–111 designers. Round 1 (202 rows) fetched, unused. **Not accessible:** the Anthropic×Adaptyv 1,320-design Claude study (post says data/sequences "coming soon" on Proteinbase; Proteinbase page lists an active Anthropic×Adaptyv competition, Sept–Dec 2026, so its measurements cannot arrive in time).

**Frozen acceptance rule (written in the script docstring before the first run, not relaxed):** fused AUROC > best single view with the 95% group-bootstrap interval of the difference excluding 0.

**Result** (`binder_views_check.py`, `systemd-run` scope, exit 0; `planning/rethink/wildcard/binder_views_check.json`):
- Out-of-fold AUROC, random group 5-fold by designer: language-model view (ESM2 pseudo-log-likelihood per residue) **0.679**; biophysics 0.573; structure-confidence 0.539; novelty 0.505; length 0.507; fused of all views 0.610.
- **Frozen rule fails:** difference (fused − best single) interval [−0.173, +0.024] includes 0; fused < best single.
- Best single view interval [0.605, 0.762] excludes 0.5; pipeline-refit permutation null (200 shuffles, descriptive): mean 0.523, 95th percentile 0.595, max 0.627 vs observed best 0.679.
- Sequence-near-duplicate sensitivity (5-mer Jaccard ≥ 0.5 groups, 297 clusters): LM 0.703, biophysics 0.663, fused 0.697; difference interval [−0.082, +0.044]: **still fails**.
- End-to-end sensitivity (unexpressed counted as failure, n = 402): LM 0.644, fused 0.545–0.571.
- Format confound: ESM-PLL AUROC 0.74 among designs <150 residues (36/307 binders) and 0.69 among ≥150 (19/73); iPTM 0.71 / 0.63 within these strata yet the pooled structure view gives only 0.539 — a pooling/format effect I did **not** resolve.

**Methods caveats (primary's review, adopted):** folds are random *group* 5-fold, not literal leave-one-designer-out; anonymous usernames each treated as separate groups (assumption); bootstrap conditions on fixed OOF predictions (excludes training/split uncertainty); best-of-five-views is exploratory; the permutation is descriptive (designs treated as exchangeable), the p-value is not reported; labels are conditional on expression in the primary analysis; the 402 designs were chosen by the organisers from 1,131 submissions; Adaptyv's own write-up describes designers optimising the selection metrics, so metric–outcome relationships are Goodhart-contaminated.

**Reading.** Data are reachable in minutes and real (wet-lab SPR). A modest LM signal exists; **fusion adds nothing; no decision (which design to order) is shown to improve.** I do not promote any of this beyond "the data are usable and the collective-of-scorers idea fails its frozen test here." That fact lowers binder triage to rank 3 for today, in line with the earlier ESM2-prior null on TrpB.

---

## 6. Buyer, pilot, why the current product may not be needed

**Not fabricated:** no market size, customer, price or savings is given here; none exists in the repository.

**Candidate buyer (hypothesis).** Teams that *reuse published or internal mechanistic models* outside their native regime — systems-biology/QSP modelling groups, synthetic-biology teams, CROs selling model-based design — and a journal/consortium wanting machine-checkable applicability statements. The head of modelling (or whoever signs the experiment budget) is the economic buyer.

**Investible pilot hypothesis (falsifiable, no numbers invented).** *In a partner's last K model-reuse decisions, a declared-assumption gate flags at least one decision whose stated assumption (domain size/boundary, N_e·s regime, parameter range, operationalisation) was violated, and the partner confirms that knowing this would have changed the experiment or analysis chosen.* **Falsified** if zero decisions are flagged, or the partner says none would change, or flagged cases are false alarms on audit. Endpoints: partner-confirmed changed decisions, false-alarm rate, engineer-hours per audit. Design: retrospective on the partner's history first (preregistered gate rule, frozen before they reveal outcomes), then one prospective round. **Nobody has been contacted; this is a plan.**

**Wet-lab pilot alternative (binder triage).** Two arms of equal assay count, ordering designs ranked by (a) the lab's usual metrics, (b) a pre-registered alternative; primary endpoint cost per confirmed binder and end-to-end yield including expression failure. Any assay price/turnaround must come from the vendor, not me.

**Why the current product may not be needed.** (1) The established LazySP-style comparator resolved 96/100 vs our 78/100, so the "smart assay chooser" adds nothing a lab couldn't get from the simpler method. (2) Enzyme teams already pick variants with models plus judgement; nobody has shown the bottleneck is "is this route open?". (3) Lean certificates are conditional on assumed intervals the data don't establish; a buyer asks "are my intervals right?", which the certificate doesn't answer. (4) For model reuse, a scoped checklist plus a notebook may be enough: the claim that machine-checked applicability changes a *paid* decision is unproven.

---

## 7. Acceptance criteria, rejection criteria, kill gates (for the director)

**Hard rejections (reject any candidate that cannot meet these by the time shown):**
1. By 09:30 PDT: ≥ **8 independently checked non-trivial instances** (not D1-trivial) in which the verdict flips with a *declared scope* change (Turing π→2π is one). Fewer ⇒ Claims-as-tests collapses to a demo of one example → fall back to #2 with a candid pitch.
2. By 10:30 PDT: a frozen instance set with exact-checker truth **and** an independent faithfulness audit of each formalization (someone other than the author). No audit ⇒ no "machine-checked" in any slide.
3. A **Delphi-claim ablation** (remove/alter the scope record) that changes a decision on ≥ 3 instances, measured. Citation links alone do not count.
4. A **collective-vs-single comparison** with matched cost, a sequential single-agent control and all attempts logged, preregistered before the run. Report it whatever it shows. If it is null, the slide says so, and we do not add arms until one wins.
5. Any slide number must trace to a committed file; no slope, hit rate or AUROC from this memo may appear as a "finding" without the stated caveats.

**Acceptance (today, measurable):** a public, runnable `applicability` service/CLI: given a model and parameter regime, return {applies / refuses / underdetermined-needs-operationalisation} + the source passage, assumption list, checker output and (where relevant) the open-data descriptive probe kept separate from the mechanical statement. Fresh-checkout run; mutated-claim test fails closed.

**Lean (non-vacuous targets):** Turing finite-domain admissible-mode criterion (exists); Kimura u(p)→p as s→0 and → 1/(2N) at p=1/(2N), with a mutated-exponent rejection; Hawk–Dove ESS p* = V/C for C > V with a payoff-mutant rejection; log-spiral whorl ratio ↔ pitch angle (b₍ₙ₊₁₎/bₙ = e^{2π cot α}). None proves a biological statement.

---

## 8. Three-minute pitch (usable draft; fill only measured facts)

*Open (0:00–0:20) — the reveal:* "Slide the domain length from 2π to π. The textbook Turing condition stays green. The pattern disappears — and our checker says exactly why." (Visual: reaction–diffusion curve, admissible-mode dots, verdict flipping.)
*(0:20–0:50)* "Science reuses models. A claim is only safe to reuse inside its scope. We took the 92 claims in Delphi that carry math and asked a machine to test, not trust: by one reader's triage, 33 look checkable as written, 29 need a model someone must state, 30 are not checkable at all. We say that out loud."
*(0:50–1:30)* Second reveal: "Thompson's tree-height claim. A regression gives 0.59; Thompson's own argument is about a buckling limit, which needs wood stiffness and density we do not have for these trees. We show the regression as a descriptive probe, the limit test as the source-faithful one with its assumptions exposed, and we refuse to call the claim confirmed or refuted." (Figure from `greenhill_envelope.json`, bound panel primary, slopes labelled descriptive.)
*(1:30–2:15)* The collective, only with a measured result: roles with different access, shared commons, who-chose-what log, matched-cost comparison to a single agent. **If null:** "We tested it; here is the curve; here is why."
*(2:15–2:40)* "Our earlier enzyme-route planner lost to a simpler method and the specialists didn't help. We keep that result public. This system fails closed."
*(2:40–3:00)* "Next: a pilot that asks a modelling team to show us the last K models they reused, and measures whether our gate would have changed a decision."

Do **not** say: first, novel biology, proof of Thompson/Darwin, beats ALDE/LazySP, "solved", or any win likelihood.

---

## 9. What I did and did not do

Ran: Delphi MCP read-only queries; Adaptyv/Tallo downloads (hashes recorded); three bounded scripts (exit 0). Did not: read the NCA/electric workers' unpublished work; verify the Shenoy-lab mechanobiology comparison (not researched — unverified); check Anthropic/Adaptyv claims beyond the two pages cited (https://www.adaptyvbio.com/blog/anthropic-1: 1,320 designs, 16 targets, 354 binders = 26.8%, SPR, data "coming soon"; model-evaluated-by-wet-lab, which our retrospective setting cannot match); send any message externally.
