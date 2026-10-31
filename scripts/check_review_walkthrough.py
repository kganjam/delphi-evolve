"""Exercise the scoped scientific examples and responsive review walkthrough.

No external requests are needed. Serve the existing site tree, inspect internal
links, change the conditions, save screenshots and an execution receipt.
"""
import functools
import hashlib
import http.server
import json
from pathlib import Path
import socketserver
import threading
from datetime import datetime
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/integration/codex-api/review-walkthrough"
OUT.mkdir(exist_ok=True)


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    server = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(ROOT / "site")))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    receipt = {"recorded_at": datetime.now(ZoneInfo("America/Los_Angeles")).isoformat(),
               "page": "site/review/index.html", "viewports": {}, "checks": [],
               "source_hashes": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in sorted((ROOT / "site/review").glob("*")) if p.is_file()}}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(args=["--no-sandbox"])
            for name, size in {"desktop": (1440, 1080), "mobile": (390, 844)}.items():
                context = browser.new_context(viewport={"width": size[0], "height": size[1]})
                page = context.new_page()
                errors = []
                page.on("pageerror", lambda e: errors.append(str(e)))
                page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
                page.on("requestfailed", lambda r: errors.append(r.url))
                page.on("response", lambda r: errors.append(f"HTTP {r.status}: {r.url}") if r.status >= 400 else None)
                page.goto(base + "/review/index.html", wait_until="networkidle")
                assert page.locator("#verdict-title").get_attribute("data-mode-count") == "0"
                page.select_option("#length", "2")
                assert page.locator("#verdict-title").get_attribute("data-mode-count") == "1"
                assert "-1/8" in page.locator("#verdict-detail").inner_text()
                page.select_option("#boundary", "periodic")
                assert page.locator("#verdict-title").get_attribute("data-mode-count") == "0"
                page.select_option("#length", "4")
                assert page.locator("#verdict-title").get_attribute("data-mode-count") == "1"
                page.click('[data-case="ratio"]')
                assert page.locator("#verdict-title").get_attribute("data-mode-count") == "1"
                assert "-21/25000" in page.locator("#verdict-detail").inner_text()
                assert "no lean execution" in page.locator(".verdict").inner_text().lower()
                page.click('[data-case="volume"]')
                assert page.locator("#verdict-title").get_attribute("data-volume-admissible") == "false"
                assert "has not been compiled in Lean" in page.locator("#receipt-description").inner_text()
                page.select_option("#mode", "2")
                assert page.locator("#verdict-title").get_attribute("data-volume-admissible") == "true"
                assert "16/9" in page.locator("#verdict-detail").inner_text()
                page.click(".appendix summary")
                assert "does not prove additive-genetic Fisher FTNS" in page.locator(".appendix").inner_text()
                page.click(".appendix summary")
                page.click('[data-case="domain"]')
                page.select_option("#length", "2")
                page.select_option("#boundary", "neumann")
                page.locator("#lab-title").scroll_into_view_if_needed()
                page.screenshot(path=str(OUT / f"{name}-lab.png"))
                page.evaluate("window.scrollTo(0,0)")
                page.screenshot(path=str(OUT / f"{name}-full.png"), full_page=True)
                overflow = page.evaluate("document.documentElement.scrollWidth-document.documentElement.clientWidth")
                assert overflow <= 1, (name, overflow)
                local_links = []
                for link in page.locator("a[href]").evaluate_all("nodes => nodes.map(n => n.getAttribute('href'))"):
                    if link.startswith(("https:", "http:", "#")):
                        continue
                    target = (ROOT / "site/review" / link).resolve()
                    assert target.is_file(), target
                    local_links.append(link)
                assert not errors, errors
                receipt["viewports"][name] = {"size": size, "horizontal_overflow_px": overflow,
                                               "errors": errors, "local_links": local_links,
                                               "screenshots": [f"{name}-lab.png", f"{name}-full.png"]}
                context.close()
            browser.close()
        receipt["checks"] = ["Neumann pi:0,2pi:1 growing modes", "periodic2pi:0,4pi:1 growing modes",
                             "fixed ratio1.1 counterexample determinant -21/25000",
                             "fixed-volume n1 rejected,n2 first-order accepted",
                             "browser vs recorded-compile labels", "Price/Fisher limitation visible",
                             "desktop/mobile controls,no console/request errors,no overflow", "local navigation targets exist"]
        receipt["ok"] = True
    except Exception as error:
        receipt["ok"] = False
        receipt["failure"] = repr(error)
        raise
    finally:
        server.shutdown()
        (OUT / "browser-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
