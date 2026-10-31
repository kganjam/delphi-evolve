"""Local, read-only MCP pilot over the reviewed Frontier inventory.

Uses the installed official MCP Python SDK 1.27.0. Draft tools return envelopes;
they do not publish, authenticate an author, reserve resources or execute work.
"""
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import BaseModel, ConfigDict, Field

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "site/review/frontier-data.json"
DATA = json.loads(DATA_PATH.read_text())
BY_ID = {node["id"]: node for node in DATA["nodes"]}
PROBLEMS = json.loads((ROOT / "site/review/frontier-problems.json").read_text())
PROBLEM_BY_ID = {problem["id"]: problem for problem in PROBLEMS["problems"]}
READ = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
server = FastMCP("Delphi Frontier review pilot", log_level="ERROR", instructions=(
    "Read-only local pilot over 21 pinned records. Review coverage is not scientific truth. "
    "Draft contributions and resource offers are unsigned and unsubmitted. No execution, "
    "reservation, public endpoint, database service or external adoption is implied."))


class Artifact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    location: str = Field(min_length=1, max_length=2000)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    kind: Literal["formal_proof", "computation", "measurement", "source_review", "counterexample"]


class Contribution(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim_id: str = Field(max_length=100)
    claim_version_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    author_identifier: str = Field(min_length=1, max_length=300)
    kind: Literal["evidence", "challenge", "reproduction", "scope_review", "negative_result"]
    statement: str = Field(min_length=1, max_length=6000)
    scope: list[str] = Field(min_length=1, max_length=30)
    limitations: list[str] = Field(min_length=1, max_length=30)
    artifacts: list[Artifact] = Field(min_length=1, max_length=20)
    acceptance_requested: str = Field(min_length=1, max_length=3000)


class ResourceOffer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider_identifier: str = Field(min_length=1, max_length=300)
    resource_kind: Literal["compute", "model_inference", "dataset_access", "review", "instrument_time"]
    description: str = Field(min_length=1, max_length=3000)
    capacity: float = Field(gt=0, allow_inf_nan=False)
    unit: str = Field(min_length=1, max_length=100)
    available_until: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}T.*(?:Z|[+-]\d{2}:\d{2})$")
    restrictions: list[str] = Field(min_length=1, max_length=30)
    price_description: str = Field(min_length=1, max_length=1000)
    verification_method: str = Field(min_length=1, max_length=2000)


class Interest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    problem_id: str = Field(max_length=100)
    problem_version_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    actor_identifier: str = Field(min_length=1, max_length=300)
    signal: Literal["following", "can_contribute", "resource_offer", "blocked_by_this"]
    explanation: str = Field(min_length=1, max_length=3000)
    downstream_reference: str = Field(default="", max_length=2000)


def envelope(kind, payload):
    content = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return {"schema_version": "frontier-draft-0.1", "kind": kind, "status": "draft_unsubmitted",
            "payload": payload, "payload_sha256": sha256(content.encode()).hexdigest(),
            "identity_verified": False, "artifact_content_verified": False,
            "resources_reserved": False, "signed": False,
            "next_step": "Submit to the coordinating project for independent review. This tool has made no external change."}


@server.tool(annotations=READ)
def frontier_search(query: str = "", category: str = "", limit: int = 10, offset: int = 0) -> dict:
    """Search pinned records by lexical terms and review category; relevance is not confidence.

    Categories: checked, related, question, unchecked. Limit 1..21, offset >=0.
    This pilot has no semantic index or entity-resolution service.
    """
    if len(query) > 2000 or not 1 <= limit <= 21 or offset < 0:
        raise ValueError("Invalid query length, limit or offset")
    if category and category not in {"checked", "related", "question", "unchecked"}:
        raise ValueError("Unknown review category")
    terms = set(re.findall(r"[\w-]+", query.lower()))
    hits = []
    for node in DATA["nodes"]:
        if category and node["category"] != category:
            continue
        text = " ".join(str(node[k]) for k in ("id", "label", "statement", "math", "context", "finding", "next_action")).lower()
        matched = sorted(term for term in terms if term in text)
        if terms and not matched:
            continue
        hits.append({"id": node["id"], "label": node["label"], "category": node["category"],
                     "review_title": node["review_title"], "version_sha256": node["record_sha256"],
                     "matched_terms": matched, "lexical_matches": len(matched)})
    hits.sort(key=lambda hit: (-hit["lexical_matches"], hit["id"]))
    return {"source_revision": DATA["source_revision"], "search_kind": "lexical pilot",
            "total": len(hits), "results": hits[offset:offset + limit],
            "next_offset": offset + limit if offset + limit < len(hits) else None}


