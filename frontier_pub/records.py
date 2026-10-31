"""Independent re-implementation of Frontier's record identity rules (frontier-record-0.1), so a bundle can be checked
without trusting the node that produced it. Pinned against kganjam/delphi-frontier 4e10ce0 / 42cd967 (models.py blob
841279b.../4faad6c...). A cross-check against Frontier's own code is in tests (needs FRONTIER_SRC) and fixtures were
produced by Frontier's real Store, so agreement on them is evidence the rule is copied correctly."""
from __future__ import annotations

import json
import re
from hashlib import sha256

SCHEMA = "frontier-record-0.1"
POLICY = "frontier-independent-review-0.1"
DIMENSIONS = ("source_fidelity", "target_fidelity", "applicability", "computational_replay_formal_check",
              "statistical_adequacy", "independent_replication", "empirical_relevance")
KINDS = ("Problem", "Claim", "Evidence", "Assessment", "Action", "Actor", "ResourceOffer", "Interest", "Event")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
RECORD_KEYS = {"namespace", "kind", "id", "issuer", "source_uri", "visibility", "predecessor", "payload", "schema_version", "created_at", "version"}


class NotPublishable(Exception):
    """A Frontier record set that this layer refuses to turn into a publication draft (message says why)."""


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value) -> str:
    return sha256(canonical(value).encode()).hexdigest()


def ref(rec: dict) -> dict:
    return {k: rec[k] for k in ("namespace", "kind", "id", "version")}


def verify_record(rec, kind: str | None = None) -> dict:
    """Return rec if it is a well-formed record whose version digest matches its content; else NotPublishable."""
    if not isinstance(rec, dict) or set(rec) != RECORD_KEYS:
        raise NotPublishable("not a frontier-record-0.1 envelope (unexpected or missing fields)")
    if rec["schema_version"] != SCHEMA:
        raise NotPublishable(f"unsupported record schema {rec['schema_version']!r}")
    if rec["kind"] not in KINDS or (kind and rec["kind"] != kind):
        raise NotPublishable(f"expected a {kind or 'known'} record, got {rec['kind']!r}")
    if not isinstance(rec["version"], str) or not HEX64.match(rec["version"]):
        raise NotPublishable("record version is not a sha256 digest")
    body = {k: v for k, v in rec.items() if k != "version"}
    try:
        got = digest(body)
    except (TypeError, ValueError) as e:
        raise NotPublishable(f"record is not canonical JSON: {e}")
    if got != rec["version"]:
        raise NotPublishable(f"record digest mismatch for {rec['kind']} {rec['id']}: stored {rec['version'][:12]}, recomputed {got[:12]}")
    return rec


def ref_text(r: dict) -> str:
    return f"{r['namespace']}/{r['kind']}/{r['id']}"
