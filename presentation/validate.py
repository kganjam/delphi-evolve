"""Validation of FINAL integrated artifacts for the deck.  Pure functions; no rendering.

The deck must never print a replay number unless this module returns no errors.  Draft mode
(build_deck.py --allow-draft) renders without replay numbers and stamps every slide DRAFT.
"""
from __future__ import annotations

import csv
import glob
import gzip
import json
from pathlib import Path

ORIGINAL_POLICIES = ["random", "greedy", "uncertainty", "directed", "q2c", "collective_shared", "collective_isolated"]
MAIN_POLICIES = ORIGINAL_POLICIES                # the pre-declared 7-arm panel
# Arms added AFTER the original run was observed (not pre-registered winners); reported separately.
POSTHOC_POLICIES = ["q2c_nomodel", "collective_shared_c", "collective_isolated_c", "collective_shared_rr"]
FOLLOWUP_POLICIES = POSTHOC_POLICIES
EPISODES_PER_SEED = 5                          # 1 family-A pair + 4 family-B targets
REQUIRED_REPLAY = ["summary.json", "table_primary.csv", "table_paired.csv", "episodes.csv"]


def _load(p):
    return json.loads(Path(p).read_text())


def read_csv(p):
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def _pair_key(r):
    return (int(r["seed"]), f"{r['family']}:{r['start']}>{r['target']}")


def _query_counts(path):
    c: dict = {}
    with gzip.open(path, "rt") as f:
        hdr = f.readline().rstrip("\n").split("\t")
        si, pi = hdr.index("seed"), hdr.index("pair")
        for line in f:
            p = line.rstrip("\n").split("\t")
            k = (int(p[si]), p[pi])
            c[k] = c.get(k, 0) + 1
    return c


