"""Scope-verdict nanopublications: PREPARE, conform, sign LOCALLY, verify. Never publishes.

Design (docs/scope-desk-nanopub.md): one verdict -> one nanopublication whose assertion is a schema:ClaimReview of the
classical result (cited by the trusty URI of its already-published Delphi nanopublication) for ONE parameter regime.

Hard rules honoured here (morphoswarm SPEC-007):
  * http(s) IRIs only; no urn:, ms:, example.org; no new ontology namespace is minted (rule 5/7): only schema.org, PROV,
    Dublin Core, RDFS, nanopub-core terms, GitHub URLs of this repository, and the cited Delphi nanopub URI.
  * temporary base against which signing rewrites to a trusty URI; dct:created pinnable (FALSIFY_NP_CREATED) so rebuilds
    are byte-identical (rule 14).
  * corrections are NEW nanopubs with npx:supersedes (same key); retraction builder provided (rules 2, 3, 6).
  * Lean witness fields are HELD by default (rule 21: no Lean result is published until a gate-verdict term exists).
  * There is NO publish function in this module or in falsify/np_sign. Publishing is a separate, human-authorized act.
  * Caller-supplied claim text and caller labels are never written into a nanopublication.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from . import SERVICE_VERSION
from .engine import PROPOSITION

REPO_URL = "https://github.com/kganjam/delphi-evolve"
PROFILE_IRI = REPO_URL + "/blob/main/docs/scope-desk-nanopub.md"
# The published Delphi nanopublication of the classical result (verified signature + pin match; see artifacts/falsify_np).
CLASSICAL_RESULT = {
    "turing-ddi": {
        "np_uri": "https://w3id.org/np/RAaQ-9SCjYC7GBJ0ZtrPcVNxZBB7z-VNAdWa8ImGAi610",
        "claim_iri": "https://w3id.org/delphi/resource/claim/turing-ddi",
        "statement": "Turing diffusion-driven instability: a homogeneous steady state of two reacting chemicals that is stable without "
                     "diffusion can become unstable to spatial perturbations when the chemicals diffuse at different rates "
                     "(linearization about a homogeneous steady state, fixed domain, no growth or mechanics).",
    }}
TEMP = "http://purl.org/nanopub/temp/scopedesk/np"
LICENSE = "https://creativecommons.org/licenses/by/4.0/"      # matches the cited Delphi nanopub; the owner confirms before publishing
OUTCOME_TEXT = {
    "survived": "the classical result's instability DOES occur (an admissible mode grows linearly) in this regime",
    "refuted": "the classical result's instability does NOT occur (no admissible mode grows linearly) in this regime",
}
ALLOWED_NS = ("https://schema.org/", "http://www.w3.org/ns/prov#", "http://purl.org/dc/terms/", "http://www.w3.org/2000/01/rdf-schema#",
              "http://www.w3.org/1999/02/22-rdf-syntax-ns#", "http://www.w3.org/2001/XMLSchema#", "http://www.nanopub.org/nschema#",
              "http://purl.org/nanopub/x/", "http://purl.org/nanopub/temp/", "https://w3id.org/np/", REPO_URL + "/",
              "https://creativecommons.org/licenses/by/4.0/")
FORBIDDEN = (re.compile(r"<urn:"), re.compile(r"<ms:"), re.compile(r"example\.org"), re.compile(r"<ipfs:"))   # ipfs allowed by verifier, held until pinned


class NotPublishable(Exception):
    pass


def esc(s) -> str:
    return json.dumps(str(s), ensure_ascii=False)


def regime_sha256(res: dict) -> str:
    """Content hash of exactly the parameter regime + proposition (no caller identity, no claim text)."""
    i = res["inputs"]
    reg = {"proposition": PROPOSITION, "jacobian": i["jacobian"], "diffusivities": i["diffusivities"], "domain": i["domain"],
           "kinetics_source": res["kinetics"]["source"]}
    return hashlib.sha256(json.dumps(reg, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def record_from_response(res: dict, code_commit: str, include_lean: bool = False) -> dict:
    """Validate that a falsify response may be nanopublished and return the record the builder serializes."""
    if res.get("verdict") == "refused":
        raise NotPublishable("refused requests are not published")
    out = res["adjudication"]["outcome"]
    if out not in ("survived", "refuted"):
        raise NotPublishable(f"outcome {out!r} is not published (no governed template for unresolved results; SPEC-007 open question 6)")
    if res.get("basis") != "delphi_claim_backed_calculation" or res["delphi_claim_basis"].get("reuse_status") != "source_authorized":
        raise NotPublishable("source pin not verified: a generic calculation is not published as Delphi-claim reuse")
    if not re.fullmatch(r"[0-9a-f]{40}", code_commit or ""):
        raise NotPublishable("code_commit must be a full 40-hex git commit that has been pushed")
    rec = {"classical": CLASSICAL_RESULT["turing-ddi"], "outcome": out, "verdict": res["verdict"], "regime": res["inputs"],
           "kinetics": res["kinetics"]["source"], "regime_sha256": regime_sha256(res), "engine_version": res["service_version"],
           "code_commit": code_commit, "receipt_id": res.get("receipt_id"),
           "unstable_witness": res["modes"]["unstable"][:5], "unstable_count": res["modes"]["unstable_count"],
           "source_check_sha256": res["delphi_claim_basis"]["source_check"].get("content_sha256"),
           "critical_length": (res.get("critical_length") or {}).get("length_over_pi_between") if (res.get("critical_length") or {}).get("status") == "verified" else None,
           "independent": {k: v.get("agrees", v.get("agrees_with_exact_verdict")) for k, v in res.get("independent_checks", {}).items()}}
    lean = res.get("lean") or {}
    if include_lean and lean.get("status") == "checked":
        rec["lean"] = {"source_sha256": lean["source_sha256"], "axioms": lean["axioms"], "lean_version": lean.get("lean_version")}
    return rec


def _pv(idx, name, value):
    return f"  sub:p{idx} a schema:PropertyValue ; schema:name {esc(name)} ; schema:value {esc(value)} .\n"


def build_trig(rec: dict, created: str | None = None, supersedes: str | None = None) -> str:
    created = created or os.environ.get("FALSIFY_NP_CREATED")
    if not created or not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", created):
        raise NotPublishable("dct:created must be pinned explicitly (arg or FALSIFY_NP_CREATED), format YYYY-MM-DDTHH:MM:SSZ")
    c, reg = rec["classical"], rec["regime"]
    d = reg["domain"]
    props = [("regime_sha256", rec["regime_sha256"]), ("kinetics", rec["kinetics"]), ("jacobian", json.dumps(reg["jacobian"])),
             ("diffusivities", json.dumps(reg["diffusivities"])), ("dimension", d["dimension"]), ("boundary", d["boundary"]),
             ("length", json.dumps(d["length_spec"])), ("length_unit", d["length_unit"]), ("verdict", rec["verdict"]),
             ("outcome", rec["outcome"]), ("unstable_mode_count", rec["unstable_count"]),
             ("unstable_mode_witness_exact", json.dumps(rec["unstable_witness"])),
             ("critical_length_over_pi_verified_bracket", json.dumps(rec["critical_length"]) if rec["critical_length"] else "not_established"),
             ("independent_checks_agree", json.dumps(rec["independent"], sort_keys=True)),
             ("engine_version", rec["engine_version"]), ("evidence_type", "model-derived; observed: none"),
             ("scope_limit", "linear stability of the declared two-species linearization only; no nonlinear pattern, biological, wet-lab or clinical implication")]
    if "lean" in rec:
        props += [("lean_source_sha256", rec["lean"]["source_sha256"]), ("lean_axioms", json.dumps(rec["lean"]["axioms"])),
                  ("lean_status", "kernel accepted the generated theorem as stated; NOT an anti-triviality (L2) verdict")]
    pv = "".join(_pv(i, n, v) for i, (n, v) in enumerate(props))
    refs = ", ".join(f"sub:p{i}" for i in range(len(props)))
    label = f"Scope verdict: {c['claim_iri'].rsplit('/', 1)[-1]} on regime {rec['regime_sha256'][:12]}: {rec['outcome']}"
    sup = f"    npx:supersedes <{supersedes}> ;\n" if supersedes else ""
    return f"""@prefix this: <{TEMP}> .
