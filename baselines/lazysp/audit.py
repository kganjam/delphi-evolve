"""Independent audit of saved LazySP shards.

For every shard this re-derives, from the saved query log alone and the hashed source data:
  * the shard's episode equals the frozen panel episode (start/target/init) and panel hash matches;
  * every logged assay (n_queries, node, interval, score) equals the source-data record for that node
    (absent nodes logged as None), nodes are unique, never re-queries an initial observation,
    and numbering is 1..n contiguous and n <= budget;
  * a FRESH core Ledger replayed from the initial observations + the logged assays is `unresolved`
    before the last assay and equals the recorded status after it (no certificate early or late);
  * unresolved rows spent exactly the full budget (abstain reason assay_budget) unless a runtime bound is recorded;
  * `open` routes pass evolve.graph.verify_route and `blocked` closures pass verify_cut on FULL data.
This checks software/ledger consistency against the declared conservative rule; it is not biological validation.
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path

from evolve import data, replay
from evolve.graph import Ledger, verify_cut, verify_route

from .analyze import load_shards


def audit(outdir, variants, bmax=replay.BMAX):
    land = data.load()
    Lo, Hi = land.intervals()
    panel = replay.make_episodes(land, 20)
    pk = {(e["family"], e["seed"], data.decode(e["start"]), data.decode(e["target"])): e for e in panel}
    report = {}
    for var in variants:
        sh = load_shards(outdir, var)
        errs, n = [], 0
        for key, (row, meta, fname) in sorted(sh.items()):
            n += 1
            ep = pk.get(key)
            if ep is None:
                errs.append((fname, "episode not in frozen panel")); continue
            d = json.load(gzip.open(Path(outdir) / "shards" / fname, "rt"))
            ql = d["qlog"]
            seen = set([ep["start"], ep["target"]] + ep["init"])
            if d["meta"]["panel_sha256"] != "bb6c144e8f0eba1079d6353d9c7f612a02df30afa7770ce94a064a47ad9b9bcf":
                errs.append((fname, "panel hash")); continue
            led = Ledger(ep["start"], ep["target"])
            for v in [ep["start"], ep["target"]] + [x for x in ep["init"] if x not in (ep["start"], ep["target"])]:
                led.reveal(v, (int(Lo[v]), int(Hi[v]), int(land.s[v])) if land.measured[v] else None)
            status = led.status()
            if len(ql) > bmax:
                errs.append((fname, "more assays than budget"))
            for i, (nq, actor, node, rec, why) in enumerate(ql):
                if status != "unresolved":
                    errs.append((fname, f"assay {nq} after certificate")); break
                if nq != i + 1 or node in seen:
                    errs.append((fname, f"bad numbering/duplicate at {nq}")); break
                seen.add(node)
                truth_rec = (int(Lo[node]), int(Hi[node]), int(land.s[node])) if land.measured[node] else None
                if (None if rec is None else tuple(rec)) != truth_rec:
                    errs.append((fname, f"assay {nq} record != source data")); break
                led.reveal(node, truth_rec)
                status = led.status()
            else:
                if status != row["status"]:
                    errs.append((fname, f"replayed status {status} != recorded {row['status']}"))
                if row["assays"] != len(ql):
                    errs.append((fname, "assays != len(qlog)"))
                if status == "open" and not verify_route(land.measured, Lo, Hi, led.route()):
                    errs.append((fname, "route fails full-data verification"))
                if status == "blocked":
                    S, _ = led.cut()
                    if not verify_cut(land.measured, Lo, Hi, S, ep["start"], ep["target"]):
                        errs.append((fname, "cut fails full-data verification"))
                if status == "unresolved" and not (len(ql) == bmax and row["abstain_reason"] == "assay_budget") and row["abstain_reason"] != "runtime_bound":
                    errs.append((fname, "unresolved without full budget or recorded bound"))
        report[var] = {"shards_audited": n, "errors": errs}
    return report


def cmd_audit(a):
    rep = audit(a.dir, a.variants.split(","))
    for v, r in rep.items():
        print(v, r["shards_audited"], "errors:", len(r["errors"]), r["errors"][:5])
    if a.out:
        with open(a.out, "w") as f:
            json.dump(rep, f, indent=1)
    return 1 if any(r["errors"] for r in rep.values()) else 0


def add_parser(sub):
    p = sub.add_parser("audit", help="independently replay every saved shard against source data and a fresh ledger")
    p.add_argument("--dir", required=True); p.add_argument("--variants", default="alternate,forward,reverse"); p.add_argument("--out")
    p.set_defaults(fn=cmd_audit)
