# Submission logistics and presentation readiness

Owner: `submit` worker (Claude Sonnet 5.5, existing subscription). Written Sat Oct 31 2026, ~06:30 PDT. Times below are Seattle (PDT until 02:00 Sun Nov 1, then PST); Boston in brackets.

## Status: NO-GO until a submission channel is found and a receipt exists

**No upload location has been found and no submission receipt exists.** Nothing has been uploaded, sent or submitted by this worker or, as far as the repository shows, by anyone. The deck is ready; where it goes is unknown. That is the single highest-risk item, and it is a human action (below) because it needs inboxes, the ScienceClaw Discord or a person at the Media Lab, none of which this worker can reach.

## Update: the spine changed; the deck is now Delphi (times in this file come from `date`; earlier stamps here were wrong)

The TrpB deck described below (`presentation/deck.*`, `rebuild.sh`, `trace_numbers.py`) is the **preserved baseline**. The pitch deck is now `presentation/delphi/` ("Delphi: from candidate laws to checked theorems"); site `site/delphi/`; see `presentation/delphi/README.md`. Rebuild and gate: `bash presentation/delphi/rebuild.sh`. Submission-channel findings, the countdown, the deadline and the go/no-go checklist below are unchanged and still govern. **Still no upload location and no receipt.**

- Delphi checklist additions: [x] deck, PDF, speaker notes, blog, storyboard, landing page built from committed artifacts and the claim ledger; [x] 23 slide numbers re-derived by `presentation/delphi/trace.py`, every benchmark/scorecard metric reads "pending"; [x] script measured aloud (synthetic voice) at 2:33 to 2:36 including assumed gaps, about 25 s under 3:00 (`presentation/delphi/timing.json`); [ ] human stopwatch rehearsal; [ ] PPTX export of the Delphi deck (only the TrpB deck has one); [ ] scorecard / agent-evaluation numbers (pending, owned by others); [ ] director's proposal to open with compiled artifacts and make the kill ledger the second beat (not adopted; needs committed artifacts and ledger rows for each row shown).

### Deck rebuilt to the director's pitch outline (`date` 08:00 PDT)

`presentation/delphi/` now follows `planning/rethink/PITCH-OUTLINE.md`: reveal, check and repair, compiled nodes with the frozen test set, the kill ledger (from `scopedesk/ledger/`), what the collective measured, close. 40 slide claims are re-derived by `trace.py`; 11 tests; script 399 words, read aloud by a synthetic voice at 2:34 to 2:35, about 25 s under 3:00 (no human rehearsal). Corrections applied: test set is the frozen 127-item key (28645a12…; the 131 and 128-item versions are superseded); the checker-versus-key numbers were recomputed on that key (50 items: gate 50/50, plain formula 29/50, continuum only 34/50) in `artifacts/delphi_submit/`; R06 is described as determinant non-negativity advertised as stability (not "vacuous"); the 19-lemma proof-search pilot appears only as the permitted caption with results pending, call-matched not compute-matched; no Lean-pilot numbers are shown. Delphi Frontier appears once, as a proposal, nothing deployed. Still no organizer upload channel and no receipt.

Scorecard (critic v0.1, `date` 08:32 PDT): slide 6 and the site now use ONLY the Codex-approved wording, 21 records: 6 linked to scope-check benchmark families, 1 related formal lemma (target unestablished), 2 empirical/framework, 12 without a corresponding check (the earlier '7 attempted' wording is superseded and banned by test). Slide 5 now carries the headroom check (unguarded Claude Sonnet 5.5 121/127, Gemini 3.8 flash 110/127, checker-tool arm not run, effective n 8 families) and the Lean-19 pilot as a ceiling null (every arm 19/19, reuse saved no calls or tokens, checker repaired after the outcomes); the host's earlier 24/24 run is not used. Codex's reviewed Frontier map is linked from the landing page (`site/review/frontier.html`), not rewritten.