def validate_replay(root: Path, shards_dir: Path | None = None) -> tuple[list[str], dict]:
    """Return (errors, info).  errors empty  <=>  replay is complete and cardinality-consistent.

    Two independent integrity sources are used for every arm that is shown:
      * shards (``shards_dir`` or ``<root>/artifacts/core/replay/shards``), if present, must all be non-empty and their
        rows must equal ``episodes.csv`` rows -- an empty shard is always an error;
      * the committed immutable query traces ``queries/queries__<policy>.tsv.gz`` must contain, for every episode of
        the arm, exactly ``assays`` paid-query rows.  This works when shards are git-ignored and absent.
    At least one of the two must be available and valid; an arm with neither is not shown.
    """
    errs: list[str] = []
    info: dict = {}
    root = Path(root)
    rd = root / "artifacts/core/replay"
    pj = root / "artifacts/core/protocol.json"
    if not pj.exists():
        return [f"missing {pj}"], info
    proto = _load(pj)
    seeds = int(proto["seeds"])
    info["protocol_seeds"] = seeds
    pols = list(proto["policies"])
    if [p for p in MAIN_POLICIES if p not in pols]:
        errs.append(f"protocol lacks main policies: {[p for p in MAIN_POLICIES if p not in pols]}")
    if not rd.is_dir():
        return errs + [f"missing replay dir {rd}"], info
    for f in REQUIRED_REPLAY:
        if not (rd / f).exists():
            errs.append(f"missing {rd / f}")
    if errs:
        return errs, info
    summ = _load(rd / "summary.json")
    if int(summ.get("seeds", -1)) != seeds:
        errs.append(f"summary.json seeds={summ.get('seeds')} != protocol seeds={seeds}")
    # --- shards: none may be empty, if they are available
    sd_path = Path(shards_dir) if shards_dir else rd / "shards"
    shards = sorted(glob.glob(str(sd_path / "*.json")))
    empty, shard_rows = [], 0
    shard_pol_rows: dict[str, int] = {}
    for s in shards:
        j = _load(s)
        n = len(j.get("rows", []))
        shard_rows += n
        if n == 0:
            empty.append(Path(s).name)
        pol = Path(s).stem.split("__")[0]
        shard_pol_rows[pol] = shard_pol_rows.get(pol, 0) + n
    info["shards_dir"] = str(sd_path) if shards else None
    info["shards"] = len(shards)
    info["empty_shards"] = len(empty)
    if empty:
        errs.append(f"{len(empty)} of {len(shards)} replay shards have zero rows (e.g. {empty[:3]})")
    # --- episodes.csv cardinality
    ep = read_csv(rd / "episodes.csv")
    info["episodes_csv_rows"] = len(ep)
    by_pol: dict[str, dict[int, int]] = {}
    for r in ep:
        by_pol.setdefault(r["policy"], {}).setdefault(int(r["seed"]), 0)
        by_pol[r["policy"]][int(r["seed"])] += 1
    info["policies_present"] = sorted(by_pol)
    full = seeds * EPISODES_PER_SEED
    complete: dict[str, bool] = {}
    for p in by_pol:
        sd = by_pol[p]
        ok = sorted(sd) == list(range(seeds)) and all(v == EPISODES_PER_SEED for v in sd.values()) and sum(sd.values()) == full
        complete[p] = ok
        if p in MAIN_POLICIES and not ok:
            errs.append(f"{p}: seeds {sorted(sd)[:25]}, {sum(sd.values())} episodes != {seeds} seeds x {EPISODES_PER_SEED} = {full}")
        elif p in POSTHOC_POLICIES and not ok:
            info.setdefault("warnings", []).append(f"post-hoc arm {p} incomplete: {sum(sd.values())} != {full} (not shown)")
        elif p not in MAIN_POLICIES and p not in POSTHOC_POLICIES:
            errs.append(f"unexpected policy {p} in episodes.csv")
    for p in MAIN_POLICIES:
        if p not in by_pol:
            errs.append(f"episodes.csv has no rows for main policy {p}")
    if shards:
        if shard_rows != len(ep):
            errs.append(f"shard rows {shard_rows} != episodes.csv rows {len(ep)}")
        for p in by_pol:
            if shard_pol_rows.get(p, 0) != sum(by_pol[p].values()):
                errs.append(f"{p}: shard rows {shard_pol_rows.get(p, 0)} != episodes.csv rows {sum(by_pol[p].values())}")
    if int(summ.get("episodes", -1)) != len(ep):
        errs.append(f"summary.json episodes={summ.get('episodes')} != episodes.csv rows {len(ep)}")
    # --- committed query traces: per-episode paid-query count must equal episodes.csv `assays`
    qdir = rd / "queries"
    qchecked, qbad = [], []
    for p in sorted(by_pol):
        qf = qdir / f"queries__{p}.tsv.gz"
        if not qf.exists():
            continue
        qc = _query_counts(qf)
        eps = {_pair_key(r): int(float(r["assays"])) for r in ep if r["policy"] == p}
        mism = [k for k in eps if qc.get(k) != eps[k]]
        extra = [k for k in qc if k not in eps]
        if mism or extra:
            qbad.append(p)
            errs.append(f"{p}: query trace disagrees with episodes.csv for {len(mism)} episodes (+{len(extra)} unknown); e.g. {mism[:2]}")
        else:
            qchecked.append(p)
    info["query_trace_verified_policies"] = qchecked
    for p in by_pol:
        if complete.get(p) and not shards and p not in qchecked and p not in qbad:
            if p in MAIN_POLICIES:
                errs.append(f"{p}: neither shards nor committed query trace available to verify the arm")
            else:
                complete[p] = False
                info.setdefault("warnings", []).append(f"post-hoc arm {p} unverifiable (no shards/query trace): not shown")
    if not shards and not qchecked:
        errs.append("no shards and no committed query traces: replay cannot be verified")
    # --- primary table must be built from the same episode counts
    tp = read_csv(rd / "table_primary.csv")
    for r in tp:
        if r["family"] == "all" and (r["policy"] in MAIN_POLICIES or r["policy"] in POSTHOC_POLICIES):
            if int(r["episodes"]) != full and complete.get(r["policy"], False):
                errs.append(f"table_primary {r['policy']}@{r['budget']} episodes={r['episodes']} != {full}")
                break
    have = {(r["family"], r["policy"], int(r["budget"])) for r in tp}
    for p in MAIN_POLICIES:
        for b in (100, 250, 500, 1000):
            if ("all", p, b) not in have:
                errs.append(f"table_primary lacks all/{p}/{b}")
    for r in tp:
        if r["family"] == "all" and int(r["certified"]) + int(r["abstain_censored"]) != int(r["episodes"]):
            errs.append(f"table_primary {r['policy']}@{r['budget']}: certified+abstain != episodes")
            break
    info["followup_policies_complete"] = [p for p in POSTHOC_POLICIES if complete.get(p) and ("all", p, 1000) in have]
    info["panel_complete_11"] = len(info["followup_policies_complete"]) == len(POSTHOC_POLICIES) and not errs
    return errs, info


