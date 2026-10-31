#!/usr/bin/env python3
"""Integrator-owned mutation check on a COPY of lean/ (never edits the repo).

Applies meaningful scientific mutants to the generated dataset certificates and
requires `lake build` to FAIL for each, while the unmutated copy must build.
Usage: python3 -I scripts/integ_mutants.py <repo_root> <workdir> > report.json
Exit 0 only if baseline passes and every mutant fails specifically in the kernel
`decide` proof of routeCertB/blockedCertB ... = true (not from a syntax/typo error).
"""
import json, os, pathlib, re, shutil, subprocess, sys

ROOT = pathlib.Path(sys.argv[1]).resolve()
WORK = pathlib.Path(sys.argv[2]).resolve()
ELAN = os.path.expanduser("~/.elan/bin")
ENV = dict(os.environ, PATH=ELAN + ":" + os.environ["PATH"])
SCOPE = ["systemd-run", "--user", "--scope", "-q", "-p", "TasksMax=128", "-p", "MemoryMax=4G",
         "-p", "MemorySwapMax=0", "-p", "RuntimeMaxSec=600"]


def build(d):
    r = subprocess.run(SCOPE + ["lake", "build"], cwd=d, env=ENV, capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr)


def fresh():
    if WORK.exists():
        shutil.rmtree(WORK)
    shutil.copytree(ROOT / "lean", WORK, ignore=shutil.ignore_patterns(".lake"))


def sub(path, fn):
    p = WORK / "DarwinBridge" / "Certs" / path
    s = p.read_text()
    t = fn(s)
    assert t != s, "mutation did not change file"
    p.write_text(t)


def bump_delta(s):
    return re.sub(r"(def delta : Int := )(\d+)", lambda m: m.group(1) + m.group(2) + "0", s, count=1)


def swap_route(s):
    a = re.search(r"def route : List Geno := \[\n(  ⟨[^\n]*,\n)(  ⟨[^\n]*,\n)", s)
    assert a
    return s.replace(a.group(1) + a.group(2), a.group(2) + a.group(1), 1)


def drop_row(s):
    lines = s.split("\n")
    i = next(k for k, l in enumerate(lines) if l.startswith("def tbl"))
    j = next(k for k in range(i + 1, len(lines)) if lines[k].strip().startswith("(⟨") and lines[k].strip().endswith("),"))
    del lines[j]
    return "\n".join(lines)


MUTANTS = [
    ("route_delta_x10", "TrpbRouteDelta005.lean", bump_delta),
    ("route_swap_first_two_interior", "TrpbRouteDelta005.lean", swap_route),
    ("blocked_drop_measured_neighbour", "TrpbBlockedDelta005.lean", drop_row),
    ("blocked_delta_x10", "TrpbBlockedDelta005.lean", bump_delta),
]
rep = {"mutants": []}
fresh()
code, tail = build(WORK)
rep["baseline_exit"] = code
ok = code == 0
for name, f, fn in MUTANTS:
    fresh()
    sub(f, fn)
    c, t = build(WORK)
    by_checker = (c != 0 and "Tactic `decide` proved that the proposition" in t
                  and re.search(r"(routeCertB|blockedCertB) delta tbl \w+ start target = true\s+is false", t) is not None)
    rep["mutants"].append({"name": name, "file": f, "build_exit": c, "rejected_by_kernel_decide_on_cert_ok": by_checker})
    ok &= by_checker
rep["all_rejected_and_baseline_passes"] = ok
print(json.dumps(rep, indent=1))
sys.exit(0 if ok else 1)
