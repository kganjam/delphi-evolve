"""Service tests: version pinning, deletion/withdrawal/edit => refusal, model-transfer refusal,
TrpB assay score != s, Fisher inference gating, receipts, and mutation of guards."""
import copy
import json
from pathlib import Path

import pytest

from claim_runtime import demo as D
from claim_runtime import fisher as F
from claim_runtime import mutation as M
from claim_runtime.common import sha, sha_file
from claim_runtime.records import REC_DIR, default_store, make_pins
from claim_runtime.service import (ADAPTERS, ClaimService, GuardConfig, adapter_source_sha, load_pins)

KIM = "https://w3id.org/delphi/resource/claim/kimura-fixation-probability"
FIS = "https://w3id.org/delphi/resource/claim/fisher-ftns"


@pytest.fixture
def receipt(tmp_path):
    """TEST-ONLY verification receipt computed from the live files (the real one is written by `claim_runtime verify`)."""
    pins = make_pins()
    rec = {"adapters": {aid: {"adapter_source_sha256": adapter_source_sha(aid), "claim_content_sha256": pins[cid]["content_sha256"]}
                        for cid, (aid, _) in ADAPTERS.items()},
           "tests": {"exit": 0}, "mutation": {"exit": 0}}
    p = tmp_path / "receipt.json"
    p.write_text(json.dumps(rec))
    return p


@pytest.fixture
def svc(receipt):
    return lambda store=None, guards=None: ClaimService(store or default_store(), guards=guards, receipt_path=receipt)


def test_valid_kimura_response_is_self_describing(svc):
    r = svc().request(D.KIMURA_OK)
    assert r["status"] == "computed" and r["decision"] == "compute"
    assert 0 < r["result"]["fixation_probability"] < 1
    cu = r["claim_use"]
    assert cu["iri"] == KIM and cu["delphi_source"] == "network"
    assert cu["nanopubs"] == ["https://w3id.org/np/RA76F4g68zgxUhMgNanl8KsuUwKDJhYuUgXowdNzSsnMQ"]
    assert cu["record_response_sha256"] == sha_file(REC_DIR / "kimura-fixation-probability.network.json")
    assert r["adapter"]["version"] == "1.0.0" and r["adapter"]["hand_authored"] is True
    assert r["adapter"]["source_sha256"] == adapter_source_sha(r["adapter"]["id"])
    assert "constant effective population size Ne" in r["assumptions"]["recorded_by_delphi"]
    assert r["verification"]["status"] == "verified"
    assert "SIMULATED" in r["epistemic_status"]
    body = {k: v for k, v in r.items() if k != "response_sha256"}
    assert r["response_sha256"] == sha(body) and r["request_sha256"] == sha(D.KIMURA_OK)


def test_value_matches_formula(svc):
    import math
    r = svc().request(D.KIMURA_OK)
    p, x = 1 / 1000, 4 * 500 * 0.01
    assert r["result"]["fixation_probability"] == pytest.approx((1 - math.exp(-x * p)) / (1 - math.exp(-x)), rel=1e-12)
    assert r["result"]["neutral_expectation"] == p


def test_pins_match_committed_records_and_local_matches_network():
    pins, fresh = load_pins(), make_pins()
    assert pins == fresh
    assert all(v["local_record_content_matches_network"] for v in pins.values())


def test_haploid_model_transfer_refused(svc):
    r = svc().request(D.KIMURA_HAPLOID_ECOLI)
    assert r["status"] == "refused" and r["reason_code"] == "model_transfer_refused"
    assert "haploid" in r["reason"] and "diploid" in r["reason"] and r["result"] is None


def test_default_trpb_request_refuses_and_names_missing_mapping(svc):
    r = svc().request(D.KIMURA_TRPB_DEFAULT)
    assert r["status"] == "refused"
    assert "unsupported_quantity_conversion" in r["guards_failed"]
    txt = " ".join(r["missing_mapping"])
    for needle in ("growth score", "ploidy", "effective population size", "uncertainty"):
        assert needle in txt
    assert r["result"] is None


def test_assay_score_refused_even_with_diploid_model(svc):
    req = copy.deepcopy(D.KIMURA_TRPB_DEFAULT)
    req["model"]["ploidy"] = "diploid"
    r = svc().request(req)
    assert r["status"] == "refused" and r["reason_code"] == "unsupported_quantity_conversion"


