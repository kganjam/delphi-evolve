# Red-team of the dx-submit Delphi materials (critic, single-reader, NOT Codex-reviewed)

Committed Sat 2026-10-31 09:44 PDT (git 471d571; time read from git, not typed). I did not write these materials. Read: `planning/rethink/SUBMISSION.md`, `presentation/delphi/blog.md`,
`presentation/delphi/speaker-notes.md`, the text of `presentation/delphi/deck.html` (all 6 slides, notes, ledger/review footers), parts of `presentation/delphi/facts.py`
(on `work/submit` @ 59c774b). NOT read: `site/delphi/index.html` in full (only grep hits), storyboard, video captions, REVIEW-BRIEF, PPTX, bundle. Each item is
checked against my ledger (`scopedesk/ledger/`), the frozen bench, or a committed file; "fix" is a suggested replacement, not an order.

## A. Wrong or stale as written (change before the cut)

**A1. Ledger counts (slide 4, notes, blog, site, facts.py).** Text: "20 ledger rows: 17 were caught by an independent reviewer or a measurement, 3 by the author's own check."
(i) The ledger now has 21 rows (R21 added, commit 9aecc40). (ii) My earlier 17/3 split came from substring matching and was wrong: R18's text "not independently confirmed" matched
"independent". Corrected, explicit per-row classes (commit 1339d4a, `caught_by_class`): **16 independent reviewer/validator/scout, 2 mixed (R09, R15), 3 author-only (R17, R18, R20)**.
(iii) "or a measurement" is wrong in the 17: all three author-only rows ARE measurements or a frozen rule, so the sentence puts measurements on both sides.
Kinds now: prior art 7, counterexample 1, measured 4, mis-operationalised 3, convention defect 4, process defect 1, design defect 1 (=21).
Fix: "21 ledger rows: 16 were caught by an independent reviewer or validator, 2 by the author with an independent hold, 3 only by the author's own measurement or rule."
**facts.py line ~350 asserts `n_rows == 20` and `caught_by_independent_vs_author == {17, 3}`; that key no longer exists in `kill_ledger.json` (renamed `caught_by_class`), so a rebuild against the new ledger fails by design: update the assertion rather than pinning the old snapshot silently.**

**A2. "More agents did not help" (slide 5 title and notes, blog).** The evidence is (a) one simulated replay panel, ~24 distinct problems, shared specialists 78/100 = single planner 78/100, lazy search 96/100 with the gain concentrated in one repeated pair and an interval including zero (ledger M1/M2); (b) a proof pilot at a 19/19 ceiling, which cannot show the absence of a benefit. That is "no advantage shown in two small comparisons", not a finding about agents. Fix: "In the two controlled comparisons we ran, a shared-evidence collective showed no advantage over a single planner (78/100 each); the proof pilot sat at a ceiling and could not discriminate." Also add "gain concentrated in one repeated pair" next to the 96/100.

**A3. "Exact answers" for the 127-item test set (notes slide 3, site, blog, slide 3 headline "a test set with exact answers").** Keys are exact rational arithmetic only for Turing, Hamilton and Hawk-Dove items. Kimura uses a floating-point linear solve of the Wright-Fisher chain, Greenhill a Rayleigh-Ritz float eigenvalue, Fisher-KPP literature closed forms (Hadeler-Rothe, exact Allee front); items within 2-3% of a threshold were excluded; every label also depends on a declared convention (10% tolerance, "buckles iff H > H_cr"). Fix: "127 requests whose answers are computed by stated methods under declared conventions (exact rational arithmetic for most families, numerical for three)".

**A4. "a blinded payload-only audit agreed on 132 of 135 items of an earlier candidate" (slide 3).** The committed file `scopedesk/bench/audit/independent_audit_AT3_director_subagent.json` says **132 of 136** (key 747ddbae…, a candidate that included the later-dropped liquid-bridge family), by a Claude Sonnet 5.5 subagent, the same model family as the key's author; three of its four disagreements were a Greenhill semantic dispute. If 135 comes from a re-score after dropping an item, cite that file; otherwise use 136. Also the later 127/127 blinded audit (`blinded_audit_v1_2_rev3_subagent.json`) was also same-family; say so.

