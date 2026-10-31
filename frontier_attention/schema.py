"""Attention and forecasting schema for the Frontier map: validators only.

Nothing here stores, serves or authenticates anything. Records are plain dicts; every validator returns a
list of issues {path, code, msg} (empty list = valid) so a curator sees ALL gaps at once. A gap is information:
a problem whose next action has no stop rule is simply "not bounded yet", it is not silently defaulted.

Premise (binding, from the director): an unguarded frontier model is already ~95% accurate on the frozen
benchmark. Nothing in this schema assumes models are inaccurate. What an answer "unlocks" is a DECISION about
reuse, scope or allocation (the witness, the refusal, the repair); it is never "fewer model errors".
"""
from __future__ import annotations

import math
import re
from datetime import datetime

EVIDENCE_KINDS = ("observed", "predicted", "simulated", "formal", "source_assessment")
# open_kind: the seed map's own kinds are accepted verbatim (no silent re-mapping) plus the proposal's extra kinds
OPEN_KINDS = (
    "project_formalization_gap", "empirical_bridge_gap", "project_computational_question",
    "project_source_review_gap", "project_coordination_question", "project_methods_question",
    "resolved_project_scope_correction", "field_open_problem", "missing_measurement", "replication_need",
)
NOVELTY_STATUS = ("unchecked", "searched", "known_open_in_field", "not_claimed")
UNLOCK_KINDS = ("logical_necessity", "empirical_relevance", "proposed_connection")  # proposal: three distinct edges
ACTION_TYPES = ("proof", "evidence_retrieval", "reanalysis", "simulation", "measurement", "review", "consolidation")
LEASE_STATES = ("leased", "running", "submitted", "reviewed", "expired", "released")
SIGNAL_KINDS = ("following", "can_contribute", "resource_offer", "blocked_by_this")
RESOURCE_VERIFICATION = ("unverified", "availability_checked")
EVIDENCE_LABEL_NOTE = "observed / predicted / simulated / formal / source_assessment stay separate; none is a composite truth score"

_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$")
_SHA = re.compile(r"^[0-9a-f]{64}$")


def issue(path: str, code: str, msg: str) -> dict:
    return {"path": path, "code": code, "msg": msg}


def _nonempty_str(v) -> bool:
    return isinstance(v, str) and bool(v.strip())


def _pos_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and v > 0


