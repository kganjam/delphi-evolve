from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .adapter import analyze
from .crosscheck import crosscheck
from .source import SourceStore, load_pins, make_pins


def _store(args):
    if args.source:
        m = {}
        for kv in args.source:
            k, _, v = kv.partition("=")
            m[k] = v
        return SourceStore.from_files(m, "explicit --source files")
    if args.source_dir:
        return SourceStore.from_dir(args.source_dir)
    return SourceStore.bundled()   # offline default


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m turing_scope", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="analyze one request JSON (offline, bundled source snapshot by default)")
    c.add_argument("request")
    c.add_argument("--source-dir", help="directory with manifest.json + raw Delphi MCP records")
    c.add_argument("--source", action="append", metavar="CLAIM=FILE", help="explicit local record file, e.g. turing-ddi=path.json (repeatable)")
    c.add_argument("--pins", help="alternate pins.json (reviewer-supplied)")
    c.add_argument("--crosscheck", action="store_true", help="add numpy eigenvalue cross-check")
    c.add_argument("--out")
    s = sub.add_parser("sources", help="verify source snapshot against the pins")
    s.add_argument("--source-dir")
    s.add_argument("--source", action="append")
    s.add_argument("--pins")
    d = sub.add_parser("demo", help="regenerate artifacts/turing_scope/results.json and site/data.js")
    d.add_argument("--out-dir", default="artifacts/turing_scope")
    sub.add_parser("lean-check", help="build the Lean project + mutants (wrap in systemd-run limits)").add_argument("--out", default="artifacts/turing_scope/lean_receipt.json")
    p = sub.add_parser("pin", help="REVIEWER STEP: print pins computed from the current bundled snapshot")
    a = ap.parse_args(argv)
    if a.cmd == "check":
        req = json.loads(Path(a.request).read_text())
        res = analyze(req, _store(a), load_pins(a.pins))
        if a.crosscheck and res["verdict"] != "refused":
            res["numeric_crosscheck"] = crosscheck(res)
        txt = json.dumps(res, indent=1)
        if a.out:
            Path(a.out).write_text(txt)
        print(txt)
        return 0 if res["verdict"] != "refused" else 2
    if a.cmd == "sources":
        pins = load_pins(a.pins)
        st = _store(a)
        rows = [st.check(cid, pins).to_dict() for cid in pins]
        print(json.dumps(rows, indent=1))
        return 0 if all(r["ok"] for r in rows) else 2
    if a.cmd == "demo":
        from .demo import build
        doc = build(Path(a.out_dir))
        print(json.dumps({"short": doc["short_domain"]["verdict"], "long": doc["long_domain"]["verdict"],
                          "written": str(Path(a.out_dir) / "results.json")}))
        return 0
    if a.cmd == "lean-check":
        from .lean_check import run
        rec = run()
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(rec, indent=1))
        print(json.dumps({"ok": rec["ok"], "build_exit": rec["build"]["exit"], "mutants": [(m["file"].split("/")[-1], m["exit"]) for m in rec["mutants"]]}))
        return 0 if rec["ok"] else 1
    if a.cmd == "pin":
        print(json.dumps(make_pins(SourceStore.bundled()), indent=1, sort_keys=True))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