def test_hypothetical_trajectory_runs_only_declared_scenarios(svc):
    r = svc().request(D.KIMURA_TRAJ)
    assert r["status"] == "computed"
    assert r["result"]["trpb_assay_scores_used"] is False
    assert "HYPOTHETICAL" in r["result"]["labels"]
    assert len(r["result"]["steps"]) == 6
    steps = r["result"]["steps"]
    assert steps[2]["declared_s"] < 0 and steps[2]["ratio_to_neutral"] < 1       # a deleterious declared step
    prod = 1.0
    for s in steps:
        prod *= s["fixation_probability"]
    assert r["result"]["product_of_step_fixation_probabilities"] == pytest.approx(prod)
    bad = copy.deepcopy(D.KIMURA_TRAJ)
    bad["scenario"]["derive_s_from_assay_scores"] = True
    assert svc().request(bad)["reason_code"] == "unsupported_quantity_conversion"
    bad2 = copy.deepcopy(D.KIMURA_TRAJ)
    bad2["s_source"] = {"kind": "trpb_assay_growth_score"}
    assert svc().request(bad2)["status"] == "refused"
    bad3 = copy.deepcopy(D.KIMURA_TRAJ)
    bad3["scenario"]["per_step_s"] = [0.01]
    assert svc().request(bad3)["reason_code"] == "invalid_parameters"


@pytest.mark.parametrize("field,val", [("selection", "dominant"), ("ne", "fluctuating"), ("linkage", "tight"), ("ploidy", None)])
def test_each_recorded_assumption_is_enforced(svc, field, val):
    req = copy.deepcopy(D.KIMURA_OK)
    req["model"][field] = val
    assert svc().request(req)["status"] == "refused"


def test_math_strings_are_never_evaluated(svc):
    for bad in ("500*2", "__import__('os').getcwd()", "1e3"):
        req = copy.deepcopy(D.KIMURA_OK)
        req["params"]["Ne"] = bad
        r = svc().request(req)
        assert r["status"] == "refused" and r["reason_code"] == "invalid_parameters"


def test_only_curated_claims_execute(svc):
    for cid in ("kimura-fixation-time", "https://w3id.org/delphi/resource/claim/hamilton-rule", "x**2"):
        r = svc().request({"claim": cid})
        assert r["reason_code"] == "no_adapter"


# -------- the causal link: removing/withdrawing/editing the claim changes the decision -------

def test_deleting_the_claim_changes_the_decision(svc):
    st = default_store()
    assert svc(st).request(D.KIMURA_OK)["decision"] == "compute"
    st.delete(KIM)
    r = svc(st).request(D.KIMURA_OK)
    assert r["decision"] == "refuse" and r["reason_code"] == "claim_unavailable" and r["result"] is None


def test_withdrawn_and_unavailable_claims_refuse(svc):
    for fn, code in (("withdraw", "claim_withdrawn"), ("mark_unavailable", "claim_unavailable")):
        st = default_store()
        getattr(st, fn)(KIM)
        assert svc(st).request(D.KIMURA_OK)["reason_code"] == code


def test_changed_claim_cannot_keep_old_verified_status(svc):
    st = default_store().with_field(KIM, "delphi:context", "Assumptions: edited")
    r = svc(st).request(D.KIMURA_OK)
    assert r["status"] == "refused" and r["reason_code"] == "claim_changed"
    for fld in ("skos:notation", "dct:description", "dct:source"):
        st = default_store().with_field(KIM, fld, "changed")
        assert svc(st).request(D.KIMURA_OK)["reason_code"] == "claim_changed"


def test_pin_check_mutant_is_noticed(svc):
    st = default_store().with_field(KIM, "delphi:context", "Assumptions: edited")
    mut = ClaimService(st, guards=GuardConfig(frozenset(["pin"])), require_verified=False).request(D.KIMURA_OK)
    assert mut["status"] == "computed"            # the mutant would silently compute: tests/mutation must see this