def parse_time(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _time_ok(v) -> bool:
    if not (isinstance(v, str) and _ISO.match(v)):
        return False
    try:
        return parse_time(v).tzinfo is not None
    except ValueError:
        return False


def _ref_issues(ref, path: str) -> list[dict]:
    if not isinstance(ref, dict) or not _nonempty_str(ref.get("id")) or not _nonempty_str(ref.get("version")):
        return [issue(path, "bad_ref", "a reference needs a non-empty id AND version (a wrong-version contribution must be rejectable)")]
    return []


# --------------------------------------------------------------------------------------------------------------
# 1. The attention profile of a problem: known / open / unlocks / working / next action
# --------------------------------------------------------------------------------------------------------------
def validate_next_action(a, path: str = "next_action") -> list[dict]:
    """A 'bounded' next action: type, pinned inputs, an ESTIMATED resource, a stop rule, an acceptance criterion and
    a named reviewer. The estimate is an estimate; consumed resource lives in a receipt (see credit.reconcile)."""
    if not isinstance(a, dict):
        return [issue(path, "missing", "no structured next action")]
    out = []
    if a.get("type") not in ACTION_TYPES:
        out.append(issue(path + ".type", "bad_enum", f"type must be one of {ACTION_TYPES}"))
    ih = a.get("input_hashes")
    if not (isinstance(ih, list) and ih and all(isinstance(h, str) and _SHA.match(h) for h in ih)):
        out.append(issue(path + ".input_hashes", "unpinned", "needs >=1 sha256 input hash; an unpinned action is not reproducible"))
    est = a.get("resource_estimate")
    if not (isinstance(est, dict) and _nonempty_str(est.get("unit")) and _pos_number(est.get("amount")) and est.get("basis") == "estimate"):
        out.append(issue(path + ".resource_estimate", "bad_estimate", "needs {unit, amount>0, basis:'estimate'}; estimates are never recorded as consumption"))
    for k in ("stop_rule", "acceptance_criterion", "reviewer"):
        if not _nonempty_str(a.get(k)):
            out.append(issue(f"{path}.{k}", "missing", f"{k} is required for a bounded action"))
    return out


def validate_unlock_edge(e, path: str) -> list[dict]:
    if not isinstance(e, dict):
        return [issue(path, "bad_type", "unlock edge must be an object")]
    out = []
    if e.get("kind") not in UNLOCK_KINDS:
        out.append(issue(path + ".kind", "untyped_edge", f"kind must be one of {UNLOCK_KINDS}; an untyped edge cannot be ranked"))
    out += _ref_issues(e.get("decision_ref"), path + ".decision_ref")
    if not _nonempty_str(e.get("independent_group")):
        out.append(issue(path + ".independent_group", "missing",
                         "descendants of one result share an independent_group so they are counted once, not once per descendant"))
    if not _nonempty_str(e.get("provenance")):
        out.append(issue(path + ".provenance", "missing", "every edge carries provenance; a suggested analogy is not an implication"))
    return out


def validate_lease(l, path: str) -> list[dict]:
    if not isinstance(l, dict):
        return [issue(path, "bad_type", "lease must be an object")]
    out = []
    if not _nonempty_str(l.get("operator")):
        out.append(issue(path + ".operator", "missing", "a lease names a responsible operator"))
    if l.get("status") not in LEASE_STATES:
        out.append(issue(path + ".status", "bad_enum", f"status must be one of {LEASE_STATES}"))
    for k in ("leased_at", "expires_at", "last_progress_at"):
        if not _time_ok(l.get(k)):
            out.append(issue(f"{path}.{k}", "bad_time", "ISO-8601 timestamp with zone required"))
    return out


def validate_profile(p: dict) -> list[dict]:
    """Attention profile of one problem version. Reads: what is known, what is open, what an answer would unlock,
    who is working, and the next bounded action. Returns ALL issues."""
    if not isinstance(p, dict):
        return [issue("$", "bad_type", "profile must be an object")]
    out = _ref_issues(p.get("problem_ref"), "problem_ref")
    known = p.get("known")
    if not (isinstance(known, list) and known):
        out.append(issue("known", "missing", "needs >=1 known item, each with an evidence kind and a source"))
    else:
        for i, k in enumerate(known):
            if not isinstance(k, dict) or not _nonempty_str(k.get("statement")):
                out.append(issue(f"known[{i}].statement", "missing", "statement required")); continue
            if k.get("evidence_kind") not in EVIDENCE_KINDS:
                out.append(issue(f"known[{i}].evidence_kind", "bad_enum", f"one of {EVIDENCE_KINDS}"))
            if not _nonempty_str(k.get("source")):
                out.append(issue(f"known[{i}].source", "missing", "source required"))
    op = p.get("open")
    if not isinstance(op, dict):
        out.append(issue("open", "missing", "what remains open must be stated"))
    else:
        if not _nonempty_str(op.get("question")):
            out.append(issue("open.question", "missing", "exact question"))
        if op.get("open_kind") not in OPEN_KINDS:
            out.append(issue("open.open_kind", "bad_enum", f"one of {OPEN_KINDS}"))
        if op.get("novelty_status") not in NOVELTY_STATUS:
            out.append(issue("open.novelty_status", "bad_enum", f"one of {NOVELTY_STATUS}; 'searched' needs scope+date, failing to retrieve a solution is not proof of novelty"))
        elif op["novelty_status"] == "searched" and not (_nonempty_str(op.get("search_scope")) and _time_ok(op.get("searched_at"))):
            out.append(issue("open.search_scope", "missing", "'searched' needs search_scope and searched_at"))
        if not _nonempty_str(op.get("acceptance_criterion")):
            out.append(issue("open.acceptance_criterion", "missing", "what evidence type would settle it, stated before any run"))
    ul = p.get("unlocks")
    if not isinstance(ul, list):
        out.append(issue("unlocks", "missing", "list of typed unlock edges (may be empty only if stated as no known downstream use)"))
    else:
        for i, e in enumerate(ul):
            out += validate_unlock_edge(e, f"unlocks[{i}]")
    wk = p.get("working")
    if not isinstance(wk, list):
        out.append(issue("working", "missing", "list of leases (empty list = nobody is recorded as working; absence of a record is not absence of work elsewhere)"))
    else:
        for i, l in enumerate(wk):
            out += validate_lease(l, f"working[{i}]")
    out += validate_next_action(p.get("next_action"))
    return out


def is_bounded(profile: dict) -> bool:
    return not validate_next_action(profile.get("next_action"))


# --------------------------------------------------------------------------------------------------------------
# 2. Signals: four different things, never merged into one score
# --------------------------------------------------------------------------------------------------------------
def validate_signal(s) -> list[dict]:
    """following | can_contribute | resource_offer | blocked_by_this. Versioned and retractable by a later
    signal with `retracts` = the id of the earlier one. None of these is a vote on truth."""
    if not isinstance(s, dict):
        return [issue("$", "bad_type", "signal must be an object")]
    out = []
    for k in ("id", "version"):
        if not _nonempty_str(s.get(k)):
            out.append(issue(k, "missing", f"{k} required (signals are immutable versions)"))
    kind = s.get("kind")
    if kind not in SIGNAL_KINDS:
        out.append(issue("kind", "bad_enum", f"one of {SIGNAL_KINDS}"))
    a = s.get("actor")
    if not (isinstance(a, dict) and _nonempty_str(a.get("operator")) and isinstance(a.get("identity_verified"), bool)):
        out.append(issue("actor", "bad_actor", "needs {operator, identity_verified:bool}; many accounts of one operator are one voice"))
    out += _ref_issues(s.get("problem_ref"), "problem_ref")
    if not _time_ok(s.get("created_at")):
        out.append(issue("created_at", "bad_time", "ISO-8601 with zone"))
    if s.get("retracts") is not None and not _nonempty_str(s.get("retracts")):
        out.append(issue("retracts", "bad_type", "id of the signal this retracts, or null"))
    pl = s.get("payload")
    if not isinstance(pl, dict):
        return out + [issue("payload", "missing", "payload object required")]
    if kind == "can_contribute":
        for k in ("capability", "availability", "proposed_task"):
            if not _nonempty_str(pl.get(k)):
                out.append(issue(f"payload.{k}", "missing", "a named capability, availability and bounded proposed task"))
    elif kind == "resource_offer":
        if not _nonempty_str(pl.get("resource_type")):
            out.append(issue("payload.resource_type", "missing", "e.g. gpu_hours, review_hours, dataset_access"))
        if not _pos_number(pl.get("amount")) or not _nonempty_str(pl.get("unit")):
            out.append(issue("payload.amount", "bad_amount", "amount>0 and unit required"))
        w = pl.get("window")
        if not (isinstance(w, dict) and _time_ok(w.get("start")) and _time_ok(w.get("end")) and parse_time(w["start"]) < parse_time(w["end"])):
            out.append(issue("payload.window", "bad_window", "{start,end} ISO times with start<end"))
        if not isinstance(pl.get("restrictions"), list):
            out.append(issue("payload.restrictions", "missing", "list of restrictions (may be empty)"))
        if pl.get("verification_status") not in RESOURCE_VERIFICATION:
            out.append(issue("payload.verification_status", "bad_enum", f"one of {RESOURCE_VERIFICATION}; a provider declaration is unverified until checked"))
    elif kind == "blocked_by_this":
        out += _ref_issues(pl.get("downstream_ref"), "payload.downstream_ref")
        if not _nonempty_str(pl.get("enablement")):
            out.append(issue("payload.enablement", "missing", "what resolving this would enable downstream; a block without a concrete downstream link is just a preference"))
    return out


# --------------------------------------------------------------------------------------------------------------
# 3. Prediction specs: a forecast is only scoreable if its event, resolver and horizon exist BEFORE it is made
# --------------------------------------------------------------------------------------------------------------
def validate_prediction_spec(s, now: str | None = None) -> list[dict]:
    if not isinstance(s, dict):
        return [issue("$", "bad_type", "prediction spec must be an object")]
    out = []
    if not _nonempty_str(s.get("id")):
        out.append(issue("id", "missing", "id required"))
    out += _ref_issues(s.get("problem_ref"), "problem_ref")
    if not _nonempty_str(s.get("event")):
        out.append(issue("event", "missing", "a defined yes/no event, not a topic"))
    elif len(s["event"]) < 15:
        out.append(issue("event", "vague", "event text too short to define a yes/no resolution"))
    if not _nonempty_str(s.get("resolution_criterion")):
        out.append(issue("resolution_criterion", "missing", "exact, checkable resolution criterion"))
    if not _nonempty_str(s.get("resolution_source")):
        out.append(issue("resolution_source", "missing", "the artifact/receipt/review that resolves it"))
    if not _nonempty_str(s.get("resolver")):
        out.append(issue("resolver", "missing", "who resolves it"))
    elif isinstance(s.get("forecasters"), list) and s["resolver"] in s["forecasters"]:
        out.append(issue("resolver", "not_independent", "the resolver must not also be a forecaster of the same event"))
    if not _time_ok(s.get("horizon")):
        out.append(issue("horizon", "bad_time", "horizon (when it expires unresolved) is required"))
    elif now is not None and _time_ok(now) and parse_time(s["horizon"]) <= parse_time(now):
        out.append(issue("horizon", "not_future", "horizon must be after spec creation"))
    if not _nonempty_str(s.get("void_conditions")):
        out.append(issue("void_conditions", "missing", "what makes the event void (void events are reported, not dropped)"))
    return out
