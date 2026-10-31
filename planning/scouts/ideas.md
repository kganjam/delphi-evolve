# ScienceClaw 24h scout: ideas, shortlist, winner, and a hostile review of EvoRoute

Written 2026-10-30 (Seattle, PDT; the box clock was not read). Max ~10 tool calls were used, so this is a fast scout.
Every claim is tagged **[VERIFIED]** (I read the source this session), **[MEMORY]** (my recollection, not checked) or **[SPECULATION]**.

## 0. Verdict up front

1. **EvoRoute as written is not novel.** "Uncertainty-aware adaptive query selection on measured TrpB/GB1 landscapes with ESM2 priors" is what ALDE (Nature Commun. 2025) already does, and two further benchmarks reuse the same landscapes (section 2). Calling it path planning would also be wrong. A pitch built on it loses the first judge question: "how is this different from ALDE?"
2. **A narrower claim survives:** *query-to-certify instead of query-to-optimize.* For a measured landscape with replicate noise, certify noise-robust statements such as "route X→Y is open" or "no ascending route from X reaches Y", with the certificate **checked in Lean**. Then measure how few assays suffice to certify. I found no prior work doing exactly this (section 2.3). My search was shallow, so treat "found none" as weak evidence.
3. **Recommended winner: narrowed EvoRoute, renamed EvoCert** (section 5). It is the only top-3 candidate where I confirmed that the open data exist and the Lean theorem is small and real. GPU use is the weak point, and I say so below.

## 1. What the event judges (live site, read 2026-10-30)

Source: https://scienceclawhack.ai **[VERIFIED]**.

- Oct 30 – Nov 1, 2026, MIT Media Lab, in person only; 2–5 members; **one overall competition, no tracks**.
- Challenge areas: A·01 Biology & Protein Design, A·02 Physical Agency, A·03 Manufacturing & Materials, A·04 Open Scientific Challenge.
- Weights:

| Criterion | Weight |
|---|---|
| Scientific/Technical Impact | 25% |
| Collective Capability | 25% |
| Problem Significance & Complexity | 20% |
| Decentralized Agency | 20% |
| Execution and Validation | 10% |

  Collaboration bonus: up to +10. "Science is the benchmark." The page wants a "Functioning System" with "Result" and "Validation", and says a concept or architecture alone does not meet the bar.
- Prizes: E14 Fund $50K SAFE for an "E14-backable startup", a Formlabs Form Studio 1 printer, NVIDIA DGX Sparks, and $500 alphaXiv credits.
- Judges: Avijit Ghosh (Hugging Face), Desiree Plata (MIT engineering), Yilun Du (Harvard), Riken Shah (xAI), Ian Ferguson (Formlabs hardware), Nikita Fedik (NVIDIA).
- Final slides due **Sun Nov 1, 1:00 PM**; presentations 2:30 PM; awards 4:30 PM. The page gives no pitch length and **no live leaderboard**.
- The page gives no time zone. I assume Eastern (Cambridge). US DST ends Sun Nov 1, 2026 at 2am, so 1:00 PM Nov 1 ET is about **10:00 AM PST** in Seattle **[SPECULATION on zone, arithmetic standard]**.
- Delphi and Lean are not sponsors. They help only as a differentiator.
- **Note on weights:** Collective Capability and Decentralized Agency together are 45%, more than the science (25%) and validation (10%) combined. A single-pipeline demo is under-weighted. Whatever we build should be a thing other teams can call (an MCP tool, a certificate format). That also earns the collaboration bonus.

## 2. Challenge to EvoRoute

### 2.1 What already exists on exactly these landscapes

- **Johnston et al., PNAS 2024** **[VERIFIED via search snippets; the full text returned 403/429]**:
  - Combinatorially complete TrpB landscape at positions 183, 184, 227 and 228: 160,000 variants, with 159,129 (99.45%) quantified in both replicates.
  - Strong epistasis and many local optima; simulated directed evolution does not reach the global optimum efficiently.
  - 520 local optima, 5.3% of active variants; global optimum is AIKG (from the search summary; check against the paper).
  - Evolution-based predictors enrich for activity but cannot rank the top variants. The best variants carry a substitution that is almost absent in natural TrpB sequences.
  - Paper: https://www.pnas.org/doi/10.1073/pnas.2400439121; preprint: https://www.biorxiv.org/content/10.1101/2024.06.23.600144
