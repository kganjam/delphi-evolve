# Resources and execution-path audit (compute, OpenResearch, BioNeMo ESM2, Brev)

Written 2026-10-30, Seattle time PDT. No GPU was spent. No job was created. No credential was read, printed or modified.
Labels: **[VERIFIED]** means I ran or fetched it. **[DOC]** means it comes from a doc page I read but did not test. **[SPEC]** means speculation.

## 1. Nebius (read-only check) [VERIFIED]

- Read `~/git/scienceclaw-hackathon-ideas/resources/research/nebius-compute.md` in full, plus `~/.nebius/README.md`.
- `~/.nebius/bin/nebius` exists. It has profile `hackathon` (default).
- `nebius --profile hackathon ai list --page-size 200` returned data, so the token is valid right now. The token lasts about 12h, so expect `Unauthenticated` later. Refresh it from the Mac as the Nebius doc describes.
- Current contents of the shared project (3 items):
  - `kg-extract`: an endpoint (`aiendpoint-e00dzmyynar8mfx0nc`) on `gpu-h100-sxm`, RUNNING. It is another team's, so don't touch it. It holds one H100.
  - `kganjam-access-test` (`aijob-e00m1t7kkma20tny7p`): ours, COMPLETED.
  - `collagen-ppg9-pilot-20261030`: another team's, COMPLETED.
- Capacity looks free. Only one H100 appears in use, and the doc says there are 16 in total.
- I can't read the tenant quota (PermissionDenied per the doc). Queue behaviour is documented: up to 30 min of queueing, then the job fails.
- The 2026-10-30 test job went from queued to done in under 2 minutes on 1× H100 80GB (driver 580, CUDA 13.0, 196 GB RAM, 48 GB root disk).
- Flags confirmed in `ai job create --help`: `--env`, `--env-secret`, `--image`, `--platform`, `--preset`, `--registry-username`, `--registry-password`, `--registry-secret`, `--timeout`, `--volume`.
- Etiquette: 1 GPU per team, and never cancel jobs you didn't start.
- The Nebius Scientific AI MCP key is not on this machine, per the doc. **[SPEC]** It may host ESMFold and similar models, but there is no key, so it is not usable now.

## 2. Credentials and keys, presence only [VERIFIED]

| Key | In environment | In `~/.env` |
|---|---|---|
| `BREV_API_KEY` | unset | unset |
| `NGC_API_KEY` | unset | unset |
| `NVIDIA_API_KEY` | unset | unset |
| `HF_TOKEN` | unset | unset |
| `OPENRESEARCH_API_KEY` | unset | unset |

- `~/.brev` and `~/.config/brev` don't exist, and the `brev` CLI is not installed.
- `docker` and `python3` are on this box. There is no `nvidia-smi` here, so this box has no GPU.
- Orchestra: I read the skill's rules and the account model. I ran no quota commands. The rules say `auth status`, `limits` and `usage` print account emails, and `--refresh` rewrites files. That is irrelevant to this task. Nothing was consumed.

## 3. OpenResearch (alphaXiv/OpenResearch)

Sources:
- https://github.com/alphaXiv/OpenResearch
- https://openresearch.sh/docs
- https://openresearch.sh/docs/cli (the Managed Compute page)
- https://openresearch.sh/install.sh

Findings:
- **[VERIFIED]** I installed the CLI as `orx` 0.2.23 to `~/.cargo/bin/orx`. I used `OPENRESEARCH_CLI_NO_MODIFY_PATH=1` and `OPENRESEARCH_CLI_DISABLE_UPDATE=1`. The installer ignored my PATH preference and installed into `~/.cargo/bin` (it is not on PATH).
- **[VERIFIED]** I ran `orx telemetry off`. Status now reads "off". I sent no `orx feedback` and did no `orx login`.
- **[VERIFIED]** `orx exp run --backend` accepts `hf`, `modal`, `k8s`, `ssh`, `slurm`, `ray`, `openresearch`, `tinker` and `local`.
- Nebius is not a native backend. The `ssh` backend can run on a Nebius VM, but our Nebius access is serverless jobs, not SSH boxes. **[SPEC]** So Nebius can't be driven from `orx` without extra work.
- **[DOC]** `--backend openresearch` rents RunPod, Vast or Lambda machines billed at cost from a prepaid org balance. It needs `orx login` (a browser flow, so it needs the user) and a balance. Example from the docs: `orx exp run <expId> --backend openresearch --flavor h100_sxm`. Offers can be browsed with `orx compute catalog --gpu H100_SXM --count 1`. The catalog may need login. I did not run it.
- Standalone instances keep billing until `orx instance delete`.
- `orx paper` and `orx discover` fetch alphaXiv, OpenAlex, bioRxiv and PubMed metadata. I did not test whether they need login.
- Verdict: **[SPEC]** for a 24h run, OpenResearch is a harness and literature helper at best. Using it for compute adds a login and a prepaid balance. The Nebius job path is already verified and free for us. Use `orx` only if the pitch benefits from showing an agent-driven experiment log.

