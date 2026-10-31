"""Heterogeneous arms (preregistered variant): one agent per live family, shared vs private library, 30 calls.
Grok is excluded (managed account rate-limited); recorded as a blocker, not silently dropped."""
import json, random, subprocess, sys, time
from pathlib import Path

ROOT = Path("artifacts/commons/runs_hetero")
FAMS = ["claude", "gemini", "minimax"]
ARMS = {"MS": "shared", "MP": "private"}
SEED, REPS, CALLS, TOKENS = 20261032, 3, 30, 1200000


def main():
    order = [(a, r) for a in ARMS for r in range(REPS)]
    random.Random(SEED).shuffle(order)
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / "ORDER.json").write_text(json.dumps({"seed": SEED, "order": order, "families": FAMS, "calls": CALLS, "token_cap": TOKENS}, indent=1))
    for a, r in order:
        out = ROOT / f"{a}_r{r}"
        if (out / "summary.json").exists():
            continue
        t0 = time.time()
        cmd = ["systemd-run", "--user", "--scope", "-q", "-p", "TasksMax=128", "-p", "MemoryMax=4G", "-p", "MemorySwapMax=0",
               "-p", "RuntimeMaxSec=1800", sys.executable, "-m", "lean_commons.experiment", "--arm", ARMS[a], "--families", *FAMS,
               "--budget", str(TOKENS), "--max-calls", str(CALLS), "--out", str(out), "--run-id", f"{a}_r{r}"]
        p = subprocess.run(cmd, capture_output=True, text=True)
        (out.parent / f"{a}_r{r}.exit").write_text(f"{p.returncode} {round(time.time()-t0)}s\n")
        print(a, r, p.returncode, round(time.time() - t0), "s", flush=True)


if __name__ == "__main__":
    main()
