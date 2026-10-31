"""Scan tracked-candidate paths for credential values / signed-URL query strings. Prints file names only."""
import re, sys
from pathlib import Path
from .common import CONFIG_DIR

def secret_values():
    vals = set()
    for env in ("nebius.env", "gemini.env"):
        for line in (CONFIG_DIR / env).read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                v = v.strip().strip('"').strip("'")
                if v and len(v) >= 6:
                    vals.add(v)
    return vals

PATTERNS = [re.compile(r"\bAIza[0-9A-Za-z_\-]{20,}"), re.compile(r"\bsk-[A-Za-z0-9_\-]{16,}"),
            re.compile(r"(?i)bearer\s+(?!\[REDACTED\])[A-Za-z0-9._\-]{16,}"),
            re.compile(r"https?://[^\s\"'<>]+\?[^\s\"'<>]*(X-Amz-|Signature=|sig=|token=|GoogleAccessId)", re.I)]

def scan(paths):
    vals = secret_values(); bad = []
    for root in paths:
        for p in ([Path(root)] if Path(root).is_file() else sorted(Path(root).rglob("*"))):
            if not p.is_file() or p.stat().st_size > 20_000_000:
                continue
            try:
                t = p.read_text(errors="ignore")
            except Exception:
                continue
            if any(v in t for v in vals) or any(r.search(t) for r in PATTERNS):
                bad.append(str(p))
    return bad

if __name__ == "__main__":
    bad = scan(sys.argv[1:] or ["artifacts/services", "docs", "scientific_services", "tasks/results"])
    print("LEAKS:" if bad else "clean", *bad)
    sys.exit(1 if bad else 0)
