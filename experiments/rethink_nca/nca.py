"""A small 1-D neural cellular automaton (NCA) trained to imitate the explicit-Euler training solver.

State per cell: 2 visible channels (u-U0, v-V0) + HID hidden channels initialised to zero. Perception: identity,
central first difference and second difference (fixed stencils, replicate = zero-flux padding) on every channel.
Update: x <- x + DT_NCA * [ Linear(perception, cond) + MLP(perception, cond) ], where cond = (log gamma, log d)
broadcast to every cell. No cell sees anything but its immediate neighbours and the global conditioning scalars.

NCA step = one Euler step (DT_NCA tau units). Training uses K-step rollouts from solver snapshots with the hidden
channels reset to zero at the window start; long-horizon behaviour (40,000 steps) is NOT trained on and is exactly what
the independent evaluator tests. The NCA is a learned surrogate of the training solver, not a model of biology.
"""
from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from . import rd

DT_NCA = 0.005
HID = 6
C = 2 + HID


class NCA(nn.Module):
    def __init__(self, hidden=128):
        super().__init__()
        self.lin = nn.Linear(3 * C + 2, C, bias=False)
        self.fc1 = nn.Linear(3 * C + 2, hidden)
        self.fc2 = nn.Linear(hidden, C)
        nn.init.zeros_(self.fc2.weight)
        nn.init.zeros_(self.fc2.bias)
        nn.init.zeros_(self.lin.weight)

    def perceive(self, x):                       # x: (S, C, N)
        xp = F.pad(x, (1, 1), mode="replicate")
        ident = x
        dx1 = (xp[..., 2:] - xp[..., :-2]) / (2 * rd.DX)
        dx2 = (xp[..., 2:] - 2 * x + xp[..., :-2]) / rd.DX ** 2
        return torch.cat([ident, dx1, dx2], 1)

    def forward(self, x, cond):                  # cond: (S, 2)
        p = self.perceive(x)
        S, _, N = p.shape
        z = torch.cat([p, cond[:, :, None].expand(S, 2, N)], 1).permute(0, 2, 1)   # (S, N, 3C+2)
        dx = self.lin(z) + self.fc2(torch.relu(self.fc1(z)))
        return x + DT_NCA * dx.permute(0, 2, 1)


def cond_of(gamma, d):
    return torch.tensor(np.stack([np.log(np.asarray(gamma, float)), np.log(np.asarray(d, float))], 1), dtype=torch.float32)


def to_nca_state(state_np):
    """(S,2,N) solver state -> (S,C,N) torch with hidden zeros, visible = deviation from steady state."""
    x = np.zeros((state_np.shape[0], C, state_np.shape[2]), np.float32)
    x[:, 0] = state_np[:, 0] - rd.U0
    x[:, 1] = state_np[:, 1] - rd.V0
    return torch.from_numpy(x)


def make_windows(rng, r, n_traj, K, T_tau=200.0, snap_every=2.0, gamma_range=(0.7, 2.0), ds=(10.0, 20.0)):
    """Generate (start, targets, gamma, d) windows from Euler trajectories. Returns torch tensors."""
    N = rd.n_cells(r)
    gam = np.exp(rng.uniform(np.log(gamma_range[0]), np.log(gamma_range[1]), n_traj))
    dd = rng.choice(ds, n_traj)
    seeds = rng.integers(0, 2 ** 31 - 1, n_traj)
    st = rd.initial_state(n_traj, N, seeds)
    _, frames = rd.euler_fd(st, gam, dd, T_tau, dt=DT_NCA, record_every_tau=snap_every)
    frames = np.concatenate([st[:, None], frames], 1)          # (n_traj, F, 2, N)
    Fn = frames.shape[1]
    starts, tg, gg, dg = [], [], [], []
    for i in range(n_traj):
        for f in range(Fn):
            starts.append(frames[i, f]); gg.append(gam[i]); dg.append(dd[i])
    starts = np.stack(starts)
    gg, dg = np.array(gg), np.array(dg)
    # targets: K successive Euler steps from each start (same step as the NCA)
    cur = starts.copy()
    seq = []
    for k in range(K):
        cur = rd.euler_fd(cur, gg, dg, DT_NCA, dt=DT_NCA)
        seq.append(cur.copy())
    seq = np.stack(seq, 1)                                     # (P, K, 2, N)
    return to_nca_state(starts), torch.from_numpy(
        np.stack([seq[:, :, 0] - rd.U0, seq[:, :, 1] - rd.V0], 2).astype(np.float32)), cond_of(gg, dg)


