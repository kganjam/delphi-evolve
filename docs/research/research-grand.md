# research-grand: what is the strongest falsifiable result Delphi Evolve can still add in 24 h?

Written 2026-10-31 (Seattle PDT; the zone becomes PST at 02:00 on 2026-11-01), 00:56–01:09 PDT wall time (measured with `date`), by the `research-grand` worker.
Model: subscription Claude Sonnet 5.5 (`claude-sonnet-5-5`). Metered spend: unknown, not inferred. No GPU, no paid service, no message sent, no agent spawned.
Machine-readable companion: `artifacts/research/research-grand.json`. Result receipt: `tasks/results/research-grand.json`.

**Coordinator review:** this report records a scout assessment, not a prediction of judging outcomes. The later claim-runtime implementation now has source-withdrawal and applicability checks that change compute/refuse decisions; clean-context assay savings still equal ordinary caching. No collective completion uplift has been established. The exact finite-domain Turing applicability check is in `inverse-design-synthesis.md`. Rubisco pilot values below remain scout-reported; no paired-control enzyme assay was run.

**Evidence tags.** `[BODY]` I read the source body. `[RAW]` I inspected or computed on a raw artifact in this session. `[SNIP]` search-result summary only, not checked. `[TEAM]` an artifact on another team branch that I read but did not rerun. `[INF]` my inference. `[UNV]` not verified. WebFetch output is a small-model summary, so every number I rely on was re-read from raw HTML, a PMC body or a CSV.

---

## 1. Bottom line

1. **The current TrpB build is the more rigorous candidate; the NCA/electrical one is the more visual one, and its validation is simulation-only.** On rigor TrpB wins clearly. On presentation NCA would win, but only by showing a model of a computer cell that nothing measured can check. §7.
2. **The measured TrpB result is real but weaker than the pitch implies.** `[TEAM]` In the recovered 700-episode replay, q2c certifies 78/100 episodes at 1000 queries against 21/100 for random and 32/100 for the `directed` baseline. The collective adds nothing measurable: shared 78, isolated 77, q2c 78. Typed claim reuse equals plain caching (`claim_gain_over_cache: 0`). The judging rubric puts 45% on agency plus collective capability, and that is exactly where the evidence is empty. §6.
3. **The best new falsifiable 24 h addition is a held-out-landscape test, not another feature.** Freeze the policies and the assumption grid on TrpB. Evaluate once on a second, independent combinatorial landscape (GB1) against a strong lazy-search baseline. Add a misspecification stress test: how wrong can the assumed error band be before certificates become false? §4.
4. **The Millennium problem for which this scout located a directly usable comparison table is Problem 4 (Rubisco).** A first pass on a real table (§5) found that no measured natural Rubisco meets both thresholds, and the gap is about 2–3×. That is a decidable ledger entry, not a solution. The FutureHouse/Edison page states no prize and no evaluator. §5.
5. **Company wedge, honestly:** an assay-decision layer for enzyme teams is the only wedge with an existing measured artifact. It sits in a category where Cradle has raised funds (press report), and we have zero customer evidence. §9.

---

## 2. Strongest existing results and closest prior art

