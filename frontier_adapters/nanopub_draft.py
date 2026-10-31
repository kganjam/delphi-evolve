"""Frontier record -> UNSIGNED nanopub DRAFT (TriG, four named graphs). Draft only: nothing is signed or published.

Reuse, deliberately:
  * layout, `np:` structure and the `de:` vocabulary come from codex-api `claim_runtime/trig.py`
    (temporary purl.org base, `de:signatureStatus "UNSIGNED DRAFT"`), so these drafts sit beside the existing
    `artifacts/{evidence,claim_reuse}/nanopubs/*.trig`.
  * determinism rules come from MorphoSwarm `nanopub/build.py` (SPEC-007): pinned `dct:created`, sorted
    statements, no blank nodes, no wall-clock, so the same record always yields byte-identical TriG.
  * the refusal stance comes from MorphoSwarm `nanopub/publish.py`: there is NO publish function here, and
    `refuse_publication()` exists only to say so.

Refusals (each has a failing test):
  * visibility is not "public"                                  -> private records never leave the store
  * content_available true with no licence                      -> the same rule the Frontier store enforces
  * the record claims the quote text was stored                 -> third-party text is never exported
  * an IRI field that is not a plain absolute IRI               -> no malformed or smuggled terms
The original Delphi claim IRI and nanopub URI are carried as `prov:wasDerivedFrom` / `de:delphiNanopub`: the
draft RECORDS A DERIVATION; it does not republish or endorse the Delphi nanopub.
"""
from __future__ import annotations

import json
import re

from .common import sha_obj

BASE = "http://purl.org/nanopub/temp/delphi-evolve/frontier"
ADAPTER = "frontier_adapters.nanopub_draft 0.1.0"
_IRI_OK = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:[^\s<>\"{}|\\^`]*$")

PREFIXES = """@prefix this: <{base}/{name}> .
@prefix sub: <{base}/{name}/> .
@prefix np: <http://www.nanopub.org/nschema#> .
@prefix npx: <http://purl.org/nanopub/x/> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix dct: <http://purl.org/dc/terms/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix delphi: <https://w3id.org/delphi/ontology/> .
@prefix de: <urn:x-delphi-evolve:vocab#> .

"""


class ExportRefused(ValueError):
    pass


def lit(s) -> str:
    return json.dumps(str(s), ensure_ascii=False)


def iri(u: str) -> str:
    if not isinstance(u, str) or not _IRI_OK.match(u):
        raise ExportRefused(f"not a plain absolute IRI: {str(u)[:80]!r}")
    return f"<{u}>"


def refuse_publication(*_a, **_k):
    raise ExportRefused("publication is not implemented and not authorised: exports are unsigned drafts only")


def check_exportable(record: dict) -> None:
    p, src = record["payload"], record["payload"].get("source") or {}
    if record.get("visibility") != "public":
        raise ExportRefused(f"{record['kind']}/{record['id']}: visibility {record.get('visibility')!r}; only public records may be exported")
    if src.get("content_available") and not src.get("license"):
        raise ExportRefused(f"{record['kind']}/{record['id']}: content asserted available under an unstated licence")
    orig = (p.get("prior_review") or {}).get("delphi_original") or {}
    if (orig.get("quote") or {}).get("text_stored"):
        raise ExportRefused(f"{record['kind']}/{record['id']}: record says quote text is stored; third-party text is never exported")


def _limits(record: dict) -> list[str]:
    p, src = record["payload"], record["payload"]["source"]
    out = ["Draft only: unsigned, no trusty URI, not published to any nanopub network, not accepted, not independently reviewed.",
           "single-reader, not Codex-reviewed."]
    out.append("Content held: " + ("YES under licence " + src["license"] if src.get("content_available") else
                                   "NO. Only a digest and locator are carried; no source bytes or quote text."))
    orig = (p.get("prior_review") or {}).get("delphi_original")
    if orig:
        perm = orig.get("permission", {})
        out.append("Delphi record licence (" + str(perm.get("delphi_record_license")) + ") applies to the Delphi nanopub only.")
        out.append("Source-text rights: " + str(perm.get("source_text_rights")))
        if orig.get("registry") == "test":
            out.append("The original Delphi nanopub is in Delphi's TEST registry, not published to the public network.")
    return out