@server.tool(annotations=READ)
def frontier_get_claim(claim_id: str, expected_version_sha256: str = "") -> dict:
    """Return the pinned claim, scope, evidence links and proposed next review action.

    An expected version mismatch is an error, not an implicit update.
    """
    if claim_id not in BY_ID:
        raise ValueError("Unknown claim ID")
    node = BY_ID[claim_id]
    if expected_version_sha256 and expected_version_sha256 != node["record_sha256"]:
        raise ValueError("Claim version mismatch")
    return {"source_revision": DATA["source_revision"], "claim": node,
            "connections": [e for e in DATA["bridges"] if claim_id in (e["from"], e["to"])],
            "limits": DATA["scope"]}


@server.tool(annotations=READ)
def frontier_contribution_contract() -> dict:
    """Get schemas for draft contributions and resource offers, plus their review boundary."""
    return {"contribution_schema": Contribution.model_json_schema(),
            "resource_offer_schema": ResourceOffer.model_json_schema(), "interest_schema": Interest.model_json_schema(),
            "supported_operations": ["read", "search", "prepare_unsigned_draft"],
            "not_implemented": ["publish", "reserve", "execute", "authenticate_author", "verify_artifact_content"],
            "protocol_version": "frontier-draft-0.1"}


@server.tool(annotations=READ)
def frontier_prepare_contribution(contribution: Contribution) -> dict:
    """Validate schema and claim version, then return an unsigned, unsubmitted contribution.

    Hash syntax is checked; artifact bytes and scientific content are not verified.
    """
    frontier_get_claim(contribution.claim_id, contribution.claim_version_sha256)
    return envelope("contribution", contribution.model_dump(mode="json"))


@server.tool(annotations=READ)
def frontier_prepare_resource_offer(offer: ResourceOffer) -> dict:
    """Prepare a draft offer of compute, data, model access, review or instrument time.

    No availability is verified; nothing is reserved, purchased or executed.
    """
    from datetime import datetime
    deadline = datetime.fromisoformat(offer.available_until.replace("Z", "+00:00"))
    if deadline.tzinfo is None:
        raise ValueError("Offer deadline requires a timezone")
    return envelope("resource_offer", offer.model_dump(mode="json"))


@server.tool(annotations=READ)
def frontier_list_problems(state: str = "open") -> dict:
    """List seeded project questions with acceptance criteria; not a field-wide frontier."""
    if state not in {"open", "resolved_in_review", "all"}:
        raise ValueError("Unknown problem state")
    return {"scope": PROBLEMS["scope"], "ranking": PROBLEMS["ranking"],
            "problems": [frontier_get_problem(p["id"]) for p in PROBLEMS["problems"] if state == "all" or p["state"] == state]}


@server.tool(annotations=READ)
def frontier_get_problem(problem_id: str) -> dict:
    """Read a scoped project question, dependencies, useful cached assets and acceptance criteria."""
    if problem_id not in PROBLEM_BY_ID:
        raise ValueError("Unknown problem ID")
    problem = PROBLEM_BY_ID[problem_id]
    digest = sha256(json.dumps(problem, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    return {"problem": problem, "problem_version_sha256": digest}


@server.tool(annotations=READ)
def frontier_prepare_interest(interest: Interest) -> dict:
    """Prepare an unsigned interest/capability/resource/blocking signal. Does not register or vote.

    Follow the returned private coordination URL with an authorized account to submit manually.
    """
    problem = frontier_get_problem(interest.problem_id)
    if problem["problem_version_sha256"] != interest.problem_version_sha256:
        raise ValueError("Problem version mismatch")
    if interest.signal == "blocked_by_this" and not interest.downstream_reference:
        raise ValueError("A blocking signal needs a concrete downstream reference")
    result = envelope("interest", interest.model_dump(mode="json"))
    result["coordination_url"] = problem["problem"].get("coordination_url")
    result["registered"] = False
    return result


@server.resource("frontier://review-map")
def review_map() -> str:
    """Full pinned map, using the same JSON as the browser prototype."""
    return json.dumps(DATA, ensure_ascii=False)


@server.resource("frontier://problems")
def problems_resource() -> str:
    """Six unresolved project questions and one resolved scope correction."""
    return json.dumps(PROBLEMS, ensure_ascii=False)


@server.resource("frontier://claim/{claim_id}")
def claim_resource(claim_id: str) -> str:
    """Pinned record plus review and evidence links."""
    return json.dumps(frontier_get_claim(claim_id), ensure_ascii=False)


if __name__ == "__main__":
    server.run(transport="stdio")
