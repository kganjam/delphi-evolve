"""Usage ledger: records every call (who / with what / what came back) and renders the public page.

Honesty rules baked in:
  * 'who' is a SELF-DECLARED label plus a salted hash of the network address. The service cannot verify identity.
  * calls from loopback, from labels starting 'delphi-'/'internal', or carrying the operator token are tagged
    origin='self-test' and counted separately; only the remaining calls are 'external-unverified'.
  * Nothing is ever fabricated, backfilled or edited; the ledger is append-only JSONL.
"""
from __future__ import annotations

import datetime
import hashlib
import html
import json
import os
import secrets
import threading
import time
from pathlib import Path
from zoneinfo import ZoneInfo

SEATTLE = ZoneInfo("America/Los_Angeles")
_LOCK = threading.Lock()


def now_pair():
    t = datetime.datetime.now(datetime.timezone.utc)
    return t.strftime("%Y-%m-%dT%H:%M:%SZ"), t.astimezone(SEATTLE).strftime("%Y-%m-%d %H:%M:%S %Z")


class Ledger:
    def __init__(self, data_dir):
        self.dir = Path(data_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "usage.jsonl"
        salt_p = self.dir / ".salt"
        if not salt_p.exists():
            salt_p.write_text(secrets.token_hex(16))
            os.chmod(salt_p, 0o600)
        self.salt = salt_p.read_text().strip()
        self.started_utc, self.started_seattle = now_pair()

    def ip_hash(self, ip):
        return hashlib.sha256((self.salt + ip).encode()).hexdigest()[:10]

    def classify(self, ip, label, internal_token_ok):
        l = (label or "").lower()
        if internal_token_ok or ip in ("127.0.0.1", "::1") or l.startswith(("delphi-", "internal", "selftest", "self-test")):
            return "self-test"
        return "external-unverified"

    def append(self, entry: dict):
        entry = dict(entry)
        entry["ts_utc"], entry["ts_seattle"] = now_pair()
        with _LOCK:
            with self.path.open("a") as f:
                f.write(json.dumps(entry, sort_keys=True, ensure_ascii=False) + "\n")
        return entry

    def read(self):
        if not self.path.exists():
            return []
        rows = []
        for ln in self.path.read_text().splitlines():
            try:
                rows.append(json.loads(ln))
            except json.JSONDecodeError:
                pass
        return rows

    def summary(self):
        rows = self.read()
        calls = [r for r in rows if r.get("tool") != "meta"]
        ext = [r for r in calls if r.get("origin") == "external-unverified"]
        by = {}
        for r in ext:
            k = (r.get("caller") or "anonymous", r.get("ip_hash"))
            d = by.setdefault(k, {"caller_label_declared": k[0], "network_hash": k[1], "calls": 0, "verdicts": {}, "first_seen_seattle": r["ts_seattle"], "last_seen_seattle": r["ts_seattle"]})
            d["calls"] += 1
            d["last_seen_seattle"] = r["ts_seattle"]
            d["verdicts"][r.get("verdict", "?")] = d["verdicts"].get(r.get("verdict", "?"), 0) + 1
        return {"service_started_utc": self.started_utc, "service_started_seattle": self.started_seattle,
                "generated_seattle": now_pair()[1],
                "totals": {"all_calls": len(calls), "self_test_calls": len(calls) - len(ext), "external_unverified_calls": len(ext),
                           "external_distinct_callers": len(by)},
                "external_callers": sorted(by.values(), key=lambda d: -d["calls"]),
                "recent_calls": list(reversed(calls[-100:])),
                "definitions": {
                    "available": "the endpoint is reachable and answers (see /v1/health)",
                    "used": "a call recorded below whose origin is external-unverified; identity is self-declared and unverified",
                    "self_test": "calls by the Delphi team's own tests (loopback, label 'delphi-*'/'internal*', or operator token); they show the service works, NOT that anyone else uses it"}}

    def page(self):
        s = self.summary()
        t = s["totals"]
        e = html.escape
        rows = "".join(
            f"<tr><td>{e(r['ts_seattle'])}</td><td>{e(r.get('origin',''))}</td><td>{e(str(r.get('caller') or 'anonymous'))}</td>"
            f"<td>{e(r.get('ip_hash') or '')}</td><td>{e(r.get('channel',''))}</td><td class=m>{e(json.dumps(r.get('request_summary'), ensure_ascii=False)[:300])}</td>"
            f"<td>{e(str(r.get('verdict','')))}</td><td>{('<a href=\"/v1/receipts/%s\">%s</a>' % (e(r['receipt_id']), e(r['receipt_id'][:10]))) if r.get('receipt_id') else ''}</td>"
            f"<td>{e(str(r.get('lean_status','')))}</td><td>{r.get('latency_ms','')}</td></tr>" for r in s["recent_calls"])
        ext = "".join(f"<tr><td>{e(c['caller_label_declared'])}</td><td>{e(c['network_hash'] or '')}</td><td>{c['calls']}</td><td>{e(json.dumps(c['verdicts']))}</td><td>{e(c['first_seen_seattle'])}</td><td>{e(c['last_seen_seattle'])}</td></tr>" for c in s["external_callers"]) \
            or "<tr><td colspan=6><b>None yet.</b> No call from outside the team has been recorded.</td></tr>"
        return f"""<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Falsification service: usage</title><meta http-equiv=refresh content=30>
<style>body{{font:15px/1.5 system-ui,sans-serif;max-width:1100px;margin:0 auto;padding:16px;color:#1b1f23;background:#fff}}
@media(prefers-color-scheme:dark){{body{{background:#14181c;color:#e6e9ec}}a{{color:#8ab4ff}}th{{background:#222a31}}td,th{{border-color:#333}}}}
table{{border-collapse:collapse;width:100%;font-size:13px;display:block;overflow-x:auto}}td,th{{border:1px solid #ccc;padding:3px 6px;text-align:left;vertical-align:top}}th{{background:#eef}}.m{{font-family:monospace;font-size:11px}}
.k{{display:flex;gap:12px;flex-wrap:wrap}}.k div{{border:1px solid #aaa;border-radius:6px;padding:8px 14px}}.k b{{font-size:28px;display:block}}</style></head><body>
<h1>Falsification service: usage ledger</h1>
<p>Live from the append-only log on the serving host. Started {e(s['service_started_seattle'])}; page generated {e(s['generated_seattle'])}. <a href=/usage.json>JSON</a> &middot; <a href=/howto>how to call it</a> &middot; <a href=/v1/health>health</a></p>
<div class=k><div><b>{t['external_unverified_calls']}</b>calls from outside the team (<i>used</i>)</div><div><b>{t['external_distinct_callers']}</b>distinct external callers</div>
<div><b>{t['self_test_calls']}</b>self-test calls (team's own; prove availability only)</div><div><b>{t['all_calls']}</b>all calls</div></div>
<p><b>Available is not used.</b> {e(s['definitions']['self_test'])} Caller names are self-declared and unverified; network addresses are shown only as salted hashes.</p>
<p>Scope reminder: a positive linear eigenmode here predicts <i>linear instability under the declared assumptions</i>, not nonlinear or biological pattern formation. No wet-lab or clinical implication.</p>
<h2>External callers</h2><table><tr><th>declared label</th><th>network hash</th><th>calls</th><th>verdicts</th><th>first</th><th>last</th></tr>{ext}</table>
<h2>Last {len(s['recent_calls'])} calls (what was sent, what came back)</h2>
<table><tr><th>time (Seattle)</th><th>origin</th><th>caller</th><th>net</th><th>channel</th><th>request</th><th>verdict</th><th>receipt</th><th>lean</th><th>ms</th></tr>{rows or '<tr><td colspan=10>no calls recorded</td></tr>'}</table>
</body></html>"""
