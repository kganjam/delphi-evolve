"""EXPLICIT replay of an exported OpenResearch run. This EXECUTES the run's command.

Only use on code you wrote or have read. Requires trust_code=True. Wrap the call in
`systemd-run --user --scope -p MemoryMax=4G -p MemorySwapMax=0 -p TasksMax=128 -p RuntimeMaxSec=600`.

It answers one question with measurements: given ONLY what the record carries (source tarball identified by
digest, plus the command), does a clean re-execution reproduce the result file byte-for-byte, under each
interpreter you name? A mutation control must change the output, or the comparison is not discriminating.
"""
from __future__ import annotations

import os
import shlex
import subprocess
import tarfile
import tempfile

from .common import iso_utc, sha_bytes


def replay(export_dir: str, *, command: str, result_file: str, recorded_sha256: str,
           interpreters: dict[str, str], mutation: tuple[str, str, str] | None = None,
           trust_code: bool = False, timeout: int = 60) -> dict:
    if not trust_code:
        raise PermissionError("replay executes the run's command; pass trust_code=True only for code you have read")
    tar = os.path.join(export_dir, "source.tar")
    results = {}
    for label, interp in interpreters.items():
        with tempfile.TemporaryDirectory() as work, tempfile.TemporaryDirectory() as bindir:
            with tarfile.open(tar) as tf:
                tf.extractall(work, filter="data")                       # no path escapes, no special files
            if mutation:
                path, old, new = mutation
                p = os.path.join(work, path)
                with open(p) as fh:
                    text = fh.read()
                if old not in text:
                    raise ValueError("mutation target not found: the control would be vacuous")
                with open(p, "w") as fh:
                    fh.write(text.replace(old, new, 1))
            os.symlink(interp, os.path.join(bindir, "python3"))
            env = {"PATH": f"{bindir}:/usr/bin:/bin", "HOME": work}       # clean environment: nothing inherited
            proc = subprocess.run(["bash", "-c", command], cwd=work, env=env, capture_output=True, timeout=timeout)
            out = os.path.join(work, result_file)
            digest = None
            if os.path.isfile(out):
                with open(out, "rb") as fh:
                    digest = sha_bytes(fh.read())
            version = subprocess.run([interp, "--version"], capture_output=True, text=True).stdout.strip()
            results[label] = {"interpreter_version": version, "exit": proc.returncode, "result_sha256": digest,
                              "matches_recorded": digest == recorded_sha256}
    return {"performed": True, "at": iso_utc(), "recorded_sha256": recorded_sha256, "mutation_control": bool(mutation),
            "command_run": shlex.split(command)[:6], "results": results,
            "note": "the interpreter and its version are NOT in the OpenResearch record; the replayer chose them"}
