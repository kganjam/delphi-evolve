"""Shared helpers: credential loading (never persisted), redaction, URL sanitising, hashing."""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from zoneinfo import ZoneInfo

CONFIG_DIR = Path.home() / ".config" / "morphoswarm"
SEATTLE = ZoneInfo("America/Los_Angeles")

# Names whose values are secret in the two env files this module may read.
_SECRET_KEYS = {
    "GEMINI_API_KEY", "GOOGLE_API_KEY", "NEBIUS_API_KEY", "NEBIUS_LOGIN_PASSWORD",
    "NEBIUS_LOGIN_EMAIL", "NEBIUS_WORKBENCH_URL",
}
_secret_values: set[str] = set()


def load_env_value(env_file: str, key: str) -> str:
    """Return one value from ~/.config/morphoswarm/<env_file>; registers it for redaction.
    Raises KeyError (without echoing any value) if absent."""
    path = CONFIG_DIR / env_file
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k in _SECRET_KEYS and v:
            _secret_values.add(v)
        if k == key:
            if not v:
                raise KeyError(f"{key} empty in {env_file}")
            return v
    raise KeyError(f"{key} not found in {env_file}")


def redact(obj):
    """Recursively replace known secret values, bearer tokens, key-looking tokens and
    signed-URL query strings in any JSON-able object. Applied before anything is written."""
    if isinstance(obj, str):
        s = obj
        for v in sorted(_secret_values, key=len, reverse=True):
            s = s.replace(v, "[REDACTED]")
        s = re.sub(r"(?i)(bearer\s+)[A-Za-z0-9._\-]{8,}", r"\1[REDACTED]", s)
        s = re.sub(r"fs2-mit-hackathon-[A-Za-z0-9\-]+", "[team-bucket-name-omitted]", s)
        s = re.sub(r"\bAIza[0-9A-Za-z_\-]{20,}", "[REDACTED]", s)
        s = re.sub(r"\bsk-[A-Za-z0-9_\-]{16,}", "[REDACTED]", s)
        s = re.sub(r"(https?://[^\s\"'<>?]+)\?[^\s\"'<>]+", r"\1?[QUERY-STRIPPED]", s)
        return s
    if isinstance(obj, dict):
        return {redact(k) if isinstance(k, str) else k: redact(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [redact(v) for v in obj]
    return obj


def strip_url(url: str) -> str:
    p = urlsplit(url)
    return urlunsplit((p.scheme, p.netloc, p.path, "", ""))


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_text(s: str) -> str:
    return sha256_bytes(s.encode())


def now_utc() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def now_seattle() -> str:
    return _dt.datetime.now(SEATTLE).strftime("%Y-%m-%d %H:%M:%S %Z")


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(redact(obj), indent=1, sort_keys=False, ensure_ascii=False) + "\n")
