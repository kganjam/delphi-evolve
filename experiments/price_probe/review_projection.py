"""Exact arithmetic witness for target review; not a Lean proof or measured data."""
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path


def main():
    p = [F(1, 4)] * 4
    genotype = [0, 0, 1, 1]
    additive = [F(2 * g - 1) for g in genotype]
    residual = list(map(F, [-1, 1, -1, 1]))
    fitness = [3 + a + e for a, e in zip(additive, residual)]

    def mean(x):
        return sum(pi * xi for pi, xi in zip(p, x))

    def cov(x, y):
        return mean([xi * yi for xi, yi in zip(x, y)]) - mean(x) * mean(y)

    def selection_change(x):
        return mean([wi * xi for wi, xi in zip(fitness, x)]) / mean(fitness) - mean(x)

    values = {
        "sum_p": sum(p),
        "mean_fitness": mean(fitness),
        "mean_additive": mean(additive),
        "mean_residual": mean(residual),
        "cov_additive_residual": cov(additive, residual),
        "variance_additive": cov(additive, additive),
        "variance_residual": cov(residual, residual),
        "variance_fitness": cov(fitness, fitness),
        "cov_fitness_additive": cov(fitness, additive),
        "selection_change_fixed_fitness": selection_change(fitness),
        "selection_change_additive": selection_change(additive),
    }
    assert all(pi >= 0 for pi in p) and sum(p) == 1
    assert min(fitness) > 0 and values["cov_additive_residual"] == 0
    assert values["variance_fitness"] == 2 and values["variance_additive"] == 1
    assert values["selection_change_fixed_fitness"] == F(2, 3)
    assert values["selection_change_additive"] == F(1, 3)
    receipt = {
        "evidence_kind": "exact_rational_analysis",
        "status": "constructed target-fidelity counterexample; no Lean compilation",
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "definitions": {
            "additive": "A_i = 2*g_i - 1, a fixed one-locus allele effect",
            "fitness": "w_i = 3 + A_i + e_i",
            "selection_change": "E_p[w*x]/E_p[w] - E_p[x], fixed assigned x",
        },
        "population": {
            "p": list(map(str, p)), "g": genotype,
            "A": list(map(str, additive)), "e": list(map(str, residual)),
            "w": list(map(str, fitness)),
        },
        "values": {k: str(v) for k, v in values.items()},
        "conclusion": "Setting z=w gives total variance/mean (2/3), not additive variance/mean (1/3), even with an orthogonal residual.",
        "limits": [
            "Constructed finite population, not biological measurements.",
            "The fixed-effect projection is a selection component, not total intergenerational change.",
            "This arithmetic witness is not an additional compiled Fisher theorem or evaluation attempt.",
        ],
    }
    root = Path(__file__).resolve().parents[2]
    output = root / "artifacts/integration/codex-api/price-projection-review.json"
    output.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"artifact": str(output.relative_to(root)), "values": receipt["values"]}))


if __name__ == "__main__":
    main()
