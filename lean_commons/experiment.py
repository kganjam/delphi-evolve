"""Run one arm (commons | none) of the commons experiment. Both arms use the same model family, the
same frozen targets, the same agent count and the same token cap; see PREREG.md."""
from __future__ import annotations

import argparse
import hashlib
import json
import threading
import time
from pathlib import Path

from . import lean_check as L
from .accounting import TokenLedger
from .adapters import make_adapter
from .agent import RunCtx, run_agent, CONTRACT
from .commons import Board, Commons, AppendOnlyLog

HERE = Path(__file__).parent


def run_arm(arm: str, family: str, model: str | None, agents: int, budget: int, out_dir: Path, run_id: str,
            targets_subset: list[str] | None = None, max_calls: int | None = None,
            families: list[str] | None = None) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    targets = L.load_targets()
    if targets_subset:
        targets = [t for t in targets if t["id"] in targets_subset]
    key = f"{run_id}:{arm}"
    ledger = TokenLedger(out_dir / "ledger.jsonl", {key: budget})
    ctx = RunCtx(arm=arm, adapter=make_adapter(family, model), ledger=ledger, budget_key=key,
                 out_dir=out_dir,
                 board=Board(out_dir / "board.jsonl"), attempts_log=AppendOnlyLog(out_dir / "attempts.jsonl"),
                 targets=targets, defs=L.load_defs(), t0=time.time(), max_calls=max_calls)
    if families:                       # heterogeneous arm: one agent per model family
        names = [f"{arm}-{f}" for f in families]
        ctx.adapters = {n: make_adapter(f) for n, f in zip(names, families)}
    else:
        names = [f"{arm}-a{i}" for i in range(agents)]
    threads = [threading.Thread(target=run_agent, args=(ctx, n), daemon=True) for n in names]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    board = ctx.board.read()
    proved = [r for r in board if r["kind"] == "proved"]
    summary = {"run_id": run_id, "arm": arm, "family": family, "model_requested": ctx.adapter.model, "agents": len(names), "families": families or [family],
               "budget_tokens": budget, "max_calls": max_calls, "calls_used": ctx.calls_used, "tokens_spent": ledger.spent(key), "n_targets": len(targets),
               "n_proved": len(proved), "proved": [{"task": r["task"], "t_s": r["t_since_start_s"], "tokens_cum": r["tokens_arm_cum"],
                                                       "tries": r["tries"], "agent": r["agent"], "used_commons": r["used_commons"]} for r in proved],
               "reuse": {"certified_with_library_lemma": sum(1 for r in proved if r["used_commons"]),
                         "cross_agent_uses": sum(1 for r in proved for u in r["used_commons"] if u["author"] != r["agent"]),
                         "total_lemma_uses": sum(len(r["used_commons"]) for r in proved)},
               "failed_tasks": sorted({r["task"] for r in board if r["kind"] == "failed"} - {r["task"] for r in proved}),
               "wall_s": round(time.time() - ctx.t0, 1), "contract_sha256": hashlib.sha256(CONTRACT.encode()).hexdigest(),
               "targets_sha256": hashlib.sha256((HERE / "targets/targets.json").read_bytes()).hexdigest()}
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=["shared", "private", "none"], required=True)
    ap.add_argument("--family", default="claude")
    ap.add_argument("--model")
    ap.add_argument("--agents", type=int, default=3)
    ap.add_argument("--budget", type=int, default=300000)
    ap.add_argument("--out", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--targets", nargs="*")
    ap.add_argument("--max-calls", type=int)
    ap.add_argument("--families", nargs="*")
    a = ap.parse_args()
    s = run_arm(a.arm, a.family, a.model, a.agents, a.budget, Path(a.out), a.run_id, a.targets, a.max_calls, a.families)
    print(json.dumps({k: v for k, v in s.items() if k != "proved"}, indent=1))


if __name__ == "__main__":
    main()
