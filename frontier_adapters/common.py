"""Hashing, time and the read-only loader for the Frontier models."""
from __future__ import annotations

import hashlib
import importlib
import json
import os
import sys
from datetime import datetime, timezone


def canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def sha_obj(obj) -> str:
    return hashlib.sha256(canon(obj).encode()).hexdigest()


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def iso_utc(ms: int | None = None) -> str:
    dt = datetime.now(timezone.utc) if ms is None else datetime.fromtimestamp(ms / 1000, timezone.utc)
    return dt.isoformat()


class FrontierUnavailable(RuntimeError):
    pass


def load_frontier():
    """Import frontier.models / frontier.store from the checkout in $FRONTIER_PATH (read-only use).

    Used ONLY to validate emitted drafts with the real pydantic models and the real licence gate.
    Raises FrontierUnavailable (never silently skips) when it is not configured, so a caller cannot
    mistake 'not validated' for 'valid'.
    """
    path = os.environ.get("FRONTIER_PATH")
    if not path or not os.path.isdir(os.path.join(path, "frontier")):
        raise FrontierUnavailable("set FRONTIER_PATH to a checkout of kganjam/delphi-frontier (read-only use)")
    if path not in sys.path:
        sys.path.insert(0, path)
    models = importlib.import_module("frontier.models")
    store = importlib.import_module("frontier.store")
    return models, store


def validate_draft(draft: dict, created_at: str | None = None) -> dict:
    """Validate with the real models; return the made record and the licence-gate result.

    Pass `created_at` to pin the record timestamp so the record (and anything derived from it) is reproducible.
    """
    models, store = load_frontier()
    d = models.Draft.model_validate(draft)
    record = models.make_record(d, created_at=created_at)
    offenders = store._unlicensed_available_content([record])
    return {"record": record, "licence_gate_offenders": offenders}