| Item | What it establishes | Tag | Consequence for us |
|---|---|---|---|
| ALDE, Nat Commun 2025, PMC11739421; code github.com/jsunn-y/ALDE, MIT | Wet-lab: protoglobin 5 sites, 216 random + 2×90 designed variants; yield 12%→93%/99%. Simulations on **both GB1 and TrpB** four-site landscapes: 96 initial + 4×96, 70 random inits, vs greedy DE walk and random. Frequentist ensembles best; ESM2 embeddings "little benefit". Authors list as open: how rounds scale with epistasis, choice of residues, only two complete datasets | `[BODY]` first 100,000 chars; last 5,269 not read | Optimisation on TrpB is not ours to claim. ALDE is the outside baseline we have not run. |
| Johnston et al., PNAS 121(32) e2400439121, bioRxiv 10.1101/2024.06.23.600144 | 160,000-variant TrpB landscape at 183/184/227/228; global optimum AIKG; 520 local optima (5.3% of active variants); accessible-path ECDFs; simulated DE methods compared | `[BODY]` bioRxiv via r.jina.ai; PNAS page 403 | **Path accessibility on this exact table is already published.** |
| Wu et al. eLife 2016 (GB1); Papkou et al. Science 2023 (DHFR, >260,000 genotypes, 514 peaks, high peaks reachable) | Indirect paths; ruggedness does not imply inaccessibility | `[SNIP]` | DHFR is the natural third landscape; data location unverified. |
| LazySP, Dellin & Srinivasa, ICAPS 2016 (arXiv 1603.03490) | Shortest path with expensive edge evaluation: search on an optimistic cheap estimate, evaluate only edges on the current best path, stop when it is fully validated; complete and optimal with an admissible estimate | `[SNIP]` | **q2c is structurally LazySP with unmeasured nodes treated optimistically.** The `directed` baseline should be exactly that, or a reviewer will say so. |
| SafeOpt family (safe-set expansion with GP bounds) | Expands a seed safe set using uncertainty bounds; reaches only optima reachable from the seed | `[SNIP]` | Same reachability question under uncertainty, different object. |
| FutureHouse/Edison Millennium Problems; de Pins et al. PNAS 2025 | See §5 | `[BODY]` | |
| Delphi MCP (880 local claims) | See §8 | `[RAW]` | |

Not found in my searches (stated as "not found", not as "absent"): a published *assay-count-to-certificate* benchmark on measured fitness landscapes; any use of LazySP-style search on protein fitness graphs.

---

## 3. Available raw measurements, code, licences

| Resource | Location | Licence / status | Checked |
|---|---|---|---|
| TrpB 4-site | CaltechDATA h5rah-5z170 (doi 10.22002/h5rah-5z170) | CC0 1.0 per record API; article CC BY-NC-ND (scout) | `[TEAM]` counts: 193,170 rows, 159,129 measured non-stop, 871 imputed kept apart. `summary_AA.csv` sha256 `a631d8cf…ee82`. I re-read the file: 9,783 active non-stop rows, `# Stop` coded `0.0`, `active` coded `True/False` |
| GB1 4-site | same zip, `data/figure_data/GB1_data/GB1_Fitness.csv` (scout) | CC0 record | `[UNV]` I did not open it |
| DHFR (Papkou) | not located | unknown | `[UNV]` |
| Rubisco kinetics, Flamholz 2019 | github.com/flamholz/rubisco `data/DatasetS2_RubiscoKinetics_Merged.csv` | **GitHub API reports no licence**; values are literature facts, cite and ask | `[RAW]` 399 rows, sha256 `98839cbc…d54d480`, every row 25 °C, all `mutant=0` |
| Rubisco carboxylation rates, de Pins 2025 | gitlab.com/milo-lab-public/rubisco_is_slow; paper CC BY per EPFL record | repo licence not checked | `[BODY]` PMC12663927: >250 new bacterial/archaeal rubiscos plus 190 literature rates; 440 sequences with rates; kcat,C only (no Sc/o); never above ~30 s⁻¹ at 30 °C; repo exists (HTTP 200); I did not download data files |
| Delphi corpus | hosted MCP `delphisci-mcp.fly.dev/mcp`, keyless | repository unlicensed: **use query outputs as data, copy no code** | `[RAW]` tools/list, graph, search, get_claim |

---

## 4. Ranked candidate projects

Ranking criterion: a falsifiable result on real measurements that the current build does not already contain. Confidence is in the evidence that the candidate can be executed and means something, not in a predicted outcome.

