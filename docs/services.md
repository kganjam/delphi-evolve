# External services receipt: Gemini review and Nebius structure evidence

Written 2026-10-31 (Seattle PDT, ~00:45) by the resources worker (Claude Sonnet 5.5), branch `work/resources`.
Everything below is traceable to files under `artifacts/services/`. Gemini outputs are **model opinion**; each item
was checked by the worker against code or data and given a verdict. Nothing here is a wet-lab or biological result.
The required demonstration is the query-to-certify benchmark and operational claim reuse. Structure predictions are auxiliary evidence, and the overall novelty assessment remains separate from this service receipt.

## 1. Ready-to-use receipt (for the integrator)

| Item | Status | Evidence |
|---|---|---|
| Gemini client | works | `scientific_services/gemini_client.py`; key read only into an `x-goog-api-key` header; persistent budget ledger (<=6 calls, <=150k input, <=30k output tokens) |
| Independent public-input review, Flash | done (2 calls; the first was truncated by hidden thinking tokens and is kept as is) | `artifacts/services/gemini/review_flash_independent{,_run2}.json` |
| Serious-claim critique, Pro | done (1 call) | `artifacts/services/gemini/review_pro_serious_claim.json` |
| Shortlist assay choice (optional) | done (1 call), **unvalidated** | `artifacts/services/gemini/shortlist_result.json` |
| Gemini usage total | 4 calls; 82,481 input tokens; 19,108 output tokens incl. thinking | `artifacts/services/gemini/usage_ledger.json`. Billing is not visible; no price is invented |
| Nebius MCP client | works | `scientific_services/nebius_mcp.py`; 69 tools discovered, catalogue in `artifacts/services/nebius/tools_list.json` |
| Structure, parent VFVS | **succeeded, low confidence** | op `op-5e3d2111a651d8dd`; `trpb_VFVS_openfold2.pdb`, `trpb_VFVS_openfold2_metrics.json` |
| Structure, AIKG | **succeeded, low confidence** | op `op-c03164a04e76c310`; `trpb_AIKG_openfold2.pdb`, `..._metrics.json` |
| ESMFold2 / ESMFold2-Fast | **blocked** (not guessed past) | server said `INVALID_REQUEST: the scientific manifest requires verified inner artifacts`; the manifest contents are not documented for these models (`esmfold2fast_attempt_v0.json`) |
| Structure panel | built, standalone | `scientific_services/demo/structure.html` (no CDN, no npm; not copied into `site/`) |
| Tests | 14 passed (offline) | `python3 -m pytest tests/test_services.py -q` |

### Actual protocol limits of the structure result (state these whenever the panel is shown)

* Tool: `infer_openfold2_native`, OpenFold2 `model_3_ptm` (parameter set 1), `relax_prediction=false`.
  **Single-sequence dummy MSA; no external MSA, no templates, no relaxation.** The tool exposes no seed field, so the seed is unspecified.
* Input: 397-aa Tm9D8s\* construct from CaltechDATA `h5rah-5z170` `tm9d8s_AAs.fasta` (sha256 `d56ebe8d…bbc6c`, verified by the gpu worker; header `Tm9D8*`; includes the C-terminal `LEHHHHHH` tag). VFVS is the parent; AIKG substitutes residues 183/184/227/228 only. Numbering is the 1-based index into the construct (Met1); PDB residue numbers equal it (tested). No mapping to wild-type *T. maritima* numbering is claimed.
* Confidence is poor: VFVS ranking confidence 40.8, pTM 0.263, mean pLDDT 40.8, 0.5% of residues pLDDT >= 70; the four sites have pLDDT 24 to 49. AIKG: 41.5, 0.262, 41.5.
* Against the deposited crystal structure of the same parent (`Tm9D8s_refine_19.pdb`, sha256 `1e2bcd9e…9676`, CC0), the prediction does **not** reproduce the fold: Calpha RMSD 28.5 Å (chain A, Kabsch, 389 common residues), 1% of Calpha within 4 Å. The four sites are displaced 12 to 22 Å after global superposition. The two predictions differ from each other by 5.9 Å Calpha RMSD. Given their low confidence and the parent prediction's disagreement with the experimental structure, this difference cannot be attributed to a mutation-induced conformational change. The number of substitutions alone does not establish how much a structure can change.
* pLDDT is model self-confidence, not functional confidence. A coordinate difference between predicted models is not causal evidence for the fitness difference. This is **predicted**, the growth scores beside it are **observed**; the panel shows them separately.
* Downloaded bytes and hashes are retained; signed URLs were used in memory and never stored; the team bucket name is omitted. Wall times: VFVS 00:29:59 to 00:35:38 PDT (338.6 s; about 5 min queue, inference 19.7 s), AIKG 00:38:31 to 00:41:09 PDT.

