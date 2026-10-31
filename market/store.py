"""Immutable forecast store, frozen claim set, and sealed resolution store.

Layout (store directory D):
  D/claims.json         frozen claim set + sha256. Claims carry NO outcome field (rejected if present).
  D/forecasts.jsonl     append-only, hash-chained. One line per forecast; never rewritten.
  D/overhead.jsonl      append-only, hash-chained token spend that is not a forecast (failed/retried calls,
                        shared-commons writes, feature-factory calls billed to an arm).
  resolutions.jsonl     append-only, hash-chained oracle outcomes. Defaults to D/resolutions.jsonl but should be
                        kept OUTSIDE agent-readable paths until reveal time (pass a different path).

Rules enforced:
  * probability in [0,1], finite, not bool. Identity fields (agent_id, guild, model_family, arm) non-empty.
  * tokens_in / tokens_out non-negative ints.
  * timestamp is assigned by the store clock (UTC, microseconds), not by the caller.
  * (claim_id, agent_id, arm, attempt) is unique: a forecast cannot be replaced or resubmitted.
  * a forecast is rejected if the claim already has a resolution in the supplied ResolutionStore.
  * scoring (report.py) additionally requires forecast.timestamp < resolution.revealed_at for every forecast.
  * every line carries prev_hash and hash, so any edit, deletion or reordering is detected by verify().

HONEST LIMIT: this is a file-based honest-process store. The hash chain gives tamper EVIDENCE, and the ordering
checks catch accidents and sloppy pipelines. It does not stop a process with write access to the files from
rebuilding the whole chain, nor an agent with read access to resolutions.jsonl from peeking. Keep resolutions out
of agents' readable paths, and publish the final chain head hash somewhere external if the record must be
credible against an adversary.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path

GENESIS = "0" * 64
FORBIDDEN_CLAIM_KEYS = {"outcome", "resolution", "label", "answer", "truth", "resolved"}


class StoreError(Exception):
    pass


class DuplicateForecast(StoreError):
    pass


class LateForecast(StoreError):
    pass


class ChainError(StoreError):
    pass


def canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _read_lines(path: Path):
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def verify_chain(path: Path):
    """Recompute every hash. Returns list of records; raises ChainError on any break."""
    prev = GENESIS
    recs = _read_lines(path)
    for i, r in enumerate(recs):
        body = {k: v for k, v in r.items() if k != "hash"}
        if r.get("prev_hash") != prev:
            raise ChainError(f"{path.name} line {i + 1}: prev_hash mismatch")
        if r.get("seq") != i + 1:
            raise ChainError(f"{path.name} line {i + 1}: seq {r.get('seq')} != {i + 1}")
        if sha256(canon(body)) != r.get("hash"):
            raise ChainError(f"{path.name} line {i + 1}: hash mismatch (record edited)")
        prev = r["hash"]
    return recs


def _append(path: Path, make_record, clock=utc_now):
    """Append under an exclusive lock. make_record(existing_records, timestamp) -> dict body (no seq/prev/hash)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a+", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            f.seek(0)
            recs = [json.loads(l) for l in f if l.strip()]
            prev = recs[-1]["hash"] if recs else GENESIS
            body = make_record(recs, clock())
            body = dict(body)
            body["seq"] = len(recs) + 1
            body["prev_hash"] = prev
            body["hash"] = sha256(canon(body))
            f.seek(0, os.SEEK_END)
            f.write(json.dumps(body, sort_keys=True, allow_nan=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
            return body
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


# ----------------------------------------------------------------------------- claims
def freeze_claims(store_dir, claims: list[dict], clock=utc_now) -> dict:
    """Freeze the claim set. Refuses to overwrite. Claims must not carry outcomes."""
    store_dir = Path(store_dir)
    path = store_dir / "claims.json"
    if path.exists():
        raise StoreError("claims already frozen; claims.json is immutable")
    if not claims:
        raise StoreError("empty claim set")
    seen = set()
    for c in claims:
        for k in ("claim_id", "text", "tier", "oracle"):
            if not isinstance(c.get(k), str) or not c[k].strip():
                raise StoreError(f"claim missing non-empty string field {k!r}: {c.get('claim_id')}")
        bad = FORBIDDEN_CLAIM_KEYS & set(c)
        if bad:
            raise StoreError(f"claim {c['claim_id']} carries outcome-like keys {sorted(bad)}")
        if c["claim_id"] in seen:
            raise StoreError(f"duplicate claim_id {c['claim_id']}")
        seen.add(c["claim_id"])
    body = {"frozen_at": clock(), "n_claims": len(claims), "claims": sorted(claims, key=lambda c: c["claim_id"])}
    body["claims_sha256"] = sha256(canon({"claims": body["claims"]}))
    store_dir.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(body, indent=1, sort_keys=True, allow_nan=False), encoding="utf-8")
    os.replace(tmp, path)
    return body


def load_claims(store_dir) -> dict:
    path = Path(store_dir) / "claims.json"
    if not path.exists():
        raise StoreError("no frozen claims.json")
    body = json.loads(path.read_text(encoding="utf-8"))
    if sha256(canon({"claims": body["claims"]})) != body["claims_sha256"]:
        raise ChainError("claims.json content does not match its recorded sha256")
    return body


# ----------------------------------------------------------------------------- resolutions
class ResolutionStore:
    def __init__(self, path):
        self.path = Path(path)

    def reveal(self, claim_ids_known: set[str], claim_id: str, outcome: int, oracle: str, evidence_ref: str, clock=utc_now):
        if claim_id not in claim_ids_known:
            raise StoreError(f"unknown claim {claim_id}")
        if isinstance(outcome, bool) or outcome not in (0, 1):
            raise StoreError("outcome must be integer 0 or 1")
        if not oracle or not evidence_ref:
            raise StoreError("a resolution needs an oracle name and an evidence_ref (file path/hash/row id)")

        def mk(recs, ts):
            if any(r["claim_id"] == claim_id for r in recs):
                raise StoreError(f"claim {claim_id} already resolved; resolutions are immutable")
            return {"claim_id": claim_id, "outcome": int(outcome), "oracle": oracle, "evidence_ref": evidence_ref, "revealed_at": ts}

        return _append(self.path, mk, clock)

    def load(self) -> dict[str, dict]:
        return {r["claim_id"]: r for r in verify_chain(self.path)}

    def has(self, claim_id: str) -> bool:
        return any(r["claim_id"] == claim_id for r in _read_lines(self.path))


# ----------------------------------------------------------------------------- forecasts
class ForecastStore:
    def __init__(self, store_dir, resolutions: ResolutionStore | None = None, clock=utc_now):
        self.dir = Path(store_dir)
        self.resolutions = resolutions
        self.clock = clock
        self.forecast_path = self.dir / "forecasts.jsonl"
        self.overhead_path = self.dir / "overhead.jsonl"

    def submit(self, *, claim_id, agent_id, guild, model_family, arm, probability, tokens_in, tokens_out, attempt=0):
        claims = load_claims(self.dir)
        if claim_id not in {c["claim_id"] for c in claims["claims"]}:
            raise StoreError(f"claim {claim_id!r} is not in the frozen claim set")
        if isinstance(probability, bool) or not isinstance(probability, (int, float)):
            raise StoreError("probability must be a number")
        probability = float(probability)
        if not math.isfinite(probability) or not 0.0 <= probability <= 1.0:
            raise StoreError(f"probability {probability} outside [0,1]")
        for name, v in (("agent_id", agent_id), ("guild", guild), ("model_family", model_family), ("arm", arm)):
            if not isinstance(v, str) or not v.strip():
                raise StoreError(f"{name} must be a non-empty string")
        for name, v in (("tokens_in", tokens_in), ("tokens_out", tokens_out), ("attempt", attempt)):
            if isinstance(v, bool) or not isinstance(v, int) or v < 0:
                raise StoreError(f"{name} must be a non-negative integer")
        if self.resolutions is not None and self.resolutions.has(claim_id):
            raise LateForecast(f"claim {claim_id} is already resolved; forecast refused")

        def mk(recs, ts):
            key = (claim_id, agent_id, arm, attempt)
            if any((r["claim_id"], r["agent_id"], r["arm"], r["attempt"]) == key for r in recs):
                raise DuplicateForecast(f"forecast already exists for {key}; forecasts are immutable")
            return {
                "claim_id": claim_id, "agent_id": agent_id, "guild": guild, "model_family": model_family,
                "arm": arm, "attempt": attempt, "probability": probability,
                "tokens_in": tokens_in, "tokens_out": tokens_out, "timestamp": ts,
                "claims_sha256": claims["claims_sha256"],
            }

        return _append(self.forecast_path, mk, self.clock)

    def add_overhead(self, *, arm, agent_id, tokens, note):
        if isinstance(tokens, bool) or not isinstance(tokens, int) or tokens < 0:
            raise StoreError("tokens must be a non-negative integer")
        if not arm or not agent_id or not note:
            raise StoreError("overhead needs arm, agent_id and a note saying what the tokens were for")
        return _append(self.overhead_path, lambda recs, ts: {"arm": arm, "agent_id": agent_id, "tokens": tokens, "note": note, "timestamp": ts}, self.clock)

    def forecasts(self):
        return verify_chain(self.forecast_path)

    def overhead(self):
        return verify_chain(self.overhead_path)

    def verify(self) -> dict:
        claims = load_claims(self.dir)
        f = self.forecasts()
        o = self.overhead()
        res = verify_chain(self.resolutions.path) if self.resolutions is not None else []
        foreign = [r["seq"] for r in f if r["claims_sha256"] != claims["claims_sha256"]]
        if foreign:
            raise ChainError(f"forecasts reference a different claim freeze: seq {foreign[:5]}")
        return {
            "claims_sha256": claims["claims_sha256"], "n_claims": claims["n_claims"],
            "n_forecasts": len(f), "forecast_chain_head": f[-1]["hash"] if f else GENESIS,
            "n_overhead": len(o), "n_resolutions": len(res),
            "resolution_chain_head": res[-1]["hash"] if res else GENESIS,
        }
