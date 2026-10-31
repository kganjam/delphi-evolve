"""Delphi claim -> Frontier Claim draft, preserving the ORIGINAL Delphi identifiers and versions.

What is preserved (all from the Delphi record itself, nothing invented):
  Draft.id            = the Delphi claim id            (e.g. `turing-ddi`, `darwin1859-ch02-04`)
  Draft.source_uri    = the Delphi claim IRI           (https://w3id.org/delphi/resource/claim/...)
  Claim.source_record_version = the claim's nanopub URI as Delphi reports it (`delphi_graph.nanopub`)
  prior_review.delphi_original = registry (production | test), domain, nanopub path, record licence,
                              creator/created/extractor, every field that has no Claim slot

What is deliberately NOT done:
  * the verbatim quote text is never copied: only its sha256, length and locator are kept. Quote text
    is third-party content whose rights the Delphi record does not state (and for Wolfram NKS states as
    "all rights reserved"). `content_available` is therefore always False and `license` None.
  * Delphi's recorded source hash is placed in `Source.content_sha256` ONLY after this adapter re-fetched
    the source and the hash matched. Otherwise it is kept under `prior_review` as "recorded, unverified".
  * Delphi's LLM assessments and `delphi_graph` truth scores are NOT evidence and are summarised only
    as counts, labelled as such.
  * `assumptions` / `limitations` stay empty: Delphi has no field for them.
"""
from __future__ import annotations

import re
import urllib.request
from collections import defaultdict

from .common import iso_utc, sha_bytes, sha_obj

ADAPTER_ID = "frontier_adapters.delphi_claim"
ADAPTER_VERSION = "0.1.0"
CLAIM_PREFIX = "https://w3id.org/delphi/resource/claim/"

P = {  # predicate IRIs -> short names (only the ones this adapter reads)
    "https://schema.org/text": "quote_text",
    "http://www.w3.org/ns/prov#hadPrimarySource": "primary_source",
    "http://www.w3.org/ns/prov#wasQuotedFrom": "work",
    "http://spdx.org/rdf/terms#checksumValue": "sha256",
    "http://purl.org/dc/terms/license": "record_license",
    "http://purl.org/dc/terms/created": "created",
    "http://purl.org/dc/terms/creator": "creator",
    "http://purl.org/dc/terms/rights": "rights",
    "http://purl.org/dc/terms/publisher": "publisher",
    "https://schema.org/pagination": "pagination",
    "https://schema.org/bookEdition": "edition",
    "http://purl.org/dc/terms/identifier": "identifier",
    "http://www.w3.org/ns/prov#wasDerivedFrom": "derived_from",
    "http://www.w3.org/2000/01/rdf-schema#seeAlso": "see_also",
    "http://www.w3.org/ns/prov#wasAssociatedWith": "extractor",
}


def _triples(mcp, claim_id: str) -> list[dict]:
    # NOTE: no '#' inside the string literal. The Delphi SPARQL endpoint treats '#' as a comment start even
    # inside quotes and then silently matches nothing (found the hard way). The assessment nanopubs live under
    # `assessments-unsigned/`, so "/unsigned/<id>.trig" selects only the claim's own four graphs.
    q = ('SELECT ?g ?s ?p ?o WHERE { GRAPH ?g { ?s ?p ?o } '
         f'FILTER(CONTAINS(STR(?g),"/unsigned/{claim_id}.trig")) }} ORDER BY ?g ?s ?p ?o LIMIT 400')
    rows = mcp.tool("delphi_sparql", {"query": q, "source": "local"})
    if not isinstance(rows, list) or not rows:
        raise LookupError(f"no nanopub graphs found for Delphi claim {claim_id!r}")
    graphs = {r["g"].rsplit("#", 1)[-1] for r in rows}
    missing = {"assertion", "provenance", "pubinfo"} - graphs
    if missing:  # fail loudly: a partial read would silently drop source/permission fields
        raise LookupError(f"claim {claim_id!r}: nanopub graphs incomplete, missing {sorted(missing)}")
    return rows


