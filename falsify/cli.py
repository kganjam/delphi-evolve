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
    nb = sub.add_parser("np-build", help="PREPARE a nanopublication for a verdict (unsigned draft; optional LOCAL signing with a key outside the repo). Never publishes.")
    nb.add_argument("request")
    nb.add_argument("--commit", required=True, help="40-hex pushed git commit of the code that computed the verdict")
    nb.add_argument("--created", required=True, help="pinned dct:created, YYYY-MM-DDTHH:MM:SSZ")
    nb.add_argument("--out-dir", required=True)
    nb.add_argument("--sign-local-key", help="PEM private key OUTSIDE the repo; produces a locally signed file for verification only")
    nb.add_argument("--supersedes")
    nb.add_argument("--include-lean", action="store_true", help="HELD by SPEC-007 rule 21; for local inspection only")
    nl = sub.add_parser("np-lookup", help="read-only SPARQL against Nanopub Query: has this regime already been certified by a published nanopub?")
    nl.add_argument("request")
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
    if a.cmd == "np-build":
        from . import nanopub as N
        req = json.loads(Path(a.request).read_text())
        res = engine.falsify_turing(req)
        li, _w = res.pop("_lean_inputs", None), res.pop("lean_wanted", None)
        if a.include_lean and li:
            d = li["dom"]
            src, _ = lean_receipt.build_source(li["J"], li["D"], d["boundary"], d["r"][0][0], [m_["index"] for m_ in li["unstable"]])
            res["lean"] = lean_receipt.run(src)
        res["receipt_id"] = "local"
        try:
            rec = N.record_from_response(res, a.commit, include_lean=a.include_lean)
        except N.NotPublishable as e:
            print(json.dumps({"prepared": False, "reason": str(e)}))
            return 3
        trig = N.build_trig(rec, a.created, a.supersedes)
        bad = N.conform(trig)
        out = Path(a.out_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "unsigned.trig").write_text(trig)
        info = {"prepared": not bad, "conformance_violations": bad, "regime_sha256": rec["regime_sha256"], "unsigned": str(out / "unsigned.trig"),
                "published": False, "stage": None}
        if a.sign_local_key and not bad:
            info["signed_local"] = N.sign_local(out / "unsigned.trig", Path(a.sign_local_key), out / "signed-LOCAL-NOT-FOR-PUBLICATION.trig")
            info["independent_check"] = N.verify_signed(out / "signed-LOCAL-NOT-FOR-PUBLICATION.trig")
        print(json.dumps(info, indent=1))
        return 0 if not bad else 1
    if a.cmd == "np-lookup":
        from . import nanopub as N
        res = engine.falsify_turing(json.loads(Path(a.request).read_text()))
        if res["verdict"] == "refused":
            print(json.dumps({"error": res["refusal"]}))
            return 2
        h = N.regime_sha256(res)
        try:
            rows = N.run_query(N.q_by_regime(h))["results"]["bindings"]
        except Exception as e:
            print(json.dumps({"regime_sha256": h, "error": f"{type(e).__name__}: {e}"}))
            return 4
        print(json.dumps({"regime_sha256": h, "published_verdicts_found": len(rows), "rows": rows,
                          "note": "a hit is a pointer, not proof: fetch the nanopub, verify trusty hash + signature, and decide whether you trust the signer; this service recomputes in milliseconds anyway"}, indent=1))
        return 0
    if a.cmd == "mcp-stdio":
        from .mcp_stdio import run
        return run(a.endpoint, a.caller)
    return 1


if __name__ == "__main__":
    sys.exit(main())
