"""Canonical hashing, Delphi record parsing, and the version-pinned claim store."""
from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

CLAIM_PREFIX = "https://w3id.org/delphi/resource/claim/"


def canon(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha(obj) -> str:
    return hashlib.sha256(canon(obj)).hexdigest()


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha_file(path) -> str:
    return sha_bytes(Path(path).read_bytes())


def claim_iri(claim_id: str) -> str:
    return claim_id if claim_id.startswith("http") else CLAIM_PREFIX + claim_id


# The exact fields an adapter was reviewed against. A change in ANY of them changes
# the content hash and un-verifies the adapter.
PINNED_FIELDS = ("rdfs:label", "dct:description", "dct:source", "delphi:context", "skos:notation",
                 "delphi:hypothesisType")


@dataclass
class SourceRecord:
    iri: str
    source: str                      # 'network' or 'local' (Delphi MCP `source` argument)
    nanopubs: list
    fields: dict
    response_sha256: str             # sha256 of the raw MCP JSON-RPC response bytes
    raw_path: str = ""

    def content(self) -> dict:
        f = self.fields
        return {"iri": self.iri, **{k: f.get(k) for k in PINNED_FIELDS}}

    def content_sha256(self) -> str:
        return sha(self.content())


def parse_mcp_response(raw: bytes, raw_path: str = "") -> SourceRecord:
    outer = json.loads(raw)
    inner = json.loads(outer["result"]["content"][0]["text"])
    return SourceRecord(iri=inner["claim"], source=inner["source"], nanopubs=list(inner.get("nanopubs", [])),
                        fields=inner["fields"], response_sha256=sha_bytes(raw), raw_path=raw_path)


@dataclass
class StoreEntry:
    record: SourceRecord | None
    status: str = "active"           # active | withdrawn | unavailable


@dataclass
class ClaimStore:
    """The set of Delphi claim records the service currently believes in.

    Deleting or withdrawing a record, or changing any pinned field, changes what the
    service will do; that is the causal link tested in tests/test_claim_runtime_service.py.
    """
    entries: dict = field(default_factory=dict)

    @classmethod
    def from_files(cls, paths) -> "ClaimStore":
        s = cls()
        for p in paths:
            rec = parse_mcp_response(Path(p).read_bytes(), str(p))
            s.entries[rec.iri] = StoreEntry(rec)
        return s

    def get(self, iri: str) -> StoreEntry | None:
        return self.entries.get(iri)

    def withdraw(self, iri: str):
        self.entries[iri].status = "withdrawn"

    def delete(self, iri: str):
        self.entries.pop(iri, None)

    def mark_unavailable(self, iri: str):
        self.entries[iri].status = "unavailable"

    def with_field(self, iri: str, key: str, value) -> "ClaimStore":
        """Copy of the store with one pinned field edited (to test changed-claim handling)."""
        c = copy.deepcopy(self)
        c.entries[iri].record.fields[key] = value
        return c
