"""Bind presentation claims to saved run receipts and actual artifact bytes."""
from __future__ import annotations

import hashlib
import csv
import json
import gzip
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


def scale_block(root: Path) -> dict:
    """Recount the complete prior follow-up; do not promote partial panels to results."""
    import numpy as np

    base = root / "artifacts/scale"
    if not (base / "replay_summary.csv").exists():
        return {"status": "unavailable"}
    receipt = json.loads((base / "library_receipts.json").read_text())
    model_keys = {"te8m", "te35m", "te150m", "te650m", "te3b"}
    if set(receipt["models"]) != model_keys or any(m["covered"] != 160000 for m in receipt["models"].values()):
        raise ValueError("Scale requires five complete 160,000-variant model libraries")
    jobs = receipt["jobs"]
    if len(jobs) != 10 or len({j["id"] for j in jobs}) != 10 or any(j["state"] != "COMPLETED" for j in jobs):
        raise ValueError("Scale requires ten distinct completed recorded jobs")
    prior = receipt["priors_z_npz"]
    p = (root / prior["file"]).resolve()
    if not p.is_relative_to(root.resolve()) or hashlib.sha256(p.read_bytes()).hexdigest() != prior["sha256"]:
        raise ValueError("Scale compact prior bytes do not match receipt")
    with np.load(p) as arrays:
        expected_keys = {f"{m}__{q}" for m in model_keys for q in ("mm_ctx", "mm_wt")}
        if set(arrays.files) != expected_keys or any(arrays[k].shape != (160000,) or not np.isfinite(arrays[k]).all() for k in arrays.files):
            raise ValueError("Scale priors have missing, nonfinite or mis-sized arrays")
    with gzip.open(base / "replay_rows.jsonl.gz", "rt") as handle:
        rows = [json.loads(line) for line in handle]
    configs = {("q2c", "none"), ("collective_shared", "none"),
               ("collective_shared", "esm_te3b_mm_ctx"), ("collective_shared", "shuf_te3b_mm_ctx")}
    configs |= {("q2c", f"esm_{m}_mm_ctx") for m in model_keys}
    configs |= {("q2c", f"shuf_{m}_mm_ctx") for m in ("te150m", "te3b")}
    if len(rows) != 1100 or {(r["policy"], r["prior_tag"]) for r in rows} != configs:
        raise ValueError("Scale requires exactly 11 declared configurations and 1,100 episodes")
    tables = list(csv.DictReader((base / "replay_summary.csv").open()))
    if len(tables) != 11 or {(r["policy"], r["tag"]) for r in tables} != configs:
        raise ValueError("Scale summary configurations differ from the declared panel")
    output = []
    with (root / "artifacts/core/replay/episodes.csv").open() as handle:
        panel = {(r["family"], int(r["seed"]), r["start"], r["target"]) for r in csv.DictReader(handle) if r["policy"] == "q2c"}
    for table in tables:
        selected = [r for r in rows if (r["policy"], r["prior_tag"]) == (table["policy"], table["tag"])]
        keys = {(r["family"], r["seed"], r["start"], r["target"]) for r in selected}
        if len(selected) != 100 or len(keys) != 100 or keys != panel or {r["seed"] for r in selected} != set(range(20)):
            raise ValueError("Scale configuration contains incomplete or duplicated episodes")
        if any(r["bmax"] != 1000 or r["core_commit"] != "8883518" or not 0 <= r["assays"] <= 1000 for r in selected):
            raise ValueError("Scale budget, pinned implementation or assay count is invalid")
        for budget in (100, 250, 500, 1000):
            certified = [r for r in selected if r["certificate"] is not None and r["assays"] <= budget]
            if len(certified) != int(table[f"cert@{budget}"]) or sum(not r["correct"] for r in certified) != int(table[f"false@{budget}"]):
                raise ValueError("Scale summary differs from episode certificate counts")
        rmst = sum(r["assays"] if r["certificate"] is not None else 1000 for r in selected) / 100
        if abs(rmst - float(table["rmst@1000"])) > 1e-8:
            raise ValueError("Scale summary differs from episode assay counts")
        output.append({"policy": table["policy"], "prior": table["tag"], "certified": int(table["cert@1000"]),
                       "episodes": 100, "rmst_assays": rmst,
                       "interval": [float(table[k]) for k in ("paired_seed_bootstrap_lo", "paired_seed_bootstrap_hi")] if table["tag"] != "none" else None})
    return {"status": "completed", "models": 5, "variants_per_model": 160000, "episodes": 1100,
            "comparisons": output, "all_rmst_intervals_include_zero": all(r["interval"] is None or r["interval"][0] <= 0 <= r["interval"][1] for r in output),
            "source_sha256": {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in (base / "replay_rows.jsonl.gz", base / "replay_summary.csv", base / "library_receipts.json")},
            "scope": "Separate follow-up on the same repeated-target panel; no clear assay-saving benefit under the tested prior integration. "
                     "Episode rows and summaries recounted; these runs did not retain per-query traces. "
                     "Protein model outputs remain predictions; intervals are descriptive seed bootstraps, not calibrated coverage."}
