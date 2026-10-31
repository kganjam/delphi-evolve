#!/usr/bin/env python3
"""Package the checked static demo and pitch without raw data, secrets or host caches.

Run after rebuilding presentation/ and scripts/assemble_demo.py, from a clean commit.
The ZIP is an offline-capable static site; serve it with python -m http.server.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def package(destination: Path) -> dict:
    def git(*args):
        return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()

    if git("status", "--porcelain"):
        raise SystemExit("Refusing to package a dirty source checkout; commit reviewed work first.")
    files = {p.removeprefix("site/"): ROOT / p for p in git("ls-files", "site").splitlines()}
    for name in ("deck.html", "deck.pdf", "speaker-notes.md", "appendix.md", "deck.provenance.json",
                 "video/darwins-bridge-walkthrough.mp4", "video/manifests/final.manifest.json"):
        p = ROOT / "presentation" / name
        if not p.is_file():
            raise SystemExit(f"Missing required presentation artifact: {p}")
        files[f"presentation/{name}"] = p
    for name in ("HANDOFF.md", "README.md", "LICENSE", "NOTICE", "docs/blog.md", "docs/company-hypothesis.md"):
        files[name] = ROOT / name
    # All local HTML references to shipped pitch assets must resolve in the archive.
    for name in ("presentation/deck.html", "presentation/deck.pdf", "presentation/video/darwins-bridge-walkthrough.mp4"):
        if name not in files:
            raise SystemExit(f"Missing linked artifact {name}")
    hashes = {name: hashlib.sha256(p.read_bytes()).hexdigest() for name, p in sorted(files.items())}
    manifest = {"source_commit": git("rev-parse", "HEAD"), "repository": "https://github.com/kganjam/delphi-evolve",
                "files_sha256": hashes,
                "start": "Extract, run python -m http.server 8000, open http://localhost:8000. PDF and video also work directly.",
                "scope": "Recorded prototype and measured-data replay; no new wet-lab observations. See HANDOFF.md."}
    destination = destination.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise SystemExit(f"Refusing to overwrite an existing bundle: {destination}")
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, p in sorted(files.items()):
            archive.write(p, name)
        archive.writestr("BUNDLE-MANIFEST.json", json.dumps(manifest, indent=2) + "\n")
    with zipfile.ZipFile(destination) as archive:
        if archive.testzip() is not None:
            raise SystemExit("Archive integrity check failed")
        for name, expected in hashes.items():
            if hashlib.sha256(archive.read(name)).hexdigest() != expected:
                raise SystemExit(f"Archive bytes differ from source: {name}")
    return {"archive": str(destination), "bytes": destination.stat().st_size,
            "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
            "source_commit": manifest["source_commit"], "files": len(files), "integrity_checked": True}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(package(args.out), indent=2))
