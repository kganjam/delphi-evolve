#!/usr/bin/env python3
"""Fetch a complete Nebius job log despite the 1000-lines-per-query API limit.

  fetch_job_logs.py <aijob-id> <start RFC3339> <end RFC3339> <out.log>

Recursively halves the [since, until] window until a query returns < 1000 lines
(timestamps have 1 s resolution, so the emitter paces output to stay below that per second).
Duplicate lines at window edges are harmless: recover_from_logs.py de-duplicates chunks.
Uses the existing nebius CLI profile; no credential value is read here.
"""
import datetime as dt
import os
import subprocess
import sys

NEB = os.environ.get("NEBIUS_BIN", os.path.expanduser("~/.nebius/bin/nebius"))
LIMIT = 1000


def q(job, a, b):
    out = subprocess.run([NEB, "--profile", "hackathon", "ai", "job", "logs", job, "--since", a.isoformat(),
                          "--until", b.isoformat(), "--tail", str(LIMIT), "--timestamps"],
                         capture_output=True, text=True, timeout=300)
    if out.returncode:
        if "in the future" in out.stderr:
            return []
        raise RuntimeError(out.stderr[:300])
    return out.stdout.splitlines()


def fetch(job, a, b, sink, depth=0):
    lines = q(job, a, b)
    if len(lines) >= LIMIT and (b - a).total_seconds() > 1.0:
        mid = a + (b - a) / 2
        fetch(job, a, mid, sink, depth + 1)
        fetch(job, mid, b, sink, depth + 1)
        return
    if len(lines) >= LIMIT:
        raise RuntimeError(f"window {a}..{b} still has >= {LIMIT} lines; cannot split further")
    sink.extend(lines)


if __name__ == "__main__":
    job, s, e, out = sys.argv[1:5]
    sink = []
    end = min(dt.datetime.fromisoformat(e), dt.datetime.now(dt.timezone.utc))   # never query the future
    fetch(job, dt.datetime.fromisoformat(s), end, sink)
    seen, uniq = set(), []
    for line in sink:
        if line not in seen:
            seen.add(line)
            uniq.append(line)
    open(out, "w").write("\n".join(uniq) + "\n")
    print(f"{len(uniq)} unique lines (from {len(sink)}) -> {out}")
