"""python -m frontier_pub <command>. Every command is local or read-only. There is no production command."""
import argparse
import json
import sys
from pathlib import Path

from .binding import build_trig, check_bundle, conform
from .collect import HttpReader, collect
from .ledger import Ledger
from .pipeline import prepare
from .records import NotPublishable
from .registry import Authorization, post_test


def main(argv=None):
    ap = argparse.ArgumentParser(prog="frontier_pub")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("collect", help="read a bundle from Frontier's loopback HTTP adapter (read endpoints only)")
    c.add_argument("--base", required=True), c.add_argument("--target", required=True, help="JSON ref"), c.add_argument("--assessment")
    c.add_argument("--out", required=True)
    b = sub.add_parser("prepare", help="check, build, conform, sign locally, verify, record in the ledger (stage null)")
    b.add_argument("bundle"), b.add_argument("--ledger", required=True), b.add_argument("--out-dir", required=True)
    b.add_argument("--key", required=True, help="PEM outside the repository"), b.add_argument("--commit", required=True)
    b.add_argument("--created", required=True), b.add_argument("--status-change", action="store_true")
    t = sub.add_parser("plan-test-publish", help="DRY RUN of the test-registry POST: prints the request, sends nothing")
    t.add_argument("signed"), t.add_argument("--uri", required=True), t.add_argument("--registry", required=True)
    a = ap.parse_args(argv)
    try:
        if a.cmd == "collect":
            res = collect(HttpReader(a.base), json.loads(a.target), json.loads(a.assessment) if a.assessment else None)
            Path(a.out).write_text(json.dumps(res, sort_keys=True, indent=1))
            print(json.dumps({"written": a.out}))
        elif a.cmd == "prepare":
            bundle = json.loads(Path(a.bundle).read_text())
            r = prepare(bundle, Ledger(Path(a.ledger)), out_dir=Path(a.out_dir), key_pem=Path(a.key), code_commit=a.commit,
                        created=a.created, status_change=a.status_change)
            print(json.dumps({k: r[k] for k in ("signed", "verified")}, indent=1))
        elif a.cmd == "plan-test-publish":
            print(json.dumps(post_test(Path(a.signed), a.uri, a.registry, None, dry_run=True), indent=1))
    except NotPublishable as e:
        print(json.dumps({"refused": str(e)}), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