def test_verification_receipt_binding(tmp_path, receipt):
    st = default_store()
    # missing receipt
    r = ClaimService(st, receipt_path=tmp_path / "none.json").request(D.KIMURA_OK)
    assert r["reason_code"] == "unverified"
    # allow_unverified computes but says so
    r = ClaimService(st, require_verified=False, receipt_path=tmp_path / "none.json").request(D.KIMURA_OK)
    assert r["status"] == "computed" and r["verification"]["status"] == "unverified"
    # adapter hash drift
    rec = json.loads(receipt.read_text())
    rec["adapters"]["kimura-fixation-probability/diploid-genic-diffusion"]["adapter_source_sha256"] = "0" * 64
    receipt.write_text(json.dumps(rec))
    assert ClaimService(st, receipt_path=receipt).request(D.KIMURA_OK)["reason_code"] == "unverified"
    # failing tests recorded
    rec["adapters"]["kimura-fixation-probability/diploid-genic-diffusion"]["adapter_source_sha256"] = adapter_source_sha("kimura-fixation-probability/diploid-genic-diffusion")
    rec["tests"]["exit"] = 1
    receipt.write_text(json.dumps(rec))
    assert ClaimService(st, receipt_path=receipt).request(D.KIMURA_OK)["reason_code"] == "unverified"


# ------------------------------- Fisher --------------------------------------------------

def test_fisher_partial_change_value(svc):
    r = svc().request(D.FISHER_OK)
    assert r["status"] == "computed"
    assert r["result"]["partial_change_in_mean_fitness_due_to_selection"] == pytest.approx(0.02 / 1.1)
    assert r["result"]["not_a_total_change"] is True and "PREDICTED" in r["epistemic_status"]
    mal = copy.deepcopy(D.FISHER_OK)
    mal["params"] = {"V_A": 0.02, "scale": "malthusian"}
    assert svc().request(mal)["result"]["partial_change_in_mean_fitness_due_to_selection"] == 0.02
    assert r["claim_use"]["nanopubs"] == ["https://w3id.org/np/RAtLFqIIyu4r-GlMcBEfmDtbV-CHwWxQ49gVMtHIX6r48"]


def test_fisher_rejects_every_mutation_step_improves(svc):
    r = svc().request(D.FISHER_STEPS)
    assert r["status"] == "refused" and r["reason_code"] == "inference_refused"
    assert "particular mutation" in r["reason"] and "lean" in svc().request({**D.FISHER_STEPS, "inference_type": "route_step_nondecreasing"})["reason"]


@pytest.mark.parametrize("req,code", [(D.FISHER_TOTAL, "inference_refused"), (D.FISHER_CLONAL, "variance_refused"), (D.FISHER_LANDSCAPE, "variance_refused")])
def test_fisher_other_refusals(svc, req, code):
    assert svc().request(req)["reason_code"] == code


def test_fisher_conditions_required(svc):
    for k in ("average_effects_held_fixed", "environment_fixed", "frequency_independent"):
        req = copy.deepcopy(D.FISHER_OK)
        req["conditions"][k] = False
        assert svc().request(req)["reason_code"] == "conditions_not_met"
    req = copy.deepcopy(D.FISHER_OK)
    del req["conditions"]
    assert svc().request(req)["reason_code"] == "conditions_not_met"


def test_fisher_negative_variance_rejected(svc):
    req = copy.deepcopy(D.FISHER_OK)
    req["params"]["V_A"] = -1
    assert svc().request(req)["reason_code"] == "invalid_parameters"


def test_one_locus_identity_and_total_vs_partial(svc):
    dom = svc().request(D.FISHER_ONE_LOCUS)["result"]
    add = svc().request(D.FISHER_ONE_LOCUS_ADDITIVE)["result"]
    assert abs(dom["identity_residual"]) < 1e-12 and abs(add["identity_residual"]) < 1e-12
    assert add["total_change_exact"] == pytest.approx(add["partial_change_VA_over_wbar"], rel=1e-9)
    assert dom["total_change_exact"] != pytest.approx(dom["partial_change_VA_over_wbar"], rel=1e-3)
    assert dom["dominance_deviation_d"] != 0


# ---------------------- decision changes and guard mutants (the demo's own controls) -------

