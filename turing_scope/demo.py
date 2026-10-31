"""Builds the recorded demonstration artifacts (results.json, site/data.js) by RUNNING the adapter.
Fault-injection scenarios copy the bundled snapshot to a temp dir and edit it: software validation of refusal
behaviour, not Delphi events and not biology."""
from __future__ import annotations

import copy
import json
import shutil
import tempfile
from fractions import Fraction
from pathlib import Path

from .adapter import analyze, fs
from .crosscheck import crosscheck
from .lean_check import seattle_now
from .source import BUNDLED_DIR, PKG, SourceStore, load_pins, sha

EX = PKG / "examples"
SCAN_R = ["1/2", "3/4", "1", "3/2", "2", "5/2", "3", "4", "5", "6"]


def load_example(name):
    return json.loads((EX / f"{name}.json").read_text())


def with_domain(req, r):
    q = copy.deepcopy(req)
    q["domain"]["length_over_pi"] = r
    q["request_id"] += f"@L={r}pi"
    return q


def brief(res):
    return {"request_id": res["request_id"], "verdict": res["verdict"],
            "refusal": res.get("refusal"), "unstable_modes": res.get("unstable_modes"),
            "wavelength_status": (res.get("wavelength") or {}).get("status"),
            "source_checks": [{k: c[k] for k in ("claim", "ok", "reason", "changed_fields")} for c in res["source_checks"]]}


def _tmp_snapshot(edit):
    d = Path(tempfile.mkdtemp(prefix="ts_snap_"))
    for f in BUNDLED_DIR.iterdir():
        if f.is_file():
            shutil.copy(f, d / f.name)
    edit(d)
    return d


def fault_scenarios(req):
    out = {}

    def run(name, desc, edit=None, request=None):
        d = _tmp_snapshot(edit or (lambda d: None))
        try:
            res = analyze(request or req, SourceStore.from_dir(d))
        finally:
            shutil.rmtree(d, ignore_errors=True)
        out[name] = {"description": desc, **brief(res)}

    def delete(d): (d / "turing-ddi.local.mcp.json").unlink()

    def withdraw(d):
        m = json.loads((d / "manifest.json").read_text()); m["claims"]["turing-ddi"]["status"] = "withdrawn"
        (d / "manifest.json").write_text(json.dumps(m))

    def withdraw_wl(d):
        m = json.loads((d / "manifest.json").read_text()); m["claims"]["turing-wavelength"]["status"] = "withdrawn"
        (d / "manifest.json").write_text(json.dumps(m))

    def change(d):
        raw = json.loads((d / "turing-ddi.local.mcp.json").read_text())
        inner = json.loads(raw["result"]["content"][0]["text"])
        inner["fields"]["delphi:context"] = inner["fields"]["delphi:context"].replace("fixed domain without growth or mechanics", "growing domain with mechanics")
        raw["result"]["content"][0]["text"] = json.dumps(inner)
        (d / "turing-ddi.local.mcp.json").write_text(json.dumps(raw))

    run("unchanged_source", "bundled snapshot, unmodified")
    run("source_missing", "FAULT INJECTION: turing-ddi record file deleted from the snapshot", delete)
    run("source_withdrawn", "FAULT INJECTION: snapshot marks turing-ddi withdrawn", withdraw)
    run("source_changed", "FAULT INJECTION: delphi:context of turing-ddi edited (assumption text altered)", change)
    run("wavelength_source_withdrawn", "FAULT INJECTION: only turing-wavelength withdrawn; stability verdict must survive, wavelength answer must refuse", withdraw_wl)
    bad = copy.deepcopy(req); bad["domain"]["boundary"] = "periodic_ring"; bad["request_id"] += "+periodic"
    run("wrong_boundary_periodic", "domain declared periodic (ring); adapter supports only zero-flux Neumann", request=bad)
    bad = copy.deepcopy(req); bad["domain"]["boundary"] = "dirichlet"; bad["request_id"] += "+dirichlet"
    run("wrong_boundary_dirichlet", "domain declared Dirichlet", request=bad)
    bad = copy.deepcopy(req); del bad["domain"]["boundary"]; bad["request_id"] += "+noboundary"
    run("boundary_undeclared", "boundary omitted", request=bad)
    bad = copy.deepcopy(req); bad["assumptions"]["fixed_domain_no_growth"] = False; bad["request_id"] += "+growth"
    run("growing_domain_declared", "requester says the domain grows", request=bad)
    bad = copy.deepcopy(req); bad["system"]["jacobian"] = [["1", "2"], ["2", "3"]]; bad["request_id"] += "+wellmixed_unstable"
    run("unstable_without_diffusion", "tr J>0: not a diffusion-driven setting", request=bad)
    return out


