"""python -m frontier_attention {selftest|cards|score-events|evaluate}"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from . import card as cardmod
from . import evaluate as evalmod
from . import forecasting, seeds, voi


def _jsonl(p):
    return [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]


def selftest() -> int:
    """Hand-worked: reuse(H: +10, notH: -20) vs skip(0), p(H)=0.6 -> EU(reuse)=-2, EU(skip)=0, EVPI=6.
    A test with sens .8 / spec .9: P(+)=.52; EVSI=4.0 (<= EVPI)."""
    prior = {"H": 0.6, "notH": 0.4}
    u = {"reuse": {"H": 10, "notH": -20}, "skip": {"H": 0, "notH": 0}}
    L = {"pos": {"H": 0.8, "notH": 0.1}, "neg": {"H": 0.2, "notH": 0.9}}
    got = {"evpi": voi.evpi(prior, u), "evsi": voi.evsi(prior, u, L), "best_action": voi.best_action(prior, u)[0]}
    want = {"evpi": 6.0, "evsi": 4.0, "best_action": "skip"}
    ok = all(abs(got[k] - want[k]) < 1e-9 for k in ("evpi", "evsi")) and got["best_action"] == "skip"
    print(json.dumps({"got": got, "want": want, "ok": ok}))
    return 0 if ok else 1


def cards(args) -> int:
    d = seeds.load_seed_map(Path(args.problems).read_text())
    now = args.now or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    states = seeds.seed_states(d["problems"])
    out = []
    for s in d["problems"]:
        prof = seeds.to_partial_profile(s)
        c = cardmod.build_card(seeds.problem_row(s), prof, decisions={}, signals=[], problem_states=states, now=now)
        out.append(c)
    summary = {
        "source_sha256": seeds.sha256(Path(args.problems).read_text()), "now": now, "n_problems": len(out),
        "bounded": sum(c["bounded"] for c in out), "ready": sum(c["ready"] for c in out),
        "with_estimated_consequence": sum(c["consequence"]["value"] is not None for c in out),
        "issue_codes": dict(Counter(i["code"] for c in out for i in c["profile_issues"])),
        "read_only": "this command reads the seed map and writes nothing unless --out is given",
        "meaning": ("a card with no decision model has NO consequence estimate; nothing is ranked by an invented number. "
                    "The issues listed are what curation must add before the card can rank or fund anything."),
    }
    if args.out:
        o = Path(args.out); o.mkdir(parents=True, exist_ok=True)
        (o / "cards.json").write_text(json.dumps({"summary": summary, "cards": out}, indent=1, sort_keys=True, default=str))
    print(json.dumps(summary, indent=1))
    for c in out:
        print(f"{c['id']}: resolved={c['resolved']} bounded={c['bounded']} ready={c['ready']} blocked_on={c['blocked_on']} "
              f"lenses={sorted(c['lenses'])} issues={len(c['profile_issues'])}")
    return 0


def score_events(args) -> int:
    rep = forecasting.score_events(json.loads(Path(args.specs).read_text()), _jsonl(args.forecasts), _jsonl(args.resolutions), args.now)
    print(json.dumps(rep, indent=1, default=str))
    return 0


def evaluate(args) -> int:
    frozen = json.loads(Path(args.frozen).read_text())
    rep = evalmod.evaluate(_jsonl(args.rows), frozen, args.arms.split(","))
    print(json.dumps(rep, indent=1, default=str))
    return 0 if rep["verdict"] != "REFUSED" else 2


def register_probe(args) -> int:
    from . import register_probe as rp
    drafts, sha = rp.load_drafts(args.drafts)
    rep = {"drafts_sha256": sha, **rp.probe(drafts, args.now)}
    if args.out:
        Path(args.out).write_text(json.dumps(rep, indent=1, sort_keys=True))
    print(json.dumps(rep, indent=1, sort_keys=True))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="frontier_attention")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    c = sub.add_parser("cards"); c.add_argument("--problems", required=True); c.add_argument("--now"); c.add_argument("--out")
    s = sub.add_parser("score-events"); s.add_argument("--specs", required=True); s.add_argument("--forecasts", required=True)
    s.add_argument("--resolutions", required=True); s.add_argument("--now", required=True)
    e = sub.add_parser("evaluate"); e.add_argument("--rows", required=True); e.add_argument("--frozen", required=True); e.add_argument("--arms", required=True)
    r = sub.add_parser("register-probe"); r.add_argument("--drafts", required=True); r.add_argument("--now", required=True); r.add_argument("--out")
    a = ap.parse_args(argv)
    return {"selftest": lambda: selftest(), "cards": lambda: cards(a), "score-events": lambda: score_events(a), "evaluate": lambda: evaluate(a), "register-probe": lambda: register_probe(a)}[a.cmd]()


if __name__ == "__main__":
    sys.exit(main())