def _stmt(pairs) -> str:
    return " ;\n".join(f"    {pred} {obj}" for pred, obj in pairs) + " ."


def _claim_assertion(record: dict) -> tuple[list, list]:
    p, src = record["payload"], record["payload"]["source"]
    orig = (p.get("prior_review") or {}).get("delphi_original") or {}
    pairs = [("a", "de:FrontierClaim"), ("rdfs:label", lit(p["title"])), ("de:statement", lit(p["statement"])),
             ("de:frontierRecord", lit(f"{record['namespace']}/{record['kind']}/{record['id']}@{record['version']}")),
             ("de:contentAvailable", '"' + str(bool(src["content_available"])).lower() + '"^^xsd:boolean')]
    derived = []
    if record.get("source_uri", "").startswith("http"):
        pairs.append(("de:originalClaim", iri(record["source_uri"]))); derived.append(record["source_uri"])
    if p.get("source_record_version", "") and p["source_record_version"].startswith("http"):
        pairs.append(("de:delphiNanopub", iri(p["source_record_version"]))); derived.append(p["source_record_version"])
    if orig.get("registry"):
        pairs.append(("de:delphiRegistry", lit(orig["registry"])))
    if src.get("uri"):
        pairs.append(("de:sourceUri", iri(src["uri"])))
    for key, pred in (("locator", "de:sourceLocator"), ("content_sha256", "de:sourceContentSha256")):
        if src.get(key):
            pairs.append((pred, lit(src[key])))
    q = orig.get("quote") or {}
    if q.get("sha256"):
        pairs.append(("de:quoteSha256", lit(q["sha256"]))); pairs.append(("de:quoteChars", str(int(q["chars"]))))
    return [("sub:claim", pairs)], derived


def _evidence_assertion(record: dict, target_claim: dict | None) -> tuple[list, list]:
    p, prov = record["payload"], record["payload"]["provenance"]
    t = p["target"]
    pairs = [("a", "de:FrontierEvidence"), ("rdfs:label", lit(f"Evidence {record['id']} ({p['evidence_kind']})")),
             ("de:frontierRecord", lit(f"{record['namespace']}/{record['kind']}/{record['id']}@{record['version']}")),
             ("de:evidenceKind", lit(p["evidence_kind"])),
             ("de:targetRecord", lit(f"{t['namespace']}/{t['kind']}/{t['id']}@{t['version']}")),
             ("de:epistemicStatus", lit(f"{p['evidence_kind']}: output of a computational run; NOT observed; not reviewed"))]
    derived = []
    if target_claim is not None:
        tc = target_claim
        if tc["version"] != t["version"] or tc["id"] != t["id"]:
            raise ExportRefused("target claim record does not match the evidence's pinned target ref")
        if tc.get("source_uri", "").startswith("http"):
            pairs.append(("de:targetOriginalClaim", iri(tc["source_uri"]))); derived.append(tc["source_uri"])
        npu = tc["payload"].get("source_record_version") or ""
        if npu.startswith("http"):
            pairs.append(("de:targetDelphiNanopub", iri(npu))); derived.append(npu)
    for key, pred in (("run_id", "de:localRunId"), ("commit_sha", "de:codeCommit"), ("source_tar_sha256", "de:codeSnapshotSha256"),
                      ("command", "de:command")):
        if prov.get(key):
            pairs.append((pred, lit(prov[key])))
    src = p["source"]
    pairs += [("de:resultSha256", lit(src["content_sha256"])), ("de:resultLocator", lit(src["locator"])),
              ("de:contentAvailable", '"' + str(bool(src["content_available"])).lower() + '"^^xsd:boolean')]
    for lim in p["limitations"]:
        pairs.append(("de:limitation", lit(lim)))
    rp = prov.get("replay") or {}
    if rp.get("performed"):
        ok = [k for k, v in rp["results"].items() if v["matches_recorded"]]
        pairs.append(("de:replay", lit(f"re-executed under {len(rp['results'])} interpreter(s); byte-identical under {ok}; "
                                       f"mutation control {'applied' if rp.get('mutation_control') else 'not applied'}")))
    return [("sub:evidence", pairs)], derived


def record_to_trig(record: dict, *, target_claim: dict | None = None) -> str:
    check_exportable(record)
    name = f"{record['kind'].lower()}-{re.sub(r'[^A-Za-z0-9_.-]', '_', record['id'])[:80]}-{record['version'][:12]}"
    if record["kind"] == "Claim":
        stmts, derived = _claim_assertion(record)
    elif record["kind"] == "Evidence":
        stmts, derived = _evidence_assertion(record, target_claim)
    else:
        raise ExportRefused(f"no draft mapping for kind {record['kind']!r}")
    assertion = "\n".join(f"  {s} " + _stmt(pairs).lstrip() for s, pairs in stmts)
    limits = "".join(f"    de:publicationLimit {lit(x)} ;\n" for x in _limits(record))
    deriv = "".join(f"  sub:assertion prov:wasDerivedFrom {iri(u)} .\n" for u in sorted(set(derived)))
    return PREFIXES.format(base=BASE, name=name) + f"""sub:Head {{
  this: a np:Nanopublication ;
    np:hasAssertion sub:assertion ;
    np:hasProvenance sub:provenance ;
    np:hasPublicationInfo sub:pubinfo .
}}

sub:assertion {{
{assertion}
}}

sub:provenance {{
  sub:assertion prov:wasAttributedTo sub:softwareAgent ;
    prov:wasGeneratedBy sub:generation .
  sub:softwareAgent a prov:SoftwareAgent ;
    rdfs:label {lit("frontier_adapters (software; model Claude Sonnet 5.5 authored the adapter)")} .
  sub:generation a prov:Activity ;
    prov:wasAssociatedWith sub:softwareAgent ;
    rdfs:comment {lit(f"{ADAPTER}; record sha256 of canonical payload {sha_obj(record['payload'])}")} .
{deriv}}}

sub:pubinfo {{
  this: dct:created "{record['created_at']}"^^xsd:dateTime ;
    rdfs:label {lit("Draft: Frontier " + record['kind'] + " " + record['id'])} ;
    npx:hasNanopubType de:Frontier{record['kind']} ;
{limits}    de:signatureStatus "UNSIGNED DRAFT: no trusty URI assigned, not published to any nanopub network" .
}}
"""


def validate_trig(trig: str) -> dict:
    """Stdlib structural check: exactly the four named graphs, balanced, no blank-node labels."""
    graphs = re.findall(r"^sub:(Head|assertion|provenance|pubinfo) \{", trig, re.M)
    # braces may legitimately appear inside string literals, so count only those outside strings
    depth, blocks = 0, 0
    in_str = False
    esc = False
    for ch in trig:
        if in_str:
            if esc: esc = False
            elif ch == "\\": esc = True
            elif ch == '"': in_str = False
            continue
        if ch == '"': in_str = True
        elif ch == "{":
            depth += 1; blocks += 1
        elif ch == "}":
            depth -= 1
    return {"graphs": sorted(graphs), "top_level_blocks": blocks, "balanced": depth == 0,
            "four_graphs": sorted(graphs) == ["Head", "assertion", "provenance", "pubinfo"] and blocks == 4,
            "blank_node_labels": bool(re.search(r"(^|[\s;,.])_:", trig))}
