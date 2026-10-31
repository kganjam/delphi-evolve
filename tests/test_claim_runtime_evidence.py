"""Typed evidence claims: identical evidence counts once; changed context / wrong coordinates /
prediction-as-observation / withdrawn evidence cannot be reused or support a certificate.
All records in this file are SYNTHETIC SOFTWARE FIXTURES (not measurements)."""
import copy

import pytest

from claim_runtime import evidence as E

DS = "a" * 64
CTX = E.context_id(E.assay_context(DS))
REF = E.reference_hash()
REQ = E.Requirement(DS, CTX, REF)


def fx(subject="VFVS", score=123456, **kw):
    base = dict(dataset_sha256=DS, ctx_id=CTX, ref_sha=REF)
    base.update(kw)
    return E.make_claim(subject, {"outcome": "measured", "score_micro": score, "replicate_micro": [score - 5, score + 5], "min_input_count": 100}, **base)


def test_identical_evidence_counts_once_and_provenance_does_not_change_identity():
    st = E.EvidenceStore()
    a, b = fx(provenance={"campaign": "c1"}), fx(provenance={"campaign": "c2"})
    assert a["id"] == b["id"]
    assert st.add(a) == "added" and st.add(b) == "duplicate_same_evidence"
    assert len(st.by_id) == 1 and st.duplicates_ignored == 1


def test_value_or_context_changes_identity():
    assert fx()["id"] != fx(score=1)["id"]
    assert fx()["id"] != fx(ctx_id="b" * 64)["id"]
    assert fx()["id"] != fx(kind="predicted")["id"]


def test_same_context_observed_evidence_is_reused():
    st = E.EvidenceStore(); c = fx(); st.add(c)
    d = st.lookup("VFVS", REQ)
    assert d["decision"] == "reuse" and d["evidence_id"] == c["id"]
    assert st.lookup("VFMS", REQ)["decision"] == "assay_required"


@pytest.mark.parametrize("name,claim_kw,guard", [
    ("changed assay context", dict(ctx_id=E.context_id({"other": 1})), "assay_context"),
    ("different dataset", dict(dataset_sha256="c" * 64), "dataset_hash"),
    ("wrong coordinates (reference)", dict(ref_sha=E.reference_hash([183, 184, 227, 229])), "reference_coordinates"),
    ("wrong coordinates (positions)", dict(positions=[183, 184, 227, 229]), "reference_coordinates"),
    ("prediction masquerading", dict(kind="predicted"), "kind_observed"),
    ("simulated", dict(kind="simulated"), "kind_observed"),
    ("withdrawn", dict(status="withdrawn"), "status_active"),
    ("superseded", dict(status="superseded"), "status_active"),
    ("units", dict(units="percent of wild type"), "units"),
])
def test_invalid_evidence_is_not_reused_and_does_not_support_a_certificate(name, claim_kw, guard):
    st = E.EvidenceStore(); c = fx(**claim_kw); st.add(c)
    d = st.lookup("VFVS", REQ)
    assert d["decision"] == "assay_required", name
    assert guard in d["rejected"][0]["failed_guards"]
    s = st.supports_certificate([c["id"]], REQ)
    assert s["supported"] is False and guard in s["problems"][0]["failed_guards"]


def test_tampered_value_breaks_id_integrity():
    st = E.EvidenceStore(); c = fx(); st.add(c)
    st.by_id[c["id"]]["value"]["score_micro"] = 999999        # edited without recomputing the id
    d = st.lookup("VFVS", REQ)
    assert d["decision"] == "assay_required" and "id_integrity" in d["rejected"][0]["failed_guards"]


def test_withdrawing_or_deleting_evidence_changes_the_decision():
    st = E.EvidenceStore(); c = fx(); st.add(c)
    assert st.lookup("VFVS", REQ)["decision"] == "reuse"
    st.withdraw(c["id"])
    assert st.lookup("VFVS", REQ)["decision"] == "assay_required"
    st2 = E.EvidenceStore(); st2.add(fx()); st2.remove(fx()["id"])
    assert st2.lookup("VFVS", REQ)["decision"] == "assay_required"


def test_a_valid_second_fact_is_found_after_an_invalid_one():
    st = E.EvidenceStore(); st.add(fx(kind="predicted")); good = fx(); st.add(good)
    d = st.lookup("VFVS", REQ)
    assert d["decision"] == "reuse" and d["evidence_id"] == good["id"] and len(d["rejected"]) == 1


def test_certificate_support_rules():
    st = E.EvidenceStore(); a, b = fx("VFVS"), fx("VFMS", 5); st.add(a); st.add(b)
    assert st.supports_certificate([a["id"], b["id"]], REQ)["supported"] is True
    assert st.supports_certificate([], REQ)["supported"] is False                    # empty is not a pass
    assert st.supports_certificate([a["id"], "0" * 64], REQ)["supported"] is False    # unknown id
    st.by_id[b["id"]]["kind"] = "predicted"
    assert st.supports_certificate([a["id"], b["id"]], REQ)["supported"] is False


@pytest.mark.parametrize("guard,claim_kw", [("assay_context", dict(ctx_id=E.context_id({"o": 1}))), ("kind_observed", dict(kind="predicted")),
                                            ("status_active", dict(status="withdrawn")), ("reference_coordinates", dict(positions=[1, 2, 3, 4])),
                                            ("dataset_hash", dict(dataset_sha256="d" * 64)), ("units", dict(units="x"))])
def test_guard_mutant_lets_the_matching_fault_through(guard, claim_kw):
    c = fx(**claim_kw)
    ok = E.EvidenceStore(); ok.add(c)
    mut = E.EvidenceStore(disabled_guards=frozenset([guard])); mut.add(c)
    assert ok.lookup("VFVS", REQ)["decision"] == "assay_required"
    assert mut.lookup("VFVS", REQ)["decision"] == "reuse"           # negative control: the mutant is visibly wrong


def test_plain_sequence_cache_is_context_blind():
    cache = E.SequenceCache()
    cache.put("VFVS", fx(ctx_id=E.context_id({"other": 1}), kind="predicted", status="withdrawn"))
    assert cache.get("VFVS") is not None                              # documents the baseline's blindness
