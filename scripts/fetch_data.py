#!/usr/bin/env python3
"""Reproducibly acquire the three TrpB source tables from the CaltechDATA archive.

The archive member data.zip is 3.3 GB; we read its central directory and the three
needed members by HTTP range requests (no full download), verify SHA256 against
data/manifest.json, and cache under data/raw/ (git-ignored).

    python scripts/fetch_data.py                 # fetch from CaltechDATA
    python scripts/fetch_data.py --from-dir DIR  # copy+verify from an existing cache
    python scripts/fetch_data.py --write-manifest  # (re)write manifest from fetched files

Never trains on anything: this script only acquires and hashes bytes.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import io
import json
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
MANIFEST = ROOT / "data" / "manifest.json"

RECORD = "https://data.caltech.edu/records/h5rah-5z170"
DOI = "https://doi.org/10.22002/h5rah-5z170"
ZIP_URL = RECORD + "/files/data.zip?download=1"
ZIP_MD5 = "210f5d23474cf9661bd61504735db475"  # from the CaltechDATA record API
ZIP_SIZE = 3321330601

MEMBERS = {
    "simplified_AA.csv": "data/figure_data/4-site_merged_replicates/20230827/four-site_simplified_AA_data.csv",
    "summary_AA.csv": "data/figure_data/4-site_merged_replicates/20230827/four-site_summary_AA_data.csv",
    "KNN_imputed_TrpB.csv": "data/figure_data/4-site_imputed/20230828_KNN_imputed_TrpB.csv",
}
UA = {"User-Agent": "delphi-evolve-fetch/0.1 (+https://github.com/kganjam/delphi-evolve)"}


class RangeFile(io.RawIOBase):
    """Seekable read-only file over an HTTP URL using Range requests.
    The CaltechDATA URL 302-redirects to a short-lived presigned URL, so we
    re-resolve through the stable URL on every request."""

    def __init__(self, url: str, size: int):
        self.url, self.size, self.pos = url, size, 0
        self.requests = 0
        self.bytes = 0

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, off, whence=0):
        self.pos = {0: off, 1: self.pos + off, 2: self.size + off}[whence]
        return self.pos

    def readinto(self, b):
        n = min(len(b), self.size - self.pos)
        if n <= 0:
            return 0
        req = urllib.request.Request(self.url, headers={**UA, "Range": f"bytes={self.pos}-{self.pos + n - 1}"})
        with urllib.request.urlopen(req, timeout=120) as r:
            data = r.read()
        self.requests += 1
        self.bytes += len(data)
        b[: len(data)] = data
        self.pos += len(data)
        return len(data)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest():
    return json.loads(MANIFEST.read_text()) if MANIFEST.exists() else None


def fetch_remote() -> dict:
    rf = RangeFile(ZIP_URL, ZIP_SIZE)
    buf = io.BufferedReader(rf, buffer_size=1 << 20)
    info = {}
    with zipfile.ZipFile(buf) as z:
        for local, member in MEMBERS.items():
            zi = z.getinfo(member)
            with z.open(zi) as src:
                data = src.read()
            (RAW / local).write_bytes(data)
            info[local] = {"zip_member": member, "zip_member_compressed_size": zi.compress_size, "bytes": len(data)}
    return {"http_range_requests": rf.requests, "http_bytes_transferred": rf.bytes, "members": info}


def verify(manifest) -> list[str]:
    problems = []
    for name, meta in manifest["files"].items():
        p = RAW / name
        if not p.exists():
            problems.append(f"missing {name}")
        elif sha256(p) != meta["sha256"]:
            problems.append(f"sha256 mismatch {name}")
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-dir", type=Path)
    ap.add_argument("--write-manifest", action="store_true", help="write data/manifest.json from files in data/raw (first-time provenance)")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()
    transfer = None
    if a.from_dir:
        for name in MEMBERS:
            shutil.copyfile(a.from_dir / name, RAW / name)
        transfer = {"copied_from": str(a.from_dir)}
    elif a.force or not all((RAW / n).exists() for n in MEMBERS):
        transfer = fetch_remote()
    if a.write_manifest or manifest is None:
        files = {n: {"sha256": sha256(RAW / n), "bytes": (RAW / n).stat().st_size, **(transfer or {}).get("members", {}).get(n, {"zip_member": MEMBERS[n]})} for n in MEMBERS}
        manifest = {
            "dataset": "Johnston et al. TrpB four-site combinatorial landscape",
            "paper_doi": "10.1073/pnas.2400439121",
            "record_url": RECORD, "doi_url": DOI, "license": "CC0 1.0 (CaltechDATA record rights, spdx cc0-1.0)",
            "archive": {"file": "data.zip", "url": ZIP_URL, "size": ZIP_SIZE, "md5_from_record_api": ZIP_MD5},
            "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "files": files,
        }
        MANIFEST.write_text(json.dumps(manifest, indent=1) + "\n")
        print("wrote", MANIFEST)
    problems = verify(manifest)
    print(json.dumps({"transfer": transfer, "problems": problems}, indent=1))
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
