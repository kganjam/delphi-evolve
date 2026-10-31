# Rehearsal checklist (human stopwatch)

**Status: no human rehearsal has been done.** The timings below are a synthetic-voice read-through (`timing.json`), not a person. Nothing on this page is a result until the blank cells are filled by someone with a stopwatch.

Measured read-aloud (synthetic voice): speech 148.0 s, with 1.5 s assumed per slide change: **2:35** against a 3:00 budget (the organizers publish no time limit; see `planning/rethink/SUBMISSION.md`). Margin about 24.5 s, which does not cover demo clicks, a stumble or questions.

## Run 1: read the script straight, no slides

| Slide | Outline beat | Words | Synthetic start | Synthetic length (s) | Your start | Your end |
|---|---|---|---|---|---|---|
| 1 | 0:00-0:25 reveal | 56 | 0:00 | 17.52 | | |
| 2 | 0:25-1:00 check and repair | 68 | 0:19 | 27.63 | | |
| 3 | 1:00-1:30 compiled nodes and test set | 62 | 0:48 | 22.8 | | |
| 4 | 1:30-2:15 ledger | 74 | 1:12 | 27.85 | | |
| 5 | 2:15-2:45 what the collective measured | 75 | 1:41 | 25.89 | | |
| 6 | 2:45-3:00 close | 64 | 2:09 | 26.35 | | |

Pass: total at most 3:00 including slide changes. Write the total here: ______ . If over, use the cuts below and rehearse again.

## Cuts if the real limit is shorter (synthetic-voice sums)

| Cut | Slides kept | Length |
|---|---|---|
| all six slides | 1, 2, 3, 4, 5, 6 | 2:35 |
| drop slide 5 (collective null) | 1, 2, 3, 4, 6 | 2:08 |
| drop slides 3 and 5 | 1, 2, 4, 6 | 1:43 |

## Run 2: with the deck (PDF, then the HTML deck with `n` for notes)

For each slide say, in your own words, the sentence below. These are the caveats the slides print; leaving one out is the usual way this talk goes wrong.

| Slide | Must say aloud |
|---|---|
| 1 | A linear-mode statement for a declared model. Classical mathematics. We ran no experiment. Not a claim that a pattern forms. |
| 2 | Limitation first: the algorithm is trivial. Model-only: one kinetics, 3 seeds, no confidence interval, near-onset patterns marginal. Not an experiment. |
| 3 | The Price identity is already in ATLAS; ours duplicates it. Test set is frozen. Agreement with our own key is not external validation. |
| 4 | 17 of 20 caught by an independent reviewer or a measurement, 3 by the author. No control arm: audit versus self-audit. One team, one day. No median. |
| 5 | More agents did not help. Checker-tool arm was not run. Headroom check measures judgement, not derivation. The pilot hit a ceiling; the checker was repaired after the outcomes. |
| 6 | Outside use: none observed yet. Delphi Frontier is a proposal, nothing deployed. Scorecard sentence exactly as printed: 6 linked, 1 related lemma, 2 empirical, 12 without a check. |

## Never say

First-ever; any claim that a named law is wrong; that a pattern forms (linear mode only); a universal diffusion threshold; that AI solved anything; that agents need the gate; a median or a '10 of 10' count; a compute-matched claim for the proof pilot; that anything is deployed or that outside people used it.

## Questions to expect, and the answers the artifacts support

| Question | Answer |
|---|---|
| What is new? | Only that a program checks the scope conditions, returns a witness and proposes a repair. The algorithm is trivial. |
| Did you run experiments? | No. Declared-model checks, an independent solver on declared kinetics, and a retrospective enzyme replay. |
| Does ATLAS already do this? | ATLAS has the Price identity; a critic's code search found no Hamilton form or Turing statements there, not exhaustive. We aim to complement it. |
| Do agents need the gate? | Not shown. The checker-tool arm was not run. |
| Is the benchmark independent? | No. It shares its conventions with the checker. Audits so far are same-family or non-blinded except Codex's recomputation of the v1.1 verdicts. |
| Who used it? | Nobody outside the team that we have observed. |
| How fast were claims refuted? | We do not show a median: times are file and commit times and rows differ in kind. |

## Logistics

- Deadline: **Sun Nov 1, 10:00 AM PST (1:00 PM Boston)**. No upload channel or receipt exists yet (`planning/rethink/SUBMISSION.md`).
- In person: the organizers say every team member should attend.
- On the presenting laptop and a USB stick, offline: `presentation/delphi/deck.pdf`, `deck.html`, `deck.pptx` (image-only fallback), the captioned video, the bundle zip.
- Backup if a live demo fails: the 90-second captioned video; it is silent, so say the captions aloud.

## What to carry (sha256 as built; recompute after any rebuild)

| File | sha256 |
|---|---|
| presentation/delphi/deck.pdf | `b04c4f1a6ad07bb474c5136385153d0b8967b356a04521d11ef1f5e891852799` |
| presentation/delphi/deck.html | `431dd89e0f92c3154716b7c790bade1efdacb90f1b83310a3c18565fae3cacbd` |
| presentation/delphi/deck.pptx | `62e5c82da7768a74dd0ae08d5df913984ee5b58b8d92f397372d27d420957841` |
| presentation/delphi/video/delphi-90s-captioned.mp4 (90.52 s, silent) | `2e8788a8f383e8965843c8ed1e0576d72185fc3aaab23a0d669751298a336a51` |

The bundle zip (site, presentation folder and every cited artifact) is built after this sheet and contains it, so its hash is recorded separately in `presentation/delphi/dist/bundle-manifest.json` and `delphi-bundle.zip.sha256`, not here.

## Results (fill in)

| Run | Total | Over/under 3:00 | Slides that ran long | Caveat missed |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |
