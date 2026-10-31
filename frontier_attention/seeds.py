"""Read-only adapter: the Frontier seed map (frontier-problems.json) -> partial attention profiles.

The seed map predates this schema. Its `unlocks`, `next_action` and `known` are prose. The adapter does NOT
upgrade prose into structure: each prose field is carried as {"text": ...} so validation reports exactly what a
curator must add (typed unlock edges, pinned input hashes, a resource estimate, a stop rule, a reviewer, an
evidence kind) before a card can rank anything. The seed's own `kind` is kept verbatim."""
from __future__ import annotations

import json

from market.store import canon, sha256


def load_seed_map(text: str) -> dict:
    d = json.loads(text)
    if d.get("schema_version") != "frontier-problems-0.1":
        raise ValueError(f"unexpected seed schema_version {d.get('schema_version')!r}")
    return d


def seed_version(seed: dict) -> str:
    """Content hash of the seed record: the version a contribution must name."""
    return sha256(canon(seed))


def to_partial_profile(seed: dict) -> dict:
    return {
        "problem_ref": {"id": seed["id"], "version": seed_version(seed)},
        "known": [{"statement": seed["known"], "source": seed.get("source", "")}],     # evidence_kind NOT inferred
        "open": {"question": seed["question"], "open_kind": seed["kind"], "novelty_status": "not_claimed",
                 "acceptance_criterion": seed["acceptance"]},
        "unlocks": [{"text": u} for u in seed.get("unlocks", [])],                      # untyped prose
        "working": [],                                                                   # no lease records exist
        "next_action": {"text": seed.get("next_action", "")},                           # prose, not a bounded action
    }


def problem_row(seed: dict) -> dict:
    return {"id": seed["id"], "depends_on": seed.get("depends_on", []), "needs": seed.get("needs", [])}


def seed_states(seeds: list[dict]) -> dict:
    return {s["id"]: ("resolved" if s["kind"] == "resolved_project_scope_correction" or s.get("state") == "resolved" else "open") for s in seeds}