- **ALDE (Yang et al., Nature Commun. 2025, DOI 10.1038/s41467-025-55987-8)** **[VERIFIED, PMC full text]**: https://pmc.ncbi.nlm.nih.gov/articles/PMC11739421/
  - Simulates on **GB1 and TrpB** four-site landscapes: 96 random starts, then 4 rounds × 96 queries, 70 seeds.
  - Acquisition: greedy, UCB (β=4), Thompson. Models: boosting ensemble, GP, DNN ensemble, deep-kernel learning. Encodings: AAIndex, Georgiev, one-hot, **ESM2**.
  - Also a wet-lab 5-site campaign (12%→93% yield).
  - Code and data: https://github.com/jsunn-y/ALDE (MIT); Zenodo record 12196802 (CC-BY-4.0; the Zenodo record lists `data.zip` at about 5.9 GB).
  - That is your "uncertainty-aware adaptive query selection + ESM2 prior", already published and open.
- **LLM-agent BO benchmark, ChemRxiv Nov 2025** **[VERIFIED via search snippet only]**: reuses the GB1/TrpB four-site framework at 60 and 480 query budgets. https://chemrxiv.org/doi/pdf/10.26434/chemrxiv-2025-w1wsh
- **"Feedback-Calibrated Protein Optimization with Batch-Aligned Tail Arbitration"** **[snippet only; the arXiv ID 2609.37808 looked odd, so verify before citing]**: reports Final@480 on GB1, PABP and TrpB, with ALDE leading on GB1. https://arxiv.org/html/2609.37808
- ICLR 2025 GEM workshop paper on benchmark risk (CVaR rankings) using GB1: https://arxiv.org/pdf/2504.00146 **[snippet only]**.
- Accessible-path analysis on combinatorial landscapes (Weinreich et al., 2006, and later work) **[MEMORY]**. It is why "does an ascending path exist" is a classical question, not a new one.

**Consequence:** on TrpB, any "we pick queries adaptively and beat random/DE" result is incremental to ALDE and these benchmarks. A judge who knows the field (Yilun Du plausibly does) will say so.

### 2.2 Where the "path" framing is weak
- On a complete landscape every path property is a graph computation. A Lean "path certificate" for a given path is trivially checkable and impresses nobody.
- The data are fully measured, so "adaptive query selection" is a retrospective simulation that reveals values already known. There is no prospective validation. Say that plainly rather than imply a wet-lab loop.
- The ESM2/BioNeMo prior is already one of ALDE's encodings. Johnston reports that evolution-based priors fail at the top end, so a prior-based router has a documented ceiling.
- GPU: ESM2 embeddings for 160k four-site variants need minutes on one H100 (roughly; I did not run it **[SPECULATION]**). GPU is not a differentiator for any idea here. Don't oversell it.

### 2.3 The precise contribution that remains (and its honest limits)
Define the ascent relation with the **measurement noise** from the two replicates: a step v→v' is *certified-ascending* if f(v') − f(v) exceeds k·σ, and *certified-blocked* only if the upper confidence bound says it cannot ascend. Then:

1. **Open-route certificate:** a path whose every step is certified-ascending. Easy to check.
2. **Blocked-route certificate (the interesting one):** a vertex set S with start ∈ S, target ∉ S, and S *closed* under possibly-ascending steps. Lean theorem: if S is closed under the ascent relation, then no ascent chain leaves S. The proof is a ~20–40 line induction. It is small, real, and generic. The counterexample is the set S itself, so it is checkable independently of the search that found it.
3. **Query-to-certify:** with a fraction of the landscape measured, plus an assumed epistasis/Lipschitz-type bound, how many assays certify open/blocked status for a start→target pair? This is the novel experiment. The assumption must be stated and tested on the real 160k data (calibration check: do certificates issued from a subsample hold on the full measured set?).
4. Delphi link: a nanopub claim of the form "route X→Y is blocked at margin kσ on dataset D (digest h), certificate c (Lean-checked)". This is evidence-linked rather than prose.

Limits: (a) a calibrated-assumption certificate is only as good as the assumption (name it in the pitch); (b) closed-set certificates may be large, so Lean checking may need `native_decide` or a reflected checker, which is a **risk** I did not test; (c) nobody has told me a reviewer wants this, so the claim is "I found nothing" not "it's novel".

### 2.4 Delphi fit (checked via the hosted MCP, source=network, 2026-10-30)
- Published network claims: darwin-origin-1859 247 (0 with math), thompson-growth-form-1917 104 (20 with math), **math-population-genetics 18 (all with math)**, morphogenesis 3, reaction-diffusion/Turing 3 **[VERIFIED]**.
- The local search for "epistasis" and for "fitness landscape" returned **zero** claims **[VERIFIED]**. Delphi has no landscape or epistasis claims, so EvoRoute would add a new domain rather than validate an existing one.
- Closest existing claims: Fisher fundamental theorem, Kimura fixation probability, neutral theory. Example: `https://w3id.org/delphi/resource/claim/kimura-fixation-probability`.
- That means "validate Delphi's Darwin/Thompson/Wolfram claims" and "EvoRoute" are different stories. Only the popgen claims connect (Kimura: probability a mutant fixes; blocked routes bound how often a walk can reach AIKG). Don't over-claim the connection.