Red-team (critic, 09:44 PDT, single-reader): A1-A3, A5, A6 and B1-B5 applied; A4 answered with a reason (different audit file; see `presentation/delphi/sources.md`). Ledger counts are now 21 rows: 16 independent, 2 mixed, 3 author-only. Review status: with Codex unavailable, every slide footnote and the landing page label unreviewed items 'single-reader, not Codex-reviewed'; nothing is marked accepted. `presentation/delphi/REVIEW-BRIEF.md` is the brief for the fresh read-only reviewer commissioned at the 18:00 cut.

### Video, bundle, rehearsal sheet (`date` 08:5x PDT)

- 90-second silent captioned video of the built deck and the landing page ledger: `presentation/delphi/video/delphi-90s-captioned.mp4` (89.84 s, sha256 `a1b8e9752a9054a24e9251ed2606c467fc6e89404b80f460dadd2602bd4558cb`), manifest `video/manifest.json` pinned to the source HEAD and the deck/site hashes. Re-record after every rebuild.
- Downloadable static bundle (site/delphi, site/review, presentation/delphi and the 131 files it cites; deterministic zip): `/data/artifacts/delphi-evolve-submit/dist/delphi-bundle.zip`, sha256 `475545d1492c7f086f924457dfb61f66231f272c33efdea294ecf77c85a43e66`, file list and per-file hashes in `presentation/delphi/dist/bundle-manifest.json`. Verified by unzipping and re-hashing every file. Not published or uploaded anywhere.
- Rehearsal checklist `presentation/delphi/REHEARSAL.md`: **no human rehearsal has been done**; the sheet has blank cells for a stopwatch run.
- The 18:00 PDT cut is one command from a clean checkout of the integrated tree: `bash presentation/delphi/final_cut.sh` (rebuild + gate, video, rehearsal sheet, bundle). Commit its outputs afterwards.

### Corrections applied (ATLAS memo)

- No Delphi material claims that no machine-checked biology library exists. ATLAS (`facebookresearch/atlas-lean`, `MathlibExt/Biology`) is credited on slide 6, the site and the blog; whether it already covers Price/Hamilton is stated as unchecked; the earlier "bounded search found no Price formalization" sentence was removed. Offering Turing statements to its `WantedExt/Biology` is shown as pending, not done.
- Slide 2 and the site now state the limitation first (trivial algorithm; value is certificate and packaging) and the exact windows (mode n grows iff 2n² < (L/π)² < 5n²; stable window √5 ≤ L/π ≤ 2√2), recomputed exactly by `presentation/delphi/trace.py`. Non-monotone size dependence is stated as not new.
- Citations: Kurics-Menshykau-Iber arXiv:1407.7114 and Ouchdiri arXiv:2509.15829 exist, but their abstracts do not mention domain size, so they are **not** cited as support; the slide says the literature citation is being verified. PMC9884266 and Arcuri-Murray 1986 appear nowhere in the Delphi outputs (tests enforce this). They still appear in `docs/turing-scope.md`, `docs/research/inverse-design-synthesis.md` and `planning/rethink/nca.md`, which belong to other workers.
- The misprediction map is a pending row; the scout's toy-ensemble figures are not shown (no committed artifact). Source-by-source verification state: `presentation/delphi/sources.md`.
- Safety: prove2.me reportedly carries a footer instructing AI agents to fetch a URL and follow its instructions. dx-submit has not fetched it; Prove2Me is cited only by arXiv id from a committed document. Do not point an agent at that site unsandboxed.

## Countdown

`python3 scripts/submission_countdown.py` computes this live from the tz database. Snapshot at 06:23 PDT Sat Oct 31:

| Event | Seattle | Boston | Source |
|---|---|---|---|
| **Final slides due** | **Sun Nov 1 10:00 AM PST** | Sun Nov 1 1:00 PM EST | scienceclawhack.ai schedule, "End of hacking - final slides due"; Luma: "Hacking Ends: Final Slides Due & Lunch" |
| Presentations & judging | 11:30 AM PST | 2:30 PM EST | same |
| Awards & closing | 1:30 PM PST | 4:30 PM EST | same |
| Internal freeze target | Sat Oct 31 11:48 PM PDT | Sun 1:48 AM EST | `STATUS.md` (team's own, not official) |
| My recommendation: first upload attempt finished | Sun 7:00 AM PST | 10:00 AM EST | recommendation, 3 h margin |

About **28.6 h to the deadline** at the snapshot. Both cities change clocks at 02:00 local on Nov 1, so the 3-hour difference still holds at the deadline.

## What was confirmed, and how

| Question | Answer | Evidence | Confidence |
|---|---|---|---|
| Deadline instant | Nov 1 1:00 PM America/New_York = 18:00 UTC = **10:00 AM PST** | The Luma event record (public API `api.lu.ma/event/get`, retrieved 13:11 UTC Oct 31) has `"timezone":"America/New_York"`, `start_at 2026-10-30T21:00Z`, `end_at 2026-11-01T22:00Z`. 21:00Z is 5:00 PM EDT, which matches the published Friday "5:00 PM check-in"; 22:00Z is 5:00 PM EST. So the event's published clock times are Eastern. `scripts/submission_countdown.py` asserts the conversion. | Event timezone: confirmed from machine-readable data. That the 1:00 PM deadline uses that same clock: inferred; no organizer text says so separately. |
| Where to upload | **Not found** | See search log. Neither scienceclawhack.ai nor Luma names a form, folder, email, Discord channel or desk. | Confirmed absent from public sources |
| Slide count, time limit, live demo allowed, projector/laptop/adapter, file format | **Not published anywhere I can read** | The site lists only "Presentations & Judging 2:30 PM". The FAQ has nothing on format. | Confirmed absent |
| In-person required | **Yes** | FAQ: "We won't be set up for remote or hybrid participation. This is an in-person event." and "every member should attend in person." Luma registration requires ticking agreement that there is no remote option. | Confirmed |
| Who on the team is physically in Boston | **Not confirmed** | Only chat evidence: Kavita booked travel Oct 29 – Nov 2 (WhatsApp Oct 9); Joel Dietz is an MIT Media Lab fellow; goals.md (Oct 16) lists five members and says the team was accepted, with an open item to confirm every on-site member is approved on Luma. Nothing shows who actually arrived. | Unknown. **Needs a human answer today.** |
| The 3-minute budget | The 3:00 is our own budget, not a published limit | The organizers give no limit. | Unconfirmed |

## Search log: where I looked

| Place | Result |
|---|---|
| scienceclawhack.ai (full page text, schedule, FAQ, rubric, every link in the HTML) | No upload location. FAQ: approved registrants are added to a "ScienceClaw Discord" (no link published). Contact: scienceclaw@mit.edu (listed for volunteers). |
| Luma `luma.com/event/evt-lrhAXSeA3Dq8uSI` page and API record | Registration closed (`sold-out`, approval required). No submission text, no FAQ (`faqs: null`). Host: E14 Fund (Habib Haddad). "Contact the host" exists but needs a Luma login. |
| `lamm-mit/scienceclaw` README | Has a Slack invite for the ScienceClaw framework community and the Infinite platform. Neither mentions the hackathon. Infinite's `/submit` page is for platform posts (hypothesis/method/data), not slides. Do not mistake it for the slide channel. |
| Web search | Nothing about this event. |
| `/home/ubuntu/git/scienceclaw-hackathon-ideas` (`resources/emails`, `resources/chat`, `resources/drive`, `OUTREACH.md`, `goals.md`, `ENTRY.md`) | Emails there are Drive/Docs notifications from Joel Dietz; **no Luma, E14 or organizer email**. The WhatsApp exports (Oct 4–17) contain no submission information. `OUTREACH.md` §1 drafts a question to scienceclaw@mit.edu asking the submission format; **no evidence it was sent and no reply is on file.** |
| Gmail, Luma guest portal, ScienceClaw Discord, organizers' Drive | **Not checked: I have no access.** These are the likeliest places the answer is. |

## Human actions that settle the channel (in order of speed)

1. **Ask a person at the Media Lab** (registration/info desk or an organizer on the Main Stage side). Whoever is on site can answer slide format, upload mechanism, time limit and demo rules in one conversation. Fastest path; do it first thing.
2. **Search inboxes** of every person who applied on Luma (Kris, Kavita, Joel Dietz): `from:(luma.com OR lu.ma OR e14.vc OR mit.edu) newer_than:30d` and `ScienceClaw`. Luma mails registered guests event updates.
3. **Open the ScienceClaw Discord** (members are added after approval) and read announcements/pinned messages for "slides", "submit", "upload".
4. **Email scienceclaw@mit.edu.** Draft below; **not sent** (no instruction to send).
5. Whatever the answer, **paste the receipt** (confirmation text, screenshot path, or the name of the person who accepted the file and the time) into the log at the bottom and into `tasks/results/submit.json` (`submission_receipt`). Do not mark the upload done on a guess.

Draft email (for the user to send, from a registered address):

> Subject: ScienceClaw: how do we submit final slides?
>
> Hello, we are a registered team at the Media Lab this weekend. The schedule says final slides are due Sunday at 1:00 PM. Could you tell us (1) where and how to submit them (form, folder, email, or in person), (2) the accepted file format (PDF / PPTX / Google Slides link), (3) the presentation time limit and whether a short live demo is allowed, and (4) whether the 1:00 PM deadline is Eastern time on the clock change day? Thank you.
>
> [Team name, members present]

## Deck pipeline (rebuild so numbers cannot go stale)

```
bash presentation/rebuild.sh              # rebuild deck.html, deck.pdf, deck.pptx, notes, appendix, provenance, screenshots; then gate
CHECK_ONLY=1 bash presentation/rebuild.sh # rebuild into a temp dir and only verify; touches no tracked file
```

What the gate does (and exits non-zero on failure):

- Refuses to build if anything under `artifacts/`, `site/`, `evolve/` or `docs/company-hypothesis.md` is uncommitted.
- `build_deck.py` recomputes every number from committed files and rejects an incomplete or inconsistent replay (existing validator).
- `export_pdf.py`: exactly 6 pages, no console errors, no slide overflow.
- **New, `trace_numbers.py`** (independent of `build_deck.py`): 67 claims, each re-derived from a named committed file and required to appear verbatim on its slide; **any number on a slide not claimed by an artifact fails the run**; speaker-note numbers must be on the slide; every number in the PDF must be on the HTML slide; the build stamp commit must exist; and every input hash recorded at build time must equal the file now (**STALE** otherwise). Output: `presentation/number_trace.json` (slide, shown text, files, SHA-256).
- `tests/test_trace_numbers.py` proves the gate fails when a number is changed, an unclaimed number is added, an artifact value changes, or an input file changes. (5 tests; 24 presentation tests pass.)

Exits recorded in `tasks/results/submit.json`. Result at commit time: all 6 pages, 67/67 claims traced, 0 errors, 0 stale inputs, 385 spoken words.

Limits of this check: it proves slide numbers are re-derived from committed files and not hand-typed or stale. It does **not** prove the science. One entry is bibliographic and flagged as such (the 2024 year of the cited PNAS paper). The direct-ordering count (24; 0 admitted) is read from `route_summary.json`, which the builder separately recounts from `site/data/landscape.js`. Three kinds of figure (route chart curves, replay curves, landscape image) are drawn from artifacts by the builder and not individually traced as numbers.

Files to bring: `presentation/deck.pdf` (primary), `presentation/deck.pptx` (**image-only fallback**, speaker notes attached, not editable text; for a PowerPoint / Google Slides requirement), `presentation/deck.html` (offline, works without network; `n` shows notes), `presentation/video/darwins-bridge-walkthrough.mp4` (90 s silent fallback; its manifest pins the earlier build source). Keep copies on the presenting laptop and a USB stick; don't depend on venue Wi-Fi.

## Three-minute script, timed (TrpB BASELINE script; the pitch script is `presentation/delphi/speaker-notes.md`, timing in `presentation/delphi/timing.json`)

**Do not present from the baseline script below; it describes the TrpB slides.** Script: `presentation/speaker-notes.md` (generated from the TrpB deck, 385 words; its slide timestamps are nominal budgets).
Timing: **read aloud by a local neural voice (Piper, `en_US-lessac-medium`) and measured from the audio**, `presentation/timing.json`, tool `presentation/time_script.py`. Five runs gave 2:43 to 2:45 (the table is the committed run, 2:45), including 1.5 s per slide change (an assumption). **Speech alone 158 s; about 15 s under the team's 3:00 budget.**

| Slide | Words | Seconds | Starts |
|---|---|---|---|
| 1 Route | 42 | 16.5 | 0:00 |
| 2 Landscape | 50 | 21.9 | 0:18 |
| 3 Challenge the assumption | 57 | 20.0 | 0:41 |
| 4 Benchmark | 84 | 34.9 | 1:03 |
| 5 Claims | 82 | 34.4 | 1:39 |
| 6 Checks + ask | 70 | 29.9 | 2:15 |

Cuts if told less time (measured sums): drop slide 2 → 2:21; drop slides 2 and 5 → 1:45; slides 1, 4, 6 only → 1:24.

**Not done: a human stopwatch rehearsal.** A synthetic voice is not the presenter. The 15 s margin does not cover demo clicks, a stumble or questions. The presenter must read it aloud once, on the clock, before 10 AM PST Sunday. If the real limit turns out shorter than 3:00, use a cut above.

## Go / no-go checklist

- [x] Deadline instant computed from the tz database: 10:00 AM PST Sun Nov 1 (event TZ America/New_York from Luma record).
- [x] Deck rebuilt from current `main` (78b8228); output identical to the committed deck except stamp and one punctuation fix on slide 4.
- [x] 67 slide numbers traced to committed artifacts; gate has mutation tests.
- [x] PDF: 6 pages, no overflow, numbers match HTML. PPTX fallback built.
- [x] 3-minute script measured aloud (machine voice): 2:45.
- [ ] **Submission channel found.** (human; see actions above)
- [ ] **Accepted file format, slide limit, time limit, demo rules known.**
- [ ] **At least one team member physically in Boston, ideally all; names recorded.**
- [ ] **Slides uploaded / handed in by 10:00 AM PST (1:00 PM EST), receipt recorded below.**
- [ ] Human stopwatch rehearsal under the real limit.
- [ ] Presenting laptop has PDF, HTML, PPTX and video locally; display adapter tested.
- [ ] Director's selection final: if the entry changes from the TrpB baseline, this deck no longer represents it (see below).

**Go** only when the four bold items are checked. Until then the status is no-go regardless of deck quality.

## Things to know

- **The deck is bound to the TrpB entry.** The rethink director may select a different spine (`planning/rethink/`). If so, `build_deck.py` and the claim registry in `trace_numbers.py` need new slides and claims; the gate and rebuild pipeline carry over. Decide early enough to leave time for a human rehearsal.
- **The public GitHub release `v0.1.0-hackathon` carries the earlier PDF** (build stamp a64c7210, without the slide-4 punctuation fix). I have not republished it: that is an outward-facing action for the coordinator.
- **Inconsistency in `docs/company-hypothesis.md`**: the partner ask says "one prospective round" (as slide 6 does) but the 120-day table says "Two prospective rounds". Not changed here; pick one before anyone reads both.
- **Speaker-note slide timestamps** (0:00–0:20 … 2:30–3:00) are nominal budgets; measured pace puts slide 6 at about 2:15.
- **Luma shows registration closed.** If a late team member needs to be added for in-person eligibility, that is an organizer question.
- No fabricated receipt, no claim of upload, no contact with organizers or other teams has been made.

## Receipt log (fill only with facts)

| Time (Seattle) | Channel | What was handed in | Receipt / who accepted | Recorded by |
|---|---|---|---|---|
| | | | | |
