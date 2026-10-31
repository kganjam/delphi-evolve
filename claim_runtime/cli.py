"""Command line: request | evidence | verify | demo | pin | benchmarks."""
from __future__ import annotations

import argparse
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

from . import __version__
from . import evidence as E
from .common import ClaimStore, sha_file
from .records import REC_DIR, default_store, make_pins
from .service import ADAPTER_FILES, ADAPTERS, RECEIPT_PATH, ClaimService, adapter_source_sha

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "artifacts" / "claim_reuse"


def seattle_now() -> str:
    from zoneinfo import ZoneInfo
    return datetime.datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d %H:%M:%S %Z")


def utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def cmd_request(a):
    store = default_store(Path(a.records)) if a.records else default_store()
    svc = ClaimService(store, require_verified=not a.allow_unverified, receipt_path=Path(a.receipt))
    req = json.loads(Path(a.file).read_text())
    resp = svc.request(req)
    print(json.dumps(resp, indent=1, sort_keys=True))
    return 0 if resp["status"] == "computed" else 2


def cmd_evidence(a):
    spec = json.loads(Path(a.file).read_text())
    req = E.Requirement(**{**spec["requirement"], "positions": tuple(spec["requirement"].get("positions", E.TRPB_POSITIONS))})
    st = E.EvidenceStore()
    log = [st.add(c) for c in spec["claims"]]
    if spec.get("action") == "supports":
        out = st.supports_certificate(spec["evidence_ids"], req)
    else:
        out = st.lookup(spec["subject"], req)
    print(json.dumps({"import_log": log, "result": out}, indent=1))
    return 0 if out.get("decision") == "reuse" or out.get("supported") else 2


def run_capture(cmd, env=None, timeout=900):
    r = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, timeout=timeout)
    return r.returncode, (r.stdout.strip().splitlines() or [""])[-1] + ((" | " + r.stderr.strip().splitlines()[-1]) if r.returncode and r.stderr.strip() else "")


def cmd_verify(a):
    env = dict(os.environ, PYTHONPATH=str(ROOT), OMP_NUM_THREADS="2", OPENBLAS_NUM_THREADS="2")
    pins = make_pins()
    t_cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_claim_runtime_kimura.py",
             "tests/test_claim_runtime_service.py", "tests/test_claim_runtime_evidence.py", "tests/test_claim_runtime_reuse.py"]
    t_exit, t_tail = run_capture(t_cmd, env)
    m_out = ART / "mutation_receipt.json"
    m_cmd = [sys.executable, "-m", "claim_runtime.mutation", str(m_out)]
    m_exit, m_tail = run_capture(m_cmd, env)
    mres = json.loads(m_out.read_text()) if m_out.exists() else {}
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    except Exception:
        commit = None
    rec = {"kind": "claim-adapter-verification/v1", "seattle_time": seattle_now(), "runtime_version": __version__,
           "adapters": {aid: {"claim": cid, "adapter_version": ver, "adapter_source_sha256": adapter_source_sha(aid),
                              "claim_content_sha256": pins[cid]["content_sha256"]}
                        for cid, (aid, ver) in ADAPTERS.items()},
           "tests": {"cmd": " ".join(t_cmd), "exit": t_exit, "tail": t_tail},
           "mutation": {"cmd": " ".join(m_cmd), "exit": m_exit, "guard_mutants_killed": sum(m["killed"] for m in mres.get("guard_mutants", [])),
                        "guard_mutants_total": len(mres.get("guard_mutants", [])),
                        "source_mutants_killed": sum(m["killed"] for m in mres.get("source_mutants", [])),
                        "source_mutants_total": len(mres.get("source_mutants", []))},
           "parent_commit": commit, "python": sys.version.split()[0],
           "note": "Verification binds THESE adapter source hashes to THESE claim content hashes. Changing either invalidates the receipt (service refuses)."}
    RECEIPT_PATH.write_text(json.dumps(rec, indent=1))
    print(json.dumps(rec, indent=1))
    return 0 if (t_exit == 0 and m_exit == 0) else 1


def cmd_pin(a):
    (ROOT / "claim_runtime" / "pins.json").write_text(json.dumps(make_pins(), indent=1, sort_keys=True))
    return 0


def cmd_demo(a):
    from . import demo
    res = demo.build(Path(a.shards) if a.shards else None, ART, utc_now())
    res["seattle_time"] = seattle_now()
    (ART / "demo_receipt.json").write_text(json.dumps(res, indent=1, sort_keys=True))
    dd = ROOT / "claim_runtime" / "demo"
    dd.mkdir(exist_ok=True)
    (dd / "receipt.js").write_text("window.CLAIM_RECEIPT = " + json.dumps(res, sort_keys=True) + ";\n")
    print("wrote", ART / "demo_receipt.json", "and", dd / "receipt.js")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="claim_runtime")
    sp = ap.add_subparsers(dest="cmd", required=True)
    r = sp.add_parser("request"); r.add_argument("file"); r.add_argument("--records"); r.add_argument("--receipt", default=str(RECEIPT_PATH)); r.add_argument("--allow-unverified", action="store_true"); r.set_defaults(f=cmd_request)
    e = sp.add_parser("evidence"); e.add_argument("file"); e.set_defaults(f=cmd_evidence)
    v = sp.add_parser("verify"); v.set_defaults(f=cmd_verify)
    p = sp.add_parser("pin"); p.set_defaults(f=cmd_pin)
    d = sp.add_parser("demo"); d.add_argument("--shards"); d.set_defaults(f=cmd_demo)
    a = ap.parse_args(argv)
    return a.f(a)


if __name__ == "__main__":
    sys.exit(main())
