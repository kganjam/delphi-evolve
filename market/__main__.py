"""CLI. Scope Desk evaluation is the supported path; the binary-claim forecast store (store.py/report.py) is retained,
tested, and NOT part of the Scope Desk interface (the director owns that interface; there is no market API here).

  python -m market selftest
  python -m market desk --key KEY.jsonl --answers answers.jsonl [--instances inst.jsonl] [--ledger arms/ledger.jsonl]
                        [--repairs repairs.jsonl] [--key-sha KEY.sha256] --out DIR
  python -m market lean --statements S.jsonl --results R.jsonl [--ledger L.jsonl] [--statements-sha S.sha256] --out DIR
  python -m market triage --freeze bench-v1-freeze.json [--records R.jsonl] [--freeze-sha HEX] --out DIR
  python -m market forecast-report --store DIR [--resolutions PATH] --out DIR      (legacy binary-claim store)
"""
from __future__ import annotations

import argparse
import json
import sys


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="market")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    d = sub.add_parser("desk")
    d.add_argument("--key", required=True); d.add_argument("--answers", required=True)
    d.add_argument("--instances"); d.add_argument("--ledger"); d.add_argument("--repairs"); d.add_argument("--key-sha")
    d.add_argument("--out", required=True)
    l = sub.add_parser("lean")
    l.add_argument("--statements", required=True); l.add_argument("--results", required=True); l.add_argument("--ledger")
    l.add_argument("--statements-sha"); l.add_argument("--out", required=True)
    t = sub.add_parser("triage")
    t.add_argument("--freeze", required=True); t.add_argument("--records"); t.add_argument("--freeze-sha"); t.add_argument("--out", required=True)
    f = sub.add_parser("forecast-report")
    f.add_argument("--store", required=True); f.add_argument("--resolutions"); f.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "selftest":
        from .diversity import self_test
        print(json.dumps(self_test(), indent=1))
        return 0
    if a.cmd == "desk":
        from .desk import run_desk
        rep, md = run_desk(a.key, a.answers, a.instances, a.ledger, a.repairs, a.key_sha, a.out)
        print(rep["headline"]["slide_markdown"])
        return 0
    if a.cmd == "triage":
        from .triage import run_triage
        print(run_triage(a.freeze, a.records, a.out, a.freeze_sha)["markdown"])
        return 0
    if a.cmd == "lean":
        from .lean import run_lean
        print(run_lean(a.statements, a.results, a.ledger, a.statements_sha, a.out)["slide_markdown"])
        return 0
    from .report import run_report
    rep, _, md = run_report(a.store, a.resolutions, a.out)
    print(rep.get("headline", {}).get("slide_markdown", rep.get("status")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
