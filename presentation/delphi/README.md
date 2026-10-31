# Delphi deck, site, blog, storyboard (dx-submit)

Spine: "Delphi: from candidate laws to checked theorems". The earlier TrpB deck (`presentation/deck.*`) and site (`site/`) are the preserved baseline and are untouched.

| File | Role |
|---|---|
| `facts.py` | Reads committed artifacts, recomputes exact values (Fractions), asserts they match the receipts, writes `facts.json`. Single source for every number. |
| `build_deck.py` | Six-slide HTML deck, speaker notes, provenance with input hashes. Pending items render as `pending`. |
| `build_site.py` | `site/delphi/` landing page, appendix, blog (+ `blog.md`), `storyboard.md`; links `site/review/` (owned by the Codex API worker) only if it exists. |
| `trace.py` | Independent gate: re-derives each slide number from artifacts, fails on any untraced number, stale input, non-ledger ID, non-pending metric, PDF/HTML mismatch. |
| `tests/test_delphi.py` | Proves the gate fails on tampering; forbidden-phrase scan (negation-aware); link and asset checks. |
| `rebuild.sh` | One command for all of the above. |

Ledger rule: every factual sentence maps to a row of `planning/rethink/CLAIM-LEDGER.md` or is marked pending / unledgered. The robustness sweep and the Mathlib probe have no ledger row yet and are labelled so.