def collect(mcp, claim_id: str) -> tuple[dict, dict]:
    """Read one claim from the Delphi MCP. Returns (snapshot, transient).

    `snapshot` is JSON-safe, contains NO quote text and is what gets saved/hashed.
    `transient` holds the quote text for in-process verification only; callers must not persist it.
    """
    iri = CLAIM_PREFIX + claim_id
    rec = mcp.tool("delphi_get_claim", {"id": claim_id, "source": "local"})
    f = rec["fields"]
    triples = _triples(mcp, claim_id)
    by = defaultdict(list)
    for t in triples:
        name = P.get(t["p"])
        if name:
            by[name].append(t["o"])
    graph = None
    for x in mcp.tool("delphi_graph", {"text": f["rdfs:label"], "limit": 25})["claims"]:
        if x["id"] == claim_id:
            graph = x
    if graph is None:
        raise LookupError(f"delphi_graph did not return {claim_id!r}")
    quote = (by.get("quote_text") or [None])[0]
    literature = quote is not None
    snap = {
        "claim_id": claim_id, "claim_iri": iri, "retrieved_at": iso_utc(),
        "delphi_source": "local", "mcp_endpoint": "https://delphisci-mcp.fly.dev/mcp",
        "nanopub_path": (rec.get("nanopubs") or [None])[0],
        "nanopub_uri": graph.get("nanopub"), "registry": graph.get("registry"),
        "fields": {k: f.get(k) for k in ("rdfs:label", "dct:description", "delphi:context", "dct:type",
                                         "skos:notation", "delphi:hypothesisType", "delphi:proposedTest",
                                         "dct:source", "rdfs:seeAlso", "delphi:hasEvidence")},
        "record": {"license": (by.get("record_license") or [None])[0], "created": (by.get("created") or [None])[0],
                   "creator": [c for c in by.get("creator", []) if c.startswith("https://orcid.org/")][:1],
                   "extractor_agent": [e for e in by.get("extractor", []) if "extractor" in e][:1]},
        "kind": "literature" if literature else "math",
        "delphi_graph": {"status": graph.get("status"), "registry": graph.get("registry"),
                         "note": "status/truth/testability are LLM-elicited; carried as labelled, never as evidence"},
        "assessments": {"count": len(rec.get("assessments") or []),
                        "types": sorted({a["type"] for a in rec.get("assessments") or []}),
                        "label": "dataset-resolvability ratings by LLM assessors: NOT evidence, NOT truth ratings"},
    }
    # domain from the graph name (the claim nanopub path begins with the domain directory)
    snap["domain_dir"] = (snap["nanopub_path"] or "").split("/")[0] or None
    if literature:
        ps = by["primary_source"][0]
        base, _, frag = ps.partition("#")
        pag = [p for p in by.get("pagination", []) if p.lower().startswith("p")]
        snap["source"] = {
            "url": base, "locator": (frag or (pag[0] if pag else None)),
            "work": (by.get("work") or [None])[0],
            "recorded_sha256": (by.get("sha256") or [None])[0],
            "hash_scope": "whole_source_file" if "gutenberg.org" in base else "pipeline_extracted_page_text_not_reproducible",
            "edition": (by.get("edition") or [None])[0], "publisher": (by.get("publisher") or [None])[0],
            "isbn": (by.get("identifier") or [None])[0], "rights_statement": (by.get("rights") or [None])[0],
        }
        snap["quote"] = {"sha256": sha_bytes(quote.encode()), "chars": len(quote), "text_stored": False}
    else:
        d = (by.get("derived_from") or [None])[0]
        snap["source"] = {
            "url": d if d and d.startswith("https://doi.org/") else None,
            "unresolved_internal_iri": d if d and not d.startswith("https://doi.org/") else None,
            "locator": None, "recorded_sha256": None, "hash_scope": None,
            "citation": f.get("dct:source"),
            "see_also_related_not_source": by.get("see_also", []),
        }
        snap["quote"] = {"sha256": None, "chars": 0, "text_stored": False, "absent_in_record": True}
    snap["snapshot_sha256"] = sha_obj({k: v for k, v in snap.items() if k not in ("retrieved_at", "snapshot_sha256")})
    return snap, {"quote": quote}


_NORM = lambda s: re.sub(r"[^a-z0-9]+", " ", re.sub(r"\[\d+\]|\{\d+\}|_", "", s.replace("’", "'")).lower()).strip()


