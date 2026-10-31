"""Validation of FINAL integrated artifacts for the deck.  Pure functions; no rendering.

The deck must never print a replay number unless this module returns no errors.  Draft mode
(build_deck.py --allow-draft) renders without replay numbers and stamps every slide DRAFT.
"""
from __future__ import annotations

import csv
import glob
import json
from pathlib import Path

MAIN_POLICIES = ["random", "greedy", "uncertainty", "directed", "q2c", "collective_shared", "collective_isolated"]
FOLLOWUP_POLICIES = ["collective_shared_rr"]   # exploratory round-robin ablation; reported separately
EPISODES_PER_SEED = 5                          # 1 family-A pair + 4 family-B targets
REQUIRED_REPLAY = ["summary.json", "table_primary.csv", "table_paired.csv", "episodes.csv"]


def _load(p):
    return json.loads(Path(p).read_text())


def read_csv(p):
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def validate_replay(root: Path) -> tuple[list[str], dict]:
    """Return (errors, info).  errors empty  <=>  replay is complete and cardinality-consistent."""
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
    # --- summary self-consistency
    if int(summ.get("seeds", -1)) != seeds:
        errs.append(f"summary.json seeds={summ.get('seeds')} != protocol seeds={seeds}")
    # --- shards: none may be empty
    shards = sorted(glob.glob(str(rd / "shards/*.json")))
    empty = []
    shard_rows = 0
    per_pol_seed = {}
    for s in shards:
        j = _load(s)
        n = len(j.get("rows", []))
        shard_rows += n
        if n == 0:
            empty.append(Path(s).name)
        stem = Path(s).stem
        pol = stem.split("__")[0]
        per_pol_seed[(pol, stem.split("seed")[-1])] = n
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
    for p in MAIN_POLICIES:
        if p not in by_pol:
            errs.append(f"episodes.csv has no rows for main policy {p}")
            continue
        sd = by_pol[p]
        if sorted(sd) != list(range(seeds)):
            errs.append(f"{p}: seeds present {sorted(sd)[:25]} != 0..{seeds - 1}")
        bad = {k: v for k, v in sd.items() if v != EPISODES_PER_SEED}
        if bad:
            errs.append(f"{p}: seeds with episodes != {EPISODES_PER_SEED}: {dict(list(bad.items())[:5])}")
        if sum(sd.values()) != seeds * EPISODES_PER_SEED:
            errs.append(f"{p}: {sum(sd.values())} episodes != {seeds * EPISODES_PER_SEED}")
    for p in by_pol:
        if p in FOLLOWUP_POLICIES:
            n = sum(by_pol[p].values())
            if n != seeds * EPISODES_PER_SEED:
                info.setdefault("warnings", []).append(f"follow-up arm {p} incomplete: {n} episodes != {seeds * EPISODES_PER_SEED} (not shown)")
        elif p not in MAIN_POLICIES:
            errs.append(f"unexpected policy {p} in episodes.csv")
    if shard_rows != len(ep):
        errs.append(f"shard rows {shard_rows} != episodes.csv rows {len(ep)}")
    if int(summ.get("episodes", -1)) != len(ep):
        errs.append(f"summary.json episodes={summ.get('episodes')} != episodes.csv rows {len(ep)}")
    # --- primary table must be built from the same episode counts
    tp = read_csv(rd / "table_primary.csv")
    for r in tp:
        if r["family"] == "all" and r["policy"] in MAIN_POLICIES:
            if int(r["episodes"]) != seeds * EPISODES_PER_SEED:
                errs.append(f"table_primary {r['policy']}@{r['budget']} episodes={r['episodes']} != {seeds * EPISODES_PER_SEED}")
                break
    have = {(r["family"], r["policy"], int(r["budget"])) for r in tp}
    for p in MAIN_POLICIES:
        for b in (100, 250, 500, 1000):
            if ("all", p, b) not in have:
                errs.append(f"table_primary lacks all/{p}/{b}")
    # --- safety numbers must exist and be coherent
    for r in tp:
        if r["family"] == "all" and int(r["certified"]) + int(r["abstain_censored"]) != int(r["episodes"]):
            errs.append(f"table_primary {r['policy']}@{r['budget']}: certified+abstain != episodes")
            break
    info["followup_policies_complete"] = [p for p in FOLLOWUP_POLICIES if p in by_pol and sum(by_pol[p].values()) == seeds * EPISODES_PER_SEED]
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
