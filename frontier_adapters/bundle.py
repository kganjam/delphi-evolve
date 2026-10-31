"""Assemble a PROPOSED Claim + Evidence pair and its unsigned nanopub drafts. Nothing is submitted or published."""
from __future__ import annotations

import json
import os
import subprocess

from . import nanopub_draft as nd
from .common import iso_utc, sha_bytes, sha_obj, validate_draft


def _frontier_commit() -> str | None:
    p = os.environ.get("FRONTIER_PATH")
    try:
        return subprocess.run(["git", "-C", p, "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10).stdout.strip() or None
    except Exception:
        return None


def assemble(claim_draft: dict, evidence_from_target, *, out_dir: str, created_at: str | None = None) -> dict:
    """`evidence_from_target(target_ref) -> evidence draft`. The Evidence is pinned to the Claim's exact version."""
    created_at = created_at or iso_utc()
    claim = validate_draft(claim_draft, created_at)
    c = claim["record"]
    target = {k: c[k] for k in ("namespace", "kind", "id", "version")}
    ev_draft = evidence_from_target(target)
    ev = validate_draft(ev_draft, created_at)
    e = ev["record"]
    if claim["licence_gate_offenders"] or ev["licence_gate_offenders"]:
        raise nd.ExportRefused(f"store licence gate would refuse: {claim['licence_gate_offenders'] + ev['licence_gate_offenders']}")
    claim_trig = nd.record_to_trig(c)
    ev_trig = nd.record_to_trig(e, target_claim=c)
    checks = {"claim": nd.validate_trig(claim_trig), "evidence": nd.validate_trig(ev_trig)}
    if not all(v["four_graphs"] and v["balanced"] and not v["blank_node_labels"] for v in checks.values()):
        raise nd.ExportRefused(f"structural check failed: {checks}")
    os.makedirs(out_dir, exist_ok=True)
    files = {"records.json": json.dumps([c, e], indent=2, sort_keys=True) + "\n",
             "claim.draft.trig": claim_trig, "evidence.draft.trig": ev_trig}
    for n, t in files.items():
        with open(os.path.join(out_dir, n), "w") as fh:
            fh.write(t)
    manifest = {
        "status": "PROPOSED. Not submitted to any store, not accepted, not published. single-reader, not Codex-reviewed.",
        "created_at": created_at,
        "records": [{"kind": r["kind"], "id": r["id"], "namespace": r["namespace"], "version": r["version"],
                     "payload_sha256": sha_obj(r["payload"])} for r in (c, e)],
        "evidence_targets_exact_claim_version": e["payload"]["target"]["version"] == c["version"],
        "original_delphi": {"claim_iri": c["source_uri"], "nanopub_uri": c["payload"]["source_record_version"],
                            "registry": c["payload"]["prior_review"]["delphi_original"]["registry"]},
        "validated_with": {"frontier_models": "frontier.models.Draft/make_record + store._unlicensed_available_content",
                           "frontier_commit_read": _frontier_commit(), "licence_gate_offenders": []},
        "trig_structure": checks,
        "file_sha256": {n: sha_bytes(t.encode()) for n, t in files.items()},
        "publication": "none. nanopub_draft has no publish function; drafts carry de:signatureStatus UNSIGNED DRAFT.",
    }
    with open(os.path.join(out_dir, "manifest.json"), "w") as fh:
        fh.write(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest
