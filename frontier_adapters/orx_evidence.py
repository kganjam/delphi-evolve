"""OpenResearch (`orx`) run -> Frontier Evidence draft.

Read-only. This adapter NEVER executes anything from a run; replay is a separate, explicit script
(`orx_replay.py`) that needs a flag and is meant for code you wrote.

A run is accepted as the subject of an Evidence record only if ALL of these hold (each is a control with
a failing test):
  * status is "done" AND the run directory's exit_code file is 0   (the DB exit_code column is NULL for a
    successful local run in orx 0.2.23, so the file is the only witness)
  * the source tarball's sha256 equals the digest orx recorded       (code identity is checked, not trusted)
  * the named result file exists in the run directory                 (we hash it ourselves)
  * the evidence kind is "simulated" or "predicted"                   (a computational run is never "observed";
    "formal" needs a proof checker and "source_assessment" is not a run)

Every Evidence field carries its ORIGIN in provenance.field_origin: "orx" (read from the run record),
"adapter" (computed here), "author" (declared by whoever ran it), or "absent" (nobody can fill it).
What OpenResearch cannot supply is therefore visible in the record, not implied.
"""
from __future__ import annotations

import json
import os
import re
import tarfile
import urllib.request

from .common import iso_utc, sha_bytes, sha_obj

ADAPTER_ID = "frontier_adapters.orx_evidence"
ADAPTER_VERSION = "0.1.0"
ALLOWED_KINDS = ("simulated", "predicted")
OPENRESEARCH_PIN = "alphaXiv/OpenResearch@703fd4bba66311625cf7e0b0776a0f949d3f4c73"  # source read for this adapter

# Always-true limitations of an orx run record (read from the pinned source and observed on orx 0.2.23).
MECHANICAL_LIMITATIONS = [
    "OpenResearch does not record the execution environment (interpreter, OS, packages, hardware); local runs use "
    "the host's own environment and container images are mutable tags, so the record alone does not say how to "
    "reproduce the environment.",
    "Inputs outside the committed git snapshot and any random seeds are not recorded; only the command string and "
    "the committed code are.",
    "OpenResearch does not hash or register run outputs; the content digest in this record was computed by the "
    "adapter from a mutable local run directory at retrieval time.",
    "Run, experiment and project ids are random UUIDs local to one machine's store: there is no shared registry, "
    "and the run can be deleted by its owner (`orx exp delete`).",
    "A run reaching status 'done' means the process exited 0. It says nothing about scientific validity and has "
    "not been reviewed.",
    "The database exit_code was NULL for this local run; the exit code was read from the run directory's exit_code "
    "file instead.",
]


class Refused(ValueError):
    """The run cannot be the subject of an Evidence record. The message names the control that failed."""


def _rb(path):
    with open(path, "rb") as fh:
        return fh.read()


def _jl(path):
    with open(path) as fh:
        return json.load(fh)


def _get(url: str):
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.load(r)


