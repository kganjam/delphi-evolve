# Capability inventory and readiness for Frontier (gpuops -> codex-api), 2026-10-31 ~08:35 PDT

Verified live by `python -m compute_ops.inventory` (artifacts/gpuops/inventory_live.json) unless marked. No job was submitted for this note.
Framing corrections the director asked me to keep: our GPU access is a SHARED 16-H100 pool of which we may use up to TEN while yielding (not 16 dedicated cards);
the hackathon page lists NO sponsor bonus points for Nebius, BioNeMo, OpenResearch or NVIDIA, only the +10 for strengthening other teams.

| Resource | Status right now | Measured facts | Genuine role / decorative |
|---|---|---|---|
| **Nebius raw jobs (H100/CPU)** | **BLOCKED: Unauthenticated at 08:29 PDT.** Token file written 21:37 PDT Oct 30 (10 h 52 m old) is rejected; not a decodable JWT so true expiry unknown. Needs a human with the browser session to re-issue (`nebius iam get-access-token` on the Mac, per nebius-compute.md). I did not try to work around it. | Worked at 06:28-06:47 PDT: ship-a-file validated; 4 H100 jobs (2 completed, 2 cancelled by me pre-run); cold image pull ~14-16 min per fresh node; compute rates below. Pool/queue state could NOT be re-read after the failure (last read 06:48: 0 active, 0 foreign waiting). | Genuine for GPU-bound work. |
| H100 share | unreadable quota (PermissionDenied for participants) | pool 16, our ceiling 10, yield to queued teams. Yield path only fake-tested; no foreign queue ever appeared. | -- |
| Nebius CPU | last probe 06:48: tenant non-GPU vCPU limit 24, ~20 in use by something not mine, so <=4 vCPU | 4-vCPU job ran real work (PDE scaling 2.95e7 cell-steps/s aggregate). Not re-probed (needs auth). | Marginal; local host is comparable for small CPU work. |
| **Nebius Scientific AI MCP** | **OK at 08:29 PDT** on both endpoints (forge.nebius.cloud and 89.169.99.188), separate API key, unaffected by the token problem | 69 tools, 26 models, catalog revision unchanged since 07:29 (c3da2fad...). Qualification strings: 19 'configured-native-dag-awaiting-exact-release-qualification', 6 'source-adapter-awaiting-live-qualification', 1 'isolated-pilot' (gromacs). One real call (ADMET-AI) succeeded; a prior worker got OpenFold2 TrpB structures. | Genuine as no-code inference IF a model proves qualified; none of the 26 is flagged fully qualified. |
| Hosted ESM2 (esm2-650m, esm2-3b) | enabled, availability 'available', regions north/south; **runtime unqualified, never run by us** | operations `score-variants` and `score-sequences` ONLY: returns natural-log model scores (strategies masked-marginals, wt-marginals, pseudo-log-likelihood), **NOT embeddings**; input is an uploaded manifest artifact + FASTA/variants CSV (the upload/finalize flow is more involved than the inline OpenFold2 call); output delivered to the team bucket; operator bounds 86400 s are 'operator configuration, not measured capacity'; gpu classes l40s/rtx-pro-6000/h100/h200 chosen by the platform. | Genuine only for scores. Whether its GPU use counts against our ten H100s is unknown. |
| Gemini API | OK | 60 models, 46 generateContent; gemini-3.8-flash; 16 concurrent calls twice, 0 HTTP errors; higher concurrency and daily quota not measured | Genuine as an extra model family. |
| Vertex / gcloud | OK for Vertex (global location); Compute Engine and Cloud Run APIs not enabled | enabling was blocked by the permission classifier, terms blocker untested | Vertex adds nothing over the Gemini API for us except OAuth; Compute: unavailable. |
| Brev | no access | no CLI, no ~/.brev, no credential; $0 spent | not usable. |
| OpenResearch (orx) | not re-tested | gpu worker used it LOCALLY (CPU only, telemetry off) as an experiment record | Logging/record only; not compute. Decorative for compute. |
| BioNeMo | only as the NVIDIA TE ESM2 checkpoint used by the gpu worker | TE bf16 772 seq/s single run (H100), parity with plain ESM2 ~ bf16 noise; ESM2-vs-assay Spearman 0.17 on TrpB (weak prior) | The TE checkpoint is a real, measured model; 'BioNeMo' as a sponsor is NOT a score bonus. |

## Measured compute rates already in hand (single runs, shared infra)
* PDE oracle (torch, float64, 128^2): 1 H100 2.2e9 cell-steps/s; the same node's 16 CPU threads 4.4e7; sizing rule in docs/gpuops.md.
* ESM2-650M TE bf16 on H100: 772 seq/s unmasked pass (gpu worker, artifacts/gpu); a full 160,000 x 5-pass TrpB sweep took 20 min 23 s.
* Gemini: median ~1.8 s per tiny call.

## Proposed plan for the lipase ESM2 pilot candidate (NOT authorized; waits for frozen data + protocol + acceptance gate)
The question is the scoring choice; compute is small either way (<=500 sequences, ~181 positions).
* **Path A, own H100 job via compute_ops** (reuses the gpu worker's validated TE pipeline; gives embeddings AND masked marginals): needs (1) a human-refreshed Nebius token; (2) a frozen protocol; then one 1-GPU job, server-side `--timeout 30m`, client watchdog, ~15 min cold pull + well under a few minutes of compute; outputs hashed and returned through the verified log channel. Fits a <=30 min pilot only if the image pull is not slower than today's.
* **Path B, hosted `submit_esm2_650m`**: no image pull and no GPU management, but scores only (no embeddings), unqualified runtime, and the manifest-upload flow is untested by us. A read-only schema check is done; a call needs the protocol first.
* **CPU-first measurement** (the director's gate): I have NO measured CPU rate for ESM2 inference (only H100 numbers), and running one is itself a model-inference job barred before the protocol, so I cannot honestly claim 'GPU needed' or 'CPU enough'. For <=500 sequences, the bounded pilot itself is the measurement.
* ESOL solubility and PEtab identifiability are CPU-first and need no Nebius resource; MolMIM only if embeddings are actually supported (not checked by me).

## Controls (unchanged)
Only I submit raw jobs; at most 10 H100 including all our active jobs (prefix-counted); cancel only job IDs in my manifest whose name matches; yield if another team's H100 job is queued; fail closed if the pool cannot be listed (this is exactly the current state: I would launch nothing even with a valid plan); <=2 h shards; price: no metered price visible to participants (event-provided), stop bound = server timeout + watchdog.
