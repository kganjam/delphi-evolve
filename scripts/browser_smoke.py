#!/usr/bin/env python3
"""Browser smoke test for the static site (integrator-owned, no network access needed).

  python3 scripts/browser_smoke.py site OUTDIR  > OUTDIR/smoke.json

Serves SITE over a local HTTP server, loads it in headless Chromium at desktop (1280x900)
and mobile (390x844) sizes and records: console errors/warnings, uncaught page errors,
failed requests, horizontal overflow, number of focusable controls, whether tabbing moves
focus through >=5 distinct elements, and a full-page screenshot per viewport.
Exit 0 only if there are no console errors, page errors, failed requests or mobile overflow.
"""
import functools, http.server, json, pathlib, socketserver, sys, threading
from playwright.sync_api import sync_playwright

site = pathlib.Path(sys.argv[1]).resolve()
out = pathlib.Path(sys.argv[2]).resolve()
out.mkdir(parents=True, exist_ok=True)


class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


handler = functools.partial(Q, directory=str(site))
httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
port = httpd.server_address[1]
threading.Thread(target=httpd.serve_forever, daemon=True).start()
report = {"site": str(site), "viewports": {}}
bad = False
with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"])
    for name, (w, h) in {"desktop": (1280, 900), "mobile": (390, 844)}.items():
        ctx = b.new_context(viewport={"width": w, "height": h})
        pg = ctx.new_page()
        console, errors, failed = [], [], []
        pg.on("console", lambda m: console.append({"type": m.type, "text": m.text[:300]}) if m.type in ("error", "warning") else None)
        pg.on("pageerror", lambda e: errors.append(str(e)[:300]))
        pg.on("requestfailed", lambda r: failed.append(r.url))
        pg.on("response", lambda r: failed.append(f"{r.status} {r.url}") if r.status >= 400 else None)
        pg.goto(f"http://127.0.0.1:{port}/index.html", wait_until="networkidle")
        pg.wait_for_timeout(500)
        overflow = pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        focusable = pg.evaluate("document.querySelectorAll('a[href],button,input,select,textarea,[tabindex]:not([tabindex=\"-1\"])').length")
        seen = set()
        for _ in range(12):
            pg.keyboard.press("Tab")
            seen.add(pg.evaluate("(document.activeElement.tagName||'')+'#'+(document.activeElement.id||'')+'.'+((document.activeElement.textContent||'').trim().slice(0,20))"))
        pg.evaluate("window.scrollTo(0, 0)")
        pg.screenshot(path=str(out / f"site_{name}.png"), full_page=True)
        text = pg.inner_text("body")
        report["viewports"][name] = {"console": console, "page_errors": errors, "failed_requests": failed,
                                     "horizontal_overflow_px": overflow, "focusable_controls": focusable,
                                     "distinct_focus_stops_in_12_tabs": len(seen), "body_text_chars": len(text),
                                     "screenshot": f"site_{name}.png"}
        bad |= bool(errors or failed or [c for c in console if c["type"] == "error"])
        if name == "mobile" and overflow > 1:
            bad = True
        ctx.close()
    b.close()
httpd.shutdown()
report["ok"] = not bad
print(json.dumps(report, indent=1))
sys.exit(1 if bad else 0)
