# Visual storyboard — 75-second video (60–90 s target)

All frames are screen recordings of the real static site (`site/index.html`, served over HTTP). No generated imagery, no mock-up numbers. On-screen numbers are read from the page, which reads them from saved artifacts. Narration is optional; subtitles carry the text.

| t (s) | Frame | On-screen action | Caption / voice-over (≈ words) | Source of any number |
|---|---|---|---|---|
| 0–6 | Title card: "Darwin's Bridge" over a slow zoom into the heatmap | none | "A protein design is not a plan." | – |
| 6–14 | Full landscape, *Observed growth* lens | hover three cells; tooltip shows genotype and measured growth | "{{landscape:counts.measured_non_stop}} real measurements. {{landscape:counts.unmeasured_cells}} unmeasured." | `landscape.meta.json` counts |
| 14–24 | Same view, start VFVS → target AIKG; route polyline appears; Decision tab shows OPEN | click preset "VFVS→AIKG" | "Parent to best measured variant: a route where no step goes down." | page computation |
| 24–32 | Expand "24 direct orderings" | scroll the list; all red ✕ | "The direct orderings all pass through a worse variant." | `route_summary.json`: {{route:direct_orderings.admitted_at_parameter_0}} of {{route:direct_orderings.orderings}} admitted |
| 32–48 | **Climax.** Press "Challenge the assumption" | κ slider sweeps; route turns dashed crimson with ✕ at the failing step; rerouting; finally BLOCKED banner | "Distrust the measurements a little more… and the route breaks." | break near κ ≈ {{route:break_points.readnoise_kappa}} (`route_summary.json`) |
| 48–56 | Evidence tab | click step 3: raw replicate values, margin, read counts, SHA-256 prefix | "Every step opens its evidence." | page / `landscape.meta.json` |
| 56–64 | Claims tab | scroll Delphi claim IDs with *local* and *network* labels; note "motivation only" chip | "Linked to Delphi — as motivation, not as a test of Darwin." | `delphi_queries.json` |
| 64–72 | Proof tab and Replay tab | show whichever state exists: receipt exit codes, or the empty state "No proof receipt loaded" | "Nothing is green unless a compiled receipt says so." | `demo.json` if integrated (proof status: {{proof:status|none}}; replay: {{demo:benchmark.status|none}}) |
| 72–75 | End card | none | "From claims to experiments we can justify." | – |

## Recording instructions (fallback if the live demo fails)

1. `cd site && python3 -m http.server 8000`; open `http://localhost:8000/` in a 1280×720 browser window at 100% zoom, light theme.
2. Record the screen (OBS, or `ffmpeg -f x11grab -video_size 1280x720 -framerate 30 -i :0 out.mkv`, or the browser's built-in screen recorder). Do not speed up or edit the slider sweep: the 4-second sweep is the evidence.
3. If `data/demo.json` is present the ledger shows "demo.json loaded"; record in that state so the Proof/Replay frames show real integrated state. If it is absent, record the empty states — they are accurate.
4. Burn in subtitles from the Caption column. Export H.264 MP4 ≤ 50 MB. Keep the PNG screenshots of frames 3, 5 and 7 as a still-image fallback.
5. Never overlay a number that is not on the page. If the replay or proof frame is unavailable, show the empty state and say "not yet integrated".
