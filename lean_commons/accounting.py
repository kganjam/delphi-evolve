"""Append-only token ledger with hard budget caps (matched-token-budget comparisons)."""
from __future__ import annotations

import json
import threading
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

SEATTLE = ZoneInfo("America/Los_Angeles")


class BudgetExceeded(RuntimeError):
    pass


@dataclass
class Usage:
    input_tokens: int = 0          # uncached prompt tokens as reported by the provider
    output_tokens: int = 0         # completion tokens INCLUDING reasoning/thinking when the provider reports it
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    reasoning_tokens: int = 0      # informational subset of output (not added again)
    source: str = "provider_reported"   # provider_reported | estimated

    @property
    def gross_input(self) -> int:
        return self.input_tokens + self.cache_read_tokens + self.cache_creation_tokens

    @property
    def total(self) -> int:
        return self.gross_input + self.output_tokens


def now_stamps() -> dict:
    n = datetime.now(timezone.utc)
    return {"ts_utc": n.isoformat(timespec="seconds"),
            "ts_seattle": n.astimezone(SEATTLE).isoformat(timespec="seconds")}


class TokenLedger:
    """JSONL ledger. One line per model call; budgets keyed by arbitrary string (guild, arm...).

    Budget is checked BEFORE a call against reserved tokens (a caller-supplied upper bound on
    the call's total) and the actual usage is added after. A failed call that consumed tokens is
    still charged. Thread-safe within a process; one writer process per ledger file.
    """

    def __init__(self, path: str | Path, budgets: dict[str, int] | None = None):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.budgets = dict(budgets or {})
        self._lock = threading.Lock()
        self._spent: dict[str, int] = {}
        self._pending: dict[str, int] = {}
        if self.path.exists():
            for line in self.path.read_text().splitlines():
                if line.strip():
                    r = json.loads(line)
                    self._spent[r["budget_key"]] = self._spent.get(r["budget_key"], 0) + int(r["tokens"]["total"])

    def spent(self, key: str) -> int:
        return self._spent.get(key, 0)

    def remaining(self, key: str) -> int | None:
        return None if key not in self.budgets else self.budgets[key] - self.spent(key)

    def check(self, key: str, reserve: int) -> None:
        """Advisory pre-check (spent + pending + reserve <= cap). Use `reserve_tokens` to hold budget atomically."""
        with self._lock:
            self._check_unlocked(key, reserve)

    def _check_unlocked(self, key: str, reserve: int) -> None:
        if key in self.budgets and self._spent.get(key, 0) + self._pending.get(key, 0) + reserve > self.budgets[key]:
            raise BudgetExceeded(f"{key}: spent {self._spent.get(key, 0)} + pending {self._pending.get(key, 0)} + reserve {reserve} > cap {self.budgets[key]}")

    def reserve_tokens(self, key: str, n: int) -> int:
        """Atomically hold `n` tokens of budget for an in-flight call; released by `record`/`release`."""
        with self._lock:
            self._check_unlocked(key, n)
            self._pending[key] = self._pending.get(key, 0) + n
        return n

    def release(self, key: str, n: int) -> None:
        with self._lock:
            self._pending[key] = max(0, self._pending.get(key, 0) - n)

    def record(self, key: str, record: dict, usage: Usage, held: int = 0) -> dict:
        row = dict(record)
        row.update(now_stamps())
        row["budget_key"] = key
        row["tokens"] = {**{k: v for k, v in asdict(usage).items()}, "gross_input": usage.gross_input, "total": usage.total}
        with self._lock:
            with self.path.open("a") as f:
                f.write(json.dumps(row, sort_keys=True) + "\n")
            self._spent[key] = self._spent.get(key, 0) + usage.total
            self._pending[key] = max(0, self._pending.get(key, 0) - held)
        return row
