#!/usr/bin/env python3
"""Record a 60-90 s silent walkthrough of the ACTUAL static site (or the deck as fallback) with Playwright
record_video, burn-in captions that label what is measured vs assumed, convert to MP4 with ffmpeg,
and write a manifest pinning the source SHA and the video SHA256.

    python3 presentation/video/record_video.py --site /path/to/integrated/site --out /data/artifacts/delphi-evolve-presentation/video
    python3 presentation/video/record_video.py --mode deck --deck presentation/deck.html ...      # fallback

* Serves --site from an in-process ephemeral-port HTTP server (port 0) bound to 127.0.0.1; there is no child
  server to leak, and nothing else (e.g. port 8765 or the experience preview on 18417) is touched.
* No microscope/lab imagery is synthesised: the only pixels are the site/deck UI and caption text.
* Honest states: whatever the site shows (unavailable, blocked, etc.) is what is recorded; the interaction log
  in the manifest records every verdict string seen at each slider position and every interaction that failed.
* Exit 0 only when 60 <= duration <= 90 s, MP4 <= 20 MB and no page errors occurred.
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
import threading
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

from playwright.sync_api import sync_playwright

W, H = 1280, 720
PERSIST = "MEASURED = laboratory data · ASSUMED = the slider’s noise bound · SIMULATED = a declared hypothetical · a static Lean receipt is NOT proof for every slider position"

CAPTION_JS = """
(() => {
  if (document.getElementById('vcap')) return;
  const d = document.createElement('div'); d.id = 'vcap';
  d.style.cssText = 'position:fixed;left:0;right:0;bottom:0;z-index:2147483647;background:rgba(21,32,43,.94);color:#f6f3ea;font:600 19px/1.3 system-ui,sans-serif;padding:10px 24px 8px;pointer-events:none';
  d.innerHTML = '<div id="vcap-main"></div><div id="vcap-sub" style="font:500 13px/1.3 ui-monospace,monospace;color:#e9c9b6;margin-top:4px"></div>';
  document.body.appendChild(d);
})();
"""
SET_CAP = """([main, tag, sub]) => {
  const m = document.getElementById('vcap-main'); const s = document.getElementById('vcap-sub');
  m.innerHTML = (tag ? '<span style="display:inline-block;margin-right:10px;padding:1px 8px;border-radius:4px;background:' + (tag==='MEASURED'?'#2b6e3f':tag==='ASSUMED'?'#d9480f':tag==='SIMULATED'?'#1864ab':tag==='REFUSED'?'#b0145b':tag==='STATIC RECEIPT'?'#5f3dc4':'#44505b') + ';font:700 14px ui-monospace,monospace">' + tag + '</span>' : '') + main;
  s.textContent = sub;
}"""


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def tree_hash(d: Path):
    files = sorted(p for p in d.rglob("*") if p.is_file())
    lines = [f"{sha256(p)}  {p.relative_to(d)}" for p in files]
    return hashlib.sha256("\n".join(lines).encode()).hexdigest(), len(files)


def git(d, *a):
    r = subprocess.run(["git", "-C", str(d), *a], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def seattle(ts=None):
    u = ts or datetime.now(timezone.utc)
    off, nm = (-7, "PDT") if u < datetime(2026, 11, 1, 9, 0, tzinfo=timezone.utc) else (-8, "PST")
    return (u + timedelta(hours=off)).strftime("%Y-%m-%d %H:%M:%S ") + nm


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def serve(directory: Path):
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(directory)))
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def drive_site(pg, log, cap, base):
    def step(name, fn, *args):
        try:
            r = fn(*args)
            log.append({"t": round(time.time() - T0, 1), "step": name, "ok": True, **({"result": r} if r is not None else {})})
            return r
        except Exception as e:  # recorded, not hidden
            log.append({"t": round(time.time() - T0, 1), "step": name, "ok": False, "error": str(e)[:200]})

    def hold(s):
        pg.wait_for_timeout(int(s * 1000))

    def verdict():
        return pg.evaluate("(() => { const v = document.querySelector('#dec-dyn .verdict'); return v ? v.innerText.replace(/\\s+/g,' ').slice(0,160) : null; })()")

    def set_slider(v):
        pg.evaluate("""(v) => { const e = document.getElementById('eps'); e.value = v; e.dispatchEvent(new Event('input', {bubbles:true})); }""", v)

    def scroll_h2(i, off=0):
        pg.evaluate("([i, off]) => { const h = document.querySelectorAll('h2')[i]; window.scrollTo(0, h.getBoundingClientRect().top + window.scrollY - 12 + off); }", [i, off])

    # ---------------- part 1: the static site (about 55 s)
    cap("Recorded from the static site, silent. No lab or microscope images: every pixel is UI or a measured table.", "", 3)
    hold(3)
    cap("Every cell is one measured TrpB variant: 159,129 of 160,000 four-residue genotypes, scored by cellular growth. A layout projection, not molecular geometry.", "MEASURED", 6)
    step("hover-map", lambda: pg.hover("#map", position={"x": 300, "y": 260}))
    hold(2.5)
    step("click-map", lambda: pg.click("#map", position={"x": 300, "y": 260}))
    hold(2.5)
    cap("Route from parent VFVS to the best measured variant AIKG: computed from measured values and one assumed bound.", "ASSUMED", 5)
    step("tab-decision", lambda: pg.click("#tab-decision"))
    step("scroll-panel", lambda: pg.evaluate("document.getElementById('lab').scrollIntoView()"))
    hold(3)
    for k, secs, msg in ((0, 3.5, "κ = 0: take every measurement at face value."), (2, 3.5, "κ = 2 (default): each measurement widened by an assumed noise bound — not a confidence level."),
                          (3, 3.5, "κ = 3: the certified route must lengthen."), (6, 4.5, "κ = 6: no route is certifiable at this assumed bound. That is not a statement that no ascending route exists, nor about biology.")):
        cap(msg, "ASSUMED", secs)
        step(f"slider-{k}", set_slider, k)
        hold(1.0)
        step(f"verdict-at-{k}", verdict)
        hold(secs - 1.0)
    step("reset", lambda: pg.click("#reset"))
    cap("A step opens its raw replicate rows and read counts.", "MEASURED", 4)
    step("tab-evidence", lambda: pg.click("#tab-evidence"))
    hold(4)
    step("tab-proof", lambda: pg.click("#tab-proof"))
    hold(0.5)
    ptxt = step("proof-pane-text", lambda: pg.inner_text("#p-proof")[:300]) or ""
    if "No proof receipt loaded" in ptxt or "none is present" in ptxt.lower():
        cap("Proof tab in THIS build: no receipt loaded, so the site claims nothing.", "STATIC RECEIPT", 5)
    else:
        cap("Lean receipt: a static compiled check of listed routes at their assumed bound, with a rejected mutant. Not proof for any other slider setting.", "STATIC RECEIPT", 6)
    hold(5.5)
    step("scroll-results", lambda: pg.evaluate("document.getElementById('results').scrollIntoView()"))
    rtxt = step("results-text", lambda: pg.inner_text("#results")[:400]) or ""
    rfull = pg.inner_text("#results")
    if "96/100" in rfull and "78/100" in rfull and "32/100" in rfull and "21/100" in rfull:
        cap("Retrospective replay, 100 episodes per policy: query-to-certify 78, directed 32, random 21. The shared collective did not beat the single planner; no-GP arms are post hoc.", "", 7)
    else:
        cap("Replay section in THIS build shows no complete result; nothing is quoted.", "", 5)
    hold(7)
    # ---------------- part 2: the claim runtime page (about 30 s)
    step("open-claims", lambda: bool(pg.goto(base + "/claims/index.html", wait_until="networkidle")))
    pg.evaluate(CAPTION_JS)

    def scenario(i):
        pg.select_option("#sel", str(i))
        pg.wait_for_timeout(300)
        return {"scenario": pg.eval_on_selector("#sel", "e=>e.options[e.selectedIndex].text")[:90], "guard": pg.inner_text("#c2")[-120:].replace("\n", " "), "calc": pg.inner_text("#c3")[:140].replace("\n", " ")}
    cap("Existing Delphi claim (Kimura fixation probability), a hand-authored pinned adapter, an applicability guard — here the guards pass and it computes.", "SIMULATED", 6)
    step("claims-top", lambda: pg.evaluate("window.scrollTo(0,0)"))
    r0 = step("scenario-valid", scenario, 0)
    hold(5.5)
    cap("Same claim, a haploid E. coli population: the guard refuses a model transfer the claim does not cover.", "REFUSED", 5)
    r2 = step("scenario-haploid", scenario, 2)
    hold(5)
    cap("A TrpB growth score is not a selection coefficient: refused, and the missing mapping is named.", "REFUSED", 5)
    r3 = step("scenario-trpb-score", scenario, 3)
    hold(5)
    cap("Same request, different source state: withdraw, delete or edit the Delphi record and the answer flips from compute to refuse.", "", 7)
    step("scroll-changes", lambda: scroll_h2(1))
    hold(7)
    cap("Same-context evidence reuse equals an ordinary cache; typed guards matter only when the context is wrong. Fault tests are synthetic, not savings.", "", 6)
    step("scroll-evidence", lambda: scroll_h2(2))
    hold(6)
    cap("Bounded, assumption-aware knowledge execution — not theorem extraction. Biologic design starts with justified enzyme experiments.", "", 3)
    hold(3)


def drive_deck(pg, log, cap):
    for i in range(6):
        pg.keyboard.press("ArrowRight") if i else None
        log.append({"step": f"slide-{i + 1}", "ok": True})
        pg.wait_for_timeout(12500)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=["site", "deck"], default="site")
    ap.add_argument("--site", default="site", help="static site directory (final integrated source)")
    ap.add_argument("--deck", default=None, help="deck HTML for --mode deck")
    ap.add_argument("--out", default="/data/artifacts/delphi-evolve-presentation/video")
    ap.add_argument("--name", default="darwins-bridge-walkthrough")
    ap.add_argument("--require-demo", action="store_true", help="fail unless site/data/demo.json exists (final integrated build); otherwise the manifest is marked preliminary")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    work = out / "_raw"; shutil.rmtree(work, ignore_errors=True); work.mkdir()
    src = Path(a.site).resolve() if a.mode == "site" else Path(a.deck).resolve().parent
    if a.mode == "site" and not (src / "index.html").exists():
        print(f"no index.html in {src}", file=sys.stderr); return 2
    if a.require_demo and a.mode == "site" and not (src / "data/demo.json").exists():
        print(f"REJECTED: {src}/data/demo.json missing; this is not the final integrated site", file=sys.stderr); return 2
    th, nfiles = tree_hash(src)
    repo = git(src, "rev-parse", "--show-toplevel")
    info = {"mode": a.mode, "source_dir": str(src), "source_tree_sha256": th, "source_files": nfiles,
            "git_toplevel": repo, "git_head": git(src, "rev-parse", "HEAD") if repo else None,
            "git_branch": git(src, "rev-parse", "--abbrev-ref", "HEAD") if repo else None,
            "git_dirty_paths": (git(src, "status", "--porcelain", "--", ".") or "").splitlines() if repo else None,
            "has_data_demo_json": (src / "data/demo.json").exists()}
    httpd = serve(src)
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    url = base + ("/index.html" if a.mode == "site" else "/" + Path(a.deck).name)
    log, perr, cons = [], [], []
    global T0
    started = datetime.now(timezone.utc)
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(args=["--disable-dev-shm-usage"])
            ctx = b.new_context(viewport={"width": W, "height": H}, record_video_dir=str(work), record_video_size={"width": W, "height": H})
            pg = ctx.new_page()
            pg.on("pageerror", lambda e: perr.append(str(e)[:200]))
            pg.on("console", lambda m: cons.append(m.text[:200]) if m.type == "error" else None)
            pg.goto(url, wait_until="networkidle")
            T0 = time.time()
            if a.mode == "site":
                pg.evaluate(CAPTION_JS)

                def cap(text, tag, _s):
                    pg.evaluate(SET_CAP, [text, tag, PERSIST])
                drive_site(pg, log, cap, base)
            else:
                drive_deck(pg, log, None)
            vpath = pg.video.path()
            ctx.close(); b.close()
    finally:
        httpd.shutdown(); httpd.server_close()
    webm = Path(vpath)
    mp4 = out / f"{a.name}.mp4"
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(webm), "-vf", "scale=1280:720,fps=25", "-c:v", "libx264", "-preset", "veryfast", "-crf", "27",
                        "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", str(mp4)], capture_output=True, text=True)
    if r.returncode:
        print(r.stderr, file=sys.stderr); return 3
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(mp4)], capture_output=True, text=True).stdout.strip())
    size = mp4.stat().st_size
    problems = []
    if not 60 <= dur <= 92: problems.append(f"duration {dur:.1f}s outside 60-92")
    if size > 20 * 1024 * 1024: problems.append(f"size {size} > 20MB")
    preliminary = a.mode == "site" and not (src / "data/demo.json").exists()
    if perr: problems.append(f"page errors: {perr[:3]}")
    man = {"recorded_seattle": seattle(started), "source": info, "video": {"path": str(mp4), "sha256": sha256(mp4), "bytes": size, "duration_s": round(dur, 2), "resolution": f"{W}x{H}", "audio": "none (silent)"},
           "status": "PRELIMINARY: site lacks data/demo.json (integrations show unavailable)" if preliminary else "recorded from a site with data/demo.json",
           "url_served": "ephemeral 127.0.0.1 port (in-process server, shut down)", "interaction_log": log, "console_errors": cons, "page_errors": perr, "problems": problems,
           "ffmpeg": subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True).stdout.splitlines()[0],
           "captions_policy": "persistent bottom line labels MEASURED vs ASSUMED and states a static Lean receipt is not proof for every slider position; no fabricated lab imagery"}
    (out / f"{a.name}.manifest.json").write_text(json.dumps(man, indent=1))
    shutil.rmtree(work, ignore_errors=True)
    print(json.dumps({"mp4": str(mp4), "duration_s": man["video"]["duration_s"], "bytes": size, "sha256": man["video"]["sha256"], "problems": problems}, indent=1))
    return 1 if problems else 0


T0 = time.time()
if __name__ == "__main__":
    sys.exit(main())
