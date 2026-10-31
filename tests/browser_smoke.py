"""Browser smoke test for site/ (run with a Python that has playwright; not the venv).

  python3 tests/browser_smoke.py            # exit 0 on success

Serves a temp copy of site/ over HTTP and checks: no page errors; real counts shown; honest empty states
when demo.json is absent; the Proof tab is green ONLY when a receipt has kernel exit 0 AND a non-zero
mutant exit; the slider changes the decision. The synthetic demo.json used for the proof-state fixtures
contains no scientific data and exists only inside the temp copy.
"""
import functools
import http.server
import json
import shutil
import sys
import tempfile
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

SITE = Path(__file__).resolve().parent.parent / "site"


def serve(root):
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a, **k):
            pass

    h = functools.partial(Quiet, directory=str(root))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


def fixture_demo(proof):
    return {"schema_version": "test-fixture", "nodes": [], "edges": [], "routes": [], "claims": [],
            "benchmark": {"status": "unavailable", "protocol": None, "metrics": None, "limitations": []},
            "proof": proof, "compute": {"status": "unavailable"}, "limitations": ["fixture"],
            "source": {"counts": {}}}


def run():
    tmp = Path(tempfile.mkdtemp())
    root = tmp / "site"
    shutil.copytree(SITE, root)
    (root / "data" / "demo.json").unlink(missing_ok=True)
    fails = []
    with sync_playwright() as p:
        try:
            b = p.chromium.launch(args=["--no-sandbox"])
        except Exception:
            b = p.chromium.launch(executable_path="/snap/bin/chromium", args=["--no-sandbox"])

        def open_page(port, query=""):
            pg = b.new_page(viewport={"width": 1280, "height": 900})
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(f"http://127.0.0.1:{port}/{query}")
            pg.wait_for_function("window.__ready===true", timeout=20000)
            return pg, errs

        srv, port = serve(root)
        pg, errs = open_page(port)
        led = pg.inner_text("#ledger")
        if "159,129 measured" not in led or "871 unmeasured" not in led:
            fails.append("ledger lacks real counts: " + led)
        if "demo.json (core output): not present" not in led:
            fails.append("ledger should say demo.json absent")
        pg.click("#tab-proof")
        if "No proof receipt loaded" not in pg.inner_text("#p-proof"):
            fails.append("Proof tab must show empty state without receipt")
        before = pg.inner_text("#dec-dyn")
        pg.evaluate("()=>{const e=document.querySelector('#eps');e.value=6;e.dispatchEvent(new Event('input'))}")
        after = pg.inner_text("#dec-dyn")
        if before == after or "NO ROUTE CERTIFIABLE" not in after.upper() or "MAY STILL EXIST" not in after.upper():
            fails.append("slider at max must flip the decision to 'no route certifiable' and say an ascending route may still exist")
        pg.click("#tab-evidence")
        if "Genotype" not in pg.inner_text("#p-evidence"):
            fails.append("evidence tab empty")
        if errs:
            fails.append("page errors: " + "; ".join(errs))
        pg.close(); srv.shutdown()

        # proof-state fixtures
        for label, proof, want_green in (
            ("kernel ok, mutant NOT rejected", {"status": "compiled", "theorem": "t", "command": "c", "exit_code": 0, "mutation_exit_code": 0, "receipt": "r"}, False),
            ("kernel ok, mutant rejected", {"status": "compiled", "theorem": "t", "command": "c", "exit_code": 0, "mutation_exit_code": 1, "receipt": "r"}, True),
            ("kernel failed", {"status": "failed", "theorem": "t", "command": "c", "exit_code": 1, "mutation_exit_code": 1, "receipt": "r"}, False),
        ):
            (root / "data" / "demo.json").write_text(json.dumps(fixture_demo(proof)))
            srv, port = serve(root)
            pg, errs = open_page(port, "?tab=proof")
            html = pg.inner_html("#p-proof")
            green = 'class="verdict open"' in html
            if green != want_green:
                fails.append(f"proof fixture '{label}': green={green}, expected {want_green}")
            if errs:
                fails.append(f"{label}: page errors {errs}")
            pg.close(); srv.shutdown()
        b.close()
    shutil.rmtree(tmp, ignore_errors=True)
    for f in fails:
        print("FAIL:", f)
    print("browser smoke:", "FAILED" if fails else "ok")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(run())
