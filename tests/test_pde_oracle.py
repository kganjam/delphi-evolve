import json
from pathlib import Path

import pytest
import torch

from pde_oracle.solver import MODELS, Solver, initial_state, steady_state

PARAMS = {
    "schnakenberg": {"a": .1, "b": .9, "Du": 1.0, "Dv": 10.0},
    "gierer_meinhardt": {"a": .4, "b": 1.0, "Du": 1.0, "Dv": 30.0},
    "gray_scott": {"F": .035, "k": .065, "Du": .16, "Dv": .08},
    "brusselator": {"A": 2.0, "B": 4.5, "Du": 1.0, "Dv": 8.0},
}


def P(model, B):
    return {k: torch.full((B,), v, dtype=torch.float64) for k, v in PARAMS[model].items()}


@pytest.mark.parametrize("model", [m for m in MODELS if m != "gray_scott"])
def test_homogeneous_steady_state_is_a_fixed_point(model):
    p = P(model, 2); u0, v0 = steady_state(model, p)
    u = u0.reshape(-1, 1, 1).expand(2, 16, 16).clone(); v = v0.reshape(-1, 1, 1).expand(2, 16, 16).clone()
    s = Solver(model, p, (16, 16), (12.0, 12.0))
    u2, v2 = s.run(u, v, 5.0, 0.05)
    assert torch.allclose(u2, u, atol=1e-10) and torch.allclose(v2, v, atol=1e-10)


@pytest.mark.parametrize("model", MODELS)
def test_batch_members_are_independent(model):
    p2 = P(model, 2); u, v = initial_state(model, p2, (24, 24), [3, 4])
    s2 = Solver(model, p2, (24, 24), (20.0, 20.0)); ub, vb = s2.run(u, v, 2.0, 0.1)
    p1 = P(model, 1); s1 = Solver(model, p1, (24, 24), (20.0, 20.0))
    u1, v1 = s1.run(u[1:], v[1:], 2.0, 0.1)
    assert torch.allclose(ub[1:], u1, atol=1e-12) and torch.allclose(vb[1:], v1, atol=1e-12)
    assert torch.isfinite(ub).all()


def test_cuda_cpu_agree_when_cuda_present():
    if not torch.cuda.is_available():
        pytest.skip("no CUDA here")
    p = P("brusselator", 2); u, v = initial_state("brusselator", p, (32, 32), [1, 2])
    a = Solver("brusselator", p, (32, 32), (16.0, 16.0)).run(u, v, 3.0, 0.05)[0]
    b = Solver("brusselator", p, (32, 32), (16.0, 16.0), "cuda").run(u.cuda(), v.cuda(), 3.0, 0.05)[0].cpu()
    assert torch.allclose(a, b, atol=1e-9)


def test_recorded_validation_against_independent_solver():
    d = json.loads(Path("artifacts/gpuops/pde_validation.json").read_text())
    assert d["max_abs_diff_all"] < 1e-10 and len(d["cases"]) >= 4