| # | Candidate | Real data in hand | Falsifiable? | Novelty risk | 24 h feasible | Confidence |
|---|---|---|---|---|---|---|
| 1 | **Landscape-held-out certification + misspecification tolerance** (TrpB→GB1, optional DHFR) | TrpB `[RAW]`; GB1 `[UNV]` | yes, pre-registered | medium: LazySP/ALDE adjacent | yes, CPU | **medium-high** |
| 2 | **Rubisco threshold-attainability ledger (Problem 4)** with clade-held-out predictor and a short assay-target list | table `[RAW]`; sequences `[UNV]` | the emptiness claim is refuted by one measured enzyme | medium: Flamholz 2019 plotted the same trade-off | ledger yes; predictor probably | medium |
| 3 | **Kimura-regime accessibility** (selective vs neutral steps on certified routes) | TrpB | yes, but conversion of growth to selection is explicitly *unsupported* per `[TEAM]` correction | low (population genetics is standard) | owned by `work/claim-reuse` | medium, **do not duplicate** |
| 4 | **Pattern Surgeon:** a perturbation that makes Turing and mechanical patterning diverge | none verified | only in simulation | low | pattern yes, validation no | low |
| 5 | **Electrical/NCA inverse design** of an ion-channel/gap-junction rule | none | simulation vs simulation | high (§7) | partially | low |
| 6 | **12-problem threshold ledger** (distance from best published to each threshold) | literature | per-row | medium | yes, but 8 of 12 are multi-year wet work | medium as an outreach artifact, low as science |

### 4.1 Top candidate in full: held-out-landscape certification (LHC)

**Question.** Does the query-to-certify advantage over a strong lazy-search baseline survive a landscape the policies were never tuned on, and how much assumed-error misspecification can a certificate tolerate?

**Exact input.**
- A measured table: genotype → per-replicate raw fitness (no `/max` column), plus read counts if present. Unmeasured genotypes kept separate and never imputed.
- An assumed half-width δ, swept over a grid fixed on TrpB before GB1 is opened. It is a sensitivity parameter, not a confidence level.
- Start/target pairs chosen by a rule that does not read held-out fitness: parent→published top variant, plus seed-sampled active starts with targets from the published top-k list.
- An oracle that reveals one row per query, and a budget B.

**Exact output per episode.** `certified-route` (path plus weakest-step margin), `certified-blocked` (closed set, labelled *within the measured graph*), or `abstain`. Also the full query log and a content hash. Unresolved cases stay in the denominator.

**Baselines.** random, greedy, uncertainty, `directed` (rewrite as LazySP on an optimistic graph), q2c, shared/isolated collective (all `[TEAM]` and already built), plus **one ALDE-style acquisition** (ensemble + UCB, MIT code) used as a query-selection policy with the same stop rule. ALDE optimises maximum fitness, not certificates; say so in the table.

**Held-out evaluation.** (a) held-out *landscape*: all hyperparameters, δ-grid and pair rules frozen on TrpB, GB1 run once; (b) held-out pairs; (c) held-out noise: certify at δ, then score against truth under 2δ and 0.5δ.

**Pre-registered hypotheses (fail conditions included).**
- H1: on GB1, q2c cert-rate at B=1000 exceeds `directed` with a paired seed-cluster bootstrap interval excluding 0. *Fails if* the interval covers 0.
- H2: policy ranking transfers (rank correlation between TrpB and GB1 above a threshold fixed in advance). *Fails otherwise.*
- H3: assays-to-certify tracks a ruggedness proxy (local-optima fraction or sign-epistasis fraction) rather than library size. *Fails if* it does not.
- H4 (misspecification): the false-certificate rate rises from 0 to a measurable value once the true error exceeds δ. The headline number is the **tolerated margin**, the δ-ratio at which the first false certificate appears. Zero false certificates under containment holds by construction and is *not* a result.

**Negative controls.** shuffled-fitness landscape (permute values among active nodes); Johnston's additive-plus-noise null; label-leak canary (policy given shuffled labels must collapse); Lean mutation (`≥` flipped to `<`, or a cut edge reopened, must be rejected); pairs fixed before any run.

