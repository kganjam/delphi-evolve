"""Claim service: request -> (pin check, verification check, applicability guards) -> compute or refuse.

Fail-closed order:
  1. claim must exist in the ClaimStore and be 'active' (deleted/withdrawn/unavailable -> refused)
  2. the live record's content hash must equal the hash the adapter was pinned to (else refused)
  3. the adapter source + claim hash must match a passing verification receipt
     (else refused unless allow_unverified, which marks the response 'unverified')
  4. applicability guards on the request (model, quantity semantics, parameter domain)
  5. only then the hand-written computation
Every response is a self-describing record (request hash, claim IRI + nanopub IRI, record
response hash, adapter id/version/source hash, assumptions, decision, reason).
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

from . import fisher as F
from . import kimura as K
from .common import ClaimStore, claim_iri, sha, sha_file

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PINS_PATH = HERE / "pins.json"
RECEIPT_PATH = ROOT / "artifacts" / "claim_reuse" / "verification_receipt.json"
# the executable adapter = the numerics module PLUS this file (guards live here); both are hashed
ADAPTER_FILES = {K.ADAPTER_ID: [HERE / "kimura.py", HERE / "service.py", HERE / "common.py"],
                 F.ADAPTER_ID: [HERE / "fisher.py", HERE / "service.py", HERE / "common.py"]}
ADAPTERS = {  # the ONLY executable claims
    K.CLAIM_ID: (K.ADAPTER_ID, K.ADAPTER_VERSION),
    F.CLAIM_ID: (F.ADAPTER_ID, F.ADAPTER_VERSION),
}

# Everything a TrpB growth score would need before it could mean a selection coefficient.
MISSING_TRPB_MAPPING = [
    "map from assay growth score (mu minus stop-codon background, pooled selection culture) to relative fitness 1+s in the evolving population's own environment",
    "ploidy/model: the TrpB assay organism is haploid E. coli; the Delphi claim is a diploid Wright-Fisher diffusion (4Ne s p). A haploid mapping (exponent 2Ns for haploid WF) is a different statement that this adapter does not implement",
    "the effective population size Ne of the population in which these variants would arise (not measured by the assay)",
    "dominance/genic assumption does not apply to a haploid; mutation supply, clonal interference and linkage are outside the claim's no-linkage assumption",
    "an uncertainty model for the conversion (two replicates do not give a calibrated error on s)",
]


@dataclass
class GuardConfig:
    """Applicability guards. `disabled` is for mutation testing only."""
    disabled: frozenset = field(default_factory=frozenset)

    def on(self, name: str) -> bool:
        return name not in self.disabled


KIMURA_GUARDS = ["pin", "ploidy_diploid", "genic_selection", "constant_ne", "no_linkage", "s_source_not_assay", "numeric_domain"]
FISHER_GUARDS = ["pin", "inference_partial_only", "variance_additive", "conditions_hold", "numeric_domain"]


def load_pins(path: Path = PINS_PATH) -> dict:
    return json.loads(Path(path).read_text())


def adapter_source_sha(adapter_id: str) -> str:
    return sha([sha_file(p) for p in ADAPTER_FILES[adapter_id]])


def verification_status(adapter_id: str, claim_content_sha: str, receipt_path: Path = RECEIPT_PATH) -> dict:
    p = Path(receipt_path)
    if not p.exists():
        return {"status": "unverified", "why": "no verification receipt"}
    r = json.loads(p.read_text())
    a = r.get("adapters", {}).get(adapter_id)
    if not a:
        return {"status": "unverified", "why": "adapter absent from receipt"}
    if a["adapter_source_sha256"] != adapter_source_sha(adapter_id):
        return {"status": "unverified", "why": "adapter source changed since verification"}
    if a["claim_content_sha256"] != claim_content_sha:
        return {"status": "unverified", "why": "claim content differs from the verified version"}
    if r.get("tests", {}).get("exit") != 0 or r.get("mutation", {}).get("exit") != 0:
        return {"status": "unverified", "why": "receipt records a failing test or mutation run"}
    return {"status": "verified", "receipt_sha256": sha_file(p), "tests_exit": 0, "mutation_exit": 0}


class ClaimService:
    def __init__(self, store: ClaimStore, pins: dict | None = None, guards: GuardConfig | None = None,
                 require_verified: bool = True, receipt_path: Path = RECEIPT_PATH):
        self.store = store
        self.pins = pins if pins is not None else load_pins()
        self.guards = guards or GuardConfig()
        self.require_verified = require_verified
        self.receipt_path = receipt_path

    # ---------------------------------------------------------------- envelope
    def _envelope(self, req: dict) -> dict:
        return {"schema": "claim-response/v1", "request": req, "request_sha256": sha(req)}

    def _finish(self, resp: dict) -> dict:
        resp["response_sha256"] = sha({k: v for k, v in resp.items() if k != "response_sha256"})
        return resp

    def _refuse(self, resp, code, reason, **extra):
        resp.update({"status": "refused", "decision": "refuse", "reason_code": code, "reason": reason, "result": None, **extra})
        return self._finish(resp)

    # ---------------------------------------------------------------- entry
    def request(self, req: dict) -> dict:
        resp = self._envelope(req)
        cid = req.get("claim")
        if not isinstance(cid, str):
            return self._refuse(resp, "bad_request", "request.claim must be a claim id string")
        short = cid.rsplit("/", 1)[-1]
        if short not in ADAPTERS:
            return self._refuse(resp, "no_adapter", f"no curated executable adapter for {cid!r}; only {sorted(ADAPTERS)} are supported (math strings are never evaluated)")
        adapter_id, adapter_version = ADAPTERS[short]
        iri = claim_iri(short)
        resp["adapter"] = {"id": adapter_id, "version": adapter_version, "hand_authored": True,
                           "source_sha256": adapter_source_sha(adapter_id)}
        entry = self.store.get(iri)
        if entry is None or entry.record is None:
            return self._refuse(resp, "claim_unavailable", "the Delphi claim record is not in the store (deleted or never fetched); the adapter keeps no cached authority", claim_use={"iri": iri})
        rec = entry.record
        resp["claim_use"] = {"iri": iri, "delphi_source": rec.source, "nanopubs": rec.nanopubs,
                             "record_response_sha256": rec.response_sha256,
                             "record_content_sha256": rec.content_sha256(),
                             "store_status": entry.status,
                             "nanopub_note": "network nanopub published by Delphi, not by this service; local drafts are not published"
                             if rec.source == "network" else "LOCAL record: not a published nanopub"}
        if entry.status != "active":
            return self._refuse(resp, "claim_" + entry.status, f"claim status is {entry.status!r}; withdrawn/unavailable claims cannot drive a computation")
        pin = self.pins.get(short)
        if self.guards.on("pin"):
            if pin is None or pin["content_sha256"] != rec.content_sha256():
                return self._refuse(resp, "claim_changed", "the claim record content differs from the version this adapter was reviewed against; re-review the adapter and re-pin", pinned_content_sha256=(pin or {}).get("content_sha256"))
        resp["claim_use"]["pinned_content_sha256"] = (pin or {}).get("content_sha256")
        ver = verification_status(adapter_id, rec.content_sha256(), self.receipt_path)
        resp["verification"] = ver
        if ver["status"] != "verified" and self.require_verified:
            return self._refuse(resp, "unverified", "adapter/claim pair has no passing verification receipt: " + ver["why"])
        resp["provenance_layers"] = {
            "source_record": f"Delphi {rec.source} record {iri} (response sha256 {rec.response_sha256[:16]}...); unchanged, status as published by Delphi",
            "curated_adapter_mapping": f"{adapter_id} v{adapter_version}: hand-authored translation of the record's math into code, bound to content hash {rec.content_sha256()[:16]}...",
            "new_operationalization": "the request itself (declared parameters/scenario) and any 'added_by_adapter' assumption; not part of the Delphi record",
            "result_kind": "simulated/predicted calculation from established mathematics; never an observed result",
        }
        handler = {K.CLAIM_ID: self._kimura, F.CLAIM_ID: self._fisher}[short]
        try:
            return self._finish(handler(req, resp))
        except ValueError as e:
            return self._refuse(resp, "invalid_parameters", str(e))

    # ---------------------------------------------------------------- Kimura
    def _kimura_guards(self, req, resp):
        g, m, sp = self.guards, req.get("model", {}) or {}, req.get("s_source", {}) or {}
        probs = []
        if g.on("s_source_not_assay"):
            kind = sp.get("kind")
            if kind == "declared_hypothetical":
                pass
            elif kind == "cited_estimate" and sp.get("citation") and sp.get("estimation_context"):
                pass
            else:
                probs.append(("unsupported_quantity_conversion",
                              f"s_source.kind={kind!r} is not a selection coefficient. Assay growth scores are not s; refusing. Missing: " + " | ".join(MISSING_TRPB_MAPPING)))
        if g.on("ploidy_diploid") and m.get("ploidy") != "diploid":
            probs.append(("model_transfer_refused",
                          f"ploidy={m.get('ploidy')!r}: the claim is a diploid Wright-Fisher diffusion (4Ne s p). Haploid populations (e.g. E. coli) have a different exponent; no haploid adapter exists. Missing mapping: variance-effective size and per-copy s for the haploid model"))
        if g.on("genic_selection") and m.get("selection") != "genic_additive":
            probs.append(("model_transfer_refused", f"selection={m.get('selection')!r}: record assumes genic (additive) selection"))
        if g.on("constant_ne") and m.get("ne") != "constant":
            probs.append(("model_transfer_refused", "record assumes constant effective size Ne"))
        if g.on("no_linkage") and m.get("linkage") != "none":
            probs.append(("model_transfer_refused", "record assumes no linkage to other selected sites"))
        return probs

    def _kimura(self, req, resp):
        task = req.get("task", "fixation_probability")
        resp["assumptions"] = {"recorded_by_delphi": K.RECORDED_ASSUMPTIONS, "added_by_adapter": K.ADAPTER_ADDED_ASSUMPTIONS}
        probs = self._kimura_guards(req, resp)
        if probs:
            code = probs[0][0]
            return self._refuse(resp, code, "; ".join(r for _, r in probs), guards_failed=[c for c, _ in probs],
                                missing_mapping=MISSING_TRPB_MAPPING if any(c == "unsupported_quantity_conversion" for c, _ in probs) else None)
        sp = req["s_source"]
        label = "SIMULATED (declared hypothetical scenario; not a measurement)" if sp["kind"] == "declared_hypothetical" \
            else "PREDICTED from a cited external estimate (not verified here)"
        resp["epistemic_status"] = label
        if task == "fixation_probability":
            pr = req.get("params", {})
            Ne, s = pr.get("Ne"), pr.get("s")
            if "p" in pr:
                p = pr["p"]
            elif "N_census_diploids" in pr:
                p = K.new_mutant_frequency(K._num("N_census_diploids", pr["N_census_diploids"]))
            else:
                raise ValueError("params needs p or N_census_diploids")
            u = K.fixation_probability(p, Ne, s)
            res = {"fixation_probability": u, "p": p, "Ne": Ne, "s": s, "neutral_expectation": p,
                   "ratio_to_neutral": (u / p if p else None), "sensitivity": K.sensitivity(p, Ne, s)}
            if abs(s) >= K.S_LARGE_WARNING:
                res["warning"] = f"|s| >= {K.S_LARGE_WARNING} (convention): outside the weak-selection regime of the diffusion derivation; see artifacts/claim_reuse/popgen_benchmark.json for exact-chain error"
            resp.update({"status": "computed", "decision": "compute", "reason_code": "ok",
                         "reason": "all applicability guards passed", "result": res})
            return resp
        if task == "hypothetical_trajectory":
            sc = req.get("scenario", {})
            if sc.get("derive_s_from_assay_scores"):
                return self._refuse(resp, "unsupported_quantity_conversion", "derive_s_from_assay_scores is not supported. Missing: " + " | ".join(MISSING_TRPB_MAPPING), missing_mapping=MISSING_TRPB_MAPPING)
            if sp["kind"] != "declared_hypothetical":
                raise ValueError("trajectory mode runs only explicit declared_hypothetical scenarios")
            route, ss, Ne = sc.get("route"), sc.get("per_step_s"), sc.get("Ne")
            if not isinstance(route, list) or len(route) < 2 or not isinstance(ss, list) or len(ss) != len(route) - 1:
                raise ValueError("scenario.route (>=2 genotypes) and scenario.per_step_s (len = steps) are required")
            N = K._num("scenario.N_census_diploids", sc.get("N_census_diploids"))
            p0 = K.new_mutant_frequency(N)
            steps, prod = [], 1.0
            for a, b, s in zip(route, route[1:], ss):
                u = K.fixation_probability(p0, Ne, s)
                prod *= u
                steps.append({"from": a, "to": b, "declared_s": s, "fixation_probability": u, "ratio_to_neutral": u / p0})
            resp.update({"status": "computed", "decision": "compute", "reason_code": "ok", "reason": "explicit hypothetical scenario",
                         "result": {"steps": steps, "product_of_step_fixation_probabilities": prod, "p0": p0, "Ne": Ne,
                                    "trpb_assay_scores_used": False,
                                    "labels": ["HYPOTHETICAL", "SIMULATED", "route genotypes are labels only; s values are declared, not derived from TrpB data"],
                                    "scenario_assumption_not_in_claim": "sequential fixation of single mutants (each step's mutant arises at 1/(2N) and the previous one is fixed); the product ignores mutation supply and waiting times"}})
            return resp
        raise ValueError(f"unknown task {task!r}")

    # ---------------------------------------------------------------- Fisher
    def _fisher(self, req, resp):
        g = self.guards
        resp["assumptions"] = {"recorded_by_delphi": F.RECORDED_CONDITIONS, "added_by_adapter": F.ADAPTER_ADDED_CONDITIONS}
        task = req.get("task", "partial_change")
        inf = req.get("inference_type")
        if g.on("inference_partial_only") and inf != F.ACCEPTED_INFERENCE:
            why = F.REFUSED_INFERENCES.get(inf, f"inference_type {inf!r} is not the partial-change reading; only {F.ACCEPTED_INFERENCE!r} is supported")
            return self._refuse(resp, "inference_refused", why)
        if task == "one_locus_check":
            pr = req["params"]
            res = F.one_locus_check(*(F._num(k, pr[k]) for k in ("p", "w_AA", "w_Aa", "w_aa")))
            resp.update({"status": "computed", "decision": "compute", "reason_code": "ok", "reason": "exact one-locus identity check",
                         "epistemic_status": "ANALYTIC/SIMULATED two-allele model; not an observation", "result": res})
            return resp
        vk = req.get("variance_kind")
        if g.on("variance_additive") and vk != F.ACCEPTED_VARIANCE:
            return self._refuse(resp, "variance_refused", F.REFUSED_VARIANCES.get(vk, f"variance_kind {vk!r} is not additive genetic variance in fitness"))
        cond = req.get("conditions", {}) or {}
        need = ("average_effects_held_fixed", "environment_fixed", "frequency_independent")
        missing = [c for c in need if cond.get(c) is not True]
        if g.on("conditions_hold") and missing:
            return self._refuse(resp, "conditions_not_met", "stated conditions not asserted true: " + ", ".join(missing) + ". The record: total change is false under dominance, epistasis, frequency dependence or a changing environment")
        pr = req.get("params", {})
        delta = F.partial_change(pr.get("V_A"), pr.get("mean_fitness"), pr.get("scale"))
        resp.update({"status": "computed", "decision": "compute", "reason_code": "ok", "reason": "partial-change reading with stated conditions asserted",
                     "epistemic_status": "PREDICTED selection-component change given the caller's declared V_A (V_A is not estimated here)",
                     "result": {"partial_change_in_mean_fitness_due_to_selection": delta, "scale": pr.get("scale"), "V_A": pr.get("V_A"),
                                "not_a_total_change": True}})
        return resp