def law_mutations(req):
    out = {}
    for name, edit, desc in (
        ("Dv_10_to_1", lambda q: q["system"].__setitem__("diffusivities", ["1", "1"]), "diffusion contrast removed (Dv=Du=1)"),
        ("d_minus3_to_minus2", lambda q: q["system"]["jacobian"][1].__setitem__(1, "-2"), "reaction law g_v changed -3 -> -2"),
        ("Dv_10_to_30", lambda q: q["system"].__setitem__("diffusivities", ["1", "30"]), "diffusion contrast raised (Dv=30)"),
    ):
        row = {"description": desc}
        for lab, r in (("L=pi", "1"), ("L=2pi", "2")):
            q = with_domain(req, r)
            edit(q)
            res = analyze(q)
            row[lab] = {"verdict": res["verdict"], "unstable_modes": res.get("unstable_modes"),
                        "continuum_band_exists": res.get("band", {}).get("band_exists")}
        out[name] = row
    return out


def curve(req, qmax=1.3, step=0.01):
    (a, b), (c, d) = [[float(Fraction(x)) for x in row] for row in req["system"]["jacobian"]]
    Du, Dv = (float(Fraction(x)) for x in req["system"]["diffusivities"])
    import math
    pts = []
    for i in range(int(round(qmax / step)) + 1):
        q = i * step
        tr = (a - q * Du) + (d - q * Dv)
        det = (a - q * Du) * (d - q * Dv) - b * c
        disc = tr * tr - 4 * det
        sig = (tr + math.sqrt(disc)) / 2 if disc >= 0 else tr / 2
        pts.append([round(q, 4), sig])
    return pts


def _lean_summary(out_dir: Path):
    f = out_dir / "lean_receipt.json"
    if not f.is_file():
        return None
    r = json.loads(f.read_text())
    return {"timestamp_seattle": r["timestamp_seattle"], "lean_version": r["lean_version"], "build_exit": r["build"]["exit"],
            "mutants": [{"file": m["file"].split("/")[-1], "exit": m["exit"], "as_expected": m["as_expected"]} for m in r["mutants"]],
            "axioms": r["axiom_audit"]["distinct_axiom_sets"]}


def build(out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    short, long_ = load_example("short_L_pi"), load_example("long_L_2pi")
    rs, rl = analyze(short), analyze(long_)
    cc = {"L=pi": crosscheck(rs), "L=2pi": crosscheck(rl)}
    scan = []
    for r in SCAN_R:
        res = analyze(with_domain(short, r))
        scan.append({"length_over_pi": r, "verdict": res["verdict"], "unstable_modes": res["unstable_modes"],
                     "q_of_unstable_modes": [m["q"] for m in res["modes"] if m["n"] in res["unstable_modes"]]})
    doc = {"kind": "recorded outputs of `python -m turing_scope demo` (Python adapter run); NOT a Lean proof, NOT an observation",
           "generated_seattle": seattle_now(), "evidence_type": "model-derived",
           "pins": {k: {"content_sha256": v["content_sha256"], "response_sha256": v["response_sha256"], "source": v["source"],
                        "nanopubs": v["nanopubs"]} for k, v in load_pins().items()},
           "short_domain": rs, "long_domain": rl, "numeric_crosscheck": cc, "length_scan": scan,
           "source_faults": fault_scenarios(short), "law_mutations": law_mutations(short)}
    (out_dir / "results.json").write_text(json.dumps(doc, indent=1, sort_keys=False))
    site = PKG / "site"
    site.mkdir(exist_ok=True)
    data = {"generated_seattle": doc["generated_seattle"], "short": rs, "long": rl, "scan": scan,
            "faults": doc["source_faults"], "mutations": doc["law_mutations"],
            "curve": curve(short), "pins": doc["pins"], "lean": _lean_summary(out_dir)}
    (site / "data.js").write_text("// Recorded Python adapter outputs (python -m turing_scope demo). Not computed in the browser.\nwindow.TURING_DATA = "
                                  + json.dumps(data) + ";\n")
    return doc