## 3. Twenty ideas

Data availability for items other than the TrpB/GB1/ALDE data is **[MEMORY], not verified**. Check before committing.

| # | Idea | Real data | Lean angle | Visual simulator | Main 24h risk |
|---|---|---|---|---|---|
| 1 | **EvoCert**: noise-robust route certificates on TrpB (narrowed EvoRoute) | Johnston 2024 landscape; ALDE Zenodo [VERIFIED exists] | closed-set soundness | landscape route explorer, blocked basins in red | file location in 5.9 GB zip; novelty is narrow |
| 2 | Where ESM2 fails on TrpB: zero-shot vs measured, top-end failure map | same | none meaningful | heatmap by site pair | Johnston already reports the effect; incremental |
| 3 | Mechanobiology: durotaxis / YAP mechanosensing fit to public traction data | uncertain | ODE bounds | cell-on-gradient sim | datasets scattered; hard to validate in 24h |
| 4 | Turing patterns: fit a reaction-diffusion model to published stripe/digit data; Lean proof of instability conditions | published images only | Jacobian instability criterion | live pattern with a drug-like knob | extracting quantitative data from figures is slow; Delphi already has 3 Turing claims |
| 5 | Materials: uncertainty-aware screening on Matbench-style data | public | little | none | crowded benchmark, no novelty |
| 6 | GFP: avGFP deep mutational scan (about 50k variants, Sarkisyan 2016) epistasis audit | public figshare [MEMORY] | additivity bound | variant brightness map | overlaps #1; weaker landscape (not combinatorially complete) |
| 7 | DHFR combinatorial landscape (Papkou 2023, 4^9 genotypes) trimethoprim resistance routes | public [MEMORY] | same closed-set theorem | route map across drug dose | big data; same novelty problem as #1 but more clinical relevance |
| 8 | SARS-CoV-2 RBD escape routes from Bloom-lab DMS | public [MEMORY] | closed-set | antibody cocktail knob | heavy domain, many caveats |
| 9 | Base-editor outcome certificates (BE-Hive-type data) | public [MEMORY] | none | guide→outcome | little 24h differentiation |
| 10 | Promoter edit simulator from yeast MPRA (Vaishnav 2022) | public [MEMORY] | none | edit→expression | large data, GPU useful (real) but no Lean |
| 11 | Gap-gene network fitting on FlyEx data | public [MEMORY] | none | embryo stripes | parameter fitting is old; weak novelty |
| 12 | **Keio knockout essentiality vs FBA**, with LP-duality (Farkas) certificates checked in Lean | Keio growth data [MEMORY] | genuine, duality certificate | knockout on metabolic map, growth rate dial | FBA vs Keio comparison is old; the Lean angle is the only new part |
| 13 | Formlabs-printed lattice stiffness vs finite-element prediction | physical, hardware needed on site | bounds on beam model | stress colouring | printer access/time; unknown |
| 14 | Drug synergy (DrugComb): Bliss/Loewe axiom conflicts | public [MEMORY] | axiom consistency | dose-matrix | noisy; weak science |
| 15 | Allen Brain cell-type to morphology/electrophysiology mapping | public [MEMORY] | none | cell explorer | big data, no clear claim |
| 16 | Reaction-yield BO on HTE datasets (Doyle/Buchwald-Hartwig) | public [MEMORY] | none | none | crowded |
| 17 | Microbial community: generalized Lotka-Volterra identifiability from public time series | public [MEMORY] | identifiability proofs | community sim | data quality unclear |
| 18 | **Mega-scale protein stability (Tsuboyama 2023, 776k ΔG) thermodynamic-cycle audit**: double-mutant cycle closure errors | public [MEMORY] | cycle-closure lemma | stabilizing-mutation designer | needs the right data subset; cycle errors may just equal assay noise |
| 19 | Cardiac ion-channel drug-block ODE simulator (hERG/CiPA data) | public [MEMORY] | ODE invariants | ECG/action-potential live | safety-adjacent; validation thin |
| 20 | Fisher/Kimura fixation claim vs experimental evolution data (Delphi claim → data test) | Lenski LTEE-type data [MEMORY] | closed-form check | population sim | directly on Delphi, but "universal biology" and data fit are hard |

## 4. Shortlist of 10 and top 3

**Shortlist:** 1, 7, 12, 18, 19, 4, 6, 20, 13, 2.

Dropped, and why: 3, 5, 9, 10, 11, 14, 15, 16, 17 have weak novelty, weak data certainty, or no Lean or intervention angle.

**Top 3 (24h risk and tangible outputs):**

