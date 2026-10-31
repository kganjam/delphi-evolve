# gpuops: remote compute scale-out (2026-10-31, PDT)

Receipts: `tasks/results/gpuops.json`, `artifacts/gpuops/`. All numbers are single measurements on shared infrastructure.

* **Controller** `compute_ops/batch.py`: `python -m compute_ops.batch run items.json --max-parallel N --gpu-cap 10`. Ships a script + files to a Nebius job, returns `$COPS_OUT` through the job log with sha256 verification. Cancels only job IDs in its own manifest; yields to queued other-team H100 jobs; fails closed if the pool cannot be listed.
* **Validated**: H100 80GB, 2.7 s compute, ~15 min cold image pull.
* **CPU limit**: tenant quota `compute.instance.non-gpu.vcpu` = 24, ~20 used by others; 128-vCPU jobs are impossible.
* **PDE oracle pilot** (`pde_oracle/`): H100 f64 2.2e9 cell-steps/s vs 4.4e7 on the node's 16 threads (~51x) and 7.8e6 per thread. Estimates for the assumed 384,000 x 128^2 x 20,000-step grid are in `artifacts/gpuops/pde_pilot/estimate_384k.json` with their assumptions. Not launched: awaiting a preregistered grid.
* Simulated output only; nothing here is observed biology.

## Sizing rule (from the measured float64 rates; scale linearly, assumptions as in `estimate_384k.json`)
* 1 H100-hour ~ 8.0e12 cell-steps; 1 hour of the H100 node's 16 CPU threads ~ 1.6e11 (ratio ~51x).
* cell-steps = integrations x N^2 x steps. Example (ASSUMED grid, not preregistered): 3 claims x 40 domains x 8 amplitudes x 10 seeds x 2 solvers = 19,200 integrations at 128^2 x 20,000 steps = 6.3e12 cell-steps ~ 0.8 H100-hours vs ~40 h on 16 CPU threads. The earlier 384,000-run grid is 20x that.
* Unmeasured: dt convergence, the finite-difference solver's cost, multi-GPU scaling, ~15 min cold start per node.