## 4. Fastest legitimate BioNeMo ESM2 on one H100

Sources:
- https://github.com/NVIDIA/bionemo-framework (README, "BioNeMo Recipes" section)
- https://huggingface.co/nvidia/esm2_t33_650M_UR50D
- https://catalog.ngc.nvidia.com/orgs/nvidia/clara/containers/bionemo-framework
- `https://nvcr.io/v2/nvidia/clara/bionemo-framework/tags/list` and the `2.7.1` manifest

### Option A (recommended): NVIDIA's TransformerEngine ESM2 checkpoints, loaded with HF `transformers` in the bionemo-framework container

- NVIDIA publishes TE-accelerated ESM2 checkpoints on HF under its BioNeMo collection: `nvidia/esm2_t6_8M_UR50D`, `t12_35M`, `t30_150M`, `t33_650M`, `t36_3B` and `t48_15B`. **[DOC]**
- **[VERIFIED]** `nvidia/esm2_t33_650M_UR50D` is not gated and has no HF token requirement. It carries the `custom_code` tag, so `trust_remote_code=True` is required. It was last modified 2026-04-08.
- **[VERIFIED]** The card says MIT license, "identical weights and outputs" within numerical precision, and slight numerical differences possible. Max input is 1022 residues. Supported hardware is Ampere, Hopper and Blackwell.
- **[VERIFIED]** `esm_nv.py` hard-imports `transformer_engine.pytorch`. A plain pip install of `transformers` is not enough. You need TransformerEngine, so use the container.
- **[VERIFIED]** The image `nvcr.io/nvidia/clara/bionemo-framework` is pullable anonymously. I got an anonymous token and the `2.7.1` manifest returned HTTP 200. The tag list includes `2.7.1`, `2.7`, `2.6.3`, `nightly` and others. Therefore **no NGC key is needed**. The pull may still be rate-limited. **[SPEC]**
- Caveat: one NGC page says the container is archived, with BioNeMo Recipes as the replacement. Another page lists `2.7.1`. I couldn't resolve which is current. The image is large, so budget pull time of a few minutes. **[SPEC]**
- Caveat: no quantified speedup of the TE checkpoint over the original is published on the card. Do NOT claim "X× faster" in the pitch without measuring it. Run the baseline (Option B) and the TE model on the same sequences and report both timings.
- Label for the pitch: "ESM2-650M, NVIDIA BioNeMo TransformerEngine checkpoint (nvidia/esm2_t33_650M_UR50D), bf16, 1× H100".

Launch (not run). The wrapper script is hypothetical: `embed.py` doesn't exist yet and must be written. The input has to arrive as an injected file or a bucket volume. `--inject-file` is limited to 64 KiB per file.

```bash
# pre-checks (free): nebius ai list; confirm nobody else is queued on H100s
nebius --profile hackathon ai job create --name kganjam-esm2-te \
  --image nvcr.io/nvidia/clara/bionemo-framework:2.7.1 \
  --container-command bash \
  --args "-c 'nvidia-smi && python /work/embed.py --model nvidia/esm2_t33_650M_UR50D --trust-remote-code'" \
  --platform gpu-h100-sxm --preset 1gpu-16vcpu-200gb \
  --timeout 45m --disk-size 100Gi \
  --subnet-id vpcsubnet-e00tc2metkvjckkqqp \
  --inject-file ./embed.py:/work/embed.py \
  --async
nebius --profile hackathon ai job logs <aijob-id> --follow
```

