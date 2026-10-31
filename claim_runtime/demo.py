"""Build the falsifiable reuse receipt: claim -> applicability -> calculation -> decision, with controls.

Every scenario stores request, response, claim IRI, record hash, assumptions, adapter version,
evidence ids, decision and reason. 'Decision changes' compare the SAME request before/after
removing, withdrawing or editing a claim/evidence item, or after disabling a guard (mutation).
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

from . import evidence as E
from . import reuse_benchmark as R
from . import trig
from .common import sha
from .records import default_store
from .service import ClaimService, GuardConfig

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "artifacts" / "claim_reuse"
DECLARED = {"label": "HYPOTHETICAL SCENARIO", "declared_by": "demo author; not derived from any measurement"}

KIMURA_OK = {"claim": "kimura-fixation-probability", "task": "fixation_probability",
             "model": {"ploidy": "diploid", "selection": "genic_additive", "ne": "constant", "linkage": "none"},
             "s_source": {"kind": "declared_hypothetical", **DECLARED},
             "params": {"Ne": 500, "s": 0.01, "N_census_diploids": 500}}
KIMURA_HAPLOID_ECOLI = {**KIMURA_OK, "model": {**KIMURA_OK["model"], "ploidy": "haploid"}, "note": "E. coli-like haploid population"}
KIMURA_TRPB_DEFAULT = {"claim": "kimura-fixation-probability", "task": "fixation_probability",
                       "model": {"ploidy": "haploid", "selection": "genic_additive", "ne": "constant", "linkage": "none"},
                       "s_source": {"kind": "trpb_assay_growth_score", "genotype_from": "VFVS", "genotype_to": "AIKG",
                                    "dataset_sha256": "a631d8cf6c5b188a801555cc4117547a1bf8e294240e1757c2d2d78dcb25ee82"},
                       "params": {"Ne": 1000, "s": 0.0, "p": 0.0005}}
ROUTE = ["VFVS", "VFMS", "SFMS", "SIMS", "SIMG", "SIKG", "AIKG"]   # route from artifacts/integration/core_kappa2_route.input.json
KIMURA_TRAJ = {"claim": "kimura-fixation-probability", "task": "hypothetical_trajectory",
               "model": {"ploidy": "diploid", "selection": "genic_additive", "ne": "constant", "linkage": "none"},
               "s_source": {"kind": "declared_hypothetical", **DECLARED},
               "scenario": {"route": ROUTE, "per_step_s": [0.01, 0.01, -0.005, 0.01, 0.01, 0.01], "Ne": 1000, "N_census_diploids": 1000,
                            "derive_s_from_assay_scores": False}}
FISHER_OK = {"claim": "fisher-ftns", "task": "partial_change", "inference_type": "partial_change_selection_component",
             "variance_kind": "additive_genetic_variance_in_fitness",
             "conditions": {"average_effects_held_fixed": True, "environment_fixed": True, "frequency_independent": True},
             "params": {"V_A": 0.02, "mean_fitness": 1.1, "scale": "relative_discrete"}, "provenance": {**DECLARED}}
FISHER_STEPS = {**FISHER_OK, "inference_type": "every_mutation_step_improves_fitness"}
FISHER_TOTAL = {**FISHER_OK, "inference_type": "total_fitness_change"}
FISHER_CLONAL = {**FISHER_OK, "variance_kind": "clonal_genotypic_variance"}
FISHER_LANDSCAPE = {**FISHER_OK, "variance_kind": "landscape_score_variance"}
FISHER_ONE_LOCUS = {"claim": "fisher-ftns", "task": "one_locus_check", "inference_type": "partial_change_selection_component",
                    "params": {"p": 0.3, "w_AA": 1.2, "w_Aa": 1.2, "w_aa": 1.0}}
FISHER_ONE_LOCUS_ADDITIVE = {**FISHER_ONE_LOCUS, "params": {"p": 0.3, "w_AA": 1.2, "w_Aa": 1.1, "w_aa": 1.0}}


def short(resp):
    return {"status": resp["status"], "decision": resp["decision"], "reason_code": resp["reason_code"]}


def claim_scenarios(svc_factory) -> list:
    svc = svc_factory()
    out = []
    def add(name, req, expect, role, resp=None):
        resp = resp or svc.request(req)
        assert resp["status"] == expect, (name, resp["status"], resp.get("reason"))
        out.append({"scenario": name, "role": role, "request": req, "response": resp})
        return resp
    add("kimura_valid_calculation", KIMURA_OK, "computed", "existing Delphi math claim drives a SIMULATED calculation")
    add("kimura_hypothetical_trpb_route", KIMURA_TRAJ, "computed", "explicit hypothetical trajectory (route labels only; s declared)")
    add("kimura_refused_haploid_model_transfer", KIMURA_HAPLOID_ECOLI, "refused", "invalid model transfer: haploid population")
    add("kimura_refused_trpb_assay_score_as_s", KIMURA_TRPB_DEFAULT, "refused", "default TrpB request: growth score is not s; names missing mapping")
    add("fisher_valid_partial_change", FISHER_OK, "computed", "existing Delphi math claim, partial-change reading only")
    add("fisher_one_locus_dominance", FISHER_ONE_LOCUS, "computed", "exact check: total change != V_A/wbar under dominance")
    add("fisher_one_locus_additive", FISHER_ONE_LOCUS_ADDITIVE, "computed", "exact check: total == partial when dominance deviation is 0")
    add("fisher_refused_every_step_improves", FISHER_STEPS, "refused", "rejected inference 'Fisher proves every mutation step improves fitness'")
    add("fisher_refused_total_change", FISHER_TOTAL, "refused", "total-change reading refused")
    add("fisher_refused_clonal_variance", FISHER_CLONAL, "refused", "clonal genotype variance is not V_A")
    add("fisher_refused_landscape_variance", FISHER_LANDSCAPE, "refused", "TrpB score variance is not a population's V_A")
    return out


def decision_changes(base_store, make_service) -> list:
    """Same request, different claim state / guard state => different decision."""
    iri = "https://w3id.org/delphi/resource/claim/kimura-fixation-probability"
    rows = []
    def row(name, change, svc, req=KIMURA_OK, base_req=KIMURA_OK):
        before = make_service(base_store).request(base_req)
        after = svc.request(req)
        rows.append({"scenario": name, "change": change, "before": short(before), "after": short(after),
                     "decision_changed": before["decision"] != after["decision"],
                     "before_result": before.get("result"), "after_response": after})
    import copy as _c
    s = _c.deepcopy(base_store); s.delete(iri)
    row("kimura_claim_deleted", "claim record removed from the store", make_service(s))
    s = _c.deepcopy(base_store); s.withdraw(iri)
    row("kimura_claim_withdrawn", "claim status = withdrawn", make_service(s))
    s = _c.deepcopy(base_store); s.mark_unavailable(iri)
    row("kimura_claim_unavailable", "claim fetch failed (unavailable)", make_service(s))
    s = base_store.with_field(iri, "delphi:context", "Assumptions: (EDITED SYNTHETIC FIXTURE) haploid, linked loci.")
    row("kimura_claim_context_edited", "assumption text changed => content hash differs from the pinned/verified one", make_service(s))
    row("mutated_guard_ploidy", "MUTANT: ploidy guard disabled; haploid E. coli request now computes (wrong) => negative control detects the mutant",
        make_service(base_store, GuardConfig(frozenset(["ploidy_diploid"]))), req=KIMURA_HAPLOID_ECOLI, base_req=KIMURA_HAPLOID_ECOLI)
    row("mutated_guard_s_source", "MUTANT: assay-score guard disabled; TrpB assay score would be treated as s",
        make_service(base_store, GuardConfig(frozenset(["ploidy_diploid", "s_source_not_assay"]))), req=KIMURA_TRPB_DEFAULT, base_req=KIMURA_TRPB_DEFAULT)
    row("mutated_guard_fisher_steps", "MUTANT: inference guard disabled; 'every step improves' request is no longer refused",
        make_service(base_store, GuardConfig(frozenset(["inference_partial_only"]))), req=FISHER_STEPS, base_req=FISHER_STEPS)
    return rows


def evidence_scenarios(shards: Path) -> dict:
    from . import trpb_data
    land, dsha = trpb_data.load_landscape()
    traces = R.load_traces(shards)
    proto = json.loads((ART / "protocol.json").read_text())
    order = R.campaign_order(traces, proto)
    ff = R.FactFactory(land, dsha)
    first = {}
    hit = None
    for ci, key in enumerate(order):
        for n, actor, code, rec in traces[key]:
            if code in first and first[code][0] != key:
                hit = (ci, key, n, code, first[code]); break
            first.setdefault(code, (key, n))
        if hit:
            break
    ci, key, n, code, (src_key, src_n) = hit
    name = lambda k: "%s/%s/%s" % k
    fact = ff.fact(code, name(src_key) + "#n=%d" % src_n)
    store = E.EvidenceStore()
    assert store.add(fact) == "added"
    dup = store.add(copy.deepcopy(fact))
    req = ff.req
    out = {"campaign_order": "protocol.json", "first_cross_campaign_repeat": {
        "requesting_campaign": name(key), "campaign_index": ci, "request_number": n, "genotype": ff.decode(code),
        "first_assayed_by": name(src_key), "first_request_number": src_n}}
    out["requirement"] = req.__dict__
    out["same_context_reuse"] = {"decision": store.lookup(ff.decode(code), req), "evidence": fact, "duplicate_import": dup,
                                 "evidence_count_after_duplicate": len(store.by_id)}
    ctx2 = dict(ff.ctx, readout="SYNTHETIC LABEL: a different selection medium / readout")
    out["changed_assay_context"] = {"requested_context_note": ctx2["readout"],
                                    "decision": store.lookup(ff.decode(code), E.Requirement(dsha, E.context_id(ctx2), ff.ref))}
    out["wrong_coordinates"] = {"decision": store.lookup(ff.decode(code), E.Requirement(dsha, ff.ctx_id, E.reference_hash([183, 184, 227, 229])))}
    pred = copy.deepcopy(fact); pred["kind"] = "predicted"; pred["provenance"] = {"synthetic_fixture": "prediction formatted as an observation"}
    pred["id"] = E.claim_id(pred)
    s2 = E.EvidenceStore(); s2.add(pred)
    out["prediction_masquerading"] = {"decision": s2.lookup(ff.decode(code), req)}
    s3 = E.EvidenceStore(); s3.add(copy.deepcopy(fact)); s3.withdraw(fact["id"])
    out["withdrawn"] = {"decision": s3.lookup(ff.decode(code), req)}
    s4 = E.EvidenceStore(); s4.add(copy.deepcopy(fact)); s4.remove(fact["id"])
    out["deleted"] = {"decision": s4.lookup(ff.decode(code), req)}
    # certificate support: first 6 distinct genotypes of the requesting campaign
    ids, s5 = [], E.EvidenceStore()
    for _, _, c2, _ in traces[key][:6]:
        f2 = ff.fact(c2, name(key)); s5.add(f2); ids.append(f2["id"])
    ok = s5.supports_certificate(ids, req)
    s5.by_id[ids[2]]["kind"] = "predicted"
    out["certificate_support"] = {"evidence_ids": ids, "all_observed_same_context": ok,
                                  "after_one_item_becomes_predicted": s5.supports_certificate(ids, req),
                                  "empty_set": s5.supports_certificate([], req)}
    out["recorded_request_accounting"] = {"requests_in_campaign": len(traces[key]),
                                          "note": "reuse here avoids the one recorded request shown; see reuse_benchmark.json for totals; not an adaptive-policy uplift"}
    out["fact_for_trig"] = fact
    return out


def build(shards: Path | None, out_dir: Path, created: str, receipt_ok=True) -> dict:
    store = default_store()
    mk = lambda st, guards=None: ClaimService(st, guards=guards, require_verified=True)
    scen = claim_scenarios(lambda: mk(store))
    changes = decision_changes(store, mk)
    res = {"kind": "claim-reuse-demo-receipt/v1", "generated_at_utc": created,
           "labels": "claim computations are SIMULATED/hypothetical; evidence reuse reuses OBSERVED source-table scores; nothing here is a new measurement or biological result",
           "claim_scenarios": scen, "decision_changes": changes}
    if shards:
        ev = evidence_scenarios(shards)
        res["evidence_scenarios"] = {k: v for k, v in ev.items() if k != "fact_for_trig"}
        np_dir = out_dir / "nanopubs"; np_dir.mkdir(exist_ok=True)
        (np_dir / "claim-use-kimura-valid.trig").write_text(trig.claim_use_trig("claim-use-kimura-valid", scen[0]["response"], created))
        (np_dir / "claim-use-kimura-refused-trpb.trig").write_text(trig.claim_use_trig("claim-use-kimura-refused-trpb", scen[3]["response"], created))
        (np_dir / "claim-use-fisher-refused-steps.trig").write_text(trig.claim_use_trig("claim-use-fisher-refused-steps", scen[7]["response"], created))
        (np_dir / "evidence-reuse-same-context.trig").write_text(trig.evidence_reuse_trig("evidence-reuse-same-context", ev["same_context_reuse"]["decision"] | {"decision": "reuse"}, ev["fact_for_trig"], created))
    res["receipt_sha256_body"] = sha({k: v for k, v in res.items() if k != "generated_at_utc"})
    return res
