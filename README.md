# Delphi Evolve — Darwin's Bridge

**Which experiment would justify the next step in a protein's evolution?**

A ScienceClaw prototype for query-to-certify on a measured enzyme landscape: evidence-linked evolutionary paths, explicit unknowns, and conditional Lean certificates. Built on the CC0 TrpB data of Johnston et al. (2024), with Delphi claim references.

The prototype includes an interactive measured landscape, conditional Lean certificates, executable adapters for existing Delphi claims, and five BioNeMo ESM2 model sizes evaluated on Nebius H100s. It contains 2,500 retrospective replay episodes: 1,100 core, 300 LazySP follow-up, and 1,100 prior comparisons on the same panel. These are not 2,500 independent biological problems. No new wet-lab experiment was performed.

The benchmark changed our design. Established LazySP-style search certified 96/100 episodes at 1,000 additional assays; the original model-assisted planner certified 78/100. Sharing among deterministic specialists did not beat the single planner, and the five-size prior study established no clear benefit under the tested integration. The useful artifact is the decision-and-evidence system, not an algorithmic superiority claim. See [core methods](artifacts/core/README.md), [strong baseline](docs/lazysp.md), and [GPU follow-up](docs/scale.md).

- [Three-minute pitch](docs/pitch.md) · [blog](docs/blog.md) · [novelty boundaries](docs/novelty.md)
- [Start here: presentation and handoff](HANDOFF.md) · [six-slide PDF](presentation/deck.pdf) · [90-second walkthrough](presentation/video/darwins-bridge-walkthrough.mp4)
- [Actual Delphi claim reuse](docs/claim-reuse.md) · [GPU/OpenResearch runs](docs/compute.md)
- [Inverse design, NCA and bioelectric research](docs/research/inverse-design-synthesis.md)
- [Executable Turing domain example](docs/turing-scope.md)
- [20 → 10 → 3 → 1 planning](planning/PLAN.md) · [scientific contract](specs/CONTRACT.md) · [current status](STATUS.md)

To explore the saved results, serve `site/` with `python -m http.server --directory site 8000` and open `http://localhost:8000`. The Claims tab links to recorded Kimura/Fisher adapter traces. The public repository contains the source; the hosted ChatGPT Site currently retains owner-private access.

For computation from this checkout, install with `python -m pip install '.[test]'`, fetch the checksum-pinned data with `python scripts/fetch_data.py`, and run `python -m evolve --help`. Lean checks require the version pinned in `lean/lean-toolchain`. `scripts/reproduce.sh` records a fresh-checkout run in a new directory; it refuses to overwrite an existing run. Full histories and run receipts live in `artifacts/` and `tasks/results/`.

Original project code is Apache-2.0. Imported data, reference documents and third-party dependencies retain their own licenses and attribution. See [NOTICE](NOTICE).
