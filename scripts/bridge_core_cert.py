#!/usr/bin/env python3
"""Integrator bridge: Lean-check core's kappa=2 ROUTE certificate (benchmark interval model).

  python3 scripts/bridge_core_cert.py CORE_CERT.json RAW_SUMMARY_AA.csv WORKDIR OUT.json

1. Independently recomputes every route node's integer interval from the raw CSV using the
   rule stated inside the core certificate (no import of evolve.data) and compares.
2. Re-expresses the intervals as a proof-worker table row (r1=lower, r2=upper, delta=0), which
   Lean's obsBounds turns back into exactly [lower, upper].
3. Renders a Lean module in a COPY of lean/ under WORKDIR, builds it with lake, and writes a
   receipt (exit codes, checks) to OUT.json. Also builds a mutant (route[1] and route[2]
   swapped) that must be rejected by the kernel.
Only ROUTE certificates are bridged. A core 'cut' means "no certifiable route", which the Lean
blocked theorem does not cover (see planning/INTEGRATION-FINDINGS.md F1).
Exit 0 only if recomputation matches, original builds and the mutant is rejected.
"""
import csv, json, math, os, pathlib, re, shutil, subprocess, sys
from fractions import Fraction

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evolve import proof as P  # noqa: E402  (proof worker's untrusted tooling; Lean is the authority)

cert_path, csv_path, work, out = map(pathlib.Path, sys.argv[1:5])
core = json.load(open(cert_path))
assert core["kind"] == "route", "only route certificates are bridged"
im = core["interval_model"]
edges, sds, kappa = im["sd_bin_edges_min_input_count"], im["sd_bin_values"], im["kappa"]
route = core["route"]

# --- 1. independent recomputation from raw CSV -------------------------------------------
rows, stop1, stop2, ns = {}, 0.0, 0.0, 0
with open(csv_path, newline="") as f:
    for r in csv.DictReader(f):
        if float(r["# Stop"]) > 0:
            stop1 += float(r["mu_1"]); stop2 += float(r["mu_2"]); ns += 1
        elif r["AAs"] in route:
            rows[r["AAs"]] = r
bg1, bg2 = stop1 / ns, stop2 / ns


def interval(r):
    s = ((float(r["mu_1"]) - bg1) + (float(r["mu_2"]) - bg2)) / 2
    c = min(float(r["InputCount_1"]), float(r["InputCount_2"]))
    b = sum(c >= e for e in edges)
    eps = math.ceil(kappa * sds[b] / 2 * 1e6)
    m = round(s * 1e6)
    return m - eps, m + eps


mismatch = []
for g in route:
    lo, hi = interval(rows[g])
    cl, ch = core["nodes"][g]["lower"], core["nodes"][g]["upper"]
    if abs(lo - cl) > 1 or abs(hi - ch) > 1:   # 1e-6 tolerance for float summation order only
        mismatch.append((g, (lo, hi), (cl, ch)))
exact = sum(interval(rows[g]) == (core["nodes"][g]["lower"], core["nodes"][g]["upper"]) for g in route)

# --- 2. table rows (r1=lower, r2=upper, delta=0) ------------------------------------------
dec = lambda n: f"{n / 10**6:.6f}"
obs = {g: (dec(core["nodes"][g]["lower"]), dec(core["nodes"][g]["upper"])) for g in route}
inst = P.Instance(obs, "0", scale_exponent=6)
source = {"sha256": core["dataset"]["summary_AA_sha256"], "file": "summary_AA.csv", "doi": core["dataset"]["doi"],
          "license": core["dataset"]["license"],
          "note": "intervals are core's kappa=2 model; r1=lower, r2=upper, delta=0 reproduces them exactly",
          "interval_model": im}
cert = P._base_certificate("route", inst, route, source, "core_kappa2_route_" + core["start"] + core["target"],
                           core["start"], core["target"])
cert["route"] = route
cert["bridged_from"] = {"file": str(cert_path.name), "body_sha256": core["body_sha256"]}
cert["certificate_sha256"] = P.certificate_digest(cert)
py_ok, py_msg = P.check_certificate_python(cert)

# --- 3. Lean build in a scratch copy -------------------------------------------------------
ENV = dict(os.environ, PATH=os.path.expanduser("~/.elan/bin") + ":" + os.environ["PATH"])
SCOPE = ["systemd-run", "--user", "--scope", "-q", "-p", "TasksMax=128", "-p", "MemoryMax=4G",
         "-p", "MemorySwapMax=0", "-p", "RuntimeMaxSec=600"]


def build(c, tag):
    if work.exists():
        shutil.rmtree(work)
    shutil.copytree(ROOT / "lean", work, ignore=shutil.ignore_patterns(".lake"))
    mod = P.module_name(c)
    f = work / "DarwinBridge" / "Certs" / (mod.rsplit(".", 1)[1] + ".lean")
    f.write_text(P.render_lean(c))
    agg = work / "DarwinBridge" / "Certs.lean"
    agg.write_text(agg.read_text() + f"import {mod}\n")
    r = subprocess.run(SCOPE + ["lake", "build"], cwd=work, env=ENV, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


c0, o0 = build(cert, "orig")
mut = json.loads(json.dumps(cert))
mut["route"][1], mut["route"][2] = mut["route"][2], mut["route"][1]
c1, o1 = build(mut, "mut")
rejected = c1 != 0 and re.search(r"routeCertB delta tbl route start target = true\s+is false", o1) is not None
rep = {"core_certificate": str(cert_path), "core_body_sha256": core["body_sha256"], "route": route,
       "nodes": len(route), "recompute_exact_matches": exact, "recompute_mismatch_gt_1e-6": mismatch,
       "python_mirror_accepts": py_ok, "lean_original_build_exit": c0,
       "lean_mutant_swap_build_exit": c1, "lean_mutant_rejected_by_kernel_decide": rejected,
       "lean_module": P.module_name(cert), "scope_note": "route statement only; not a blocked/cut certificate"}
rep["ok"] = (not mismatch) and py_ok and c0 == 0 and rejected
json.dump(rep, open(out, "w"), indent=1)
json.dump(cert, open(out.with_name(out.stem + ".certificate.json"), "w"), indent=1)
print(json.dumps(rep, indent=1))
sys.exit(0 if rep["ok"] else 1)
