# Brief for the independent review of the Delphi materials (after the 18:00 PDT cut)

Reviewer: please do not edit any file. Write findings to `/data/artifacts/delphi-evolve-rethink/messages/dx-submit-independent-review.md` (or wherever the director names), one finding per item: file and line or slide, what is wrong, the evidence, severity. Say what you did **not** check.

## What to review
`presentation/delphi/` (deck.html, deck.pdf, speaker-notes.md, blog.md, storyboard.md, REHEARSAL.md, video/), `site/delphi/` (index, appendix, blog), and the bundle manifest `presentation/delphi/dist/bundle-manifest.json`. Governing documents: `planning/rethink/PITCH-OUTLINE.md`, `planning/rethink/CLAIM-LEDGER.md`, and `presentation/delphi/sources.md` (what was verified and what was not).

## Fast mechanical checks (should all pass)
- `python3 presentation/delphi/trace.py` and `python3 -m pytest -q presentation/delphi/tests`
- `bash presentation/delphi/rebuild.sh` from a clean checkout; the deck should be reproduced from committed files only.
- Unzip the bundle and re-hash every file against `BUNDLE-MANIFEST.json`.

## Where a human or independent model is most useful (the gate cannot do these)
1. **Meaning, not numbers.** The trace gate proves each slide number is re-derived from a committed file. It does not prove the sentence around it is a fair reading. Read each slide against its source: slide 2 repair demo (`artifacts/rethink_nca/repair.json`), slide 3 checker-versus-key table (`artifacts/delphi_submit/at5_v1_2_frozen127.json`, a recomputation by the same author as the deck), slide 4 ledger rows (`scopedesk/ledger/kill_ledger.json`), slide 5 headroom and pilot (`tasks/results/guilds.json`), slide 6 scorecard (`scopedesk/scorecard/`).
2. **Overclaims.** Look for anything that reads as: a pattern forms; a named law is wrong; first-ever; universal threshold; agents need the gate; collective advantage; compute-matched; outside use; deployed; a median or a "10 of 10" headline. The tests ban specific strings only.
3. **Single-reader, not Codex-reviewed items.** These are labelled on the slides and the site: repair demo and nonlinear grid; checker-versus-key recomputation; kill ledger rows; scorecard statuses; headroom check; proof-search pilot. Judge whether the label is enough, or whether the claim should be dropped.
4. **Scope of the ledger framing.** The ledger shows 17 of 20 rows caught by an independent reviewer or a measurement and 3 by the author. Check that no slide or the script implies a collective-intelligence measurement (there is no control arm).
5. **The ATLAS statements.** "Price identity already in ATLAS; Hamilton form not found by a critic's non-exhaustive code search" rests on the critic's reading (`lean_price/README.md`). Spot-check against `facebookresearch/atlas-lean` if you can reach it.
6. **Captions and video.** `video/captions.json` and the recorded frames against the slides.

## Known limitations (so you do not have to rediscover them)
- Timing is a synthetic-voice read-through; no human rehearsal has been done.
- No organizer upload channel and no receipt exist; the presentation format, time limit and who is in Boston are unconfirmed (`planning/rethink/SUBMISSION.md`).
- Claim-ledger row P03 still describes the earlier 128-item candidate; the frozen set is 127 items.
- The headroom check has no checker-tool arm and was scored by the key's author; effective n is 8 families.
- The proof-search pilot's checker was repaired after the outcomes were observed; the statements are integer surrogates; Codex's fidelity review of them is advisory only.
- The robustness sweep (appendix) and the repair demo are not claim-ledger rows.
- delphi-frontier (a separate repository) findings are intentionally not cited.
