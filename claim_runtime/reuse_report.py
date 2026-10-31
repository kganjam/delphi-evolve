"""Run the pre-declared reuse protocol and write artifacts/claim_reuse/reuse_benchmark.json."""
from __future__ import annotations

import csv
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

from . import reuse_benchmark as R
from .common import sha_file

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "artifacts" / "claim_reuse"


def by_policy(per_campaign: list) -> dict:
    out = defaultdict(lambda: defaultdict(int))
    for row in per_campaign:
        pol = row["campaign"].rsplit("/", 1)[1]
        for k, v in row.items():
            if k != "campaign":
                out[pol][k] += v
    return {p: dict(v) for p, v in sorted(out.items())}


def certificate_lookup(episodes_csv: Path) -> dict:
    m = {}
    with open(episodes_csv) as f:
        for r in csv.DictReader(f):
            m["%s/%s:%s>%s/%s" % (r["seed"], r["family"], r["start"], r["target"], r["policy"])] = r["certificate"]
    return m


def curve(per_campaign: list, every: int = 50) -> list:
    cum_req = cum_hit = 0
    out = []
    for i, r in enumerate(per_campaign, 1):
        cum_req += r.get("requests", 0)
        cum_hit += r.get("claim_hits", 0)
        if i % every == 0 or i == len(per_campaign):
            out.append({"campaigns": i, "cumulative_requests": cum_req, "cumulative_claim_hits": cum_hit})
    return out


def main(shards: Path, episodes_csv: Path, tar_path: Path | None, out: Path):
    from . import trpb_data
    t0 = time.time()
    proto_path = ART / "protocol.json"
    proto = json.loads(proto_path.read_text())
    land, dsha = trpb_data.load_landscape()
    traces = R.load_traces(shards)
    assert len(traces) == proto["trace_source"]["expected_episodes"], len(traces)
    total_req = sum(len(v) for v in traces.values())
    assert total_req == proto["trace_source"]["expected_paid_requests"], total_req
    src = R.verify_against_source(traces, land)
    assert src["mismatches"] == 0, src
    order = R.campaign_order(traces, proto)
    assert len(order) == 700 and len(set(order)) == 700
    ff = R.FactFactory(land, dsha)
    certs = certificate_lookup(episodes_csv)

    res = {"kind": "claim-reuse-benchmark/v1", "protocol_sha256": sha_file(proto_path),
           "inputs": {"shard_tar_sha256": sha_file(tar_path) if tar_path else None, "shard_files": len(list(shards.glob('*.json'))),
                      "dataset_summary_AA_sha256": dsha, "episodes_csv_sha256": sha_file(episodes_csv),
                      "episodes": len(traces), "paid_requests": total_req},
           "source_verification": src,
           "scope_notes": "recorded requests only; no policy was rerun; no wet-lab cost; the 'assay' is a lookup in already-measured data",
           "baseline": {}, "fault_injection": {}, "negative_controls": {}}
    csv_rows = None
    for scope in ("pooled", "per_policy"):
        r = R.run(traces, order, ff, scope)
        t = r["totals"]
        assert t["cache_hits"] == t["claim_hits"], "identical contexts: cache and claim reuse must avoid the same requests"
        res["baseline"][scope] = {
            "fresh_assays": t["requests"], "cache_avoided": t["cache_hits"], "claim_avoided": t["claim_hits"],
            "avoided_fraction": t["claim_hits"] / t["requests"], "unique_genotypes_assayed_with_reuse": t["requests"] - t["claim_hits"],
            "cache_equals_claim": t["cache_hits"] == t["claim_hits"], "claim_gain_over_cache": t["claim_hits"] - t["cache_hits"],
            "by_policy": by_policy(r["per_campaign"]), "curve": curve(r["per_campaign"])}
        if scope == "pooled":
            csv_rows = r["per_campaign"]
    rates = proto["fault_injection"]["rate_per_mille"]
    for scope in ("pooled", "per_policy"):
        r = R.run(traces, order, ff, scope, fault_per_mille=rates)
        t = r["totals"]
        base = res["baseline"][scope]
        touched = r["campaigns_touching_invalid_fact_cache"]
        decided = [k for k in touched if certs.get(k, "none") in ("open", "blocked")]
        res["fault_injection"][scope] = {
            "label": "SYNTHETIC SOFTWARE VALIDATION FIXTURES, not biological measurements", "rate_per_mille": rates,
            "cache": {"avoided": t["cache_hits"], "invalid_reuse_events": t.get("cache_invalid_reused", 0),
                      "distinct_invalid_facts_reused": r["distinct_invalid_facts_reused_cache"],
                      "campaigns_touching_invalid_fact": len(touched),
                      "of_which_with_recorded_open_or_blocked_certificate": len(decided),
                      "events_by_attack": {k[6:]: v for k, v in r["invalid_reuse_events_by_attack"].items() if k.startswith("cache:")}},
            "typed_claim_reuse": {"avoided": t["claim_hits"], "invalid_reuse_events": t.get("claim_invalid_reused", 0),
                                  "forced_reassays": t.get("claim_reassays_forced", 0),
                                  "campaigns_touching_invalid_fact": len(r["campaigns_touching_invalid_fact_claim"])},
            "avoided_lost_by_failing_closed_vs_clean_baseline": base["claim_avoided"] - t["claim_hits"]}
    for a, g in R.CATCHING_GUARD.items():
        r = R.run(traces, order, ff, "pooled", fault_per_mille={a: rates[a]}, disabled_guards=frozenset([g]))
        res["negative_controls"][a] = {"disabled_guard": g, "claim_invalid_reuse_events": r["totals"].get("claim_invalid_reused", 0),
                                       "expect": "> 0 (guard removal must let the matching attack through)",
                                       "passed": r["totals"].get("claim_invalid_reused", 0) > 0}
        r2 = R.run(traces, order, ff, "pooled", fault_per_mille={a: rates[a]})
        res["negative_controls"][a]["with_guard_enabled_invalid_reuse_events"] = r2["totals"].get("claim_invalid_reused", 0)
        res["negative_controls"][a]["passed"] = res["negative_controls"][a]["passed"] and r2["totals"].get("claim_invalid_reused", 0) == 0
    res["negative_controls_all_passed"] = all(v["passed"] for v in res["negative_controls"].values())
    res["wall_seconds"] = round(time.time() - t0, 1)
    out.write_text(json.dumps(res, indent=1, sort_keys=True))
    with open(out.with_name("reuse_per_campaign_pooled.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["campaign", "requests", "avoided_by_cache_and_claim_reuse"])
        for r in csv_rows:
            w.writerow([r["campaign"], r["requests"], r.get("claim_hits", 0)])
    return res


if __name__ == "__main__":
    a = sys.argv[1:]
    main(Path(a[0]), Path(a[1]), Path(a[2]) if a[2] != "-" else None, Path(a[3]))
