"""Source loading, identity pinning and refusal reasons for Delphi claim records.

Hash convention intentionally matches claim_runtime/common.py on origin/work/release
(canonical JSON of the pinned fields) so pins are comparable; no code is copied from Delphisci.
Nothing here extracts a theorem from the record: the adapter's mathematics is hand-written in
adapter.py and is bound to the exact record content by the content hash.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

PKG = Path(__file__).resolve().parent
BUNDLED_DIR = PKG / "sources"
CLAIM_PREFIX = "https://w3id.org/delphi/resource/claim/"
PINNED_FIELDS = ("rdfs:label", "dct:description", "dct:source", "delphi:context", "skos:notation",
                 "delphi:hypothesisType")


def canon(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha(obj) -> str:
    return hashlib.sha256(canon(obj)).hexdigest()


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha_file(p) -> str:
    return sha_bytes(Path(p).read_bytes())


def claim_iri(cid: str) -> str:
    return cid if cid.startswith("http") else CLAIM_PREFIX + cid


@dataclass
class Record:
    iri: str
    source: str
    nanopubs: list
    fields: dict
    response_sha256: str
    path: str = ""

    def content(self) -> dict:
        return {"iri": self.iri, **{k: self.fields.get(k) for k in PINNED_FIELDS}}

    def content_sha256(self) -> str:
        return sha(self.content())

    def field_sha256(self) -> dict:
        return {k: sha(self.fields.get(k)) for k in PINNED_FIELDS}


def parse_record(raw: bytes, path: str = "") -> Record:
    """Accept the raw Delphi MCP tools/call JSON-RPC response, or the already-unwrapped claim object."""
    obj = json.loads(raw)
    inner = json.loads(obj["result"]["content"][0]["text"]) if "result" in obj else obj
    if "fields" not in inner or "claim" not in inner:
        raise ValueError("not a Delphi get_claim record (needs 'claim' and 'fields')")
    return Record(iri=inner["claim"], source=inner.get("source", "unknown"), nanopubs=list(inner.get("nanopubs", [])),
                  fields=inner["fields"], response_sha256=sha_bytes(raw), path=path)


def load_pins(path=None) -> dict:
    return json.loads(Path(path or BUNDLED_DIR / "pins.json").read_text())


@dataclass
class SourceCheck:
    claim: str
    ok: bool
    reason: str                      # 'accepted' or a refusal code
    detail: str = ""
    iri: str = ""
    content_sha256: str | None = None
    pinned_content_sha256: str | None = None
    response_sha256: str | None = None
    pinned_response_sha256: str | None = None
    source: str | None = None
    nanopubs: list = field(default_factory=list)
    changed_fields: list = field(default_factory=list)
    status: str | None = None
    path: str = ""

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


class SourceStore:
    """Claim records offered to the adapter. `manifest` maps claim id -> {file, status}.
    Default: the bundled offline snapshot. A different snapshot is an explicit input."""

    def __init__(self, entries: dict, label: str):
        self.entries = entries       # claim id -> {"path": Path|None, "status": str}
        self.label = label

    @classmethod
    def bundled(cls) -> "SourceStore":
        return cls.from_dir(BUNDLED_DIR)

    @classmethod
    def from_dir(cls, d) -> "SourceStore":
        d = Path(d)
        man = json.loads((d / "manifest.json").read_text())
        ents = {cid: {"path": d / e["file"], "status": e.get("status", "active")} for cid, e in man["claims"].items()}
        return cls(ents, str(d))

    @classmethod
    def from_files(cls, mapping: dict, label="explicit files") -> "SourceStore":
        return cls({cid: {"path": Path(p), "status": "active"} for cid, p in mapping.items()}, label)

    def check(self, claim: str, pins: dict) -> SourceCheck:
        pin = pins.get(claim)
        if pin is None:
            return SourceCheck(claim, False, "no_pin", "adapter has no reviewed pin for this claim")
        base = dict(claim=claim, iri=pin["claim_iri"], pinned_content_sha256=pin["content_sha256"],
                    pinned_response_sha256=pin.get("response_sha256"))
        ent = self.entries.get(claim)
        if ent is None:
            return SourceCheck(ok=False, reason="source_missing", detail="claim not present in snapshot", **base)
        base["status"] = ent["status"]
        if ent["status"] != "active":
            return SourceCheck(ok=False, reason=f"source_{ent['status']}", detail=f"snapshot marks claim {ent['status']}", **base)
        p = ent["path"]
        base["path"] = str(p)
        if p is None or not Path(p).is_file():
            return SourceCheck(ok=False, reason="source_missing", detail="record file absent", **base)
        try:
            rec = parse_record(Path(p).read_bytes(), str(p))
        except Exception as e:  # malformed input is a refusal, not a crash
            return SourceCheck(ok=False, reason="source_malformed", detail=f"{type(e).__name__}: {e}", **base)
        base.update(content_sha256=rec.content_sha256(), response_sha256=rec.response_sha256, source=rec.source,
                    nanopubs=rec.nanopubs)
        if rec.iri != pin["claim_iri"]:
            return SourceCheck(ok=False, reason="iri_mismatch", detail=f"record is {rec.iri}", **base)
        if rec.content_sha256() != pin["content_sha256"]:
            ch = [k for k, h in rec.field_sha256().items() if h != pin["field_sha256"].get(k)]
            return SourceCheck(ok=False, reason="claim_changed", detail="pinned fields differ from reviewed record",
                               changed_fields=ch, **base)
        low = json.dumps(rec.fields.get("delphi:context", "")).lower()
        missing = [ph for ph in pin.get("required_context_phrases", []) if ph.lower() not in low]
        if missing:
            return SourceCheck(ok=False, reason="assumption_text_missing",
                               detail=f"record context lacks: {missing}", **base)
        return SourceCheck(ok=True, reason="accepted", **base)


def make_pins(store: SourceStore) -> dict:
    """Reviewer step: derive pins from the CURRENT snapshot. Run deliberately (CLI `pin`), never at check time."""
    meta = json.loads((BUNDLED_DIR / "provenance.json").read_text())
    pins = {}
    for cid, ent in store.entries.items():
        rec = parse_record(Path(ent["path"]).read_bytes(), str(ent["path"]))
        pins[cid] = {
            "claim_iri": rec.iri, "content_sha256": rec.content_sha256(), "field_sha256": rec.field_sha256(),
            "response_sha256": rec.response_sha256, "source": rec.source, "nanopubs": rec.nanopubs,
            "nanopub_note": "local UNSIGNED nanopub path as reported by the Delphi MCP; no network nanopub ID exists/claimed",
            "required_context_phrases": meta["claims"][cid]["required_context_phrases"],
            "retrieved_utc": meta["retrieved_utc"], "retrieved_seattle": meta["retrieved_seattle"],
            "reviewed_by": "hand-authored and pinned by a Claude Sonnet 5.5 worker; NOT an independent human review",
        }
    return pins
