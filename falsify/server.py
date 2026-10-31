"""HTTP + MCP front end (stdlib only).

  POST /v1/falsify/turing   JSON request -> verdict + receipt
  GET  /v1/receipts/<id>    stored receipt
  GET  /usage, /usage.json  public ledger
  GET  /howto, /, /v1/health, /v1/schema, /v1/examples
  POST /mcp                 MCP streamable-HTTP (JSON-RPC 2.0, stateless): initialize, tools/list, tools/call, ping
Run:  python -m falsify.server --port 8765 --data-dir data/falsify
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import SERVICE_VERSION, engine, lean_receipt
from .usage import Ledger, now_pair

ROOT = Path(__file__).resolve().parent
MAX_BODY = 64 * 1024
COMPUTE = threading.Semaphore(4)
LEAN_SLOT = threading.Semaphore(1)
_RATE: dict = {}
_RATE_LOCK = threading.Lock()
RATE_PER_MIN = int(os.environ.get("FALSIFY_RATE_PER_MIN", "30"))
LEAN_PER_HOUR = int(os.environ.get("FALSIFY_LEAN_PER_HOUR", "10"))

EXAMPLE = {"claim": "Our model forms Turing patterns on a domain of length pi", "caller": "your-team-name",
           "jacobian": [[1, -2], [2, -3]], "diffusivities": [1, 10],
           "domain": {"dimension": 1, "boundary": "neumann", "length_over_pi": "1"}, "lean": True}
EXAMPLE_MODEL = {"caller": "your-team-name", "model": {"name": "brusselator", "params": {"A": 1, "B": "3/2"}},
                 "diffusivities": [1, 30], "domain": {"dimension": 1, "boundary": "dirichlet", "length": 12.5}}

TOOL_SCHEMA = {
    "name": "falsify_turing_pattern",
    "description": ("Try to BREAK a pattern-formation claim: does ANY admissible Laplacian mode grow linearly for a two-species "
                    "reaction-diffusion system on a finite 1-D or 2-D domain (neumann / dirichlet / periodic)? Returns an exact-rational "
                    "verdict (survived / refuted / out_of_scope / unresolvable), the complete list of unstable modes, the smallest domain "
                    "length that admits any, independent cross-checks, and a stored receipt id. lean=true adds a Lean 4 machine-checked "
                    "proof of the 1-D classification (about 15 s). A growing linear mode is a LINEAR-instability prediction under the "
                    "declared assumptions, not proof of nonlinear or biological pattern formation."),
    "inputSchema": {"type": "object", "properties": {
        "caller": {"type": "string", "description": "your team / tool name (self-declared; shown on the public usage page)"},
        "claim": {"type": "string", "description": "optional text of the claim being tested"},
        "jacobian": {"type": "array", "description": "2x2 Jacobian at the homogeneous steady state; numbers or exact strings like '3/2'", "items": {"type": "array", "items": {}}},
        "model": {"type": "object", "description": "instead of jacobian: {name: brusselator|schnakenberg|gierer_meinhardt, params: {...}}"},
        "diffusivities": {"type": "array", "items": {}, "description": "[Du, Dv], both > 0"},
        "domain": {"type": "object", "description": "{dimension:1|2, boundary:neumann|dirichlet|periodic, length_over_pi | length (1-D) or lengths_over_pi | lengths (2-D)}"},
        "lean": {"type": "boolean", "description": "also produce a Lean receipt (1-D, exact length_over_pi only)"}},
        "required": ["diffusivities", "domain"]}}
LEAN_UNCHECKED = ["Routh-Hurwitz (trace<0 and det>0) taken as the meaning of 'linearly stable' (definition in Basic.lean)",
                  "rational J, D scaled by a common positive integer (signs unchanged)",
                  "dirichlet = neumann spectrum minus the stable constant mode; periodic length L = neumann length L/2",
                  "the PDE itself, nonlinear dynamics, and the physical meaning of the declared Jacobian"]
GET_RECEIPT = {"name": "get_receipt", "description": "Fetch a stored receipt by id.", "inputSchema": {
    "type": "object", "properties": {"receipt_id": {"type": "string"}}, "required": ["receipt_id"]}}


class App:
    def __init__(self, data_dir, trust_forwarded=False, internal_token=None):
        self.ledger = Ledger(data_dir)
        self.rdir = Path(data_dir) / "receipts"
        self.rdir.mkdir(parents=True, exist_ok=True)
        self.trust_forwarded = trust_forwarded
        self.internal_token = internal_token or os.environ.get("FALSIFY_INTERNAL_TOKEN")
        self.lean_ok = None

    # -- rate limit
    def rate_ok(self, key, kind="req"):
        lim, win = (RATE_PER_MIN, 60) if kind == "req" else (LEAN_PER_HOUR, 3600)
        now = time.time()
        with _RATE_LOCK:
            q = [t for t in _RATE.get((key, kind), []) if now - t < win]
            if len(q) >= lim:
                _RATE[(key, kind)] = q
                return False
            q.append(now)
            _RATE[(key, kind)] = q
            return True

    # -- core call
    def falsify(self, req, ctx):
        t0 = time.time()
        caller = (req.get("caller") if isinstance(req, dict) else None) or ctx.get("caller") or None
        if isinstance(caller, str):
            caller = re.sub(r"[^\w .@:/+-]", "", caller)[:60] or None
        if ctx["origin"] != "self-test":
            ctx = dict(ctx, origin=self.ledger.classify(ctx["ip"], caller, False))
        with COMPUTE:
            res = engine.falsify_turing(req if isinstance(req, dict) else {})
        lean_in = res.pop("_lean_inputs", None)
        want_lean = res.pop("lean_wanted", False)
        lean = {"requested": bool(want_lean)}
        if want_lean:
            if lean_in is None:
                lean.update(status="not_applicable", detail="Lean receipts cover 1-D domains with exact length_over_pi and a decided verdict")
            elif not self.rate_ok(ctx["ip_hash"], "lean"):
                lean.update(status="rate_limited", detail=f"{LEAN_PER_HOUR} Lean receipts per hour per caller")
            else:
                try:
                    d = lean_in["dom"]
                    src, meta = lean_receipt.build_source(lean_in["J"], lean_in["D"], d["boundary"], d["r"][0][0],
                                                          [m["index"] for m in lean_in["unstable"]])
                    if not LEAN_SLOT.acquire(timeout=60):
                        lean.update(status="busy", detail="Lean checker busy; retry")
                    else:
                        try:
                            out = lean_receipt.run(src)
                        finally:
                            LEAN_SLOT.release()
                        lean.update(out, meta=meta, lean_version=lean_receipt.lean_version(), source=src,
                                    library="turing_scope/lean (TuringScope); generic tail theorem neumann_tail_hurwitz",
                                    unchecked_modelling_steps=LEAN_UNCHECKED)
                except ValueError as e:
                    lean.update(status="not_applicable", detail=str(e))
        res["lean"] = lean
        body_hash = hashlib.sha256(json.dumps(res, sort_keys=True, default=str).encode()).hexdigest()
        rid = body_hash[:20]
        res["receipt_id"] = rid
        res["receipt"] = {"id": rid, "issued_utc": now_pair()[0], "issued_seattle": now_pair()[1],
                          "request_sha256": engine.request_hash(req if isinstance(req, dict) else {}),
                          "reproduce_locally": "python -m falsify.cli check request.json   |   python -m falsify.cli verify-receipt receipt.json",
                          "service_version": SERVICE_VERSION}
        (self.rdir / f"{rid}.json").write_text(json.dumps({"request": req, "response": res}, indent=1, default=str))
        self.log(ctx, caller, "falsify_turing_pattern", req, res.get("verdict"), rid, lean.get("status"), t0, 200)
        return res

    def log(self, ctx, caller, tool, req, verdict, rid, lean_status, t0, status):
        summ = None
        if isinstance(req, dict):
            summ = {k: req.get(k) for k in ("model", "jacobian", "diffusivities", "domain", "claim") if k in req}
            if len(json.dumps(summ, default=str)) > 1500:
                summ = {"truncated": True}
        self.ledger.append({"channel": ctx["channel"], "tool": tool, "caller": caller, "origin": ctx["origin"], "ip_hash": ctx["ip_hash"],
                            "user_agent": (ctx.get("ua") or "")[:80], "request_summary": summ, "verdict": verdict, "receipt_id": rid,
                            "lean_status": lean_status, "http_status": status, "latency_ms": int((time.time() - t0) * 1000)})

    def get_receipt(self, rid):
        if not re.fullmatch(r"[0-9a-f]{8,64}", rid or ""):
            return None
        p = self.rdir / f"{rid}.json"
        return json.loads(p.read_text()) if p.exists() else None

    # -- MCP
    def mcp(self, msg, ctx):
        mid, method = msg.get("id"), msg.get("method")
        ok = lambda r: {"jsonrpc": "2.0", "id": mid, "result": r}
        err = lambda c, m: {"jsonrpc": "2.0", "id": mid, "error": {"code": c, "message": m}}
        if method == "initialize":
            pv = (msg.get("params") or {}).get("protocolVersion") or "2025-03-26"
            ci = (msg.get("params") or {}).get("clientInfo") or {}
            return ok({"protocolVersion": pv if pv in ("2024-11-05", "2025-03-26", "2025-06-18") else "2025-03-26",
                       "capabilities": {"tools": {"listChanged": False}},
                       "serverInfo": {"name": "delphi-falsify", "version": SERVICE_VERSION},
                       "instructions": "Call falsify_turing_pattern with a 2x2 Jacobian (or preset model), [Du,Dv] and a domain. "
                                       "Set 'caller' to your team name. Linear-instability verdicts only; see tool description."})
        if method and method.startswith("notifications/"):
            return None
        if method == "ping":
            return ok({})
        if method == "tools/list":
            return ok({"tools": [TOOL_SCHEMA, GET_RECEIPT]})
        if method == "tools/call":
            p = msg.get("params") or {}
            name, args = p.get("name"), p.get("arguments") or {}
            if name == "falsify_turing_pattern":
                if not self.rate_ok(ctx["ip_hash"]):
                    return ok({"isError": True, "content": [{"type": "text", "text": "rate limited"}]})
                res = self.falsify(args, ctx)
                return ok({"content": [{"type": "text", "text": json.dumps(res, indent=1)}], "isError": False})
            if name == "get_receipt":
                r = self.get_receipt(args.get("receipt_id"))
                return ok({"content": [{"type": "text", "text": json.dumps(r, indent=1) if r else "not found"}], "isError": r is None})
            return err(-32602, f"unknown tool {name}")
        return err(-32601, f"method not found: {method}")


def make_handler(app: App):
    class H(BaseHTTPRequestHandler):
        server_version = "delphi-falsify/" + SERVICE_VERSION

        def log_message(self, *a):
            pass

        def ctx(self, channel):
            ip = self.client_address[0]
            if app.trust_forwarded and self.headers.get("X-Forwarded-For"):
                ip = self.headers["X-Forwarded-For"].split(",")[0].strip()
            tok = self.headers.get("X-Internal-Token")
            tok_ok = bool(app.internal_token and tok and hmac.compare_digest(tok, app.internal_token))
            label = self.headers.get("X-Caller")
            ch = self.headers.get("X-Channel") or channel
            return {"ip": ip, "ip_hash": app.ledger.ip_hash(ip), "caller": label, "ua": self.headers.get("User-Agent"),
                    "channel": ch, "origin": app.ledger.classify(ip, label, tok_ok)}

        def send(self, code, body, ctype="application/json"):
            b = body.encode() if isinstance(body, str) else body
            self.send_response(code)
            self.send_header("Content-Type", ctype + "; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b)

        def jsend(self, code, obj):
            self.send(code, json.dumps(obj, indent=1, default=str))

        def do_OPTIONS(self):
            self.send_response(204)
            for k, v in (("Access-Control-Allow-Origin", "*"), ("Access-Control-Allow-Headers", "Content-Type, X-Caller, X-Channel"),
                         ("Access-Control-Allow-Methods", "GET, POST, OPTIONS")):
                self.send_header(k, v)
            self.end_headers()

        def do_GET(self):
            path = self.path.split("?")[0]
            if path in ("/", "/howto"):
                proto = self.headers.get("X-Forwarded-Proto", "http") if app.trust_forwarded else "http"
                base = f"{proto}://{self.headers.get('Host', 'localhost')}"
                return self.send(200, (ROOT / "static" / "howto.html").read_text().replace("{{BASE}}", base), "text/html")
            if path == "/usage":
                return self.send(200, app.ledger.page(), "text/html")
            if path == "/usage.json":
                return self.jsend(200, app.ledger.summary())
            if path == "/v1/health":
                return self.jsend(200, {"status": "ok", "service": "delphi-falsify", "version": SERVICE_VERSION,
                                        "available": True, "used_by_others": "see /usage (available is not used)",
                                        "started_seattle": app.ledger.started_seattle, "time_seattle": now_pair()[1]})
            if path == "/v1/schema":
                return self.jsend(200, {"tools": [TOOL_SCHEMA, GET_RECEIPT]})
            if path == "/v1/examples":
                return self.jsend(200, {"jacobian_form": EXAMPLE, "preset_form": EXAMPLE_MODEL})
            m = re.fullmatch(r"/v1/receipts/([0-9a-f]{8,64})", path)
            if m:
                r = app.get_receipt(m.group(1))
                return self.jsend(200, r) if r else self.jsend(404, {"error": "receipt not found"})
            self.jsend(404, {"error": "not found", "see": "/howto"})

        def do_POST(self):
            path = self.path.split("?")[0]
            n = int(self.headers.get("Content-Length") or 0)
            if n > MAX_BODY:
                return self.jsend(413, {"error": f"body over {MAX_BODY} bytes"})
            raw = self.rfile.read(n) if n else b""
            c = self.ctx("http" if path != "/mcp" else "mcp-http")
            if not app.rate_ok(c["ip_hash"]):
                return self.jsend(429, {"error": f"rate limit {RATE_PER_MIN}/min"})
            try:
                body = json.loads(raw or b"{}")
            except json.JSONDecodeError as e:
                app.log(c, c["caller"], "invalid_json", None, "bad_request", None, None, time.time(), 400)
                return self.jsend(400, {"error": f"invalid JSON: {e}"})
            if path == "/v1/falsify/turing":
                return self.jsend(200, app.falsify(body, c))
            if path == "/mcp":
                if isinstance(body, list):
                    outs = [r for r in (app.mcp(m, c) for m in body) if r]
                    return self.jsend(200, outs) if outs else self.send(202, "")
                r = app.mcp(body, c)
                return self.jsend(200, r) if r else self.send(202, "")
            self.jsend(404, {"error": "not found", "see": "/howto"})
    return H


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m falsify.server")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--data-dir", default="data/falsify")
    ap.add_argument("--trust-forwarded", action="store_true", help="use X-Forwarded-For for caller address (only behind a proxy you control)")
    a = ap.parse_args(argv)
    app = App(a.data_dir, a.trust_forwarded)
    srv = ThreadingHTTPServer((a.host, a.port), make_handler(app))
    print(f"delphi-falsify {SERVICE_VERSION} on {a.host}:{a.port} data={a.data_dir}", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
