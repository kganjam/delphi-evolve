"""Probe: what do the attention cards and lenses do on the 250 imported open problems (drafts from import_register.py)?

Read-only. Input is the importer's JSONL (each draft embeds the full register record, so nothing else is needed); the
sha256 of that file is printed so the number is pinned to an artifact, not to a copy. Nothing is invented:
  * no utilities, no decision models, no consequence estimates;
  * the only ordering keys used are fields the records carry (curator `importance`/`tractability` labels, counts of
    attestations and distinct sources, `stance`, textual mentions of other slugs), each reported with its ties;
  * the importer's enum `sourced_field_open_problem` is mapped to this schema's `field_open_problem` and that mapping is
    labelled as inferred.
"""
from __future__ import annotations

import json
from collections import Counter
from hashlib import sha256
from itertools import combinations
from math import comb

from . import card as cardmod
from .card import LENSES

IMPORTANCE = {"foundational": 3, "significant": 2, "specialist": 1}      # declared direction: higher = more important
TRACTABILITY = {"near-term": 3, "medium-term": 2, "long-term": 1}        # declared direction: nearer = more tractable (a feasibility assumption)
KIND_MAP = {"sourced_field_open_problem": "field_open_problem"}          # INFERRED mapping, see module docstring


def load_drafts(path: str) -> tuple[list[dict], str]:
    raw = open(path, "rb").read()
    return [json.loads(l) for l in raw.decode().splitlines() if l.strip()], sha256(raw).hexdigest()


def partial_profile(draft: dict) -> dict:
    p = draft["payload"]
    return {
        "problem_ref": {"id": draft["id"], "version": "unversioned-draft"},
        "known": [{"statement": p["known_state"], "source": p["source"].get("uri") or ""}],          # evidence_kind NOT inferred
        "open": {"question": p["question"], "open_kind": KIND_MAP.get(p["problem_kind"], p["problem_kind"]), "novelty_status": "unchecked"},
        "unlocks": [{"text": u} for u in p.get("downstream_uses", [])],                                # untyped prose
        "working": [],
        "next_action": {k: v for k, v in (("text", p.get("next_action")),) if v},                      # absent for 'recorded'
    }


def _ordinal(values: list) -> dict:
    """Pair accounting for one ordinal key; None = unrated = incomparable with everything."""
    n = len(values)
    rated = [v for v in values if v is not None]
    c = Counter(rated)
    tied = sum(comb(k, 2) for k in c.values())
    ordered = comb(len(rated), 2) - tied
    return {"n": n, "rated": len(rated), "groups": dict(sorted(c.items(), key=lambda kv: -kv[0])), "pairs_total": comb(n, 2),
            "pairs_ordered": ordered, "pairs_tied": tied, "pairs_incomparable": comb(n, 2) - comb(len(rated), 2),
            "fraction_pairs_ordered": ordered / comb(n, 2) if n > 1 else None}


def pareto_layers(points: list[tuple | None]) -> dict:
    """Non-dominated sorting on (importance, tractability), higher better on both, no weights. None = unrated, excluded."""
    idx = [i for i, p in enumerate(points) if p is not None]
    dom = lambda a, b: all(x >= y for x, y in zip(a, b)) and a != b
    remaining, layers = set(idx), []
    while remaining:
        front = {i for i in remaining if not any(dom(points[j], points[i]) for j in remaining)}
        if not front:
            raise ValueError("dominance relation has a cycle; non-dominated sorting cannot terminate")
        layers.append(len(front)); remaining -= front
    comparable = sum(1 for i, j in combinations(idx, 2) if dom(points[i], points[j]) or dom(points[j], points[i]))
    return {"rated": len(idx), "layer_sizes": layers, "pairs_comparable": comparable, "pairs_rated": comb(len(idx), 2),
            "fraction_rated_pairs_comparable": comparable / comb(len(idx), 2) if len(idx) > 1 else None}


def probe(drafts: list[dict], now: str) -> dict:
    ids = [d["id"] for d in drafts]
    states = {i: "open" for i in ids}
    cards = [cardmod.build_card({"id": d["id"], "depends_on": [], "needs": []}, partial_profile(d), decisions={}, signals=[],
                                problem_states=states, now=now) for d in drafts]
    recs = [d["payload"]["original"]["register_record"] for d in drafts]
    lens_counts = {l: sum(l in c["lenses"] for c in cards) for l in LENSES}
    imp = [IMPORTANCE.get((r.get("importance") or {}).get("value")) for r in recs]
    tra = [TRACTABILITY.get((r.get("tractability") or {}).get("value")) for r in recs]
    pts = [(a, b) if a is not None and b is not None else None for a, b in zip(imp, tra)]
    att = [r.get("attestations") or [] for r in recs]
    full = lambda a: bool(a.get("pmcid")) and bool(a.get("locator")) and bool(a.get("quote"))
    pm = Counter(a["pmcid"] for r in att for a in r if a.get("pmcid"))
    slugs = set(ids)
    text = lambda r: json.dumps({k: r.get(k) for k in ("statement", "why_it_matters", "curator_note", "data_needed", "model_handles", "our_attack", "verification")}, default=str)
    edges = sorted({(r["slug"], s) for r in recs for s in slugs if s != r["slug"] and s in text(r)})
    indeg = Counter(t for _, t in edges)
    importer_path = Counter(d["payload"]["original"]["provenance_path"] for d in drafts)
    return {
        "n_problems": len(drafts),
        "cards": {"bounded": sum(c["bounded"] for c in cards), "ready": sum(c["ready"] for c in cards),
                  "with_consequence_estimate": sum(c["consequence"]["value"] is not None for c in cards),
                  "issue_codes": dict(Counter(i["code"] for c in cards for i in c["profile_issues"]))},
        "lens_membership": lens_counts,
        "lenses_nonempty": [l for l, n in lens_counts.items() if n],
        "carried_orderings": {
            "importance_label": _ordinal(imp), "tractability_label": _ordinal(tra),
            "pareto_importance_x_tractability": pareto_layers(pts),
            "note": "curator ordinal labels, one labeller, no calibration, no consequence estimate. They order labels, not consequence."},
        "provenance_as_carried_by_the_records": {
            "importer_provenance_path": dict(importer_path),
            "records_with_a_full_attestation_pmcid_locator_quote": sum(any(full(a) for a in r) for r in att),
            "of_importer_none_path_with_a_full_attestation": sum(1 for d, r in zip(drafts, att) if d["payload"]["original"]["provenance_path"] == "none" and any(full(a) for a in r)),
            "attestations_total": sum(map(len, att)), "distinct_pmcids": len(pm), "max_problems_sharing_one_pmcid": max(pm.values()),
            "records_with_exactly_one_distinct_source": sum(1 for r in att if len({a.get("pmcid") for a in r if a.get("pmcid")}) == 1),
            "records_with_a_settled_stance_attestation": sum(any(a.get("stance") == "settled" for a in r) for r in att),
            "quotes_are_curator_transcriptions_unverified_here": True},
        "candidate_dependency_edges_from_text_mentions": {
            "n_edges": len(edges), "problems_mentioned_by_others": len(indeg), "max_in_degree": max(indeg.values()) if indeg else 0,
            "meaning": "a slug appearing in another record's prose is NOT a typed dependency; these are untyped candidates a curator must confirm or reject"},
        "unrated_records": sum(1 for a in imp if a is None),
    }