def test_demo_decision_changes(receipt):
    mk = lambda st, guards=None: ClaimService(st, guards=guards, receipt_path=receipt)
    rows = D.decision_changes(default_store(), mk)
    by = {r["scenario"]: r for r in rows}
    for name in ("kimura_claim_deleted", "kimura_claim_withdrawn", "kimura_claim_unavailable", "kimura_claim_context_edited"):
        assert by[name]["decision_changed"] and by[name]["before"]["decision"] == "compute" and by[name]["after"]["decision"] == "refuse"
    # mutated guards: refused before (original service), computes after?  `before` uses the ORIGINAL guards.
    for name in ("mutated_guard_ploidy", "mutated_guard_s_source", "mutated_guard_fisher_steps"):
        assert by[name]["before"]["decision"] == "refuse" and by[name]["after"]["decision"] == "compute"


def test_guard_mutants_all_detected():
    res = M.guard_mutants()
    assert res and all(m["killed"] for m in res), [m for m in res if not m["killed"]]


def test_trig_drafts_are_valid_unsigned_and_unpublished():
    rdflib = pytest.importorskip("rdflib")
    d = Path(__file__).resolve().parent.parent / "artifacts" / "claim_reuse" / "nanopubs"
    files = sorted(d.glob("*.trig"))
    assert len(files) >= 4
    for f in files:
        txt = f.read_text()
        assert "UNSIGNED DRAFT" in txt and "purl.org/nanopub/temp" in txt
        assert "RA" not in txt.split("sub:Head")[0]                       # no invented trusty URI for our own nanopub
        g = rdflib.Dataset()
        g.parse(data=txt, format="trig")
        assert {str(c.identifier).rsplit("/", 1)[-1] for c in g.contexts()} >= {"Head", "assertion", "provenance", "pubinfo"}


def test_trpb_default_reason_leads_with_quantity_conversion(svc):
    r = svc().request(D.KIMURA_TRPB_DEFAULT)
    assert r["reason_code"] == "unsupported_quantity_conversion" and "Assay growth scores are not s" in r["reason"]


def test_cli_examples_run_without_delphi_network_or_credentials():
    import os, subprocess, sys
    root = Path(__file__).resolve().parent.parent
    env = dict(os.environ, PYTHONPATH=str(root), CLAIM_RUNTIME_MUTANT_RUN="")
    def run(*a):
        return subprocess.run([sys.executable, "-m", "claim_runtime", *a], cwd=root, env=env, capture_output=True, text=True, timeout=60)
    if os.environ.get("CLAIM_RUNTIME_MUTANT_RUN") == "1" or os.environ.get("CLAIM_RUNTIME_VERIFYING") == "1":
        pytest.skip("receipt-dependent test: skipped while the receipt is being (re)generated or in mutant copies")
    ok = run("request", "claim_runtime/examples/kimura_valid.json")
    assert ok.returncode == 0 and json.loads(ok.stdout)["status"] == "computed"
    no = run("request", "claim_runtime/examples/kimura_trpb_default_refused.json")
    assert no.returncode == 2 and json.loads(no.stdout)["reason_code"] == "unsupported_quantity_conversion"
    ev = run("evidence", "claim_runtime/examples/evidence_lookup_prediction_refused.json")
    assert ev.returncode == 2 and "kind_observed" in ev.stdout
    assert run("evidence", "claim_runtime/examples/evidence_lookup_reuse.json").returncode == 0


def test_committed_verification_receipt_matches_current_adapters():
    import os
    if os.environ.get("CLAIM_RUNTIME_MUTANT_RUN") == "1" or os.environ.get("CLAIM_RUNTIME_VERIFYING") == "1":
        pytest.skip("receipt-dependent test: skipped while the receipt is being (re)generated or in mutant copies")
    from claim_runtime.service import RECEIPT_PATH, verification_status
    pins = load_pins()
    for cid, (aid, _) in ADAPTERS.items():
        assert verification_status(aid, pins[cid]["content_sha256"], RECEIPT_PATH)["status"] == "verified"


def test_response_separates_source_mapping_operationalization_and_result(svc):
    r = svc().request(D.KIMURA_OK)
    L = r["provenance_layers"]
    assert set(L) == {"source_record", "curated_adapter_mapping", "new_operationalization", "result_kind"}
    assert "never an observed result" in L["result_kind"]