def read_run(*, run_id: str, api: str | None = None, export_dir: str | None = None, result_file: str) -> dict:
    """Collect and VERIFY the facts about one run, from a live `orx up/serve` API or an export directory."""
    if bool(api) == bool(export_dir):
        raise ValueError("give exactly one of api= or export_dir=")
    if api:
        run = _get(f"{api}/api/runs/{run_id}")["run"]
        health = _get(f"{api}/api/health")
        base = run["backend"].get("jobId")            # local path; read, never emitted
        tar_path = run["backend"].get("sourcePath")
    else:
        run = _jl(os.path.join(export_dir, "run.json"))["run"]
        health = _jl(os.path.join(export_dir, "health.json"))
        base, tar_path = export_dir, os.path.join(export_dir, "source.tar")
    be = run["backend"]
    if run["status"] != "done":
        raise Refused(f"run status is {run['status']!r}, not 'done': a run that did not complete is not evidence")
    def read(name, sub=""):
        p = os.path.join(base, sub, name) if sub else os.path.join(base, name)
        return _rb(p) if os.path.isfile(p) else None
    exit_raw = read("exit_code")
    if exit_raw is None or exit_raw.strip() != b"0":
        raise Refused(f"exit_code file is {exit_raw!r}: only an exit code of 0 is accepted")
    if not tar_path or not os.path.isfile(tar_path):
        raise Refused("source tarball is not available, so code identity cannot be checked")
    tar_bytes = _rb(tar_path)
    if sha_bytes(tar_bytes) != be.get("sourceDigest"):
        raise Refused("source tarball sha256 does not match the digest orx recorded: the snapshot was altered")
    with tarfile.open(tar_path) as tf:
        tracked = sorted(m.name for m in tf.getmembers() if m.isfile())
    out_sub = "outputs" if export_dir else "repo"
    result = read(result_file, out_sub)
    if result is None:
        raise Refused(f"result file {result_file!r} not found in the run directory")
    outputs = []
    if export_dir:
        names = sorted(os.listdir(os.path.join(base, "outputs")))
    else:
        names = sorted(os.listdir(os.path.join(base, "repo")))
    for n in names:
        if n not in tracked:                                           # produced by the run, not in the snapshot
            b = read(n, out_sub)
            outputs.append({"path": n, "sha256": sha_bytes(b), "bytes": len(b)})
    log = read("log") or b""
    return {
        "run_id": run["id"], "experiment_id": run["experimentId"], "project_id": run["projectId"],
        "status": run["status"], "command": run["command"], "commit_sha": run.get("commitSha"),
        "created_ms": run["createdAt"], "ended_ms": run.get("endedAt"),
        "backend_kind": be.get("kind"), "source_tar_sha256": be["sourceDigest"], "source_tar_bytes": be.get("sourceSize"),
        "source_files": tracked, "exit_code_file": 0, "db_exit_code": run.get("exitCode"),
        "orx_version": health.get("version"), "result_file": result_file, "result_sha256": sha_bytes(result),
        "outputs": outputs, "log_sha256": sha_bytes(log), "log_bytes": len(log),
    }


def export_run(*, api: str, run_id: str, out_dir: str) -> str:
    """Write a portable, path-scrubbed export (run.json, health.json, exit_code, log, outputs/, source.tar)."""
    run = _get(f"{api}/api/runs/{run_id}")
    health = _get(f"{api}/api/health")
    be = run["run"]["backend"]
    os.makedirs(os.path.join(out_dir, "outputs"), exist_ok=True)
    src = be["jobId"]
    with tarfile.open(be["sourcePath"]) as tf:
        tracked = {m.name for m in tf.getmembers() if m.isfile()}
    for name in ("exit_code", "log"):
        with open(os.path.join(out_dir, name), "wb") as fh:
            fh.write(_rb(os.path.join(src, name)))
    for n in os.listdir(os.path.join(src, "repo")):
        p = os.path.join(src, "repo", n)
        if n not in tracked and os.path.isfile(p):
            with open(os.path.join(out_dir, "outputs", n), "wb") as fh:
                fh.write(_rb(p))
    with open(os.path.join(out_dir, "source.tar"), "wb") as fh:
        fh.write(_rb(be["sourcePath"]))
    for k in ("jobId", "sourcePath"):                                   # local absolute paths do not travel
        be[k] = "<local path withheld>"
    for name, obj in (("run.json", run), ("health.json", health)):
        with open(os.path.join(out_dir, name), "w") as fh:
            json.dump(obj, fh, indent=2, sort_keys=True)
    return out_dir


