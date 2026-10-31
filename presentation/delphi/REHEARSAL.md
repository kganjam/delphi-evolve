# Rehearsal checklist (human stopwatch)

**Status: no human rehearsal has been done.** The timings below are a synthetic-voice read-through (`timing.json`), not a person. Nothing on this page is a result until the blank cells are filled by someone with a stopwatch.

Measured read-aloud (synthetic voice): speech 148.1 s, with 1.5 s assumed per slide change: **2:35** against a 3:00 budget (the organizers publish no time limit; see `planning/rethink/SUBMISSION.md`). Margin about 24.4 s, which does not cover demo clicks, a stumble or questions.

## Run 1: read the script straight, no slides

| Slide | Outline beat | Words | Synthetic start | Synthetic length (s) | Your start | Your end |
|---|---|---|---|---|---|---|
| 1 | 0:00-0:25 reveal | 57 | 0:00 | 19.25 | | |
| 2 | 0:25-1:00 check and repair | 68 | 0:20 | 27.82 | | |
| 3 | 1:00-1:30 compiled nodes and test set | 65 | 0:50 | 23.86 | | |
| 4 | 1:30-2:15 ledger | 73 | 1:15 | 27.28 | | |
| 5 | 2:15-2:45 what the collective measured | 61 | 1:44 | 21.46 | | |
| 6 | 2:45-3:00 close | 68 | 2:07 | 28.44 | | |

Pass: total at most 3:00 including slide changes. Write the total here: ______ . If over, use the cuts below and rehearse again.

## Cuts if the real limit is shorter (synthetic-voice sums)

| Cut | Slides kept | Length |
|---|---|---|
| all six slides | 1, 2, 3, 4, 5, 6 | 2:35 |
| drop slide 5 (collective null) | 1, 2, 3, 4, 6 | 2:12 |
| drop slides 3 and 5 | 1, 2, 4, 6 | 1:47 |

## Run 2: with the deck (PDF, then the HTML deck with `n` for notes)

For each slide say, in your own words, the sentence below. These are the caveats the slides print; leaving one out is the usual way this talk goes wrong.

| Slide | Must say aloud |
|---|---|
| 1 | A linear-mode statement for a declared model. Classical mathematics. No wet-lab experiment; simulations only. Not a claim that a pattern forms. |
| 2 | Limitation first: the algorithm is trivial. Model-only: one kinetics, 3 seeds, no confidence interval, near-onset patterns marginal. Not an experiment. |
| 3 | The Price identity is already in ATLAS; ours duplicates it. Test set is frozen. Agreement with our own key is not external validation. |
| 4 | 16 of 21 caught by an independent reviewer or validator, 2 by the author with an independent hold, 3 only by the author's own measurement or rule. No control arm: audit versus self-audit. One team, one day. No median. |
| 5 | No advantage shown in two small comparisons (the proof pilot sat at a ceiling and could not discriminate). Checker-tool arm was not run. Headroom check measures judgement, not derivation. The pilot hit a ceiling; the checker was repaired after the outcomes. |
| 6 | Outside use: none observed yet. Delphi Frontier is a proposal, nothing deployed, and our own seed questions failed our own validator (0 of 7 bounded, ledger R21). Scorecard sentence exactly as printed: 6 linked, 1 related lemma, 2 empirical, 12 without a check; single reader, revised after a Codex review of v0, not re-reviewed. |

## Never say

First-ever; any claim that a named law is wrong; that a pattern forms (linear mode only); a universal diffusion threshold; that AI solved anything; that agents need the gate; a median or a '10 of 10' count; a compute-matched claim for the proof pilot; that more agents did not help (say: no advantage shown in two small comparisons); that the test set has exact answers (say: stated methods under declared conventions); that the Frontier seeds are ready or sourced; that anything is deployed or that outside people used it.

## Questions to expect, and the answers the artifacts support

| Question | Answer |
|---|---|
| What is new? | Only that a program checks the scope conditions, returns a witness and proposes a repair. The algorithm is trivial. |
| Did you run experiments? | No wet-lab experiments. Declared-model checks, an independent solver on declared kinetics, and a retrospective enzyme replay (simulations only). |
| Does ATLAS already do this? | ATLAS has the Price identity; a critic's code search found no Hamilton form or Turing statements there, not exhaustive. We aim to complement it. |
| Do agents need the gate? | Not shown. The checker-tool arm was not run. |
| Is the benchmark independent? | No. It shares its conventions with the checker. Audits so far are same-family or non-blinded; Codex recomputed the v1.1 verdicts and checked metadata and wording only, and is unavailable now. |
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
| presentation/delphi/deck.pdf | `b67c2a267a8d36ea02a81767322376f119b65e213372ced9d57caca6ce3a8750` |
| presentation/delphi/deck.html | `57dc65082bf5179c6d1fb90b976c1422094c80738433099648a5ed7533ffe1fd` |
| presentation/delphi/deck.pptx | `de7e14170137eaacffa80e6f2aef225c662107de55cb037f8b9651405ee5dd3c` |
| presentation/delphi/video/delphi-90s-captioned.mp4 (90.6 s, silent) | `614ad6d6f5645c1631af01e2d11a444ec78509ad98fb98c1d912ec6bd252ebeb` |

The bundle zip (site, presentation folder and every cited artifact) is built after this sheet and contains it, so its hash is recorded separately in `presentation/delphi/dist/bundle-manifest.json` and `delphi-bundle.zip.sha256`, not here.

## Results (fill in)

| Run | Total | Over/under 3:00 | Slides that ran long | Caveat missed |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |
