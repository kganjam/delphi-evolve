"""Execute the preregistered same-model arms in a fixed pseudo-random order (seed recorded).
Each run is its own bounded systemd scope; failures are logged, never silently dropped."""
import json, random, subprocess, sys, time
from pathlib import Path

ROOT = Path("artifacts/commons/runs")
ARMS = {"S": ("shared", 3), "P": ("private", 3), "Q": ("private", 1), "N": ("none", 3)}
SEED, REPS, CALLS, TOKENS = 20261031, 3, 30, 400000


def main(which=None):
    order = [(a, r) for a in ARMS for r in range(REPS)]
    random.Random(SEED).shuffle(order)
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / "ORDER.json").write_text(json.dumps({"seed": SEED, "order": order, "calls": CALLS, "token_cap": TOKENS}, indent=1))
    for a, r in order:
        if which and a not in which:
            continue
        arm, agents = ARMS[a]
        out = ROOT / f"{a}_r{r}"
        if (out / "summary.json").exists():
            continue
        t0 = time.time()
        cmd = ["systemd-run", "--user", "--scope", "-q", "-p", "TasksMax=128", "-p", "MemoryMax=4G", "-p", "MemorySwapMax=0",
               "-p", "RuntimeMaxSec=1500", sys.executable, "-m", "lean_commons.experiment", "--arm", arm, "--family", "claude",
               "--agents", str(agents), "--budget", str(TOKENS), "--max-calls", str(CALLS), "--out", str(out), "--run-id", f"{a}_r{r}"]
        p = subprocess.run(cmd, capture_output=True, text=True)
        (out.parent / f"{a}_r{r}.exit").write_text(f"{p.returncode} {round(time.time()-t0)}s\n")
        print(a, r, p.returncode, round(time.time() - t0), "s", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:] or None)
