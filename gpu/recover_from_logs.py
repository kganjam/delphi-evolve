#!/usr/bin/env python3
"""Rebuild RESULT_FILE blobs and RESULT_JSON objects from a Nebius job log.

  nebius --profile hackathon ai job logs <aijob-id> > job.log
  python3 recover_from_logs.py job.log OUTDIR

Every chunk carries a 12-hex SHA-256 prefix and every file a full SHA-256; any
mismatch, missing or duplicated-but-different chunk aborts with a non-zero exit.
Log lines may be prefixed by a timestamp or stream marker; the parser keys on the
RESULT_* token.
"""
import base64
import hashlib
import json
import re
import sys
from pathlib import Path

TOK = re.compile(r"(RESULT_FILE|RESULT_CHUNK|RESULT_END|RESULT_JSON)\s(.*)$")


def recover(text, outdir):
    files, chunks, jsons = {}, {}, {}
    for line in text.splitlines():
        m = TOK.search(line)
        if not m:
            continue
        kind, rest = m.groups()
        rest = rest.strip()
        if kind == "RESULT_FILE":
            meta = json.loads(rest)
            files[meta["name"]] = meta
        elif kind == "RESULT_CHUNK":
            name, i, n, h, part = rest.split(" ", 4)
            part = part.strip()
            if hashlib.sha256(part.encode()).hexdigest()[:12] != h:
                raise ValueError(f"chunk checksum mismatch {name} {i}")
            prev = chunks.setdefault(name, {}).get(int(i))
            if prev is not None and prev != part:
                raise ValueError(f"conflicting duplicate chunk {name} {i}")
            chunks[name][int(i)] = part
        elif kind == "RESULT_JSON":
            name, payload = rest.split(" ", 1)
            jsons[name] = json.loads(payload)
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    written = {}
    for name, meta in files.items():
        got = chunks.get(name, {})
        missing = [i for i in range(meta["chunks"]) if i not in got]
        if missing:
            raise ValueError(f"{name}: missing chunks {missing[:5]}... ({len(missing)} of {meta['chunks']})")
        raw = base64.b64decode("".join(got[i] for i in range(meta["chunks"])))
        if len(raw) != meta["bytes"] or hashlib.sha256(raw).hexdigest() != meta["sha256"]:
            raise ValueError(f"{name}: assembled size/sha256 mismatch")
        (out / name).write_bytes(raw)
        written[name] = {"bytes": len(raw), "sha256": meta["sha256"]}
    for name, obj in jsons.items():
        (out / f"{name}.json").write_text(json.dumps(obj, indent=1))
    return written, sorted(jsons)


if __name__ == "__main__":
    w, j = recover(Path(sys.argv[1]).read_text(errors="replace"), sys.argv[2])
    print(json.dumps({"files": w, "json": j}, indent=1))
