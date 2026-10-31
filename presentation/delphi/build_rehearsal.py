#!/usr/bin/env python3
"""Generate presentation/delphi/REHEARSAL.md: a stopwatch checklist for a human run-through.  Nothing in it is a result.

    python3 presentation/delphi/build_rehearsal.py
Reads timing.json (synthetic-voice measurement), speaker-notes.md, the video manifest and the bundle manifest if present.
"""
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    t = json.loads((HERE / "timing.json").read_text())
    notes = (HERE / "speaker-notes.md").read_text()
    parts = re.split(r"\n\*\*Slide (\d)\*\* \([^)]*\)\n\n", notes)
    spoken = {int(parts[i]): parts[i + 1].strip() for i in range(1, len(parts), 2)}
    mm = lambda s: f"{int(s // 60)}:{int(s % 60):02d}"
    outline = {1: "0:00-0:25 reveal", 2: "0:25-1:00 check and repair", 3: "1:00-1:30 compiled nodes and test set", 4: "1:30-2:15 ledger", 5: "2:15-2:45 what the collective measured", 6: "2:45-3:00 close"}
    must = {
        1: "A linear-mode statement for a declared model. Classical mathematics. We ran no experiment. Not a claim that a pattern forms.",
        2: "Limitation first: the algorithm is trivial. Model-only: one kinetics, 3 seeds, no confidence interval, near-onset patterns marginal. Not an experiment.",
        3: "The Price identity is already in ATLAS; ours duplicates it. Test set is frozen. Agreement with our own key is not external validation.",
        4: "17 of 20 caught by an independent reviewer or a measurement, 3 by the author. No control arm: audit versus self-audit. One team, one day. No median.",
        5: "More agents did not help. Checker-tool arm was not run. Headroom check measures judgement, not derivation. The pilot hit a ceiling; the checker was repaired after the outcomes.",
        6: "Outside use: none observed yet. Delphi Frontier is a proposal, nothing deployed. Scorecard sentence exactly as printed: 6 linked, 1 related lemma, 2 empirical, 12 without a check.",
    }
    L = ["# Rehearsal checklist (human stopwatch)", "",
         "**Status: no human rehearsal has been done.** The timings below are a synthetic-voice read-through (`timing.json`), not a person. Nothing on this page is a result until the blank cells are filled by someone with a stopwatch.", "",
         f"Measured read-aloud (synthetic voice): speech {t['speech_seconds']} s, with {t['transition_s_assumed']} s assumed per slide change: **{t['total_mm_ss']}** against a 3:00 budget (the organizers publish no time limit; see `planning/rethink/SUBMISSION.md`). Margin about {t['margin_to_limit_s']} s, which does not cover demo clicks, a stumble or questions.", "",
         "## Run 1: read the script straight, no slides", "",
         "| Slide | Outline beat | Words | Synthetic start | Synthetic length (s) | Your start | Your end |", "|---|---|---|---|---|---|---|"]
    for r in t["per_slide"]:
        L.append(f"| {r['slide']} | {outline[r['slide']]} | {r['words']} | {mm(r['starts_at_s'])} | {r['seconds']} | | |")
    L += ["", "Pass: total at most 3:00 including slide changes. Write the total here: ______ . If over, use the cuts below and rehearse again.", "",
          "## Cuts if the real limit is shorter (synthetic-voice sums)", "", "| Cut | Slides kept | Length |", "|---|---|---|"]
    for k, v in t["cuts"].items():
        L.append(f"| {k} | {', '.join(map(str, v['slides']))} | {v['mm_ss']} |")
    L += ["", "## Run 2: with the deck (PDF, then the HTML deck with `n` for notes)", "",
          "For each slide say, in your own words, the sentence below. These are the caveats the slides print; leaving one out is the usual way this talk goes wrong.", "",
          "| Slide | Must say aloud |", "|---|---|"]
    for n in range(1, 7):
        L.append(f"| {n} | {must[n]} |")
    L += ["", "## Never say", "",
          "First-ever; any claim that a named law is wrong; that a pattern forms (linear mode only); a universal diffusion threshold; that AI solved anything; that agents need the gate; a median or a '10 of 10' count; a compute-matched claim for the proof pilot; that anything is deployed or that outside people used it.", "",
          "## Questions to expect, and the answers the artifacts support", "",
          "| Question | Answer |", "|---|---|",
          "| What is new? | Only that a program checks the scope conditions, returns a witness and proposes a repair. The algorithm is trivial. |",
          "| Did you run experiments? | No. Declared-model checks, an independent solver on declared kinetics, and a retrospective enzyme replay. |",
          "| Does ATLAS already do this? | ATLAS has the Price identity; a critic's code search found no Hamilton form or Turing statements there, not exhaustive. We aim to complement it. |",
          "| Do agents need the gate? | Not shown. The checker-tool arm was not run. |",
          "| Is the benchmark independent? | No. It shares its conventions with the checker. Audits so far are same-family or non-blinded except Codex's recomputation of the v1.1 verdicts. |",
          "| Who used it? | Nobody outside the team that we have observed. |",
          "| How fast were claims refuted? | We do not show a median: times are file and commit times and rows differ in kind. |", "",
          "## Logistics", "",
          "- Deadline: **Sun Nov 1, 10:00 AM PST (1:00 PM Boston)**. No upload channel or receipt exists yet (`planning/rethink/SUBMISSION.md`).",
          "- In person: the organizers say every team member should attend.",
          "- On the presenting laptop and a USB stick, offline: `presentation/delphi/deck.pdf`, `deck.html`, `deck.pptx` (image-only fallback), the captioned video, the bundle zip.",
          "- Backup if a live demo fails: the 90-second captioned video; it is silent, so say the captions aloud.", ""]
    files = []
    for rel in ("deck.pdf", "deck.html", "deck.pptx"):
        if (HERE / rel).exists():
            files.append((f"presentation/delphi/{rel}", sha(HERE / rel)))
    vm = HERE / "video/manifest.json"
    if vm.exists():
        m = json.loads(vm.read_text())
        files.append((f"presentation/delphi/video/{m['video']['file']} ({m['video']['duration_s']} s, silent)", m["video"]["sha256"]))
    L += ["## What to carry (sha256 as built; recompute after any rebuild)", "", "| File | sha256 |", "|---|---|"] + [f"| {a} | `{b}` |" for a, b in files]
    L += ["", "The bundle zip (site, presentation folder and every cited artifact) is built after this sheet and contains it, so its hash is recorded separately in `presentation/delphi/dist/bundle-manifest.json` and `delphi-bundle.zip.sha256`, not here."]
    L += ["", "## Results (fill in)", "", "| Run | Total | Over/under 3:00 | Slides that ran long | Caveat missed |", "|---|---|---|---|---|", "| 1 | | | | |", "| 2 | | | | |", "| 3 | | | | |", ""]
    (HERE / "REHEARSAL.md").write_text("\n".join(L))
    print("wrote", HERE / "REHEARSAL.md")


if __name__ == "__main__":
    main()