### What cannot be inferred
That any variant is active or inactive; that AIKG is structurally different from VFVS; that low fitness has a structural cause; anything about epistasis from these models. The structure adds no evidence to any certificate, route, benchmark or Lean claim.

### Narrow pitch paragraph (use only if space allows)
"For the four mutable sites the project can show the observed growth scores next to a *predicted* TrpB backbone obtained through the Nebius Scientific AI MCP (OpenFold2, single-sequence, low confidence, 28 Å from the deposited crystal), together with the exact tool call and hashes. We use it only to show where the sites sit in the sequence and as a worked example of an auditable external-model call; it does not contribute to the route certificates." Do **not** say the structure explains the fitness landscape.

## 2. Gemini review (independent, public inputs only)

Inputs (`artifacts/services/gemini/review_bundle.md`, sha256 prefix `8bc25a1f`): excerpts of `planning/PLAN.md` and `specs/CONTRACT.md`; the project's own prior-art note (ALDE row etc.); core's frozen `protocol.json`; an independently aggregated replay snapshot (seeds 0 to 4); and core's actual code at commit `8883518` with line numbers (`evolve/{data,graph,oracle,policies,model,replay,collective}.py`). Deliberately excluded: the integrator's findings and `tasks/semantics-review.md`. **Independence caveat:** the bundle said that replay shards for seeds 5 to 19 had no per-episode rows, so Gemini's finding on that was prompted by me, not independent.

| Call | Model id requested → returned | Time (PDT) | Tokens in / out (thinking) | Finish |
|---|---|---|---|---|
| Flash run 1 | gemini-3.8-flash | 00:32 | 26,236 / 1,593 (10,403) | MAX_TOKENS: hidden thinking used the budget; partial text kept |
| Flash run 2 (`thinkingLevel=low`) | gemini-3.8-flash | 00:34 | 26,253 / 3,633 (0) | STOP |
| Pro | gemini-3.1-pro-preview | 00:34 | 25,940 / 1,380 (1,767) | STOP |
| Shortlist | gemini-3.8-flash | 00:42 | 4,052 / 332 (0) | STOP |

Prompts, system instructions, raw responses, usage and timestamps are in each JSON. Line citations in the responses were accurate against the listing where checked (policies.py:109/174/224, collective.py:130-140, graph.py:141, replay.py:101-104).

### Findings and verdicts (verified by the worker, not by the model)

Verification script: `scientific_services/verify_review.py`, output `artifacts/services/review_verification.json`. It re-implements the declared score/interval/edge rule from the pinned `summary_AA.csv` (sha256 `a631d8cf…25ee82`) without importing `evolve/`.

