"""Assay oracle and immutable event log for the retrospective replay.

The oracle exposes ONLY observed labels (interval + score) for genotypes a policy
explicitly queries; it never returns rankings, maxima, neighbours' labels or
anything unqueried.  Each query costs one assay, including queries that reveal a
genotype is outside the measured scope.
"""
from __future__ import annotations

import hashlib
import json

import numpy as np


class EventLog:
    """Append-only, hash-chained event list (tamper-evident, not signed)."""

    def __init__(self):
        self.events: list[dict] = []
        self._h = "0" * 64

    def emit(self, type_: str, actor: str, **payload):
        ev = {"seq": len(self.events), "type": type_, "actor": actor, **payload}
        ev["prev"] = self._h
        self._h = hashlib.sha256(json.dumps(ev, sort_keys=True, default=int).encode()).hexdigest()
        ev["hash"] = self._h
        self.events.append(ev)
        return ev

    def verify(self) -> bool:
        h = "0" * 64
        for ev in self.events:
            body = {k: v for k, v in ev.items() if k != "hash"}
            if body["prev"] != h:
                return False
            h = hashlib.sha256(json.dumps(body, sort_keys=True, default=int).encode()).hexdigest()
            if h != ev["hash"]:
                return False
        return True


class Oracle:
    def __init__(self, land, kappa, log: EventLog | None = None):
        self._meas = land.measured
        self._Lo, self._Hi = land.intervals(kappa)
        self._s = land.s
        self.queried: set[int] = set()
        self.log = log or EventLog()
        self.n_queries = 0

    def reveal_free(self, idx, actor="data", why="initial"):
        """Initial admissible observations (shared identically across policies)."""
        rec = self._rec(int(idx))
        self.log.emit("reveal", actor, node=int(idx), rec=rec, cost=0, why=why)
        self.queried.add(int(idx))
        return rec

    def query(self, idx, actor, why=""):
        idx = int(idx)
        if idx in self.queried:
            raise ValueError("duplicate query " + str(idx))
        self.queried.add(idx)
        self.n_queries += 1
        rec = self._rec(idx)
        self.log.emit("reveal", actor, node=idx, rec=rec, cost=1, why=why, n_queries=self.n_queries)
        return rec

    def _rec(self, idx):
        if not self._meas[idx]:
            return None
        return (int(self._Lo[idx]), int(self._Hi[idx]), int(self._s[idx]))
