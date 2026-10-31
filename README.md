# Delphi Evolve — Darwin's Bridge

**Which experiment would justify the next step in a protein's evolution?**

A ScienceClaw prototype for query-to-certify on a measured enzyme landscape: evidence-linked evolutionary paths, explicit unknowns, and conditional Lean certificates. Built on the CC0 TrpB data of Johnston et al. (2024), with Delphi claim references.

The prototype includes a 1,100-episode retrospective benchmark, an interactive measured landscape, conditional Lean certificates, source-pinned Delphi claim adapters, and a 160,000-variant BioNeMo prior run on a Nebius H100. No new wet-lab experiment was performed. The original query-to-certify policy resolved 78/100 cases at 1,000 additional assays versus 32/100 for directed frontier search; a post-hoc no-model variant reached 96/100. A stronger follow-up using established LazySP also resolves96/100; the model-assisted policy is not demonstrated to beat it. Sharing among the deterministic specialists did not beat the single planner. See [methods and limitations](artifacts/core/README.md).

- [Three-minute pitch](docs/pitch.md) · [blog](docs/blog.md) · [novelty boundaries](docs/novelty.md)
- [Actual Delphi claim reuse](docs/claim-reuse.md) · [GPU/OpenResearch runs](docs/compute.md)
- [Inverse design, NCA and bioelectric research](docs/research/inverse-design-synthesis.md)
- [20 → 10 → 3 → 1 planning](planning/PLAN.md) · [scientific contract](specs/CONTRACT.md) · [current status](STATUS.md)

To explore the saved results, serve `site/` with `python -m http.server --directory site 8000` and open `http://localhost:8000`. The Claims tab links to recorded Kimura/Fisher adapter traces. The public repository contains the source; the hosted ChatGPT Site currently retains owner-private access.

For computation from this checkout, install with `python -m pip install '.[test]'`, fetch the checksum-pinned data with `python scripts/fetch_data.py`, and run `python -m evolve --help`. Lean checks require the version pinned in `lean/lean-toolchain`. `scripts/reproduce.sh` records a fresh-checkout run in a new directory; it refuses to overwrite an existing run. Full histories and run receipts live in `artifacts/` and `tasks/results/`.

Original project code is Apache-2.0. Imported data, reference documents and third-party dependencies retain their own licenses and attribution. See [NOTICE](NOTICE).
