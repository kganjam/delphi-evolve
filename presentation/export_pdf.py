#!/usr/bin/env python3
"""Export deck HTML -> PDF (one 1280x720 page per slide) and per-slide PNG screenshots via Playwright/Chromium.

    python3 presentation/export_pdf.py presentation/deck.html [--shots DIR]
Reports PDF page count (must be 6).  Local file URL only; no network.
"""
import argparse
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("html")
    ap.add_argument("--shots", default=None)
    a = ap.parse_args()
    src = Path(a.html).resolve()
    pdf = src.with_suffix(".pdf")
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--disable-dev-shm-usage"])
        pg = b.new_page(viewport={"width": 1280, "height": 720})
        errs = []
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(src.as_uri())
        if a.shots:
            d = Path(a.shots); d.mkdir(parents=True, exist_ok=True)
            for i in range(1, 7):
                pg.goto(src.as_uri() + f"#{i}")
                pg.reload()
                pg.wait_for_timeout(150)
                pg.screenshot(path=str(d / f"{src.stem}-slide{i}.png"))
        pg.emulate_media(media="print")
        pg.goto(src.as_uri())
        pg.pdf(path=str(pdf), width="1280px", height="720px", print_background=True, prefer_css_page_size=True)
        b.close()
    from pypdf import PdfReader
    n = len(PdfReader(str(pdf)).pages)
    print(f"{pdf} pages={n} console_errors={errs}")
    return 0 if n == 6 and not errs else 1


if __name__ == "__main__":
    sys.exit(main())
