"""stdio MCP proxy: lets any stdio-MCP client (Claude Desktop/Code, etc.) use the hosted service.
Forwards each JSON-RPC line to POST {endpoint}/mcp so every call lands in the central usage ledger.
Nothing is computed locally."""
from __future__ import annotations

import json
import sys
import urllib.request


def run(endpoint: str, caller: str) -> int:
    url = endpoint.rstrip("/") + "/mcp"
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        req = urllib.request.Request(url, data=line.encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Caller": caller, "X-Channel": "mcp-stdio-proxy"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                body = r.read().decode()
        except Exception as e:
            if "id" in msg:
                sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": msg["id"], "error": {"code": -32000, "message": f"endpoint error: {e}"}}) + "\n")
                sys.stdout.flush()
            continue
        if body.strip():
            data = json.loads(body)
            for d in (data if isinstance(data, list) else [data]):
                sys.stdout.write(json.dumps(d) + "\n")
            sys.stdout.flush()
    return 0
