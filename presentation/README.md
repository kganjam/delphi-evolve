# presentation/ — 3-minute deck, PDF, video harness

Owner: work/presentation. Brand: Darwin's Bridge / Delphi Evolve. Standalone HTML (no npm, no network, system fonts), print CSS for one slide per page.

| File | Role |
|---|---|
| `build_deck.py` | Renders `deck.html` from FINAL integrated artifacts under `--root`. Every number is computed from files there; input SHA-256s and the git HEAD go to `deck.provenance.json`. |
| `validate.py` | Replay validation for the 7 original arms plus the 4 post hoc arms (11 arms, 1,100 episodes). Rejects: missing replay files, any shard with zero rows, summary seeds ≠ protocol seeds, an arm without exactly seeds×5 episodes (20 seeds → 100 per policy), shard rows ≠ `episodes.csv` rows, a committed `queries/queries__<arm>.tsv.gz` whose per-episode paid-query count ≠ `assays`, no shards and no traces, `table_primary.csv` episode counts ≠ 100, curve ≠ table at budgets. A post hoc arm is shown only when complete and verified. |
| `export_pdf.py` | Playwright/Chromium → `deck.pdf` (6 pages, 1280×720) and per-slide PNGs. |
| `deck.css`, `deck.js` | Cream/ink/orange styling (tokens from `site/style.css`), arrow-key navigation, `n` toggles speaker notes. |
| `video/record_video.py` | Playwright `record_video` of the actual static site (or `--mode deck`), caption overlay, ffmpeg → MP4, manifest with source SHA and video SHA-256. |
| `video/storyboard.md` | Shot list and caption policy. |
| `tests/` | `pytest presentation/tests` — validator and render path. `tests/fixture.py` builds TEST-ONLY synthetic replays; nothing built from it is committed or quoted. |

## Final vs draft

```
python3 presentation/build_deck.py --root /path/to/release [--shards-dir <core replay shards>]   # final: exit 2 if replay is not complete; also writes speaker-notes.md and appendix.md; refuses > 420 spoken words
python3 presentation/build_deck.py --root ... --allow-draft                        # writes deck.DRAFT.html: DRAFT watermark on every slide, no replay numbers
python3 presentation/export_pdf.py presentation/deck.html --shots presentation/screenshots
```

A draft never overwrites `deck.html`. The replay slide's headline is generated from the data: it states the single-policy vs random numbers, and describes specialists vs the single policy as "higher than", "lower than" or "not distinguishable from" according to whether the seed-cluster bootstrap interval in `table_paired.csv` excludes 0. Negative outcomes therefore print as negative. The four post hoc arms (no-GP single and shared/isolated specialists, round-robin) are shown only if complete and verified, under a separator that says they were added after the original run was observed. Pending items (LazySP-style baseline, GPU-prior policy ablation) are stated as pending unless a result file exists, and are never given numbers by the builder.

## Caveats carried on the slides
* "κ" is an assumed sensitivity, not a confidence level.
* A replay "blocked/no route certifiable" is not the Lean no-path theorem (see `planning/INTEGRATION-FINDINGS.md` F1).
* Specialists are deterministic software objects in one process (F7); shared vs isolated differ in evidence visibility *and* arbitration.
* Query-efficient path evaluation is prior art (LazySP, BAEE); ALDE already studies active learning on this landscape and was not run.
