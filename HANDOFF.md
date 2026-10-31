# Delphi Evolve / Darwin's Bridge — presentation handoff

**Pitch:** Turn a proposed biological intervention into an experiment we can justify. Start with a measured enzyme landscape; choose a mutation route, expose the weakest evidential step, and carry its assumptions and a conditional certificate into the next decision. Existing Delphi claims become executable applicability checks rather than decorative citations.

## Present in three minutes

- [x] Six-slide [PDF](presentation/deck.pdf) and [HTML deck](presentation/deck.html), with [385-word speaker notes](presentation/speaker-notes.md).
- [x] [90-second captioned walkthrough](presentation/video/darwins-bridge-walkthrough.mp4). It is silent; use it as a fallback demonstration, not an additional three-minute talk. Its manifest pins the earlier recording source; the latest PDF includes the later GPU comparison.
- [x] [Interactive Site](https://delphi-evolve.lefthill1.chatgpt.site) retains owner-private access. The [public repository](https://github.com/kganjam/delphi-evolve) and [downloadable release](https://github.com/kganjam/delphi-evolve/releases/tag/v0.1.0-hackathon) do not require Site access.
- [x] [Blog](docs/blog.md), [company hypothesis and pilot](docs/company-hypothesis.md), [20 → 10 → 3 → 1 plan](planning/PLAN.md), and [scientific appendix](presentation/appendix.md).
- [ ] Actual competition upload and live presentation: no submission receipt or organizer upload credentials were available. The public schedule says slides due November 1 at 1pm Boston time, which is **10am PST (UTC−8)** in Seattle; presentations start **11:30am PST**. Confirm organizer instructions before presenting. [Official schedule](https://scienceclawhack.ai/).

Open with the route, not the architecture. VFVS → AIKG looks like four mutations. In this measured table every direct ordering has a descending step; the declared uncertainty rule admits a six-step detour. Move the uncertainty slider and show the route length change, then the refusal to certify. Open the weakest step's source measurements. Finish with the claim adapter refusing an invalid transfer and the exact scope of the Lean check.

## What is real

| Artifact | Established here | Boundary |
|---|---|---|
| TrpB landscape | 159,129 measured non-stop variants; 871 imputed-only variants excluded as observations | Published E. coli growth assay; not new measurements or catalytic constants |
| Strong baseline | LazySP-style primary 96/100; original model-assisted policy 78/100 at 1,000 additional assays | Follow-up; gain concentrated in one repeated endpoint pair; no general superiority claim |
| Protein-model evaluation | Five BioNeMo ESM2 sizes, 8M–3B, 160,000 variants each; 1,100 matched prior/control episodes | No clear assay-saving benefit; no individual query traces retained for that follow-up |
| Lean | Generic route/cut theorems, specific route/cut checks, meaningful rejected law mutations | Conditional on stated interval/model assumptions; no proof of biological validity or all replay decisions |
| Existing Delphi claims | Kimura, Fisher and Turing source-pinned adapters change compute/refuse decisions | Hand-authored adapters; no automatic theorem extraction; Darwin links remain motivation |
| Evidence reuse | Same-context reuse equals ordinary caching; typed reuse catches injected context faults | Software fault tests do not establish wet-lab savings |
| NCA / bioelectric work | Reviewed research and a finite-domain Turing applicability example | No trained NCA, fabricated material, designed channel or solved Millennium Problem |

Source files and checks are linked in `docs/` and `artifacts/`. Nanopublications are unsigned, structurally validated drafts; they were not published to a public nanopub network. A fresh checkout at the recorded base passed 238 tests with two documented skips and compiled the proofs; later additions have separate targeted checks. See [reproduction receipt](artifacts/integration/fresh-checkout-317203a0.json), [LazySP audit](artifacts/integration/lazysp-coordinator-audit.json) and [scale audit](artifacts/integration/scale-coordinator-audit.json).

## Judging and company case

The [public rubric](https://scienceclawhack.ai/) weights scientific significance 20%, potential impact 25%, decentralized agency 20%, collective capability 25%, and execution 10%, with +10 for demonstrated external collaboration. It does not list automatic sponsor-use points. We used Nebius, BioNeMo and OpenResearch, but do not claim an unlisted bonus or another team's reuse.

The strongest case is execution and inspectable scientific decisions. The weakest is collective advantage: the study found none, and the benchmark's specialists are deterministic objects in a central process. Do not describe it as a proven decentralized laboratory. The unusual systems combination is useful, but no first-ever novelty claim has been established.

The company hypothesis is an evidence and experiment-decision layer for enzyme-engineering teams, integrated above existing models. The next milestone is one lab, one historical campaign, and a prospectively registered equal-budget comparison measured in assay cost and days to a defensible decision. No customer, revenue, LOI or market size has been established.

## Run and reuse

For the downloadable static bundle: extract it, run `python -m http.server 8000` in that directory, and open `http://localhost:8000`. The PDF and video also work without a server. For code, clone the repo, install `python -m pip install '.[test]'`, run `python scripts/fetch_data.py`, then `python -m evolve --help`. Additional claim and Turing CLIs are documented in their method files.

The reusable handoff consists of source-linked measurements, conditional certificates, compact scalar priors, recorded decision traces and typed nanopub drafts. Reusing one is not evidence that its source claim is correct; preserve assay context and distinguish measured, predicted, simulated and model-derived values.

## Resources and collaboration

Ten scale jobs finished, totaling 9,475 recorded GPU job-seconds (2.632 H100-hours), in addition to the base GPU worker's runs. Peak scale concurrency was eight. All ten were queried live as COMPLETED; no other team's job was cancelled. This measures job time, not billing. Actual metered charges remain unknown. Claude subscription workers, Gemini reviews, Nebius structure calls and local CPU OpenResearch analysis have receipts. OpenAI credits were unused; Brev access was unavailable; Nebius LLM credentials were unavailable.

Write invitations are pending for `fractastical`, `tkuhn`, `kavitahkulkarni`, `ashleycaselli`, and `xX-its-amit-Xx`. This includes the existing non-owner MorphoSwarm collaborators plus the additional requested people. Invitations do not imply acceptance. Existing MorphoSwarm work was preserved.
