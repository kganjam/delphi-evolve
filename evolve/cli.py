"""python -m evolve {audit,replay,summarize,demo}"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "core"


def cmd_audit(a):
    from . import audit
    r = audit.run(OUT / "audit.json")
    print(json.dumps(r["counts"], indent=1)); print("noise_check_ok:", r["noise_model_check"]["ok"])


def cmd_replay(a):
    from multiprocessing import Pool
    from . import replay
    pols = a.policies.split(",") if a.policies else list(replay.POLICIES)
    out = Path(a.out)
    jobs = [(str(out), p, s, a.kappa, a.budget) for s in range(a.seed_start, a.seed_end) for p in pols]
    with Pool(a.procs) as pool:
        for path, cached in pool.imap_unordered(replay.run_shard, jobs):
            print(("cached " if cached else "ran    ") + path, flush=True)


def cmd_summarize(a):
    from . import summarize
    summarize.run(Path(a.dir), OUT)


def cmd_demo(a):
    from . import demo
    demo.build(Path(a.output), replay_dir=Path(a.replay_dir))
    print("wrote", a.output)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m evolve")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("audit").set_defaults(f=cmd_audit)
    r = sub.add_parser("replay")
    r.add_argument("--out", default=str(OUT / "replay")); r.add_argument("--policies", default="")
    r.add_argument("--seed-start", type=int, default=0); r.add_argument("--seed-end", type=int, default=20)
    r.add_argument("--kappa", type=float, default=2.0); r.add_argument("--budget", type=int, default=1000)
    r.add_argument("--procs", type=int, default=2); r.set_defaults(f=cmd_replay)
    s = sub.add_parser("summarize"); s.add_argument("--dir", default=str(OUT / "replay")); s.set_defaults(f=cmd_summarize)
    d = sub.add_parser("demo"); d.add_argument("--output", default="artifacts/demo.json")
    d.add_argument("--replay-dir", default=str(OUT / "replay")); d.set_defaults(f=cmd_demo)
    a = ap.parse_args(argv)
    a.f(a)


if __name__ == "__main__":
    main()