- Use a large disk. The image is multi-GB, and the doc's root disk default was 48 GB.
- Confirm `python` inside the image has `transformer_engine`, and print the versions in the first line of the log.
- `embed.py` should: load the model in bf16, sort sequences by length, batch to fit memory, time warmed-up throughput (residues/s), and write embeddings to the bucket volume or stdout as a small summary.
- Outputs should be small (under 64 KiB) or go to a mounted bucket. The `--volume s3://BUCKET:/output` form needs a bucket we may not have. Fallback: print compact results to the job log and copy them from there.

### Option B (fallback, label it "plain ESM2"): original Meta weights

- `facebook/esm2_t33_650M_UR50D` is not gated **[VERIFIED]**.
- Use any `pytorch/pytorch` or `nvidia/cuda` image with `pip install transformers torch`. Run the original `EsmModel` with bf16 or fp16 and SDPA attention.
- This is the baseline for the comparison. Label it exactly: "ESM2-650M (Meta/HF original weights, plain PyTorch)". Never call it BioNeMo.

### Not used

- The ESM2 NIM: I found no NIM doc or container page. The docs page https://docs.nvidia.com/nim/bionemo/esm2/latest/index.html returned 404. The only NIM that came up was ESMFold (https://docs.nvidia.com/ai-enterprise/nim-biology/latest/esmfold.html), and NIMs need an NGC key we don't have. Don't claim a NIM.

## 5. NVIDIA Brev [DOC for commands, VERIFIED for key absence]

Sources:
- https://docs.nvidia.com/brev/cli/getting-started.md
- https://docs.nvidia.com/brev/latest/brev-cli.html

- Install (Linux, no sudo): `bash -c "$(curl -fsSL https://raw.githubusercontent.com/brevdev/brev-cli/main/bin/install-latest.sh)"`. The script writes to `~/.local/bin`.
- Login: `brev login --token "<TOKEN>"`, copied from https://brev.nvidia.com/settings/cli, or `--api-key` for CI. Both need the user's Brev account, which makes it a human step.
- Pricing and instance-create commands are on the "Instance Management" page, which I did not read. Instance creation is blocked by a missing key and by the no-purchase rule.
- Verdict: Brev is a **fallback only**, if Nebius is saturated. It needs the user to log in and to approve spend within the $150 budget. I did not install the CLI, because nothing needs it yet.

## 6. Execution path and recommendations

1. Primary: a Nebius serverless job on 1× H100. It is verified free and fast to start.
2. Order of work: write `embed.py` and test it on CPU or a tiny model on this box (8M ESM2 on CPU works as a smoke test), and only then launch the H100 job.
3. Run the plain ESM2 baseline (Option B) and the BioNeMo TE checkpoint (Option A) in one job, or in two jobs run back to back. Report both timings and the max abs difference in embeddings. That is a defensible "BioNeMo ESM2 on H100" claim.
4. Cost: Nebius is covered by the event, so $0 of the $150. The Brev path is $0 unless the user logs in and rents. OpenResearch managed compute is $0 unless the user logs in and adds a balance. **[SPEC]** I can't price either without their catalogs.
5. Unknowns:
   - The actual H100 queue state at launch time.
   - Whether `nvcr.io` pulls inside Nebius work anonymously (the anonymous manifest fetch worked from here; the pull itself was not tested).
   - Whether the TE image's `python` already has a compatible `transformers`.
   - Any speedup of the TE checkpoint over the plain one: no number is published.
   - Token expiry (about 12h).
6. Tangible 24h deliverables from this audit:
   - `embed.py` (benchmark plus embeddings), plus a CPU smoke test. Check in.
   - One H100 job log with `nvidia-smi`, library versions and measured residues/s for TE versus plain ESM2-650M.
   - An embeddings file for whatever protein set the scientific story needs. Choose it from experimental data, not from the compute.
   - A clearly labelled pitch line stating exactly which model and which weights were used.

## 7. Side effects of this audit

- Installed `orx` 0.2.23 at `~/.cargo/bin/orx`, with telemetry off.
- Used `/tmp/orx-install` as a scratch directory.
- Nothing else was changed. No jobs, no configs, no credentials.