| | A: EvoCert (#1) | B: Keio/FBA duality (#12) | C: Stability cycle audit (#18) |
|---|---|---|---|
| Data certainty now | **Verified open** (but TrpB file path in the 5.9 GB zip not located) | unverified | unverified |
| Novelty | narrow but defensible (section 2.3) | Lean angle only | thin (noise explains closure error?) |
| Lean | closed-set soundness, small and real | duality certificate, medium | lemma is trivial |
| GPU value | low–medium (ESM2 prior baseline) | none | medium |
| Visual simulator | route map + "block a mutation / add an assay" | knockout dial on metabolic map (good visually) | ok |
| Biggest 24h risk | assumption-calibration result may be negative; Lean check on a large set | data wrangling and an old comparison | finding nothing beyond noise |
| Tangible outputs | certificate tool, Lean file, data-digest, nanopub draft, 3 plots | FBA solver + Lean file + demo | audit table |

## 5. Winner and pitch argument

**Pick A, EvoCert** (the narrowed EvoRoute). Reasons:
- It is the only top-3 idea whose real data I confirmed exist and are open (ALDE Zenodo; PNAS data).
- It has a Lean theorem that does real work and is not decorative: the *negative* certificate (a closed set proving a route blocked).
- A **negative result is a good outcome.** If subsample-issued certificates fail calibration on the full 160k, report exactly that. A measured "where certification fails" is science; a vague success is not.
- It sets up a company story that is not "yet another MLDE tool."

**Company (3-minute pitch skeleton):**
1. *Problem:* enzyme-engineering groups spend rounds of assays without knowing whether their intended evolutionary route is open or silently blocked by epistasis. Existing tools (ALDE, BO) recommend what to test; none says what has been **proven** about the route.
2. *Product:* a certificate service. Input: assay table with replicates. Output: Lean-checked open/blocked certificates with their assumptions, plus the cheapest next assays that would resolve the grey zone. Delphi/nanopub gives each certificate a citable, linkable record.
3. *Proof today:* TrpB 160k, replicate-aware; calibration of subsample certificates against the full measured landscape (a number, with its failure cases).
4. *Be honest on the ask:* buyer is unproven (**[SPECULATION]**); MLDE tools are free and open, so the moat is the audit format and Lean-checked guarantees, not the optimizer. The E14 prize rewards a backable company, so name the first customer type (protein-engineering CROs or academic enzyme labs) and the unproven assumption.
5. *Collective capability / agency (45% of the score):* expose the checker as an MCP tool and a certificate schema so other teams' agents can attach certificates to their own claims; that also targets the +10 collaboration bonus.

**24h deliverables (tangible):**
1. Locate the TrpB table in Zenodo 12196802 (or the Johnston PNAS data deposit) and record its SHA-256 and row count. If the file cannot be found in 2h, switch to GB1 from the same repo and say so. (~2h)
2. Python: replicate-aware ascent graph, closed-set/blocked finder, open-path finder. Run on the full 160k with CPU; one H100 job only for the ESM2 baseline (optional). (~5h)
3. Calibration experiment: reveal 1–10% random/adaptive subsets, issue certificates under a stated epistasis assumption, compare against the full data; report hit and false-certificate rates. (~5h)
4. Lean 4 file: closed-set soundness theorem plus a small reflected instance (a real local-optimum basin, small enough for `decide`). If the full set is too large, say it was checked by the Python checker only. (~3h)
5. Visual: a route-explorer page (positions as 4 axes; block/unblock a mutation; show certified open/blocked/unresolved). (~4h)
6. One Delphi nanopub-format claim draft (unsigned) linking a certificate to the dataset digest; do **not** claim it was published unless it is. (~1h)

## 6. What I did not verify
- I did not open the PNAS or bioRxiv full text (403/429), so landscape numbers come from search summaries.
- I did not locate the TrpB table inside the Zenodo zip, run any code, test Lean on a closed set, or check that the 2026 arXiv entry exists.
- All data claims for ideas 3–20 are from memory. No credentials were used or written.

## Sources
- https://scienceclawhack.ai
- https://www.pnas.org/doi/10.1073/pnas.2400439121 ; https://www.biorxiv.org/content/10.1101/2024.06.23.600144
- https://pmc.ncbi.nlm.nih.gov/articles/PMC11739421/ ; https://www.nature.com/articles/s41467-025-55987-8
- https://github.com/jsunn-y/ALDE ; https://zenodo.org/records/12196802
- https://chemrxiv.org/doi/pdf/10.26434/chemrxiv-2025-w1wsh ; https://arxiv.org/html/2609.37808 ; https://arxiv.org/pdf/2504.00146
- Delphi MCP (`delphisci`, source=network), queried 2026-10-30; read as context: `resources/research/nebius-compute.md` (1 H100/team, shared project) and `morphoswarm/docs/research/delphisci-mcp-and-nanopub-network.md`.