@prefix sub: <{TEMP}#> .
@prefix np: <http://www.nanopub.org/nschema#> .
@prefix npx: <http://purl.org/nanopub/x/> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix dct: <http://purl.org/dc/terms/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix schema: <https://schema.org/> .

sub:Head {{
  this: a np:Nanopublication ;
    np:hasAssertion sub:assertion ;
    np:hasProvenance sub:provenance ;
    np:hasPublicationInfo sub:pubinfo .
}}

sub:assertion {{
  sub:review a schema:ClaimReview ;
    schema:name {esc(label)} ;
    schema:claimReviewed {esc(PROPOSITION)} ;
    schema:itemReviewed <{c['np_uri']}> ;
    schema:reviewRating sub:rating ;
    schema:additionalProperty {refs} .
  sub:rating a schema:Rating ;
    schema:alternateName {esc(rec['outcome'])} ;
    schema:ratingExplanation {esc(OUTCOME_TEXT[rec['outcome']] + '. Classical result cited: ' + c['statement'])} .
{pv}}}

sub:provenance {{
  sub:assertion prov:wasAttributedTo <{REPO_URL}> ;
    prov:wasDerivedFrom <{c['np_uri']}>, <{REPO_URL}/tree/{rec['code_commit']}/falsify> ;
    prov:wasGeneratedBy sub:generation .
  <{REPO_URL}> a prov:SoftwareAgent ; rdfs:label "delphi-evolve falsify service (software; exact-rational engine, optional Lean checker)" .
  sub:generation a prov:Activity ;
    prov:wasAssociatedWith <{REPO_URL}> ;
    rdfs:comment {esc("Computed by falsify " + rec['engine_version'] + " at the cited commit; receipt id " + str(rec['receipt_id']) + ". Source pin of the cited Delphi record verified (content sha256 " + str(rec['source_check_sha256']) + ").")} .
}}

