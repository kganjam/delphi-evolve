"""Shared verified commons + coordination board. Append-only JSONL, flock-serialised, no dispatcher.

* Commons (`commons.jsonl`): kernel-verified theorems (lemmas, witnesses) with provenance. An entry is
  appended only after the Lean kernel accepts it; every agent in the arm may read and write.
* Board (`board.jsonl`): coordination records (claim / proved / failed / release). Present in BOTH
  arms so the arms differ only in whether verified lemma TEXT is shared.
Rows are never edited or deleted; the current state is a fold over the log.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import time
from contextlib import contextmanager
from pathlib import Path

from .accounting import now_stamps


class AppendOnlyLog:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)
        self.lockpath = self.path.with_suffix(self.path.suffix + ".lock")

    @contextmanager
    def locked(self):
        with open(self.lockpath, "a") as lf:
            fcntl.flock(lf, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lf, fcntl.LOCK_UN)

    def read(self) -> list[dict]:
        out = []
        with open(self.path) as f:
            for line in f:
                if line.strip():
                    out.append(json.loads(line))
        return out

    def _append_unlocked(self, row: dict) -> dict:
        rows = self.read()
        row = dict(row)
        row["seq"] = len(rows)
        row.update(now_stamps())
        with open(self.path, "a") as f:
            f.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
            f.flush()
        return row

    def append(self, row: dict) -> dict:
        with self.locked():
            return self._append_unlocked(row)


class Commons(AppendOnlyLog):
    """Verified-lemma store. `add` refuses duplicate names (same statement => dedup no-op)."""

    def entries(self) -> list[dict]:
        return [r for r in self.read() if r.get("kind") == "lemma"]

    def names(self) -> set[str]:
        return {e["name"] for e in self.entries()}

    def add(self, *, name: str, statement: str, source: str, author: str, task: str | None, meta: dict) -> tuple[str, dict | None]:
        """Returns (status, row) with status in {added, duplicate, name_taken}."""
        eid = hashlib.sha256(f"{name}\n{statement}".encode()).hexdigest()[:16]
        with self.locked():
            for e in self.entries():
                if e["name"] == name:
                    return ("duplicate" if e["statement"] == statement else "name_taken", e)
            row = self._append_unlocked({"kind": "lemma", "entry_id": eid, "name": name, "statement": statement,
                                         "source": source, "author": author, "task": task, **meta})
            return "added", row


    def add_many(self, items: list[dict]) -> tuple[bool, list[tuple[str, str]]]:
        """All-or-nothing publish under ONE lock. Each item: name, statement, source, author, task, meta.
        An existing entry with the same name and statement is skipped (dedup); the same name with a different
        statement aborts the whole batch and writes nothing."""
        with self.locked():
            existing = {e["name"]: e for e in self.entries()}
            plan = []
            for it in items:
                e = existing.get(it["name"])
                if e is not None and e["statement"] != it["statement"]:
                    return False, [(it["name"], "name_taken")]
                plan.append((it, e is not None))
            status = []
            for it, dup in plan:
                if dup:
                    status.append((it["name"], "duplicate"))
                    continue
                eid = hashlib.sha256(f"{it['name']}\n{it['statement']}".encode()).hexdigest()[:16]
                self._append_unlocked({"kind": "lemma", "entry_id": eid, "name": it["name"], "statement": it["statement"],
                                       "source": it["source"], "author": it["author"], "task": it.get("task"), **it.get("meta", {})})
                status.append((it["name"], "added"))
            return True, status


class Board(AppendOnlyLog):
    """Pull-based claiming. A task is available if not proved, not live-claimed, and under the try cap."""

    def state(self, now: float | None = None, claim_ttl: float = 900.0) -> dict[str, dict]:
        now = now if now is not None else time.time()
        st: dict[str, dict] = {}
        for r in self.read():
            t = r.get("task")
            if not t:
                continue
            s = st.setdefault(t, {"proved": False, "tries": 0, "claimed_by": None, "claim_t": 0.0})
            if r["kind"] == "claim":
                s["claimed_by"], s["claim_t"] = r["agent"], r["t_mono_epoch"]
                s["tries"] += 1
            elif r["kind"] == "proved":
                s["proved"], s["claimed_by"] = True, None
            elif r["kind"] in ("failed", "release"):
                s["claimed_by"] = None
        for s in st.values():
            if s["claimed_by"] and now - s["claim_t"] > claim_ttl:
                s["claimed_by"] = None
        return st

    def claim_next(self, agent: str, order: list[str], max_tries: int, claim_ttl: float = 900.0) -> str | None:
        """Atomically claim the first available task in the FROZEN order. No dispatcher: any agent may call."""
        with self.locked():
            st = self.state(claim_ttl=claim_ttl)
            for t in order:
                s = st.get(t, {"proved": False, "tries": 0, "claimed_by": None})
                if not s["proved"] and not s["claimed_by"] and s["tries"] < max_tries:
                    self._append_unlocked({"kind": "claim", "task": t, "agent": agent, "t_mono_epoch": time.time()})
                    return t
        return None
