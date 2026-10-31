# gpuops: remote compute scale-out (2026-10-31, PDT)

Receipts: `tasks/results/gpuops.json`, `artifacts/gpuops/`. All numbers are single measurements on shared infrastructure.

* **Controller** `compute_ops/batch.py`: `python -m compute_ops.batch run items.json --max-parallel N --gpu-cap 10`. Ships a script + files to a Nebius job, returns `$COPS_OUT` through the job log with sha256 verification. Cancels only job IDs in its own manifest; yields to queued other-team H100 jobs; fails closed if the pool cannot be listed.
* **Validated**: H100 80GB, 2.7 s compute, ~15 min cold image pull.
* **CPU limit**: tenant quota `compute.instance.non-gpu.vcpu` = 24, ~20 used by others; 128-vCPU jobs are impossible.
* **PDE oracle pilot** (`pde_oracle/`): H100 f64 2.2e9 cell-steps/s vs 4.4e7 on the node's 16 threads (~51x) and 7.8e6 per thread. Estimates for the assumed 384,000 x 128^2 x 20,000-step grid are in `artifacts/gpuops/pde_pilot/estimate_384k.json` with their assumptions. Not launched: awaiting a preregistered grid.
* Simulated output only; nothing here is observed biology.