def train(seed=0, iters=3000, K=16, batch=192, lr=2e-3, shuffle_cond=False, rs=(10, 20), n_traj=48, log=print):
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    data = {r: make_windows(rng, r, n_traj, K) for r in rs}
    model = NCA()
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, iters)
    hist = []
    for it in range(iters):
        r = rs[it % len(rs)]
        x0, tg, cond = data[r]
        idx = torch.randint(0, x0.shape[0], (batch,))
        x, c = x0[idx], cond[idx]
        if shuffle_cond:
            c = c[torch.randperm(batch)]
        loss = 0.0
        for k in range(K):
            x = model(x, c)
            t = tg[idx, k]
            s2 = (t ** 2).mean((1, 2), keepdim=True) + 1e-5          # per-window magnitude normalisation (frozen choice)
            loss = loss + (((x[:, :2] - t) ** 2) / s2).mean()
        loss = loss / K
        opt.zero_grad(); loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step(); sched.step()
        hist.append(float(loss))
        if it % 500 == 0 or it == iters - 1:
            log(f"iter {it} loss {np.mean(hist[-50:]):.5f}")
    return model, hist


@torch.no_grad()
def rollout(model, state_np, gamma, d, T_tau, checkpoints=()):
    """Run the NCA from solver-format initial states; returns final visible state in solver coordinates (S,2,N)."""
    x = to_nca_state(state_np)
    c = cond_of(gamma, d)
    n = int(round(T_tau / DT_NCA))
    cps = {int(round(t / DT_NCA)): t for t in checkpoints}
    saved = {}
    for k in range(n):
        x = model(x, c)
        if (k + 1) in cps:
            saved[cps[k + 1]] = _vis(x)
    return _vis(x), saved


def _vis(x):
    out = x[:, :2].numpy().astype(np.float64).copy()
    out[:, 0] += rd.U0
    out[:, 1] += rd.V0
    return out


@torch.no_grad()
def fast_rollout(model, state_np, gamma, d, T_tau):
    """Numerically equivalent to `rollout` (tested), with fused matmuls and a channels-last layout. Same weights, same maths."""
    x = to_nca_state(state_np).permute(0, 2, 1).contiguous()          # (S, N, C)
    cond = cond_of(gamma, d)
    Wl, W1, b1, W2, b2 = model.lin.weight, model.fc1.weight, model.fc1.bias, model.fc2.weight, model.fc2.bias
    P = 3 * C
    Wp = torch.cat([W1[:, :P], Wl[:, :P]], 0).t().contiguous()         # (3C, hidden + C)
    Wc = torch.cat([W1[:, P:], Wl[:, P:]], 0).t().contiguous()         # (2, hidden + C)
    bias = (cond @ Wc + torch.cat([b1, torch.zeros_like(b2)])[None])[:, None, :]   # (S, 1, hidden + C)
    H = W1.shape[0]
    W2t = W2.t().contiguous()
    i1, i2 = 1.0 / (2 * rd.DX), 1.0 / rd.DX ** 2
    for _ in range(int(round(T_tau / DT_NCA))):
        xp = torch.cat([x[:, :1], x, x[:, -1:]], 1)
        lft, rgt = xp[:, :-2], xp[:, 2:]
        z = torch.cat([x, (rgt - lft) * i1, (rgt - 2 * x + lft) * i2], 2)
        o = z @ Wp + bias
        x = x + DT_NCA * (torch.relu(o[..., :H]) @ W2t + b2 + o[..., H:])
    out = x.permute(0, 2, 1)[:, :2].numpy().astype(np.float64).copy()
    out[:, 0] += rd.U0
    out[:, 1] += rd.V0
    return out