def to_evidence_draft(facts: dict, *, target: dict, author: dict, namespace: str = "node-a",
                      issuer: str = "importer", kind: str = "simulated", replay: dict | None = None,
                      evidence_id: str | None = None, visibility: str = "public") -> dict:
    """Build a PROPOSED Evidence draft. `target` is an exact Ref {namespace, kind, id, version}.

    `author` is the run author's own declaration: {assumptions, limitations, uncertainty, source_dependence,
    method, context}. Whatever the author leaves out is recorded as absent, never filled in.
    """
    if kind not in ALLOWED_KINDS:
        raise Refused(f"evidence_kind {kind!r} refused: a computational run may be 'simulated' or 'predicted' only")
    if set(target) != {"namespace", "kind", "id", "version"} or not re.fullmatch(r"[0-9a-f]{64}", target["version"]):
        raise Refused("target must be an exact Ref with a 64-hex version digest")
    f = facts
    origin = {}
    def put(field, value, who):
        origin[field] = who
        return value

    method = author.get("method") or (
        f"Local OpenResearch run (backend {f['backend_kind']}) of the command `{f['command']}` on the code snapshot "
        f"git:{f['commit_sha']} (source tar sha256 {f['source_tar_sha256']}). The method description is the run's own command, not an "
        "author-written protocol.")
    context = author.get("context") or "No context was declared by the run author; OpenResearch stores only a title and description."
    undeclared = "Not declared by the run author; OpenResearch records no uncertainty."
    payload = {
        "target": put("target", target, "author"),
        "evidence_kind": put("evidence_kind", kind, "author"),
        "source": put("source", {
            "uri": None,                                                           # nothing resolvable by others
            "locator": f"orx-run:{f['run_id']}/{f['result_file']}",
            "source_version": f"git:{f['commit_sha']}; source-tar-sha256:{f['source_tar_sha256']}",
            "content_sha256": f["result_sha256"], "content_available": False,       # no licence stated => digest only
            "access": ("Local-only: held in the producing machine's OpenResearch store; not published or served. "
                       "Only the digest of the result file is carried. OpenResearch (MIT) licenses its software, not "
                       "the content of a user's runs, so no licence for this content is stated."),
            "license": None}, "adapter+orx"),
        "created_time": put("created_time", {"value": iso_utc(f["ended_ms"]), "basis": "witnessed"}, "orx"),
        "retrieved_time": put("retrieved_time", {"value": iso_utc(), "basis": "witnessed"}, "adapter"),
        "method": put("method", method, "author" if author.get("method") else "orx"),
        "context": put("context", context, "author" if author.get("context") else "absent"),
        "assumptions": put("assumptions", list(author.get("assumptions") or []), "author" if author.get("assumptions") else "absent"),
        "provenance": put("provenance", {
            "system": "alphaXiv/OpenResearch orx", "orx_version": f["orx_version"], "openresearch_source_read": OPENRESEARCH_PIN,
            "run_id": f["run_id"], "experiment_id": f["experiment_id"], "project_id": f["project_id"],
            "commit_sha": f["commit_sha"], "source_tar_sha256": f["source_tar_sha256"], "command": f["command"],
            "backend_kind": f["backend_kind"], "status": f["status"], "exit_code_file": f["exit_code_file"],
            "db_exit_code": f["db_exit_code"], "outputs": f["outputs"], "log_sha256": f["log_sha256"],
            "time_witness": "ended_at is the local orx supervisor's clock on the producing machine; uncorroborated",
            "replay": replay or {"performed": False},
            "field_origin": origin,
            "adapter": {"id": ADAPTER_ID, "version": ADAPTER_VERSION}}, "adapter+orx"),
        "source_dependence": put("source_dependence", author.get("source_dependence") or {"declared": False}, "author" if author.get("source_dependence") else "absent"),
        "uncertainty": put("uncertainty", author.get("uncertainty") or undeclared, "author" if author.get("uncertainty") else "absent"),
        "limitations": put("limitations", MECHANICAL_LIMITATIONS + list(author.get("limitations") or []), "adapter+author"),
        "local_id": put("local_id", f["run_id"], "orx"),
        "provider_assessment": put("provider_assessment", None, "absent"),
    }
    payload["provenance"]["field_origin"] = origin
    eid = evidence_id or f"orx-run-{f['run_id']}"
    return {"namespace": namespace, "kind": "Evidence", "id": eid, "issuer": issuer,
            "source_uri": "urn:frontier:adapter:openresearch-local-run",   # import-path label, not an identifier of the run
            "visibility": visibility, "predecessor": None, "payload": payload}
