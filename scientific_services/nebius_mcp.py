"""Minimal Nebius Scientific AI MCP client (JSON-RPC 2.0 over streamable HTTP).

Endpoint: https://forge.nebius.cloud/mcp (no trailing slash). Bearer key from
~/.config/morphoswarm/nebius.env (NEBIUS_API_KEY) goes only into the Authorization header.
This client does not submit raw Nebius compute jobs; it only calls the hosted tools.
"""
from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request

from .common import load_env_value, now_utc, redact

ENDPOINT = "https://forge.nebius.cloud/mcp"
MAX_CONCURRENT = 2                       # contract: at most 2 scientific API operations at once
_sem = threading.BoundedSemaphore(MAX_CONCURRENT)


class MCPError(RuntimeError):
    def __init__(self, msg, payload=None, http_status=None):
        super().__init__(msg)
        self.payload, self.http_status = payload, http_status


def _parse_body(raw: bytes, ctype: str):
    text = raw.decode("utf-8", "replace")
    if "text/event-stream" in ctype:
        msgs = []
        for block in text.split("\n\n"):
            data = "\n".join(l[5:].lstrip() for l in block.splitlines() if l.startswith("data:"))
            if data.strip():
                msgs.append(json.loads(data))
        return msgs[-1] if msgs else None
    return json.loads(text) if text.strip() else None


class NebiusMCP:
    def __init__(self, endpoint=ENDPOINT, timeout=90, log=None):
        self.endpoint, self.timeout = endpoint, timeout
        self._key = load_env_value("nebius.env", "NEBIUS_API_KEY")
        self.session_id = None
        self._id = 0
        self.log = log if log is not None else []     # request/response transcript (redacted on dump)

    def _post(self, body: dict):
        headers = {
            "Authorization": f"Bearer {self._key}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        req = urllib.request.Request(self.endpoint, data=json.dumps(body).encode(), headers=headers, method="POST")
        t0 = time.time()
        with _sem:
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    raw, ctype, status, hdrs = r.read(), r.headers.get("Content-Type", ""), r.status, dict(r.headers)
            except urllib.error.HTTPError as e:
                raw, ctype, status, hdrs = e.read(), e.headers.get("Content-Type", ""), e.code, dict(e.headers)
        sid = hdrs.get("Mcp-Session-Id") or hdrs.get("mcp-session-id")
        if sid and not self.session_id:
            self.session_id = sid
        try:
            parsed = _parse_body(raw, ctype)
        except Exception:
            parsed = {"unparsed": raw[:2000].decode("utf-8", "replace")}
        self.log.append({"t_utc": now_utc(), "elapsed_s": round(time.time() - t0, 2), "request": body,
                         "http_status": status, "response": parsed})
        return status, parsed

    def rpc(self, method, params=None, notify=False):
        body = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            body["params"] = params
        if not notify:
            self._id += 1
            body["id"] = self._id
        status, parsed = self._post(body)
        if notify:
            return None
        if parsed is None or "error" in (parsed or {}):
            raise MCPError(f"{method}: HTTP {status}", payload=parsed, http_status=status)
        return parsed.get("result")

    def initialize(self):
        res = self.rpc("initialize", {"protocolVersion": "2025-03-26", "capabilities": {},
                                      "clientInfo": {"name": "delphi-evolve-resources", "version": "0.1"}})
        self.rpc("notifications/initialized", notify=True)
        return res

    def list_tools(self):
        out, cursor = [], None
        while True:
            res = self.rpc("tools/list", {"cursor": cursor} if cursor else {})
            out += res.get("tools", [])
            cursor = res.get("nextCursor")
            if not cursor:
                return out

    def call_tool(self, name, arguments):
        """Returns (result_dict, structured). MCP tool errors (isError) come back, not raised,
        so the caller can read e.g. an accepted operation id from a 503-style payload."""
        res = self.rpc("tools/call", {"name": name, "arguments": arguments})
        return res

    @staticmethod
    def tool_payload(res):
        """Best-effort decode of a tools/call result to a python object."""
        if res is None:
            return None
        if res.get("structuredContent") is not None:
            return res["structuredContent"]
        texts = [c.get("text", "") for c in res.get("content", []) if c.get("type") == "text"]
        joined = "\n".join(texts)
        try:
            return json.loads(joined)
        except Exception:
            return {"text": joined}
