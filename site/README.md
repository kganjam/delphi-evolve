# site/ — Darwin's Bridge (static, no build step)

Open over HTTP: `cd site && python3 -m http.server 8000`. `file://` shows the landscape but cannot fetch `data/*.json`.

| File | Role |
|---|---|
| `index.html`, `style.css`, `app.js` | UI. Heatmap of all 160,000 four-residue genotypes, tile inspector, Decision / Evidence / Claims / Proof / Replay tabs |
| `lib.js` | Pure graph logic (edge rule, search, widest-path break point, direct orderings). Tested from Node against a Python mirror |
| `data/landscape.js`, `data/landscape.meta.json` | Real TrpB measurements packed by `python -m evolve.evidence landscape`, with source SHA-256 and counts |
| `data/evidence.json`, `data/nanopubs/` | Delphi MCP query record and unsigned nanopublication drafts (`site-data` command) |
| `data/demo.json` | **Optional core output** (`python -m evolve demo --output ...`). Copied here by the integrator; absent = every integration shows as unavailable. Never edited by this worker |

Rules the page follows: score = raw growth μ minus per-replicate stop-codon mean (core's definition); imputed rows are never observations; the slider parameter (κ, ε) is an *assumed* sensitivity, not a confidence level; "blocked" is claimed only if the route is blocked even when every unmeasured genotype is allowed to be perfect; the Proof tab is green only when `demo.json → proof` has kernel exit 0 and a non-zero mutant exit; layout is a projection of sequence space, not molecular geometry.

Deployment metadata (e.g. hosting manifests) is intentionally absent; the coordinator owns it.