| ID | Claim (source) | Verdict | Basis |
|---|---|---|---|
| R1 | Shards written by `run_shard` have empty `rows` (Flash, prompted) | **Confirmed; fixed on `work/integration` (commit `4398fad`) and independently in core's working tree** | Commit `bcc0729` dropped `rows.append(out)`; shards for seeds 5 to 19 had no rows when first read. By 00:45 the core tree had an uncommitted `rows.append(out)` and was regenerating shards (13 to 14 of 20 seeds per policy had rows in my last snapshot, `artifacts/services/core_shard_summary_current.json`). Remaining check for the integrator: every shard in the final run has rows, and `summarize` covers 20 seeds |
| R2 | "False certificates = 0" is structural (Flash B1, Pro #2) | **Confirmed** | Ledger and truth use the same `Lo[v] >= Hi[u]` table (`graph.py`, `replay.py`); an open or blocked certificate on revealed nodes cannot contradict it. It is a software-correctness check, not evidence about biology. Present it that way |
| R2b | Intervals/kappa are not coverage; a replicate-level check would be non-zero (Flash B2/D2, Pro #2) | **Confirmed in principle; magnitude small, measured** | Of 1,612,145 admissible directed edges at kappa=2, 2,748 (0.17%) have at least one replicate going down, 0 have both; the mean never decreases. The rule ignores per-genotype replicate disagreement, so Flash's counterexample (replicates 0.50/0.10 vs 0.20/0.50) is admitted by the rule, but such cases are rare in this table. Pro's "held-out third replicate" is impossible: only two replicates exist. kappa is already declared assumed |
| R3 | Target-aware proposed policies vs target-blind baselines confound the headline (Pro #1) | **Mechanism confirmed; "conclusion fails" not established** | `ctx.target` is used only by `Directed` (109), `Planner.open_routes` (174) and `frontier_probs` (224); random, greedy, uncertainty never read it. The target-aware non-learned baseline `directed` exists and, in the current partial replay (about 12 of 20 seeds), certifies 25% of Family B episodes vs 79% for q2c. The missing control is a target-aware **learned-uncertainty** baseline (Pro's prediction that it would match q2c is **unresolved**, not run) |
| R4 | Greedy baseline is crippled (Pro #3) | **Confirmed in a different form** | `Greedy.rank` sorts `np.lexsort((F, -sc))`, so equal-score frontier nodes tie-break by genotype index. Seed 0, VFVS to AIKG: first 25 queries are AFVS, CFVS, DFVS, EFVS, FFVS, GFVS, HFVS, IFVS, … i.e. alphabetical. It also has no surrogate and ignores the target by design. 0 of 48 Family B episodes certify |
| R5 | `collective_isolated` gets free information via duplicate requests (Flash A3, `collective.py:130-140`) | **Confirmed as an isolation breach; refuted as a budget leak** | Duplicates return only genotypes already paid for, so no new label is free, but private ledgers are fed from the pooled ledger, so the arm is not isolated. Flash's explanation of 19/20 vs 15/20 is unresolved (arbitration also differs, as the integrator's F7 says) |
| R6 | Family B is 100% open and cannot test blocked decisions (Flash A2) | **Confirmed** | All four published targets are reachable from VFVS (independent BFS). The VFVS closure has only 137 nodes, so a blocked certificate would need on the order of 10^4 assays against a budget of 1000. Blocked decisions are tested only by Family A starts (e.g. local peaks); in the partial replay, 3 of 12 per policy |
| R7 | Noise bins and SDs fitted on all 159,129 genotypes (Flash A1) | **Confirmed**; neutral between policies | Recomputed SDs equal the hardcoded ones to 4 digits (0.01495, 0.01000, 0.00585, 0.00299). Estimating them from the 96 initial observations alone leaves 18.8% of per-seed bins with fewer than 5 observations, so the benchmark presupposes prior noise knowledge. Keep calling this transductive sensitivity calibration |
| R8 | Target label is revealed free in Family B (Flash run 1 A1) | **Confirmed, low severity** | `replay.py:101-104`; identical for all policies; about one assay of cost in a real lab |
| R9 | Median assays among certified hides censoring (Flash C1) | **Confirmed for my snapshot table, refuted for core's protocol** | Core's `summarize.py` uses RMST with right-censoring. My `shard_summary.py` now also reports cert fraction and RMST at budget |
| R10 | Planner only proposes monotone completions, blind to detours (Flash D3) | **Partly confirmed; effect unresolved** | `open_routes` permutes only the differing sites from each closure member. But all 31 truth-open q2c episodes with rows have shortest routes 1 to 2 steps longer than Hamming distance, so detours are the norm; detours are found by growing the closure, not by the route specialist. Whether this costs assays is untested |
| R11 | Compute asymmetry across policies (Flash C2) | Real, outside the protocol | Budget is matched in assays, not CPU; rows record `wall_s` |
| R12 | ALDE is not an equivalent baseline (Flash C3) | **Confirmed**; Flash's attribution is wrong | ALDE is Yang, Lal, …, Yue, Arnold, *Nature Communications* 2025 (doi 10.1038/s41467-025-55987-8), not Johnston et al. I read the page: it simulates GB1 and TrpB four-site landscapes (96 random starts, four rounds of 96, encodings AAIndex/Georgiev/one-hot/ESM2, several models and acquisition functions, 70 random initialisations, metric normalised maximum fitness reached) and has a wet-lab ParPgb campaign. It reports no path/reachability or certificate analysis. We have not run ALDE, so no comparison is made |
| R13 | Unmeasured genotypes act as barriers in "blocked" (Flash B3) | Confirmed scope limit; already declared | `protocol.json graph_scope`; see `tasks/semantics-review.md` for the strong-vs-conservative distinction |
| R14 | GP hyperparameters tuned to the landscape (Flash A4) | **Unresolved** | `model.py` states they are fixed a priori; git history cannot show that nothing was tuned. Needs the author's statement |
| R15 | Stop-codon background offset leaks labels (Flash run 2 A4) | **Not material** (reasoned, not run) | Stop rows are outside the graph; a per-replicate constant cancels in `Lo[v] >= Hi[u]` up to micro-unit rounding |

The benchmark was **not** changed to satisfy any review.

### Proposed fixes for the integrator (paths are in the core checkout; none applied here)

1. `evolve/replay.py` `run_shard`: keep `rows.append(out)` and add a test that every shard has rows (`tests/test_core_replay.py`). Re-aggregate all 20 seeds before quoting any number.
2. `evolve/policies.py` `Greedy.rank`: random (seeded) tie-break instead of genotype index; add target-aware variants `greedy+target` and `uncertainty+target` (Hamming-weighted) as controls for R3. Report q2c against these, not only target-blind policies.
3. `evolve/collective.py:130-140`: label the isolated arm "pooled-ledger duplicate answers" or remove the side channel; pair with a matched-arbitration shared/isolated pair (the `collective_shared_rr` arm appears to start this).
4. Report `artifacts/core/...` results with an explicit second panel of truth-blocked pairs (Family A local-peak starts) and state that Family B has no negative class. Do not report "false certificates = 0" without saying it is structural.
5. Add the replicate-reversal statistic (0.17% of admissible edges at kappa=2, `artifacts/services/review_verification.json`) to the demo as a descriptive diagnostic labelled "not a confidence level".
6. In docs/pitch/blog: reference ALDE with the correct authors and state that ALDE was not run as a baseline.

### Optional shortlist experiment (unvalidated; one sample)
Episode: Family B seed 0, VFVS to AIKG; the initial-observation hash matches the protocol (`32592d5f…`). Prompt contained only the 98 revealed labels with assumed intervals. Shortlist rule was label-free (four one-step moves toward the target plus four seeded random neighbours). Gemini chose **AFVS**; after the fact AFVS is **not** admissible from VFVS, and the only admissible candidate, VIVS, was ranked fourth. Its quoted numbers were correct, but its claim that AGCN is "highly active" is not supported (AGCN score 148,648 vs AIKG 357,764 micro-units). The known full-data route starts VFVS to VFMS (a 227 V to M move away from the target residue), which this shortlist did not contain. This is a single anecdote, was not compared with core policies at the same assay budget, and is not counted as any improvement in scientific agency.

## 3. Nebius Scientific AI MCP: what was called

Endpoint `https://forge.nebius.cloud/mcp` with the team bearer key (key in header only). Calls made: `initialize`, `tools/list` (69 tools), `get_tool_catalog_revision`, `list_scientific_models`, `get_model_schema` for esmfold2 and esmfold2-fast, `infer_openfold2_native` twice (stable keys `delphi-evolve-structure-c0964e6dbcd43854` and `…-f4055b5868027bbf`, `<sequence sha256[:16]>`), `get_operation` polling, `get_operation_result`, `download_scientific_artifact` twice, and for the ESMFold2-Fast attempt `begin_`/`finalize_scientific_artifact_upload` (an 82-byte manifest) and one rejected `submit_esmfold2_fast`. At most one operation was in flight at a time; no raw Nebius compute job was submitted; no account or terms action was taken.
Protocol facts observed: the VFVS submit returned a 503 `SERVERLESS_REQUEST_FAILED` with `admission: accepted`, and I polled that same operation id (no resubmit) until `SUCCEEDED`. The AIKG submit returned `operation.id` instead of `operation_id`; my first poller missed it, so the same id was polled afterwards (`structure_AIKG_submit_original.json` keeps the original response; this is also a regression test). No price or quota is exposed by the tools and none is invented.

## 4. Reproduce

```
python3 -m scientific_services.discover_nebius            # tools_list
python3 -m scientific_services.predict_structure --genotype VFVS   # OpenFold2, polls same op id
python3 -m scientific_services.fetch_structure ...        # see file docstring; in-memory signed URL
python3 -m scientific_services.structure_artifacts VFVS   # PDB + metrics + crystal comparison
python3 -m scientific_services.build_structure_demo       # demo/structure.html
python3 -m scientific_services.build_review_bundle && python3 -m scientific_services.run_review flash _run2
python3 -m scientific_services.verify_review <summary_AA.csv> <shards_dir> out.json
python3 -m scientific_services.leak_scan                  # credentials / signed URL check
```
Every process was run under `systemd-run --user --scope -p TasksMax=128 -p MemoryMax=4G -p MemorySwapMax=0 -p RuntimeMaxSec=...`; NumPy threads were capped at 2.

## 5. Limitations
Gemini reviewed a snapshot (core `8883518`, replay seeds 0 to 4); core's code and shards have since moved. The partial-replay numbers in `core_shard_summary_current.json` are a mid-run snapshot, not results. The crystal comparison is a plain Calpha Kabsch superposition on common residues, descriptive only. External reuse of any of this by another team has **not** been observed.
