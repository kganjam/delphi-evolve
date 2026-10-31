#!/usr/bin/env python3
"""Record a 90 s silent, captioned walkthrough of the Delphi deck (six slides) and the landing page's ledger section.

    python3 presentation/delphi/video/record_delphi_video.py [--out presentation/delphi/video]

* Only UI pixels: the built deck (presentation/delphi/deck.html) and site/delphi/index.html. No generated imagery, no audio.
* Captions are read from presentation/delphi/video/captions.json (written by build_site.py from the storyboard).
* Exit 0 only if 60 <= duration <= 95 s, MP4 <= 20 MB and no page error occurred.
* The manifest pins the source git HEAD, the deck and site hashes and the video sha256. Re-record after every rebuild.
"""
from __future__ import annotations

import argparse
import functools
import hashlib
import http.server
import json
import shutil
import socketserver
import subprocess
import sys
import tempfile
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
W, H, CAPH = 1280, 840, 60  # 1280x720 deck letterboxed with a 60 px caption bar below it
HOLD = {1: 11, 2: 16, 3: 14, 4: 16, 5: 14, 6: 9}  # seconds per slide
SITE_HOLD = 8


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def tree_hash(d: Path):
    h = hashlib.sha256()
    for p in sorted(x for x in d.rglob("*") if x.is_file()):
        h.update(str(p.relative_to(d)).encode())
        h.update(sha256(p).encode())
    return h.hexdigest()


def seattle():
    u = datetime.now(timezone.utc)
    off, name = (-7, "PDT") if u < datetime(2026, 11, 1, 9, 0, tzinfo=timezone.utc) else (-8, "PST")
    return (u + timedelta(hours=off)).strftime("%Y-%m-%d %H:%M:%S ") + name


def status(*paths):
    r = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "--", *paths], capture_output=True, text=True)
    return [l[3:] for l in r.stdout.splitlines()]


def git(*a):
    r = subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


CAP_JS = """([main, tag]) => {
  let d = document.getElementById('vcap');
  if (!d) {
    d = document.createElement('div'); d.id = 'vcap';
    d.style.cssText = 'position:fixed;left:0;right:0;bottom:0;height:%dpx;z-index:2147483647;background:#15202b;color:#f6f3ea;padding:7px 20px;font:600 19px/1.25 system-ui,sans-serif;box-sizing:border-box;overflow:hidden';
    d.innerHTML = '<div id="vcap-main"></div><div id="vcap-tag" style="font:500 12px/1.3 ui-monospace,monospace;color:#e9c9b6;margin-top:3px"></div>';
    document.body.appendChild(d);
  }
  document.getElementById('vcap-main').textContent = main;
  document.getElementById('vcap-tag').textContent = tag;
}""" % CAPH


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE))
    a = ap.parse_args()
    out = Path(a.out)
    caps = json.loads((HERE / "captions.json").read_text())
    deck = ROOT / "presentation/delphi/deck.html"
    site = ROOT / "site"
    handler = functools.partial(Quiet, directory=str(site))
    srv = socketserver.TCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    log, errors = [], []
    t0 = None
    with tempfile.TemporaryDirectory() as td, sync_playwright() as p:
        b = p.chromium.launch(args=["--disable-dev-shm-usage"])
        ctx = b.new_context(viewport={"width": W, "height": H}, record_video_dir=td, record_video_size={"width": W, "height": H})
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        pg.on("requestfailed", lambda r: errors.append("requestfailed " + r.url))
        pg.goto(deck.as_uri() + "#1")
        pg.wait_for_timeout(400)
        for n in range(1, 7):
            if n > 1:
                pg.keyboard.press("ArrowRight")
            pg.wait_for_timeout(250)
            pg.evaluate(CAP_JS, [caps["deck_slide_captions"][str(n)], caps["persistent_tag"]])
            log.append({"scene": f"deck slide {n}", "hold_s": HOLD[n], "caption": caps["deck_slide_captions"][str(n)]})
            pg.wait_for_timeout(int(HOLD[n] * 1000))
        pg.goto(base + "/delphi/index.html#ledger")
        pg.wait_for_timeout(500)
        pg.add_style_tag(content="body{padding-bottom:70px}")
        pg.evaluate(CAP_JS, [caps["site_ledger_caption"], caps["persistent_tag"]])
        pg.evaluate("document.getElementById('ledger').scrollIntoView()")
        log.append({"scene": "site ledger section", "hold_s": SITE_HOLD, "caption": caps["site_ledger_caption"]})
        pg.wait_for_timeout(int(SITE_HOLD * 1000))
        ctx.close()
        b.close()
        webm = next(Path(td).glob("*.webm"))
        out.mkdir(parents=True, exist_ok=True)
        mp4 = out / "delphi-90s-captioned.mp4"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(webm), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "27", "-an", "-movflags", "+faststart", str(mp4)], check=True)
    srv.shutdown()
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(mp4)], capture_output=True, text=True, check=True).stdout)
    size = mp4.stat().st_size
    ok = 60 <= dur <= 95 and size <= 20 * 1024 * 1024 and not errors
    manifest = {
        "recorded_seattle": seattle(), "kind": "silent captioned screen recording of the built deck and the landing page's ledger section; no audio, no generated imagery",
        "source": {"git_head": git("rev-parse", "HEAD"), "git_branch": git("rev-parse", "--abbrev-ref", "HEAD"),
                   "git_dirty_paths": status("presentation/delphi", "site/delphi"),
                   "deck_html_sha256": sha256(deck), "site_delphi_tree_sha256": tree_hash(site / "delphi"), "captions_sha256": sha256(HERE / "captions.json")},
        "video": {"file": mp4.name, "sha256": sha256(mp4), "bytes": size, "duration_s": round(dur, 2), "resolution": f"{W}x{H}", "audio": "none"},
        "scenes": log, "page_errors": errors, "ok": ok,
        "note": "Re-record after every rebuild: the manifest pins the source HEAD, and the deck/site hashes change when numbers change.",
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print(json.dumps({k: manifest["video"][k] for k in ("duration_s", "bytes", "sha256")}, indent=1), "ok" if ok else "FAILED", errors[:3])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
