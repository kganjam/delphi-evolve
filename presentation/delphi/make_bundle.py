#!/usr/bin/env python3
"""Build the downloadable static bundle: site/delphi + site/review + presentation/delphi + every committed artifact the deck cites.

    python3 presentation/delphi/make_bundle.py [--out-dir /data/artifacts/delphi-evolve-submit/dist]

* Deterministic: sorted entries, fixed timestamps, so the same inputs give the same zip sha256.
* Inside the zip: BUNDLE-MANIFEST.json (sha256 of every file, source git HEAD), README.txt (how to view and verify).
* Outside: delphi-bundle.zip.sha256 and, in the repository, presentation/delphi/dist/bundle-manifest.json (file list + zip sha256).
* Refuses to bundle files over 8 MB (reports them) and files that do not exist.
Does not publish anything.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MAXB = 8 * 1024 * 1024
FIXED = (2026, 10, 31, 0, 0, 0)
EXCLUDE = ("__pycache__", ".pyc", "/dist/")


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def status(*paths):
    r = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "--", *paths], capture_output=True, text=True)
    return [l[3:] for l in r.stdout.splitlines()]


def git(*a):
    r = subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def collect() -> list[str]:
    files = set()
    for base in ("site/delphi", "site/review", "presentation/delphi", "scopedesk/ledger", "scopedesk/scorecard"):
        for p in (ROOT / base).rglob("*"):
            if p.is_file() and not any(x in str(p) for x in EXCLUDE):
                files.add(str(p.relative_to(ROOT)))
    files |= {"presentation/deck.css", "presentation/deck.js", "presentation/trace_numbers.py", "presentation/export_pdf.py", "presentation/time_script.py",
              "planning/rethink/CLAIM-LEDGER.md", "planning/rethink/PITCH-OUTLINE.md"}
    prov = json.loads((HERE / "deck.provenance.json").read_text())
    files |= set(prov["sha256"])
    nt = json.loads((HERE / "number_trace.json").read_text())
    for t in nt["trace"]:
        files |= set(t["files"])
    return sorted(f for f in files if (ROOT / f).is_file() or f not in files)


README = """Delphi: from candidate laws to checked theorems. Static review bundle (draft).

View:    unzip, then in the unzipped folder run   python3 -m http.server 8000   and open http://localhost:8000/site/delphi/index.html
         (the six-slide deck is presentation/delphi/deck.pdf; deck.html works offline; press n for notes)
Verify:  python3 -c "import json,hashlib; m=json.load(open('BUNDLE-MANIFEST.json')); bad=[f for f,h in m['files'].items() if hashlib.sha256(open(f,'rb').read()).hexdigest()!=h]; print('mismatches:', bad)"
         and compare the zip's own sha256 with delphi-bundle.zip.sha256.

What it is not: not a submission to the organizers (no upload channel and no receipt exist), not a published site, and not a claim that any
named law is wrong. Items marked pending in the deck are not results. The robustness sweep and the repair demo are not in the claim ledger.
Rebuild (from a git checkout): bash presentation/delphi/rebuild.sh
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="/data/artifacts/delphi-evolve-submit/dist")
    a = ap.parse_args()
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    files = collect()
    missing = [f for f in files if not (ROOT / f).is_file()]
    big = [f for f in files if (ROOT / f).is_file() and (ROOT / f).stat().st_size > MAXB]
    if missing or big:
        print("REFUSING", {"missing": missing, "over_8MB": big}, file=sys.stderr)
        return 2
    manifest = {"source_git_head": git("rev-parse", "HEAD"), "source_git_branch": git("rev-parse", "--abbrev-ref", "HEAD"),
                "dirty": status("site", "presentation", "scopedesk", "artifacts"),
                "n_files": len(files), "files": {f: sha(ROOT / f) for f in files}}
    mj = json.dumps(manifest, indent=1, sort_keys=True) + "\n"
    zp = out / "delphi-bundle.zip"
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        def add(name, data):
            zi = zipfile.ZipInfo(name, FIXED)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            z.writestr(zi, data)
        add("README.txt", README)
        add("BUNDLE-MANIFEST.json", mj)
        for f in files:
            add(f, (ROOT / f).read_bytes())
    zsha = sha(zp)
    (out / "delphi-bundle.zip.sha256").write_text(f"{zsha}  delphi-bundle.zip\n")
    d = HERE / "dist"
    d.mkdir(exist_ok=True)
    (d / "bundle-manifest.json").write_text(json.dumps({"zip": "delphi-bundle.zip", "zip_sha256": zsha, "zip_bytes": zp.stat().st_size, "zip_location": str(zp),
                                                         **{k: manifest[k] for k in ("source_git_head", "source_git_branch", "dirty", "n_files")}, "files": manifest["files"]}, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"zip": str(zp), "sha256": zsha, "bytes": zp.stat().st_size, "n_files": len(files), "dirty": manifest["dirty"]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
