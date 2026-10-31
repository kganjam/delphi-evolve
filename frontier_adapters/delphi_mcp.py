"""Minimal read-only client for the keyless Delphi MCP (streamable HTTP), with 429 backoff."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

URL = "https://delphisci-mcp.fly.dev/mcp"
CLAIM_PREFIX = "https://w3id.org/delphi/resource/claim/"


class Delphi:
    def __init__(self, url: str = URL, pause: float = 0.4):
        self.url, self.sid, self.n, self.pause = url, None, 0, pause
        self._rpc("initialize", {"protocolVersion": "2025-03-26", "capabilities": {},
                                 "clientInfo": {"name": "frontier-adapters", "version": "0.1"}})
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def _post(self, body):
        for attempt in range(6):
            h = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
            if self.sid:
                h["Mcp-Session-Id"] = self.sid
            try:
                with urllib.request.urlopen(urllib.request.Request(self.url, json.dumps(body).encode(), h), timeout=120) as r:
                    self.sid = r.headers.get("Mcp-Session-Id") or self.sid
                    txt = r.read().decode()
                break
            except urllib.error.HTTPError as e:
                if e.code != 429 or attempt == 5:
                    raise
                time.sleep(3 * (attempt + 1))
        time.sleep(self.pause)
        for line in txt.split("\n"):
            if line.startswith("data:"):
                return json.loads(line[5:])
        return json.loads(txt) if txt.strip() else None

    def _rpc(self, method, params):
        self.n += 1
        return self._post({"jsonrpc": "2.0", "id": self.n, "method": method, "params": params})

    def tool(self, name: str, args: dict):
        r = self._rpc("tools/call", {"name": name, "arguments": args})
        if "error" in r:
            raise RuntimeError(r["error"])
        text = "".join(c.get("text", "") for c in r["result"].get("content", []))
        if r["result"].get("isError"):
            raise RuntimeError(text[:300])
        return json.loads(text)