def verify_source(snap: dict, transient: dict, fetch=None) -> dict:
    """Re-fetch a Project Gutenberg source and check hash + quote-at-locator. Skips (says so) otherwise."""
    s = snap["source"]
    if snap["kind"] != "literature" or "gutenberg.org" not in (s["url"] or ""):
        return {"performed": False, "reason": "no re-fetchable, rights-clear source (math claim or non-Gutenberg)"}
    raw = (fetch or (lambda u: urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "frontier-adapters/0.1 (read-only check)"}), timeout=60).read()))(s["url"])
    m = re.fullmatch(r"line=(\d+),(\d+)", s["locator"] or "")
    out = {"performed": True, "fetched_at": iso_utc(), "sha256_fetched": sha_bytes(raw),
           "sha256_match": sha_bytes(raw) == s["recorded_sha256"], "quote_at_locator": "no_locator"}
    if m and transient.get("quote"):
        lines = raw.decode("utf-8", "replace").splitlines()
        a, b = int(m.group(1)), int(m.group(2))
        win = " ".join(lines[a:b])
        q = transient["quote"]
        norm_ws = lambda x: re.sub(r"\s+", " ", x.replace("’", "'").replace("“", '"').replace("”", '"')).strip().lower()
        out["quote_at_locator"] = ("exact" if norm_ws(q) in norm_ws(win)
                                   else "after_markup_strip" if _NORM(q) in _NORM(win) else "not_found")
    return out


def rights_for(snap: dict) -> dict:
    s = snap["source"]
    return {
        "delphi_record_license": snap["record"]["license"],
        "delphi_record_license_applies_to": "the Delphi nanopub only, NOT to the quoted source text",
        "source_text_rights": s.get("rights_statement") or "not stated in the Delphi record",
        "quote_text_included_in_output": False,
        "redistribution": "digest and locator only; no source bytes or quote text",
        "adapter_does_not_assert": "public-domain status; a reviewer must supply it with a citation before any quote is stored",
    }


def to_claim_draft(snap: dict, *, namespace: str = "node-a", issuer: str = "importer",
                   verification: dict | None = None, visibility: str = "public") -> dict:
    f, s = snap["fields"], snap["source"]
    ver = verification or {"performed": False, "reason": "not requested"}
    verified_hash = s["recorded_sha256"] if ver.get("performed") and ver.get("sha256_match") else None
    if snap["kind"] == "literature":
        access = ("Public web source named by the Delphi record. This adapter did not store the source bytes or the "
                  "quote text (" + rights_for(snap)["source_text_rights"] + "). "
                  + ("Hash re-verified against the fetched source." if verified_hash else
                     "The recorded hash was NOT re-verified here, so it is not carried as content_sha256."))
    else:
        access = ("A bibliographic citation from the Delphi record" + (" with a resolvable DOI" if s["url"] else
                  "; the record's source IRI is a Delphi-internal identifier that does not resolve")
                  + ". No locator, quote or hash exist in the record; the claim is not span-anchored to its source.")
    payload = {
        "title": f["rdfs:label"], "statement": f["dct:description"], "context": f["delphi:context"],
        "assumptions": [], "limitations": [],
        "source": {"uri": s["url"], "locator": s["locator"], "source_version": None,
                   "content_sha256": verified_hash, "content_available": False, "access": access, "license": None},
        "source_record_version": snap["nanopub_uri"],
        "prior_review": {
            "delphi_original": {
                "claim_iri": snap["claim_iri"], "claim_id": snap["claim_id"], "nanopub_uri": snap["nanopub_uri"],
                "registry": snap["registry"], "nanopub_path": snap["nanopub_path"], "domain_dir": snap["domain_dir"],
                "record": snap["record"], "kind": snap["kind"],
                "unmapped_fields": {k: f[k] for k in ("dct:type", "skos:notation", "delphi:hypothesisType",
                                                      "delphi:proposedTest", "dct:source", "rdfs:seeAlso") if f.get(k)},
                "source_detail": {k: v for k, v in s.items() if k not in ("url", "locator")},
                "quote": snap["quote"],
                "recorded_sha256_unverified": None if verified_hash else s.get("recorded_sha256"),
                "permission": rights_for(snap),
                "absent_in_record": ["access", "assumptions", "limitations", "source_version"]
                + ([] if snap["kind"] == "literature" else ["locator", "quote", "content_sha256"]),
                "delphi_graph": snap["delphi_graph"], "assessments": snap["assessments"],
            },
            "source_verification": ver,
            "adapter": {"id": ADAPTER_ID, "version": ADAPTER_VERSION, "snapshot_sha256": snap["snapshot_sha256"],
                        "retrieved_at": snap["retrieved_at"]},
        },
    }
    return {"namespace": namespace, "kind": "Claim", "id": snap["claim_id"], "issuer": issuer,
            "source_uri": snap["claim_iri"], "visibility": visibility, "predecessor": None, "payload": payload}