**Realistic 24 h allocation** (≤2 CPU threads, bounded scopes): H0–2 audit GB1 and port the loader; H2–4 pre-register and freeze; H4–12 run replays; H12–16 controls and misspecification; H16–20 statistics and plots; H20–24 integrate and write up. I did not measure CPU time of the existing replay (488,601 paid queries over 700 episodes `[TEAM]`); consult core's logs before committing to seed counts.

**GPU vs CPU.** CPU carries everything on the critical path. GPUs are optional: ESM2 zero-shot priors on GB1 (56 residues) reuse the scale worker's pipeline, and the question is the one it already asks (prior vs shuffled prior). A null there is a result. Do not launch GPU work for this candidate.

**Conditional Lean statement** (extends what the proof worker has; do not claim until it compiles):
For a finite graph G and intervals containing f, every edge satisfying L(next) ≥ U(current) is non-decreasing in f. For a strong impossibility certificate, form the optimistic edge graph using U(next) ≥ L(current); a cut with no exit in that graph excludes a non-decreasing path under every interval-consistent assignment. A cut lacking only conservative admitted edges establishes no guaranteed route, which is weaker. Do not assign one global optimistic value to each vertex: an edge-wise relaxation may use different interval extremes. These statements are conditional on containment and graph scope.

**Novelty beyond a demo, stated narrowly.** A preregistered cross-landscape test with an external baseline, and a measured *tolerated-margin* metric for conditional certificates. Not a first, and not a new epistasis result.

**Why it may fail.**
- GB1 may be too connected or too sparse for any policy to separate; the advantage could be TrpB-specific.
- q2c may equal a properly written LazySP baseline. Then the honest result is "q2c is LazySP".
- Unmeasured GB1 nodes (about 10,639 of 160,000, `[UNV]`) change the graph semantics.
- DHFR is nucleotide-level and not the same graph.
- Replicate-range intervals are not confidence intervals; the tolerated margin is only as meaningful as the noise model.

