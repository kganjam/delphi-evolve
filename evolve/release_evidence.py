"""Bind presentation claims to saved run receipts and actual artifact bytes."""
from __future__ import annotations

import hashlib
import csv
import json
from pathlib import Path


def compute_block(root: Path) -> dict:
    """Read a successful GPU run only when its job and files match the receipt."""
    path = root / "artifacts/gpu/compute_block.json"
    if not path.exists():
        return {"status": "unavailable", "provider": None, "model": None,
                "job_id": None, "artifacts": [], "note": "No GPU compute block integrated."}
    block = json.loads(path.read_text())
    receipt = json.loads((root / "tasks/results/gpu.json").read_text())
    if block.get("status") != "completed" or receipt.get("status") != "completed":
        raise ValueError("GPU block and worker receipt must both be completed")
    jobs = [j for j in receipt.get("nebius_jobs", []) if j.get("id") == block.get("job_id")]
    if len(jobs) != 1 or jobs[0].get("state") != "COMPLETED" or jobs[0].get("exit") != 0:
        raise ValueError("GPU block must name one completed, exit-zero recorded job")
    if block.get("evidence_kind") != "predicted" or not block.get("model") or not block.get("provider"):
        raise ValueError("GPU model outputs must be identified as predictions")
    if not block.get("artifacts"):
        raise ValueError("GPU block has no artifacts")
    for artifact in block["artifacts"]:
        p = (root / artifact["path"]).resolve()
        if not p.is_relative_to(root.resolve()):
            raise ValueError("GPU artifact escapes the repository")
        raw = p.read_bytes()
        if len(raw) != artifact["bytes"] or hashlib.sha256(raw).hexdigest() != artifact["sha256"]:
            raise ValueError(f"GPU artifact content does not match receipt: {artifact['path']}")
    return {**block, "receipt": "tasks/results/gpu.json",
            "note": "Predictions may guide measurement; they never discharge an empirical premise. "
                    "The completed sweep does not itself establish an assay-policy improvement."}


def claim_block(root: Path) -> dict:
    """Describe the recorded operational adapter demo without implying a live backend."""
    path = root / "artifacts/claim_reuse/demo_receipt.json"
    if not path.exists():
        return {"status": "unavailable", "scenarios": []}
    receipt = json.loads(path.read_text())
    scenarios = receipt.get("claim_scenarios", [])
    if not scenarios or not receipt.get("decision_changes"):
        raise ValueError("Claim reuse requires nonempty scenarios and source-change decisions")
    return {"status": "recorded", "demo": "claims/index.html",
            "receipt": "artifacts/claim_reuse/demo_receipt.json",
            "receipt_file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "scenarios": [{"scenario": s["scenario"], "decision": s["response"]["decision"],
                           "reason_code": s["response"]["reason_code"]} for s in scenarios],
            "scope": "Existing Kimura and Fisher claims select hand-authored, source-pinned model adapters. "
                     "Applicability checks compute or refuse; withdrawing the source changes the decision. "
                     "This is recorded execution, not a live browser service or a biological validation.",
            "reuse_limit": "Same-context savings equal ordinary caching. Additional context-fault checks "
                           "are software fixtures, not measured wet-lab savings."}


def lazysp_block(root: Path) -> dict:
    """Recount the stronger follow-up baseline from episode rows, not prose."""
    base = root / "artifacts/lazysp/results"
    if not (base / "episodes.csv").exists():
        return {"status": "unavailable"}
    summary = json.loads((base / "summary.json").read_text())
    audit = json.loads((base / "audit.json").read_text())
    with (base / "episodes.csv").open() as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 300:
        raise ValueError("LazySP follow-up requires all 300 episode rows")
    output = []
    for variant in ("alternate", "forward", "reverse"):
        selected = [r for r in rows if r["variant"] == variant]
        keys = {(r["family"], r["seed"], r["start"], r["target"]) for r in selected}
        if len(selected) != 100 or len(keys) != 100 or {int(r["seed"]) for r in selected} != set(range(20)):
            raise ValueError(f"Incomplete or duplicated LazySP panel: {variant}")
        if audit[variant]["shards_audited"] != 100 or audit[variant]["errors"]:
            raise ValueError(f"LazySP audit missing or failed: {variant}")
        if any(int(r["bmax"]) != 1000 or r["status"] not in {"open", "blocked", "unresolved"} for r in selected):
            raise ValueError("LazySP budget or verdict differs from the declared follow-up")
        count = sum(r["status"] != "unresolved" for r in selected)
        rmst = sum(int(r["assays"]) if r["status"] != "unresolved" else 1000 for r in selected) / 100
        expected = summary["variants"][variant]
        if count / 100 != expected["resolved_at"]["1000"] or abs(rmst - expected["rmst_assays"]) > 0.001:
            raise ValueError(f"LazySP summary differs from episode rows: {variant}")
        output.append({"variant": variant, "basis": "primary follow-up" if variant == "alternate" else "secondary follow-up",
                       "certified": count, "episodes": 100, "rmst_assays": rmst})
    return {"status": "completed", "primary": output[0], "variants": output,
            "sources": {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in (base / "episodes.csv", base / "summary.json", base / "audit.json")},
            "scope": "Follow-up node-query adaptation of established LazySP; same 100 episodes and 1,000-assay budget. "
                     "Selectors were declared before this follow-up, after the original experiment. "
                     "The apparent gain over original Q2C is concentrated in one repeated endpoint pair. "
                     "This does not establish general superiority. No route certifiable is not biological impossibility."}
