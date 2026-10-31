# Video sketch — silent 60–90 s recording of the actual site

Source: the static `site/` of the final integrated checkout, served by an in-process HTTP server on an ephemeral 127.0.0.1 port (shut down on exit; no other service is touched). Produced by `record_video.py`; the manifest records the source git HEAD, a SHA-256 over every site file, dirty paths, every interaction (with the verdict text the site showed at each slider position) and the MP4's SHA-256. If the site lacks `data/demo.json` the manifest says PRELIMINARY and `--require-demo` refuses.

A persistent caption line reads: **MEASURED = laboratory data · ASSUMED = the slider's noise bound · a static Lean receipt is NOT proof for every slider position.** The tag chip changes: MEASURED (green) for the landscape and evidence, ASSUMED (orange) for every slider position, STATIC RECEIPT (violet) on the Proof tab.

| s | Shot | Caption (main line) |
|---|---|---|
| 0–5 | Site loads | Recorded from the static site, silent capture. No lab or microscope images. |
| 5–15 | Landscape hover and click | MEASURED: every cell is one measured TrpB variant; a layout projection, not geometry. |
| 15–20 | Decision tab, VFVS → AIKG | ASSUMED: the route is computed from measured values and one assumed bound. |
| 20–40 | Slider κ = 0, 2, 3, 4, 6 | ASSUMED, one caption per position; at κ=6: no route certifiable at this bound — not a claim that none exists. |
| 40–47 | Evidence tab | MEASURED: raw replicate rows and read counts behind each step. |
| 47–56 | Proof tab | STATIC RECEIPT: one route, one assumed bound. If the build has no receipt the caption says so. |
| 56–64 | Replay tab | Shows whatever the site reports; "unavailable" is recorded as unavailable. |
| 64–68 | Close | Biologic design starts with justified enzyme experiments — not text-to-organism. |

Fallback: `--mode deck --deck presentation/deck.html` records the deck advancing every 12.5 s.
No stock footage, no generated lab imagery, no narration. Video files stay outside the repository in `/data/artifacts/delphi-evolve-presentation/video/` (≤ 20 MB); only the manifest is committed.
