"""Attempt ESMFold2-Fast (submit_esmfold2_fast) for the VFVS parent. The request schema requires an uploaded
`input_manifest` artifact whose content contract is NOT documented for this model (input_artifact_contract is null),
so this script sends a minimal manifest following the advertised manifest schema id and records the server's
verdicts verbatim. No retries beyond the ones listed here; failures are recorded, not worked around."""
import hashlib, json, sys, time, urllib.request
from pathlib import Path
from .common import now_seattle, now_utc, sha256_bytes, sha256_text, strip_url, write_json
from .nebius_mcp import NebiusMCP
from .predict_structure import OUT, find_key, find_status, genotype_sequence, load_parent, TERMINAL_BAD, TERMINAL_OK

MODEL = "esmfold2-fast"

def main(variant=0, budget_s=600):
    header, parent = load_parent(); seq = genotype_sequence(parent, "VFVS"); h = sha256_text(seq)
    manifests = [
        {"schema": "fs2-serve.nebius.ai/scientific-artifact-manifest/v1", "artifacts": []},
    ]
    man = json.dumps(manifests[variant], sort_keys=True).encode()
    rec = {"model": MODEL, "sequence_sha256": h, "manifest_variant": variant, "manifest_json": manifests[variant],
           "t_utc": now_utc(), "t_seattle": now_seattle(), "steps": []}
    c = NebiusMCP(); c.initialize()
    t0 = time.time()
    try:
        up = c.tool_payload(c.call_tool("begin_scientific_artifact_upload", {
            "model_id": MODEL, "sha256": sha256_bytes(man), "size_bytes": len(man),
            "media_type": "application/vnd.fs2.scientific-manifest+json", "idempotency_key": f"delphi-evolve-manifest-{h[:16]}-v{variant}-a2"}))
        rec["steps"].append({"begin_upload": up})
        upload_id = find_key(up, "upload_id")
        handle = up.get("handle") or {}
        url = handle.get("url") or up.get("direct_upload_url")
        hdrs = handle.get("headers") or {}
        if url:
            req = urllib.request.Request(url, data=man, method=handle.get("method", "PUT"),
                                         headers={**{"Content-Type": "application/vnd.fs2.scientific-manifest+json"}, **{k: v for k, v in hdrs.items() if isinstance(v, str)}})
            with urllib.request.urlopen(req, timeout=60) as r:
                rec["steps"].append({"put_status": r.status, "url_query_stripped": strip_url(url)})
        fin = c.tool_payload(c.call_tool("finalize_scientific_artifact_upload", {"upload_id": upload_id}))
        rec["steps"].append({"finalize": fin})
        ref = fin.get("artifact") or fin
        art = {k: ref[k] for k in ("artifact_id", "sha256", "size_bytes", "media_type") if k in ref}
        art.setdefault("compression", "none")
        args = {"schema": "fs2-serve.nebius.ai/scientific-run-request/v1", "operation": "predict-protein-structure",
                "service_class": "interactive", "input_manifest": art,
                "parameters": {"sequence": seq, "mode": "single-sequence", "seed": 0},
                "client_context": {"display_name": "delphi-evolve TrpB VFVS parent"},
                "output_prefix": f"runs/delphi-evolve/structure-esmfold2fast/{h[:16]}",
                "idempotency_key": f"delphi-evolve-structure-{h[:16]}-esmfold2fast"}
        rec["submit_arguments"] = args
        res = c.call_tool("submit_esmfold2_fast", args)
        pay = c.tool_payload(res); rec["submit_response"] = {"isError": res.get("isError"), "payload": pay}
        op = find_key(pay, "operation_id"); rec["operation_id"] = op
        status = None
        while op and time.time() - t0 < budget_s:
            st = c.tool_payload(c.call_tool("get_operation", {"operation_id": op})); status = find_status(st)
            rec.setdefault("polls", []).append({"t_utc": now_utc(), "status": status, "detail": st if status in TERMINAL_BAD else None})
            if status in TERMINAL_OK | TERMINAL_BAD: break
            time.sleep(15)
        rec["final_status"] = status
        if status in TERMINAL_OK:
            rec["result"] = c.tool_payload(c.call_tool("get_operation_result", {"operation_id": op}))
    except Exception as e:
        rec["exception"] = f"{type(e).__name__}: {e}"
        if hasattr(e, "payload"): rec["exception_payload"] = e.payload
    rec["wall_s"] = round(time.time() - t0, 1)
    write_json(OUT / f"esmfold2fast_attempt_v{variant}.json", rec)
    write_json(OUT / f"transcript_esmfold2fast_attempt_v{variant}.json", c.log)
    print(json.dumps({k: rec.get(k) for k in ("operation_id", "final_status", "exception", "wall_s")}))

if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 0)
