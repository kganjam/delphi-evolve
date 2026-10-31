#!/usr/bin/env python3
"""Bounded, resumable Claude worker using Orchestra's managed auth allocation.

Invoke inside a systemd scope. No credential is persisted or printed here.
The coordinator supplies isolated worktree, prompt and log directories.
"""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import uuid


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("role")
    parser.add_argument("worktree", type=Path)
    parser.add_argument("prompt", type=Path)
    parser.add_argument("logs", type=Path)
    parser.add_argument("--rounds", type=int, default=3)
    args = parser.parse_args()
    if os.environ.get("DELPHI_WORKER_ACTIVE"):
        raise SystemExit("Refusing a nested worker launcher")
    from orchestra.auth import acquire_credentials, release_credentials

    wid = "delphi-evolve-" + args.role + "-" + str(uuid.uuid4())
    session = str(uuid.uuid4())
    args.logs.mkdir(parents=True, exist_ok=True)
    creds = acquire_credentials(worker_id=wid, preferred="claude", requested_model="sonnet")
    if creds is None:
        raise SystemExit("No available managed Claude subscription allocation")
    # Allocator can serve several harness-backed providers. Require an OAuth
    # subscription for this launch; never fall through into an uncapped API route.
    if not (creds.provider.startswith("max_") or creds.provider.startswith("ent_")):
        release_credentials(worker_id=wid)
        raise SystemExit("Allocation is not a Max/Enterprise subscription; not launching")
    env = os.environ.copy()
    for key in list(env):
        if key.startswith("ANTHROPIC_") or key in {"CLAUDE_CODE_OAUTH_TOKEN", "OPENAI_API_KEY"}:
            env.pop(key, None)
    env.update(creds.env_vars)
    env.update(DELPHI_WORKER_ACTIVE="1", OMP_NUM_THREADS="2", OPENBLAS_NUM_THREADS="2")
    env["PATH"] = "/home/ubuntu/.elan/bin:/home/ubuntu/.cargo/bin:" + env.get("PATH", "")
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))
    signal.signal(signal.SIGINT, lambda *_: sys.exit(130))
    (args.logs / "launch.json").write_text(json.dumps({
        "worker": wid, "session": session, "role": args.role,
        "model": "sonnet", "account": creds.provider,
        "worktree": str(args.worktree), "cost_basis": "subscription; CLI estimates are not spend",
    }, indent=2) + "\n")
    try:
        for round_no in range(args.rounds):
            prompt = args.prompt.read_text() if round_no == 0 else (
                "Continue your assigned goal. Read your task and current receipts, inspect other "
                "workers' pushed changes if needed, finish implementation and tests, commit and push. "
                "Do not stop at a plan. If complete, write tasks/results/" + args.role +
                ".json with status completed and truthful checks/limitations. "
                "If blocked, record the exact blocker and finish independent work."
            )
            command = ["/home/ubuntu/.local/bin/claude", "-p", "--model", "sonnet",
                       "--effort", "high", "--allowedTools", "Read", "Write", "Edit", "Bash",
                       "WebFetch", "WebSearch", "--max-turns", "100", "--verbose",
                       "--output-format", "stream-json"]
            command += ["--session-id" if round_no == 0 else "--resume", session]
            with (args.logs / f"round-{round_no}.jsonl").open("w") as out, \
                 (args.logs / f"round-{round_no}.err").open("w") as err:
                result = subprocess.run(command, input=prompt, text=True, cwd=args.worktree,
                                        env=env, stdout=out, stderr=err, check=False)
            (args.logs / f"round-{round_no}.exit").write_text(str(result.returncode) + "\n")
            receipt = args.worktree / "tasks" / "results" / f"{args.role}.json"
            if receipt.exists():
                status = json.loads(receipt.read_text()).get("status")
                if status in {"completed", "blocked"}:
                    break
            if result.returncode != 0:
                break
    finally:
        release_credentials(worker_id=wid)


if __name__ == "__main__":
    main()
