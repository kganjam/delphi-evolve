#!/usr/bin/env python3
"""List / extract members of a remote ZIP by HTTP range requests (no full download).

Used to fetch the TrpB reference-sequence evidence from the CaltechDATA record
h5rah-5z170 (CC0 1.0) without pulling the 3.3 GB data.zip.  Uses curl because
Python's urllib receives HTTP 403 from the host.

  zip_range.py list    <record> <zipname> [substring]
  zip_range.py extract <record> <zipname> <member> <out>
"""
import struct
import subprocess
import sys
import zlib


def url(record, name):
    return f"https://data.caltech.edu/api/records/{record}/files/{name}/content"


def rng(u, a, b):
    return subprocess.check_output(["curl", "-sSL", "-r", f"{a}-{b}", u], timeout=300)


def size(u):
    out = subprocess.check_output(["curl", "-sSL", "-r", "0-0", "-D", "-", "-o", "/dev/null", u], timeout=60).decode()
    for line in out.splitlines():
        if line.lower().startswith("content-range"):
            return int(line.split("/")[-1])
    raise RuntimeError("no content-range")


def central_directory(u):
    n = size(u)
    tail = rng(u, max(0, n - 70000), n - 1)
    i = tail.rfind(b"PK\x05\x06")
    eocd = tail[i:i + 22]
    _, _, _, nent, _, cdsize, cdoff, _ = struct.unpack("<IHHHHIIH", eocd)
    if cdoff == 0xFFFFFFFF or nent == 0xFFFF:
        j = tail.rfind(b"PK\x06\x06")
        z = tail[j:j + 56]
        nent, = struct.unpack("<Q", z[32:40])
        cdsize, cdoff = struct.unpack("<QQ", z[40:56])
    cd = rng(u, cdoff, cdoff + cdsize - 1)
    ents, p = [], 0
    while p < len(cd) and cd[p:p + 4] == b"PK\x01\x02":
        (_, _, _, _, method, _, _, _, csz, usz, fnl, exl, cml, _, _, _, lho) = struct.unpack(
            "<IHHHHHHIIIHHHHHII", cd[p:p + 46])
        name = cd[p + 46:p + 46 + fnl].decode("utf8", "replace")
        extra = cd[p + 46 + fnl:p + 46 + fnl + exl]
        q = 0
        while q + 4 <= len(extra):
            tid, tsz = struct.unpack("<HH", extra[q:q + 4])
            if tid == 1:
                f = extra[q + 4:q + 4 + tsz]
                k = 0
                if usz == 0xFFFFFFFF:
                    usz, = struct.unpack("<Q", f[k:k + 8]); k += 8
                if csz == 0xFFFFFFFF:
                    csz, = struct.unpack("<Q", f[k:k + 8]); k += 8
                if lho == 0xFFFFFFFF:
                    lho, = struct.unpack("<Q", f[k:k + 8]); k += 8
            q += 4 + tsz
        ents.append(dict(name=name, method=method, csize=csz, usize=usz, offset=lho))
        p += 46 + fnl + exl + cml
    return ents


def extract(u, e, out):
    h = rng(u, e["offset"], e["offset"] + 29 + 1024)
    fnl, exl = struct.unpack("<HH", h[26:30])
    st = e["offset"] + 30 + fnl + exl
    d = rng(u, st, st + e["csize"] - 1)
    data = zlib.decompress(d, -15) if e["method"] == 8 else d
    open(out, "wb").write(data)
    return len(data)


if __name__ == "__main__":
    cmd, record, zname = sys.argv[1:4]
    u = url(record, zname)
    ents = central_directory(u)
    if cmd == "list":
        sub = sys.argv[4] if len(sys.argv) > 4 else ""
        for e in ents:
            if sub.lower() in e["name"].lower():
                print(e["usize"], e["name"])
    else:
        member, out = sys.argv[4:6]
        e = next(x for x in ents if x["name"] == member)
        print(extract(u, e, out), "bytes ->", out)