**A5. "Codex reviewed the corrected descriptions" (slide 6, site, blog, facts.py).** Codex reviewed scorecard **v0** and wrote corrected descriptions; **v0.1 as committed was never re-reviewed** (Codex is out of credits). The director and host say keep "single-reader, not Codex-reviewed". Fix: "Single-reader statuses, revised after a Codex review of v0; the revised version was not re-reviewed." I changed my own `SCORECARD.md` line (it said "Codex-approved") in this commit. Note facts.py asserts the strings "Codex reviewed v0" and "approves the CORRECTED descriptions" inside `scorecard.json:global_limits`: those still exist and are accurate about v0.

**A6. Frontier (slide 6, site, blog).** "Delphi Frontier, one page per open problem showing what we know, what is next and who is working on it" is fine as a proposal, but the committed evidence is currently negative about our own seeds: ledger **R21** (witness `kganjam/delphi-frontier` @ 4e10ce0, seeds sha256 3bf14a9c…): our 7 seed questions score 0 of 7 bounded, 0 ready, 105 validator issues; the morphoswarm register is 250 problems of which only 34 carry a locator and quote, 68 a references list only, **148 no source** (host correction, critic re-counted from the YAML: 34/68/148), and 0 of 250 are actionable. The frontier commit 42cd967's own subject line says "250 sourced" and is wrong. Do not call the register "sourced open problems" anywhere, and the site link "Codex's reviewed Frontier map" must not read as endorsing the seeds. Fix: add "our own seed questions failed our own validator (0 of 7 bounded)" to the Frontier proposal sentence, or drop Frontier from slide 6 and keep it on the site as a backlog.

## B. Overclaim-adjacent; tighten

**B1. Slide 2 / blog: "The plain formula's design without repair succeeded on 0 of 16."** The 16 requests have equal diffusivities, for which diffusion-driven instability is impossible for any kinetics: "0 of 16" is a theorem, not a result. Say "by construction", or drop the comparison. Also "mean 0.708" has no unit/definition on the slide.

**B2. "We ran no experiment" next to "an independent solver found a pattern on 11 of 16".** Say "no wet-lab experiment; simulations only" once, consistently (slide 1, blog).

**B3. Slide 3 "Gate with the record 50/50", "Plain textbook formula 29/50".** The 50 items are the Turing, 2-D Turing and wavelength items; key and gate are two implementations (mine; the NCA worker's) of one declared convention, so 50/50 shows implementation agreement, and 29/50 reflects trap enrichment, not how often the plain formula is wrong. The printed caveat covers this; keep it on the slide, not only in notes.

**B4. Headroom 121/127 (95.3%) and 110/127.** Fine as labelled (judgement without tools, scored by the key's author, effective n 8, arm U). Add: the keys of five families had no independent oracle until the audit below; the 95% number mostly says the benchmark is not hard for a frontier model with no tool, which weakens "needs the gate" and the deck already says nothing here says agents need it. Keep that sentence on the slide.

**B5. "Codex's metadata and text check passes (14 of 14)."** True for the frozen hashes, but it checks metadata and wording, not the answers; Codex is unavailable now. Say "metadata and wording check (Codex, 14/14)". Do not let it read as an answer audit.

**B6. Time-stamped phrases.** "Fresh-clone acceptance run passed at an earlier commit; receipt pending" is correctly hedged; keep it.

## C. Fine as written (checked)
Turing strip arithmetic (10q²-7q+1=(5q-1)(2q-1); L=2π mode n=1 det -1/8; windows 2n²<(L/π)²<5n²); "Price duplicates ATLAS"; R06 as determinant non-negativity; Gemini misses wavelength 7/14 and Greenhill 6/13 (recomputed from `headroom_unguarded/critic_scoring.json`); no "first library", no "AI solved" claims; ATLAS/Prove2Me credited; no median shown; R09 correctly labelled mismatched run, not a measured null; headroom and proof pilot labelled single-reader.

## D. Limits of this red-team
Single reader; same model family as the deck's author and the benchmark's author; not blinded; I did not read the whole site or the video captions; I did not re-run any of the deck's numbers beyond those named.
