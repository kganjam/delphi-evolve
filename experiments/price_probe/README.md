# Bounded Price/Hamilton feasibility probe

`Price.lean` proves a finite weighted Price identity over real numbers and a regression-form Hamilton criterion, under stated assumptions. It uses explicit finite sums rather than axiomatizing an arbitrary “expectation” operator. `Population` restricts interpretation to normalized nonnegative frequencies and nonnegative reproductive weights with positive mean. The core algebra holds more generally.

This is feasibility work, authored and tested by one Codex session. It is not the independent 21-claim evaluation, a new biological discovery, a causal intervention theorem, or a first-ever formalization claim. The Price-to-Hamilton derivation is established literature. `fitness_selection` is total-variance selection with a transmitted assigned fitness trait; it is **not additive-genetic Fisher FTNS**.

Reproduce with Lean/Mathlib pinned by `lean-toolchain` and `lake-manifest.json`:

```
cd experiments/price_probe
systemd-run --user --scope -p TasksMax=128 -p MemoryMax=4G -p MemorySwapMax=0 -p RuntimeMaxSec=600 lake exe cache get
cd ../..
systemd-run --user --scope -p TasksMax=128 -p MemoryMax=4G -p MemorySwapMax=0 -p RuntimeMaxSec=600 env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 python3 experiments/price_probe/run_probe.py
```

The recorded execution reused the existing pinned Mathlib cache through an ignored `.lake` symlink to `/data/artifacts/mathlib-probe/.lake`; it did not download/rebuild Mathlib or modify that cache's sources. The driver invokes the configured lake binary at `/home/ubuntu/.elan/bin/lake` and Lean with two threads; adjust that binary path if needed on another host.

Receipt: `artifacts/integration/codex-api/price-probe.json`. Original compile must exit zero with clean printed axiom sets. Two target mutants reverse the transmission and Hamilton cost signs and retain the original attempted proofs; they must fail. `Witnesses.lean.inc` is appended in a temporary compilation unit to prove explicit two-type witnesses: nonzero transmission bias, a nonvacuous regression population, false reversed-cost criterion, and a reversal when residual orthogonality is dropped. No private data, network call, credentials or measurements are used by the driver.

Biological interpretation requires an external statement-fidelity review. The regression assumptions explicitly carry the covariance meaning of relatedness, positive focal variance, positive mean reproductive weight, orthogonal residual, and perfect transmission. Neither empirical coefficient estimation nor causal effects are inferred.
