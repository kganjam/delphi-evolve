"""Typed evidence claims for OBSERVED assay results, with an applicability guard.

A typed evidence claim is a content-addressed record:
  kind (observed | predicted | simulated), status (active | withdrawn | superseded),
  dataset hash, assay-context id, reference-coordinate hash (+ positions), units, subject
  genotype, and the value. Its `id` hashes the identity fields only, so identical evidence
  imported twice has the same id and is counted ONCE; campaign provenance is carried
  outside the id.

A requester states what it needs (a `Requirement`). `check()` returns the list of guard
failures; reuse is allowed only when that list is empty. Facts that fail are never used
(fail closed). `SequenceCache` is the deliberately naive baseline: it keys on sequence
alone and returns whatever it holds.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .common import sha

GUARDS = ["id_integrity", "kind_observed", "status_active", "dataset_hash", "assay_context", "reference_coordinates", "units"]
IDENTITY_FIELDS = ("kind", "subject", "dataset_sha256", "assay_context_id", "reference_sha256", "positions", "units", "value")

TRPB_UNITS = "integer micro-units of raw growth-rate score mu minus per-replicate stop-codon mean (evolve.data, 1e-6 resolution)"
TRPB_POSITIONS = [183, 184, 227, 228]
TRPB_PARENT = "VFVS"
AA_ALPHABET = "ACDEFGHIKLMNPQRSTVWY"


def assay_context(dataset_sha256: str) -> dict:
    return {"system": "TrpB four-site combinatorial library (Johnston et al., doi 10.1073/pnas.2400439121)",
            "dataset_file": "summary_AA.csv", "dataset_sha256": dataset_sha256,
            "readout": "pooled growth-based selection, 2 replicates, raw mu_1/mu_2 columns (never the /max columns, never the KNN-imputed file)",
            "genotype_alphabet": AA_ALPHABET}


def context_id(ctx: dict) -> str:
    return sha(ctx)


def reference_hash(positions=TRPB_POSITIONS, parent=TRPB_PARENT, alphabet=AA_ALPHABET) -> str:
    return sha({"positions": list(positions), "parent": parent, "alphabet": alphabet,
                "genotype_string": "residues at `positions` in this order"})


def claim_id(c: dict) -> str:
    return sha({k: c[k] for k in IDENTITY_FIELDS})


def make_claim(subject: str, value, *, dataset_sha256: str, ctx_id: str, ref_sha: str, kind="observed",
               status="active", positions=None, units=TRPB_UNITS, provenance=None) -> dict:
    c = {"schema": "typed-evidence-claim/v1", "kind": kind, "status": status, "subject": subject, "value": value,
         "dataset_sha256": dataset_sha256, "assay_context_id": ctx_id, "reference_sha256": ref_sha,
         "positions": list(positions or TRPB_POSITIONS), "units": units, "provenance": provenance or {}}
    c["id"] = claim_id(c)
    return c


@dataclass(frozen=True)
class Requirement:
    dataset_sha256: str
    assay_context_id: str
    reference_sha256: str
    positions: tuple = tuple(TRPB_POSITIONS)
    units: str = TRPB_UNITS
    kind: str = "observed"


def check(c: dict, req: Requirement, disabled=frozenset()) -> list:
    """Return the guard names that FAIL for claim c under requirement req ([] means usable)."""
    bad = []
    on = lambda g: g not in disabled
    if on("id_integrity") and c.get("id") != claim_id(c):
        bad.append("id_integrity")
    if on("kind_observed") and c.get("kind") != req.kind:
        bad.append("kind_observed")
    if on("status_active") and c.get("status") != "active":
        bad.append("status_active")
    if on("dataset_hash") and c.get("dataset_sha256") != req.dataset_sha256:
        bad.append("dataset_hash")
    if on("assay_context") and c.get("assay_context_id") != req.assay_context_id:
        bad.append("assay_context")
    if on("reference_coordinates") and (c.get("reference_sha256") != req.reference_sha256 or tuple(c.get("positions", ())) != tuple(req.positions)):
        bad.append("reference_coordinates")
    if on("units") and c.get("units") != req.units:
        bad.append("units")
    return bad


@dataclass
class EvidenceStore:
    disabled_guards: frozenset = frozenset()
    by_id: dict = field(default_factory=dict)
    by_subject: dict = field(default_factory=dict)
    duplicates_ignored: int = 0

    def add(self, c: dict) -> str:
        if c["id"] in self.by_id:
            self.duplicates_ignored += 1
            return "duplicate_same_evidence"
        self.by_id[c["id"]] = c
        self.by_subject.setdefault(c["subject"], []).append(c["id"])
        return "added"

    def withdraw(self, cid: str):
        self.by_id[cid]["status"] = "withdrawn"

    def remove(self, cid: str):
        c = self.by_id.pop(cid)
        self.by_subject[c["subject"]].remove(cid)

    def lookup(self, subject: str, req: Requirement) -> dict:
        """Decision for a request to assay `subject`: reuse a valid stored fact or require a fresh assay."""
        rejected = []
        for cid in self.by_subject.get(subject, []):
            c = self.by_id[cid]
            bad = check(c, req, self.disabled_guards)
            if not bad:
                return {"decision": "reuse", "evidence_id": cid, "reason": "valid same-context observed evidence", "rejected": rejected}
            rejected.append({"evidence_id": cid, "failed_guards": bad})
        return {"decision": "assay_required", "evidence_id": None,
                "reason": "no stored evidence" if not rejected else "stored evidence failed applicability guards", "rejected": rejected}

    def supports_certificate(self, evidence_ids, req: Requirement) -> dict:
        """May these facts support an assay decision/certificate? All must pass; unknown ids fail."""
        problems = []
        for cid in evidence_ids:
            c = self.by_id.get(cid)
            if c is None:
                problems.append({"evidence_id": cid, "failed_guards": ["missing_evidence"]})
                continue
            bad = check(c, req, self.disabled_guards)
            if bad:
                problems.append({"evidence_id": cid, "failed_guards": bad})
        if not evidence_ids:
            return {"supported": False, "reason": "no evidence supplied (an empty set supports nothing)", "problems": []}
        return {"supported": not problems, "reason": "all evidence usable" if not problems else "evidence failed guards", "problems": problems}


class SequenceCache:
    """Ordinary sequence-keyed cache: no kind/status/context/coordinate checks at all."""

    def __init__(self):
        self.d = {}

    def put(self, subject, claim):
        self.d[subject] = claim

    def get(self, subject):
        return self.d.get(subject)
