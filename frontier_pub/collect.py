"""READ-ONLY collection of the records a publication needs from a Frontier node.

`reader` is anything with get(ref) -> {"record","local_review","is_head",...} and events(after, limit) -> {"events":[{"sequence","envelope"}],
"next_cursor"}: Frontier's Store (read methods only, no token => public records only) or HttpReader against the loopback HTTP adapter.
This module never calls a Frontier write operation (propose/review/transition/lease/import).
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from .records import NotPublishable, ref


class Missing(Exception):
    pass


class HttpReader:
    """Reads Frontier's loopback HTTP adapter (POST /v1/read/*). Public records only: no token is ever sent."""

    def __init__(self, base_url: str):
        if not base_url.startswith("http://127.0.0.1:"):
            raise ValueError("Frontier's HTTP adapter is loopback-only; refusing other hosts")
        self.base = base_url.rstrip("/")

    def _post(self, path, body):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise Missing(path)
            raise

    def get(self, target):
        return self._post("/v1/read/get", {"target": target})

    def events(self, after=0, limit=50):
        return self._post("/v1/read/events", {"after": after, "limit": limit})


def _missing(e: Exception) -> bool:
    return isinstance(e, Missing) or type(e).__name__ == "Missing"


def collect(reader, target_ref: dict, assessment_ref: dict | None = None, max_pages: int = 200) -> dict:
    t = reader.get(target_ref)
    target = t["record"]
    if ref(target) != target_ref:
        raise NotPublishable("node returned a different record than the pinned reference")
    mine, after = [], 0
    for _ in range(max_pages):
        page = reader.events(after=after, limit=50)
        for row in page["events"]:
            env = row["envelope"]
            if env["payload"]["target"] == target_ref:
                mine.append(env)
        if page["next_cursor"] is None:
            break
        after = page["next_cursor"]
    else:
        raise NotPublishable("event log longer than the scan bound; raise max_pages deliberately")
    reviews = [e for e in mine if e["payload"]["event_type"] == "review_recorded"]
    origin = [e for e in mine if e["payload"]["event_type"] in ("record_proposed", "record_imported")]
    if not reviews or not origin:
        raise NotPublishable("no review_recorded / record_proposed|record_imported event found for this exact version")
    rev = next((e for e in reviews if assessment_ref and e["payload"]["details"].get("assessment") == assessment_ref), None) if assessment_ref else reviews[-1]
    if rev is None:
        raise NotPublishable("no review event names that assessment")
    a_ref = rev["payload"]["details"]["assessment"]
    a = reader.get(a_ref)["record"]
    evidence = []
    for d in a["payload"]["dimensions"].values():
        for link in d["evidence_links"]:
            if link in [ref(e) for e in evidence]:
                continue
            try:
                evidence.append(reader.get(link)["record"])
            except Exception as e:      # an unresolvable link stays a digest-pinned reference
                if not _missing(e):
                    raise
    return {"target": target, "assessment": a, "review_event": rev, "proposal_event": origin[0], "evidence": evidence,
            "target_is_head": t["is_head"], "local_review": dict(t["local_review"] or {})}
