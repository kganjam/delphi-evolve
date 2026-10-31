# Video — 78 s silent screen walkthrough of the actual static site

Source: the static `site/` of the final release checkout (`work/release`), served by an in-process HTTP server on an ephemeral 127.0.0.1 port (shut down on exit). Produced by `record_video.py`; `manifests/final.manifest.json` records the source git HEAD, a SHA-256 over every site file, dirty paths (none), every interaction (including the verdict text at each slider position and the text of each claim scenario) and the MP4's SHA-256. The recorder refuses without `site/data/demo.json` (`--require-demo`). Captions are chosen from what the page actually shows; "unavailable" wording appears only if a section is actually missing.

Persistent caption: **MEASURED = laboratory data · ASSUMED = the slider's noise bound · SIMULATED = a declared hypothetical · a static Lean receipt is NOT proof for every slider position.**

| s | Shot | Caption (main line) |
|---|---|---|
| 0–3 | Site loads | Silent capture of the static site; no lab images. |
| 3–11 | Map hover/click | MEASURED: 159,129 of 160,000 genotypes; a layout projection. |
| 11–26 | Decision tab, κ = 0, 2, 3, 6 | ASSUMED: 5 → 6 → 7 steps, then "no route certifiable at this bound" (not "none exists"). |
| 26–31 | Evidence tab | MEASURED: raw replicate rows and read counts. |
| 31–37 | Proof tab | STATIC RECEIPT: compiled route/cut statements at an assumed bound; mutant rejected. |
| 37–44 | Replay section | 100 episodes per policy: Q2C 78, directed 32, random 21; shared collective did not beat the single planner; no-GP arms post hoc. |
| 44–51 | Claims page: Kimura valid scenario | SIMULATED: an existing Delphi claim, a hand-authored pinned adapter, guards pass → computes. |
| 51–61 | Haploid E. coli, TrpB score as s | REFUSED: guard names the model/quantity mismatch. |
| 61–68 | Decision-change table | Withdraw/delete/edit the Delphi record → compute becomes refuse. |
| 68–74 | Evidence-reuse table | Same-context reuse = ordinary cache; fault tests are synthetic, not savings. |
| 74–78 | Close | Bounded, assumption-aware knowledge execution; justified enzyme experiments. |

No stock footage, no generated lab imagery, no narration. The committed MP4 is `presentation/video/darwins-bridge-walkthrough.mp4` (≈1.7 MB).
