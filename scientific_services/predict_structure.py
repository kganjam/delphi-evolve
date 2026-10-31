"""Predict a TrpB structure via Nebius Scientific AI MCP `infer_openfold2_native`.

Inputs: pinned parent FASTA (sha256 verified against gpu worker's recorded hash), genotype at
sites 183/184/227/228 (1-based index into the FASTA; Met1). Idempotency key is
delphi-evolve-structure-<sha256(sequence)[:16]>; after an accepted timeout the SAME operation id
is polled, never resubmitted. Signed download URLs are fetched in memory and never persisted.
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.request
from pathlib import Path

from .common import now_seattle, now_utc, redact, sha256_bytes, sha256_text, strip_url, write_json
from .nebius_mcp import MCPError, NebiusMCP

SITES = (183, 184, 227, 228)
FASTA_SHA256 = "d56ebe8d8c556d80bf97329ec34c872b737fb84953f0d83dfe015894e54bbc6c"
OUT = Path("artifacts/services/nebius")
TERMINAL_OK = {"SUCCEEDED"}
TERMINAL_BAD = {"FAILED", "CANCELLED", "CANCELED", "EXPIRED", "TIMED_OUT"}


def load_parent(path=OUT / "parent_tm9d8s_AAs.fasta"):
    raw = Path(path).read_bytes()
    if sha256_bytes(raw) != FASTA_SHA256:
        raise ValueError("parent FASTA hash mismatch")
    lines = raw.decode().splitlines()
    seq = "".join(x.strip() for x in lines[1:])
    assert len(seq) == 397
    return lines[0][1:], seq


def genotype_sequence(seq, genotype):
    s = list(seq)
    for p, aa in zip(SITES, genotype):
        s[p - 1] = aa
    return "".join(s)


def find_status(payload):
    if isinstance(payload, dict):
        for k in ("status", "state"):
            if isinstance(payload.get(k), str):
                return payload[k].upper()
        for v in payload.values():
            r = find_status(v)
            if r:
                return r
    return None


def find_key(obj, key):
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            r = find_key(v, key)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = find_key(v, key)
            if r is not None:
                return r
    return None


def run(genotype="VFVS", budget_s=1200, tag="parent"):
    header, parent = load_parent()
    seq = genotype_sequence(parent, genotype)
    h = sha256_text(seq)
    idem = f"delphi-evolve-structure-{h[:16]}"
    args = {"input_id": f"trpb-{genotype}-{h[:8]}", "sequence": seq, "selected_models": [1],
            "relax_prediction": False, "idempotency_key": idem, "wait_seconds": 30,
            "output_prefix": f"runs/delphi-evolve/structure/{h[:16]}"}
    c = NebiusMCP()
    rec = {"tool": "infer_openfold2_native", "genotype": genotype, "sequence": seq, "sequence_sha256": h,
           "parent_fasta_header": header, "parent_fasta_sha256": FASTA_SHA256, "idempotency_key": idem,
           "request_arguments": args, "submitted_t_utc": now_utc(), "submitted_t_seattle": now_seattle(),
           "polls": []}
    t_start = time.time()
    c.initialize()
    op_id = None
    try:
        res = c.call_tool("infer_openfold2_native", args)
        pay = c.tool_payload(res)
        rec["submit_response"] = {"isError": res.get("isError"), "payload": pay}
        op_id = find_key(pay, "operation_id")
    except Exception as e:  # network timeout etc.: the idempotency key lets us resubmit the SAME work safely
        rec["submit_exception"] = f"{type(e).__name__}: {e}"
        if isinstance(e, MCPError) and e.payload:
            rec["submit_error_payload"] = e.payload
            op_id = find_key(e.payload, "operation_id")
    rec["operation_id"] = op_id
    if not op_id:
        rec["note"] = "no operation id returned; see submit_response"
        write_json(OUT / f"structure_{tag}_{genotype}.json", rec)
        return rec
    status = None
    while time.time() - t_start < budget_s:
        try:
            st = c.tool_payload(c.call_tool("get_operation", {"operation_id": op_id}))
        except Exception as e:
            rec["polls"].append({"t_utc": now_utc(), "exception": f"{type(e).__name__}: {e}"}); time.sleep(10); continue
        status = find_status(st)
        rec["polls"].append({"t_utc": now_utc(), "elapsed_s": round(time.time() - t_start, 1), "status": status})
        rec["last_operation"] = st
        if status in TERMINAL_OK | TERMINAL_BAD:
            break
        time.sleep(15)
    rec["final_status"] = status
    if status in TERMINAL_OK:
        out = c.tool_payload(c.call_tool("get_operation_result", {"operation_id": op_id}))
        rec["result"] = out
    rec["finished_t_utc"] = now_utc(); rec["finished_t_seattle"] = now_seattle()
    rec["wall_s"] = round(time.time() - t_start, 1)
    write_json(OUT / f"structure_{tag}_{genotype}.json", rec)
    write_json(OUT / f"transcript_structure_{tag}_{genotype}.json", c.log)
    return rec


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--genotype", default="VFVS")
    ap.add_argument("--budget-s", type=int, default=1200)
    a = ap.parse_args()
    r = run(a.genotype, a.budget_s)
    print(json.dumps({k: r.get(k) for k in ("operation_id", "final_status", "wall_s", "idempotency_key")}))
