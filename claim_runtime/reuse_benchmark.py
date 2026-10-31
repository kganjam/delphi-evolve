"""Cross-campaign reuse accounting on the recorded query histories (NOT a policy rerun).

Inputs: original core shards (extracted from the committed tarball), the Caltech CSVs
(for source verification of every recorded query), the pre-declared protocol
artifacts/claim_reuse/protocol.json. Nothing about any policy's behaviour is changed:
we only ask, for the campaigns in the declared order, how many recorded paid requests
were for a genotype already assayed by an earlier campaign in the same store.

Comparisons: fresh (all requests are assays), sequence cache, typed claim reuse.
Fault injection (SYNTHETIC software fixtures) corrupts a deterministic subset of stored facts.
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path

from . import evidence as E
from .common import sha

ATTACKS = ["context_drift", "coordinate_shift", "prediction_as_observation", "withdrawn"]
# which guard is the one that should catch each attack (used by the negative controls)
CATCHING_GUARD = {"context_drift": "assay_context", "coordinate_shift": "reference_coordinates",
                  "prediction_as_observation": "kind_observed", "withdrawn": "status_active"}


def attack_selected(attack: str, evidence_id: str, per_mille: int) -> bool:
    return int(hashlib.sha256((attack + "|" + evidence_id).encode()).hexdigest()[:8], 16) % 1000 < per_mille


def corrupt(claim: dict, attack: str) -> dict:
    """SYNTHETIC corrupted copy of a stored fact. Content faults keep a self-consistent id for the
    corrupted content (like a genuine fact from another context); `withdrawn` only flips status."""
    c = json.loads(json.dumps(claim))
    if attack == "context_drift":
        c["assay_context_id"] = sha({"synthetic_other_assay_context": claim["assay_context_id"]})
    elif attack == "coordinate_shift":
        c["positions"] = [p + 1 for p in c["positions"]]
        c["reference_sha256"] = sha({"synthetic_shifted_reference": claim["reference_sha256"]})
    elif attack == "prediction_as_observation":
        c["kind"] = "predicted"            # value stays observation-shaped on purpose
    elif attack == "withdrawn":
        c["status"] = "withdrawn"
    else:
        raise ValueError(attack)
    c["provenance"] = dict(c.get("provenance", {}), synthetic_fault=attack)
    if attack != "withdrawn":
        c["id"] = E.claim_id(c)
    return c


def load_traces(shard_dir: Path) -> dict:
    """{(seed, pair, policy): [(n, actor, code, rec_or_None)]} from the immutable shards."""
    traces = {}
    for p in sorted(Path(shard_dir).glob("*__seed*.json")):
        policy, seed = p.stem.split("__seed")
        d = json.loads(p.read_text())
        for pair, q in d["qlogs"].items():
            traces[(int(seed), pair, policy)] = [(r[0], r[1], r[2], r[3]) for r in q]
    return traces


def campaign_order(traces: dict, protocol: dict) -> list:
    pol_rank = {p: i for i, p in enumerate(protocol["policy_order_within_pair"])}
    b_order = ["B:VFVS>AIKG", "B:VFVS>CLKG", "B:VFVS>VLKG", "B:VFVS>ALKG"]
    keys = []
    for seed in protocol["seeds"]:
        seed_keys = [k for k in traces if k[0] == seed]
        pairs = [p for p in b_order if any(k[1] == p for k in seed_keys)]
        pairs += sorted({k[1] for k in seed_keys if k[1].startswith("A:")})
        for pair in pairs:
            for pol in sorted({k[2] for k in seed_keys if k[1] == pair}, key=lambda x: pol_rank[x]):
                keys.append((seed, pair, pol))
    return keys


def verify_against_source(traces: dict, land, kappa: float = 2.0) -> dict:
    import numpy as np
    Lo, Hi = land.intervals(kappa)
    n = bad = unmeasured = 0
    for tr in traces.values():
        for _, _, code, rec in tr:
            n += 1
            if not land.measured[code]:
                unmeasured += 1
                bad += rec is not None
            else:
                bad += rec is None or [int(Lo[code]), int(Hi[code]), int(land.s[code])] != list(rec)
    return {"queries_checked": n, "mismatches": bad, "queries_of_unmeasured_genotypes": unmeasured}


class FactFactory:
    """Builds the typed evidence claim for a genotype from the verified source landscape."""

    def __init__(self, land, dataset_sha: str):
        from evolve.data import decode
        self.land, self.decode = land, decode
        self.ctx = E.assay_context(dataset_sha)
        self.ctx_id = E.context_id(self.ctx)
        self.ref = E.reference_hash()
        self.dataset_sha = dataset_sha
        self.req = E.Requirement(dataset_sha, self.ctx_id, self.ref)

    def fact(self, code: int, campaign=None) -> dict:
        l = self.land
        g = self.decode(code)
        if l.measured[code]:
            val = {"outcome": "measured", "score_micro": int(l.s[code]), "replicate_micro": [int(l.s1[code]), int(l.s2[code])],
                   "min_input_count": int(l.count_min[code])}
        else:
            val = {"outcome": "absent_from_measured_table"}
        return E.make_claim(g, val, dataset_sha256=self.dataset_sha, ctx_id=self.ctx_id, ref_sha=self.ref,
                            provenance={"source_file": "summary_AA.csv", "first_requested_by": campaign})


def run(traces: dict, order: list, ff: FactFactory, scope: str = "pooled", fault_per_mille: dict | None = None,
        disabled_guards=frozenset()) -> dict:
    """Account one pass over the campaigns in `order`. scope: 'pooled' or 'per_policy'.

    Per request the same recorded genotype is looked up by three strategies:
      fresh   : always an assay (so avoided = 0 by definition)
      cache   : sequence-keyed cache; a hit returns whatever was stored (valid or not)
      claim   : typed store; a hit needs every guard to pass, else a forced fresh assay
    Stored copies may be SYNTHETICALLY corrupted at first storage (same deterministic
    rule for both strategies). The requester that first assays a genotype always gets the
    valid result; corruption only affects what LATER campaigns can reuse.
    """
    faults = fault_per_mille or {}

    def maybe_corrupt(fresh):
        for a in ATTACKS:
            if a in faults and attack_selected(a, fresh["id"], faults[a]):
                return corrupt(fresh, a)
        return fresh

    new = lambda: {"store": E.EvidenceStore(disabled_guards=frozenset(disabled_guards)), "cache": E.SequenceCache()}
    states = defaultdict(new)
    tot = defaultdict(int)
    per_campaign, tainted_cache, tainted_claim = [], set(), set()
    invalid_cache_ids, invalid_claim_ids = set(), set()
    by_attack = defaultdict(int)
    for key in order:
        st = states["all" if scope == "pooled" else key[2]]
        store, cache = st["store"], st["cache"]
        name = "%s/%s/%s" % key
        c = defaultdict(int)
        for _, _, code, _rec in traces[key]:
            c["requests"] += 1
            g = ff.decode(code)
            hit = cache.get(g)                                    # ---- ordinary cache
            if hit is None:
                cache.put(g, maybe_corrupt(ff.fact(code, name)))
            else:
                c["cache_hits"] += 1
                fault = hit["provenance"].get("synthetic_fault")
                if fault:
                    c["cache_invalid_reused"] += 1
                    by_attack["cache:" + fault] += 1
                    invalid_cache_ids.add(hit["id"] + "|" + fault)
                    tainted_cache.add(key)
            d = store.lookup(g, ff.req)                           # ---- typed claim reuse
            if d["decision"] == "reuse":
                c["claim_hits"] += 1
                fault = store.by_id[d["evidence_id"]]["provenance"].get("synthetic_fault")
                if fault:                                         # only reachable with a guard disabled
                    c["claim_invalid_reused"] += 1
                    by_attack["claim:" + fault] += 1
                    invalid_claim_ids.add(d["evidence_id"] + "|" + fault)
                    tainted_claim.add(key)
            elif d["rejected"]:
                c["claim_reassays_forced"] += 1
                for bad in d["rejected"]:                         # fail closed: drop unusable copies,
                    store.remove(bad["evidence_id"])
                store.add(ff.fact(code, name))                    # pay for a fresh, valid assay
            else:
                store.add(maybe_corrupt(ff.fact(code, name)))
        per_campaign.append({"campaign": name, **c})
        for k, v in c.items():
            tot[k] += v
    return {"scope": scope, "campaigns": len(order), "totals": dict(tot),
            "unique_genotypes_stored_total": sum(len(s["store"].by_subject) for s in states.values()),
            "stores": len(states), "per_campaign": per_campaign,
            "distinct_invalid_facts_reused_cache": len(invalid_cache_ids),
            "distinct_invalid_facts_reused_claim": len(invalid_claim_ids),
            "invalid_reuse_events_by_attack": dict(by_attack),
            "campaigns_touching_invalid_fact_cache": sorted("%s/%s/%s" % k for k in tainted_cache),
            "campaigns_touching_invalid_fact_claim": sorted("%s/%s/%s" % k for k in tainted_claim)}