sub:pubinfo {{
  this: dct:created "{created}"^^xsd:dateTime ;
    dct:license <{LICENSE}> ;
    dct:conformsTo <{PROFILE_IRI}> ;
    npx:hasNanopubType schema:ClaimReview ;
    npx:introduces sub:review ;
{sup}    rdfs:label {esc(label)} .
}}
"""


def build_retraction(target_uri: str, reason: str, created: str | None = None) -> str:
    created = created or os.environ.get("FALSIFY_NP_CREATED")
    if not created:
        raise NotPublishable("dct:created must be pinned")
    return f"""@prefix this: <{TEMP}> .
@prefix sub: <{TEMP}#> .
@prefix np: <http://www.nanopub.org/nschema#> .
@prefix npx: <http://purl.org/nanopub/x/> .
@prefix dct: <http://purl.org/dc/terms/> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
sub:Head {{ this: a np:Nanopublication ; np:hasAssertion sub:assertion ; np:hasProvenance sub:provenance ; np:hasPublicationInfo sub:pubinfo . }}
sub:assertion {{ sub:retraction npx:retracts <{target_uri}> . }}
sub:provenance {{ sub:assertion prov:wasAttributedTo <{REPO_URL}> . }}
sub:pubinfo {{ this: dct:created "{created}"^^xsd:dateTime ; rdfs:label {esc("Retraction: " + reason[:120])} ; rdfs:comment {esc(reason)} . }}
"""


def conform(trig: str) -> list[str]:
    """Return a list of violations (empty = conforms). Lightweight textual conformance; nanopub-rs does the real parse on signing."""
    bad = []
    code = re.sub(r'"(?:[^"\\]|\\.)*"', '""', trig)          # IRIs are scanned outside string literals
    for g in ("Head", "assertion", "provenance", "pubinfo"):
        if len(re.findall(rf"^sub:{g}\s*\{{", trig, flags=re.M)) != 1:
            bad.append(f"graph sub:{g} must appear exactly once")
    for rx in FORBIDDEN:
        if rx.search(code):
            bad.append(f"forbidden IRI scheme/host: {rx.pattern}")
    for m in re.findall(r"<([^>\s]*)>", code):
        if not m.startswith(("http://", "https://")):
            bad.append(f"non-http(s) IRI: {m}")
        elif m != REPO_URL and not m.startswith(ALLOWED_NS):
            bad.append(f"IRI outside allowed namespaces (rule 5/7): {m}")
    for pfx, ns in re.findall(r"@prefix\s+(\w*):\s*<([^>]+)>", code):
        if not ns.startswith(ALLOWED_NS):
            bad.append(f"prefix {pfx}: points outside allowed namespaces: {ns}")
    return bad


# ---- local sign / verify through the pinned @nanopub/sign (no network, no publish)
NP_DIR = Path(__file__).resolve().parent / "np_sign"


def _node(args, timeout=60):
    if not (NP_DIR / "node_modules").exists():
        raise RuntimeError("run `npm ci --ignore-scripts` in falsify/np_sign first")
    p = subprocess.run(["node", "--no-warnings", *args], cwd=NP_DIR, capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout + p.stderr).strip()


def sign_local(unsigned: Path, key_pem: Path, out: Path, name="local-throwaway") -> dict:
    if str(key_pem.resolve()).startswith(str(Path(__file__).resolve().parent.parent)):
        raise RuntimeError("signing keys must live outside the repository (SPEC-007 rule 18)")
    code, o = _node(["sign.mjs", str(unsigned), str(key_pem), str(out), name])
    if code:
        raise RuntimeError("sign failed: " + o[-300:])
    return json.loads(o.splitlines()[-1])


def verify_signed(path: Path) -> dict:
    code, o = _node(["check.mjs", str(path)])
    return json.loads(o.splitlines()[-1]) | {"exit": code}


# ---- queries (read-only SPARQL against Nanopub Query)
QUERY_ENDPOINT = "https://query.knowledgepixels.com/repo/full"
PREFIXES = ("PREFIX np: <http://www.nanopub.org/nschema#>\nPREFIX npx: <http://purl.org/nanopub/x/>\nPREFIX dct: <http://purl.org/dc/terms/>\n"
            "PREFIX schema: <https://schema.org/>\nPREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n")


def q_by_regime(regime_hash: str) -> str:
    assert re.fullmatch(r"[0-9a-f]{64}", regime_hash)
    return PREFIXES + f"""SELECT ?np ?outcome ?label WHERE {{
  GRAPH ?pi {{ ?np dct:conformsTo <{PROFILE_IRI}> ; rdfs:label ?label . }}
  GRAPH ?a {{ ?r schema:additionalProperty ?p1, ?p2 .
             ?p1 schema:name "regime_sha256" ; schema:value "{regime_hash}" .
             ?p2 schema:name "outcome" ; schema:value ?outcome . }}
}} LIMIT 20"""


def q_all_verdicts(limit=100) -> str:
    return PREFIXES + f"""SELECT ?np ?label WHERE {{ GRAPH ?pi {{ ?np dct:conformsTo <{PROFILE_IRI}> ; rdfs:label ?label . }} }} ORDER BY ?label LIMIT {int(limit)}"""


def q_introduces(claim_iri: str) -> str:
    return PREFIXES + f"SELECT ?np WHERE {{ GRAPH ?g {{ ?np npx:introduces <{claim_iri}> }} }} LIMIT 5"


def run_query(sparql: str, endpoint=QUERY_ENDPOINT, timeout=30) -> dict:
    import urllib.parse
    import urllib.request
    req = urllib.request.Request(endpoint + "?" + urllib.parse.urlencode({"query": sparql}),
                                 headers={"Accept": "application/sparql-results+json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())
