"""Local CLI: run the engine offline and re-verify a stored receipt.
  python -m falsify check request.json [--lean]
  python -m falsify verify-receipt receipt.json [--lean]
  python -m falsify mcp-stdio --endpoint https://HOST --caller your-team   (stdio MCP proxy, calls are logged centrally)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m falsify")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("request")
    c.add_argument("--lean", action="store_true")
    v = sub.add_parser("verify-receipt")
    v.add_argument("receipt")
    v.add_argument("--lean", action="store_true", help="also re-run the stored Lean source")
    m = sub.add_parser("mcp-stdio")
    m.add_argument("--endpoint", required=True)
    m.add_argument("--caller", default="")
    a = ap.parse_args(argv)
    from . import engine, lean_receipt
    if a.cmd == "check":
        req = json.loads(Path(a.request).read_text())
        res = engine.falsify_turing(req)
        li, _ = res.pop("_lean_inputs", None), res.pop("lean_wanted", None)
        if a.lean and li:
            d = li["dom"]
            src, meta = lean_receipt.build_source(li["J"], li["D"], d["boundary"], d["r"][0][0], [m_["index"] for m_ in li["unstable"]])
            res["lean"] = dict(lean_receipt.run(src), meta=meta)
        print(json.dumps(res, indent=1, default=str))
        return 0 if res["verdict"] != "refused" else 2
    if a.cmd == "verify-receipt":
        doc = json.loads(Path(a.receipt).read_text())
        req, old = doc["request"], doc["response"]
        new = engine.falsify_turing(req)
        new.pop("_lean_inputs", None)
        ok = new["verdict"] == old["verdict"] and new.get("modes", {}).get("unstable") == old.get("modes", {}).get("unstable")
        out = {"engine_reproduces_verdict": ok, "verdict": old["verdict"]}
        lean = old.get("lean", {})
        if a.lean and lean.get("source"):
            r = lean_receipt.run(lean["source"])
            out["lean_recheck"] = {k: r.get(k) for k in ("status", "exit", "axioms")}
            ok = ok and r.get("status") == "checked"
        print(json.dumps(out, indent=1))
        return 0 if ok else 1
    if a.cmd == "mcp-stdio":
        from .mcp_stdio import run
        return run(a.endpoint, a.caller)
    return 1


if __name__ == "__main__":
    sys.exit(main())
