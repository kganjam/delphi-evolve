"""Train the frozen NCA models (3 seeds + 1 shuffled-conditioning control). Writes models and loss history only."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import torch

from . import nca

OUT = Path("artifacts/rethink_nca/models")


def main():
    torch.set_num_threads(2)
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = [("nca_seed0", 0, False), ("nca_seed1", 1, False), ("nca_seed2", 2, False), ("nshuf_seed0", 0, True)]
    hist_all = {}
    for name, seed, shuf in jobs:
        if (OUT / f"{name}.pt").exists():
            continue
        t = time.time()
        model, hist = nca.train(seed=seed, iters=1000, K=16, batch=192, shuffle_cond=shuf, log=lambda s: print(name, s, flush=True))
        torch.save(model.state_dict(), OUT / f"{name}.pt")
        hist_all[name] = {"final_loss_mean_last50": sum(hist[-50:]) / 50, "first_loss_mean_first50": sum(hist[:50]) / 50,
                          "wall_s": time.time() - t}
        print(name, hist_all[name], flush=True)
        lp = OUT / "train_log.json"
        prev = json.loads(lp.read_text()) if lp.exists() else {}
        lp.write_text(json.dumps({**prev, **hist_all}, indent=1))


if __name__ == "__main__":
    sys.exit(main())