**Cannot be verified without new experiments.** That growth in the *E. coli* auxotroph tracks catalytic activity (the paper's own kinetics cover three variants); that any certified route is walkable by a real population; that unmeasured genotypes behave as bounded; anything about enzymes outside these four sites.

### 4.2 Scout-grade probe (not a benchmark result)

I ran a read-only probe on `summary_AA.csv` (python `-I`, `systemd-run --user --scope` caps, exit 0). It uses the source's row-specific `mu_k-bg` columns, **not** core's score definition, so it is directional only. For the 9,782 active non-stop starts, the fraction with a non-decreasing path to AIKG (top raw value 0.358):

| assumed δ (raw units) | δ=0 | 0.01 | 0.02 | 0.05 |
|---|---|---|---|---|
| using mean values only | 89.6% | 80.3% | 55.6% | 3.7% |
| using mean ± half replicate gap | 88.0% | 78.3% | 51.3% | 2.9% |

The parent VFVS had a certified path at δ=0 and lost it by δ=0.01. This matches the direction of the proof worker's sweep `[TEAM]` (VFVS→AIKG route of length 5 at δ≤0.001, length 7 at 0.0025). It says the headline route is **fragile to small assumed error**, which is the most presentable single fact the build already has.

---

## 5. FutureHouse/Edison Millennium Problems for Biology

**What the sources say.** `[RAW]` raw HTML of both pages, HTTP 200 (27,345 B and 23,413 B).
- Published 2026-09-23, by Sam Rodriques; full author list Sam Rodriques, Michaela Hinks. FutureHouse is a nonprofit; Edison Scientific is its for-profit spinout (press: $70M seed, December 2025 `[SNIP]`).
- Framing: the list borrows the challenge format from mathematics, prioritizing difficult biological achievements with relatively straightforward experimental validation.
- **Prizes: none stated.** I searched the raw text of both pages for "prize", "$", "reward", "award", "funding": the only hit is the allusion to the *mathematics* Prize Problems. No amount, no evaluator, no submission process for solutions. The only action offered is a comment/proposal form and the address millenniumproblems@futurehouse.org. It is "a living project". **Do not call these prizes.**

The twelve challenges and their exact acceptance criteria are on the [official challenge page](https://millenniumproblems.bio/). This report examines Rubisco as the most tractable data-analysis connection located in this search.

**Which are tractable in 24 h without pretending.** This scout located a usable threshold-comparison table for **Problem 4**; the search does not establish that the other problems lack relevant public data. Problems 2, 6, 7 and 1 involve animals or de novo life and are out of scope. 8 and 9 are designed-protein tasks with a pass/fail wet-lab evaluator, and 9 touches intracellular targeting; I recommend not building them. No suitable ready-to-run threshold dataset was verified for Problems 3, 10, 11 or 12 in this search.

**Problem 4, paraphrase.** A candidate must combine carbon-dioxide/oxygen specificity matching the named *Galdieria partita* reference with turnover matching maize. Evaluation requires paired assays with those controls. The challenge page does not supply the comparative kinetics table.

**First pass on that claim** `[RAW]`, Flamholz 2019 table (399 rows, all natural, all 25 °C):
- *G. partita* Tokara: Sc/o 238, kcat 1.6 s⁻¹ (Uemura 1997). Maize rows: Sc/o 75–96, kcat 4.05–4.4 s⁻¹.
- 256 rows have both values; only 245 are distinct (species, Sc/o, kcat) triples (one literature value is reused across rows, so rows are not independent), from 216 species.
- Rows with Sc/o ≥ 238 and kcat ≥ 4.05: **none**. Only *G. partita* reaches 238. At kcat ≥ 4.05 the best Sc/o is 112 (*Poa palustris*, 4.2). The 15-row Pareto set runs from (238, 1.6) to (43, 14.4).
- Required step from the frontier: about 2.1× in Sc/o at maize-level turnover, or about 2.5–2.75× in kcat at *G. partita*-level specificity.
- 10 natural rows have kcat ≥ 4.05 but no Sc/o on that row (e.g. *Setaria viridis*, *Rhodobacter sphaeroides*, *Acidithiobacillus ferrooxidans*); some of those species have Sc/o on other rows. Measurements of those ten rows could complete this table's joint-value check, subject to compatible assay conditions; literature lookups alone may not supply the missing values. That is the whole query-to-certify content of this problem: it is a finite check, not a learning problem.

**Caveats that matter.** Heterogeneous labs and methods; the page names no strain or temperature for either control (its own rule is paired assays, which sidesteps absolute values); Flamholz 2019 itself reports that the kcat–Sc/o inverse relationship is substantially weaker in the larger set `[SNIP]`; the de Pins dataset adds kcat for >250 enzymes but not Sc/o `[BODY]`. A claim "no natural rubisco passes" is a statement about this table, falsified by one measured enzyme, and says nothing about engineered variants (the table has no mutants).

**Meaningful 24 h outcome (candidate 2).** A signed, hashed ledger: the table, the Pareto set, the empty joint region with fold-gaps under alternative controls, the duplicate-row correction, and a clade-held-out comparison of a clade-mean baseline against a sequence-embedding regressor for kcat (and Sc/o where sequences can be matched). Expected honest outcome `[INF]`: sequence models do not beat clade membership, consistent with Bouvier 2021's phylogenetic-constraint finding `[SNIP]`, which would argue for assay-first selection. No claim of solving Problem 4, no designed enzyme.

**Comparison with inverse-design cellular computation/electrical control.** Problem 4 has measurements and a decidable threshold; the cellular-computation framing has no problem on the list that it addresses, and no stated threshold. The closest list items (12 nitrogenase, 11 polymerases, 1 origins) are not electrical or computational.

---

## 6. Judging criteria, the existing pitch, and where it is weak

**Stated by `scienceclawhack.ai`** (fetched; weights cross-checked against `planning/PLAN.md`): Problem Significance & Complexity 20%; Scientific/Technical Impact 25%; Decentralized Agency 20%; Collective Capability 25%; Execution and Validation 10%. **Collaboration Bonus +10**, outside the core score, for capabilities that "materially strengthen other teams, such as a tool reused by another team". **Sponsor bonus: none stated.** The page describes shared compute, models and tools subject to availability. It does not specify points for using a named sponsor service; the user may have additional event guidance not published there. Prizes listed: E14 Fund $50K SAFE "on incorporation of an E14-backable startup", a Formlabs printer, NVIDIA DGX Sparks (quantity not stated in the page the coordinator read), $500 alphaXiv OpenResearch GPU credits; "more prizes will be announced". In person only; slides due Sunday 1 Nov 1:00 PM (venue time; 10:00 AM PST in Seattle after the zone change, `[INF]`). One competition with four challenge areas, not tracks.

**Read:** `docs/pitch.md` and `docs/novelty.md` on `origin/work/experience`; replay and claim-reuse artifacts on `work/replay-recovery` and `work/claim-reuse` `[TEAM]`.

**Strengths.** The pitch states what is established and what is not, labels the slider as an assumption, and refuses to quote unavailable numbers. That honesty is rare and will read as rigor.

**Weaknesses a judge will find:**
1. **The 45% bucket has no positive evidence.** Shared 78 vs isolated 77 vs q2c 78 of 100; the recovery note itself says "NO demonstrated collective uplift". Pitching "collective capability" without an uplift invites the lowest score on two criteria. Either run the preregistered round-robin ablation or reframe agency around what was measured (a single decision procedure that beats five baselines).
2. **The headline 78% vs 21% compares against weak baselines.** Random over 160,000 genotypes is a strawman, and the one strong comparator (`directed`, 32%) must be shown to be a faithful LazySP. Lead with q2c vs `directed`.
3. **Claim reuse currently equals caching** (`claim_gain_over_cache = 0`, 427,215 avoided assays either way). Deleting the historical Darwin links leaves route planning unchanged. The subsequently completed claim-runtime adapter now has withdrawal-sensitive compute/refuse decisions, separately from the route planner. Keep that distinction explicit.
4. **Script slots read "not available".** The three-minute script still contains placeholders for replay, proof and GPU. The strongest sentence the team already has is missing: *the headline route is certifiable at zero assumed error and breaks at a small one* (§4.2, and the proof sweep).
5. **No result about biology.** Everything is retrospective on already-assayed variants. The honest ceiling is "decision tooling"; the Significance score depends on the question being consequential, which §5 and §4.1 are the two ways to raise.
6. **Company claim is untested** (the pitch says so). Fine, but say it once.

---

## 7. TrpB route benchmark vs NCA/electrical candidate

I found **no NCA or electrical artifact on any origin branch** (file lists checked). The assessment is of the proposal as documented in local notes (`living-nca.md`, `ion-channel-rule-encoding.md`, `enhancer-voltage-transfer-function.md`), which I did not re-verify.

| Criterion | TrpB query-to-certify | NCA/electrical inverse design |
|---|---|---|
| Real measurements | 159,129 measured genotypes, CC0 `[RAW]` | none that validate a design; electrophysiology exists but not for the designed object |
| Truth definition | finite measured graph; declared | simulated target pattern; the simulator is the truth |
| Falsifiable by an outside party | yes: rerun from hashed data | only against its own model |
| Prior-art exposure | ALDE, LazySP, Johnston, Wu | BETSE (forward bioelectric simulation, Pietak & Levin), BEN, Jaxley (differentiable biophysical simulator, Nature Methods 2025), differentiable morphogenesis (arXiv 2407.06295), vertex-model inverse design `[SNIP]`, plus Neural CA |
| Biology bridge | growth proxy for activity; stated | none without a clamp/perturbation experiment |
| Visual appeal | moderate; the breaking-route slider is good | high |
| 24 h risk | low | high |

Local notes `[UNV]` already flag the structural obstacle: V_mem is both register and bus, measured electrotonic length is 12–40 cell diameters where an automaton needs 1, and synNotch steps take 13–20 h.

**Verdict.** TrpB is stronger on rigor. NCA is stronger on presentation. Do not switch. If anything electrical is shown, label it a *computer cell* model, separate from *biological cells* and separate again from *externally applied fields* versus *endogenous* bioelectricity, and require an interventional negative control.

---

## 8. Delphi claims that change the design or test

Queried live (`delphi_overview`, `delphi_graph` by thinker, `delphi_search_claims`, `delphi_get_claim`; local source only, network source not queried): 880 claims = Wolfram 321, Thompson 291, Darwin 247, population genetics 18, Turing-math 3. Statuses: all Darwin/Thompson/Wolfram claims `untested`; Turing's three are partial/proved/untested. The truth scores are model elicitations from 2 assessors, not posterior probabilities, and the "resolvability" scores are assessors' judgments of how testable a claim is with public data. Search for "epistasis" and "fitness landscape" returns zero claims (`[TEAM]` and my domain list agree).

| Claim id | What Delphi holds | How it changes a design or test |
|---|---|---|
| `kimura-fixation-probability` | u(p) = (1−e^(−4N_e s p))/(1−e^(−4N_e s)); assumes genic selection, constant N_e, no linkage; proposed test: barcoded lineages | The model estimates fixation probability under stated population assumptions. Near-neutral variants can fix by drift, so N_e·s near zero must not be turned into a hard impossibility rule. A regime-dependent fixation calculation is separate from the assay-dominance edge criterion. **Do not convert growth rate to s** (the team's own correction rejects that). Owned by `work/claim-reuse`. |
| `darwin1859-ch04-10` (truth 0.285, spread 0.13; resolvability 0.666: "how small" is contested) | selection acts only through very small modifications | Make step-size profile a first-class output: distribution of Δf along certified routes vs along the unrestricted best. Pre-register what "small" means. Motivation by analogy only. |
| `darwin1859-ch06-07` (truth 0.95; resolvability 0.481: "a clean series would not reconstruct the historical path") | graded useful steps build complex organs | Forbids the inference *graph path exists ⇒ historical path*. Already in the contract; keep it in the UI. |
| `turing-morphogen-hypothesis` (proposed test quoted: confirm novel predictions *while ruling out mechanical alternatives*; "a matching pattern alone does not identify the mechanism") | reaction-diffusion framework | Any pattern-design task is scored on **a perturbation where two mechanisms diverge**, never on pattern similarity. This is the evaluation rule for candidate 4. |
| `turing-ddi`, `turing-wavelength` (formal: tr J<0, det J>0; k_c² = √(det J/(D_u D_v))) | linear-stability conditions, wavelength scaling | Analytic oracle and negative control: check the conditions before simulating, and require λ ∝ √D under uniform rescaling as a held-out test. |
| `wolfram2002-ch06-05` (truth 0.915: class "cannot be read off the rule"), `ch01-08` (irreducibility, truth 0.475) | class is not predictable from the rule | For any CA/NCA inverse design: stratify by rule class and test on **held-out initial conditions**; computational irreducibility does not itself imply failure of statistical generalization on a finite distribution. Class-stratified performance is an exploratory comparison, not a consequence of this claim. |
| `wolfram2002-ch01-11` (truth 0.58, spread 0.28; resolvability 0.395: "mechanistic rivals remain compatible with the same images") | simple programs capture genetic programs | Image reproduction is not success; require discrimination against a rival mechanism. |
| `thompson1917-ch04-08` (truth 0.22; resolvability 0.40: causal clamping data sparse) | electric potential differences in cell division | Observational correlation does not count; require a clamp/block intervention that changes the output in the model, and say that the model intervention is not an experiment. |
| `thompson1917-ch07-08` (truth 0.87) | hexagon regularity needs equal cell sizes and uniform forces | Evaluate lattice-based designs on irregular (Voronoi) topologies as a held-out geometry. |

Honest limit: for TrpB, only the Kimura and Darwin step-size rows change what is computed; the others change a different candidate. Historical Darwin claims remain motivation, not tests.

---

## 9. Hostile novelty review

- **"This is LazySP."** Likely true structurally. The domain transfer (optimistic unmeasured nodes, interval-admitted edges, Lean-checked output) is real but small. Survive only with the `directed` baseline written as LazySP.
- **"ALDE already does this on TrpB."** ALDE does active learning for *maximum fitness* on TrpB and GB1; it does not issue route or cut certificates. But we have not run it, so no claim against it is licensed.
- **"Path accessibility is Johnston."** Yes, and Wu 2016 and Papkou 2023. No novelty claim here.
- **"Interval containment is assumed, not shown."** Correct. Two replicates are not 95% bounds over 159,129 variants. Only H4's tolerated margin addresses this.
- **"Zero false certificates is trivially true."** Under containment it is. Report it only as a software check.
- **"Provenance/nanopubs/Lean are packaging."** Operational use needs a changed decision, which the later claim-runtime withdrawal tests now demonstrate. Same-context cache savings still give no graph-specific advantage.
- **"Agents add nothing."** Measured: 78 vs 78 vs 77.
- **"Sites in one assay."** Four residues, one growth proxy, one organism. LHC adds a second landscape; nothing here reaches a real enzyme program.
- **Rubisco ledger:** "Flamholz 2019 already plotted this." They examined trade-off correlations `[SNIP]`; I did not find a statement of emptiness of this exact joint region, which is "not found", not "nobody did".

---

## 10. Company wedges (evidence, not market size)

I give no market-size number; none was measured.

1. **Assay-decision layer for enzyme and protein-engineering teams.** Evidence for: ALDE reports six 96-well plates and an estimated five greedy rounds `[BODY]`; our retrospective replay shows fewer assays to certify `[TEAM]`; Cradle's press-reported $73M Series B (December 2024) shows paying capital in AI protein engineering `[SNIP]`, which is also direct competition. Evidence against/missing: no customer, no prospective wet-lab uplift, ALDE is MIT-licensed and free. Moat hypothesis: prospective decision-and-outcome data.
2. **Verification and pre-registration infrastructure for AI-for-biology claims.** Evidence for: FutureHouse's list requires preregistered targets, blinded evaluation and 24 h turnaround, with no evaluator named; the Arc challenge's scorer ships a noise-ceiling flag (local note `[UNV]`); Edison's $70M seed shows the "AI scientist" category is funded `[SNIP]`. Against: no buyer shown; it may be nonprofit infrastructure. Natural first artifact: the Problem 4 ledger.
3. **Threshold-closing vertical for carbon fixation (Rubisco first).** Evidence for: Problem 4 is defined by paired assays with public comparators; a public kcat dataset now exists. Against: wet-lab capital, long timelines, no demand evidence from us. Defer.

Not recommended as a wedge: bioelectric/NCA computing (no data, no buyer evidence found).

---

## 11. What I could not read or verify

- Weizmann-hosted de Pins PDF: WebFetch `ECONNRESET`, curl empty. Read instead from PMC12663927 via r.jina.ai (HTTP 200, 110,733 B). Last 21,513 chars of that page were not read via WebFetch (the `dp.txt` grep covered the full text).
- PNAS Johnston page: HTTP 403. Used bioRxiv via r.jina.ai. bioRxiv direct fetch: 429.
- ALDE: last 5,269 chars unread. GB1 and DHFR data: not opened. Flamholz repo licence: absent per API; de Pins repo licence: not checked. Arc VCC, Cradle and Edison items are press or local-note level.
- Edison Scientific primary funding announcement not located; figures are trade-press repeats.
- I ran no GPU job, no wet-lab, and did not touch the build code.

## 12. Draft only (not sent): comment for the Millennium Problems form

"For Problem 4 we compared the stated thresholds with the 399-row Flamholz 2019 kinetics table: no natural row has Sc/o ≥ 238 and kcat ≥ 4.05 s⁻¹ at 25 °C; the nearest rows need roughly 2.1× in Sc/o or 2.5× in kcat. Sc/o was not measured in the 2025 de Pins kcat survey. Data, hashes and caveats attached." Sending requires an explicit user instruction.