LAZY_VARIANTS = ["alternate", "forward", "reverse"]
LAZY_FILES = ["summary.json", "table_primary.csv", "episodes.csv", "exploratory_post_hoc.json", "audit.json"]
LAZY_TAU = 1000
LAZY_BUDGETS = (100, 250, 500, 750, 1000)


def lazysp_stats(rows: list[dict]) -> dict:
    """Resolved@B and restricted-mean assays (tau=1000, unresolved counted as tau) from raw episode rows."""
    n = len(rows)
    res = [r for r in rows if r["certificate"] in ("open", "blocked")]
    out = {"n": n, "resolved": len(res), "open": sum(r["certificate"] == "open" for r in rows), "blocked": sum(r["certificate"] == "blocked" for r in rows),
           "resolved_at": {b: sum(1 for r in res if float(r["assays"]) <= b) / n for b in LAZY_BUDGETS}}
    out["rmst"] = sum(min(float(r["assays"]), LAZY_TAU) if r["certificate"] in ("open", "blocked") else LAZY_TAU for r in rows) / n
    return out


def validate_lazysp(root: Path, core_episodes: list[dict] | None = None, seeds: int = 20) -> tuple[list[str], dict]:
    """The strong LazySP-style follow-up lives in artifacts/lazysp/results/ (NOT .../panel/).

    Complete = 3 variants x seeds x 5 episodes, every shard audited with zero errors, every number in summary.json and
    table_primary.csv re-derived from episodes.csv, and (when the core q2c rows are supplied) the paired
    only-LazySP / only-q2c / both / neither counts in summary.json re-derived from the episodes themselves.
    """
    errs: list[str] = []
    info: dict = {}
    d = Path(root) / "artifacts/lazysp/results"
    for f in LAZY_FILES:
        if not (d / f).exists():
            errs.append(f"missing {d / f}")
    if errs:
        return errs, info
    summ, audit, post = _load(d / "summary.json"), _load(d / "audit.json"), _load(d / "exploratory_post_hoc.json")
    ep = read_csv(d / "episodes.csv")
    tp = read_csv(d / "table_primary.csv")
    full = seeds * EPISODES_PER_SEED
    stats: dict = {}
    by_v: dict = {}
    for v in LAZY_VARIANTS:
        pol = f"lazysp_{v}"
        rows = [r for r in ep if r["policy"] == pol]
        by_v[v] = rows
        keys = {(int(r["seed"]), r["family"], r["start"], r["target"]) for r in rows}
        per_seed: dict = {}
        for r in rows:
            per_seed[int(r["seed"])] = per_seed.get(int(r["seed"]), 0) + 1
        if len(rows) != full or len(keys) != full or sorted(per_seed) != list(range(seeds)) or any(c != EPISODES_PER_SEED for c in per_seed.values()):
            errs.append(f"{pol}: {len(rows)} rows / {len(keys)} distinct episodes over seeds {sorted(per_seed)[:3]}.. != {seeds} seeds x {EPISODES_PER_SEED} = {full}")
            continue
        sv = summ.get("variants", {}).get(v, {})
        if not (sv.get("complete_panel") is True and sv.get("status") == "COMPLETE_100" and sv.get("episodes_present") == full):
            errs.append(f"{pol}: summary.json does not report a COMPLETE_100 panel")
        a = audit.get(v, {})
        if a.get("shards_audited") != full or a.get("errors"):
            errs.append(f"{pol}: audit.json shards_audited={a.get('shards_audited')} errors={len(a.get('errors') or [])} (need {full} shards, 0 errors)")
        if any(r["verified_by_full_data"] not in ("True", "true") and r["certificate"] in ("open", "blocked") for r in rows) or any(r["correct"] in ("False", "false") for r in rows):
            errs.append(f"{pol}: an issued certificate is not full-data verified / correct")
        st = lazysp_stats(rows)
        stats[v] = st
        for b in LAZY_BUDGETS:
            if abs(st["resolved_at"][b] - float(sv.get("resolved_at", {}).get(str(b), -9))) > 1e-9:
                errs.append(f"{pol}@{b}: episodes.csv gives {st['resolved_at'][b]} but summary.json says {sv.get('resolved_at', {}).get(str(b))}")
        if abs(st["rmst"] - float(sv.get("rmst_assays", -9))) > 0.01:
            errs.append(f"{pol}: RMST from episodes {st['rmst']:.2f} != summary.json {sv.get('rmst_assays')}")
        if {k: c for k, c in sv.get("status_counts", {}).items() if c} != {k: c for k, c in (("open", st["open"]), ("blocked", st["blocked"]), ("unresolved", full - st["resolved"])) if c}:
            errs.append(f"{pol}: status_counts in summary.json disagree with episodes.csv")
        tr = next((r for r in tp if r["variant"] == v), None)
        if tr is None or int(tr["episodes"]) != full or abs(float(tr["resolved@1000"]) - st["resolved_at"][1000]) > 0.005 or abs(float(tr["rmst_assays"]) - st["rmst"]) > 0.06:
            errs.append(f"{pol}: table_primary.csv row disagrees with episodes.csv")
        elif int(tr["false_certificates"]) or int(tr["full_data_verification_failures"]):
            errs.append(f"{pol}: nonzero false certificates / verification failures recorded")
    if core_episodes is not None and not errs:
        q = {(int(r["seed"]), r["family"], r["start"], r["target"]): r for r in core_episodes if r["policy"] == "q2c"}
        lz = {(int(r["seed"]), r["family"], r["start"], r["target"]): r for r in by_v["alternate"]}
        if set(q) != set(lz):
            errs.append("core q2c episodes and lazysp_alternate episodes are not the same panel")
        else:
            ok = lambda r: r["certificate"] in ("open", "blocked") and float(r["assays"]) <= LAZY_TAU
            only_lz = [k for k in lz if ok(lz[k]) and not ok(q[k])]
            only_q = [k for k in lz if ok(q[k]) and not ok(lz[k])]
            both = [k for k in lz if ok(q[k]) and ok(lz[k])]
            pr = summ["variants"]["alternate"]["paired"]["q2c"]
            if (len(only_lz), len(only_q), len(both)) != (pr["resolved_only_by_lazysp"], pr["resolved_only_by_comparator"], pr["both_resolved"]):
                errs.append(f"paired counts from episodes {(len(only_lz), len(only_q), len(both))} != summary.json {(pr['resolved_only_by_lazysp'], pr['resolved_only_by_comparator'], pr['both_resolved'])}")
            by_pair: dict = {}
            for k in only_lz:
                lab = f"{k[2]}→{k[3]}" if k[1] == "B" else "family A"
                by_pair[lab] = by_pair.get(lab, 0) + 1
            info["only_lazysp_by_pair"] = by_pair
            info["only_lazysp"], info["only_q2c"], info["both"] = len(only_lz), len(only_q), len(both)
            if abs(stats["alternate"]["rmst"] - float(pr["rmst_lazysp"])) > 0.01 or abs(float(pr["rmst_comparator"]) - sum(min(float(q[k]["assays"]), LAZY_TAU) if ok(q[k]) else LAZY_TAU for k in q) / len(q)) > 0.5:
                errs.append("RMST in summary.json paired block disagrees with episodes")
    if "POST HOC" not in str(post.get("label", "")).upper():
        errs.append("exploratory_post_hoc.json is not labelled POST HOC")
    info["stats"] = stats
    info["post_hoc_clusters"] = post.get("problem_clusters")
    return errs, info


def validate_misc(root: Path) -> list[str]:
    errs = []
    root = Path(root)
    need = ["artifacts/proof/receipt.json", "site/data/landscape.js", "artifacts/core/protocol.json"]
    for n in need:
        if not (root / n).exists():
            errs.append(f"missing {n}")
    if not (root / "artifacts/demo.json").exists() and not (root / "site/data/demo.json").exists():
        errs.append("missing artifacts/demo.json (and site/data/demo.json)")
    return errs
