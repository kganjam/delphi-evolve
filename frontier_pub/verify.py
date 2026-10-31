"""Receipt verifier for a party who does NOT trust the issuer of the nanopublication.

Given (a) the signed nanopublication and (b) the Frontier records it claims to render (target, assessment, two Events, evidence), decide for yourself:
  1. trusty URI hash and signature verify, with a second implementation (@nanopub/sign);
  2. every record's version digest recomputes from its content (the node's own checks are re-run, not believed);
  3. direct field-by-field agreement, read straight from the records and straight from the parsed nanopublication, independent of the builder:
     seven dimensions each with the record's status, reviewer-visible rationale; issuer, operators, node namespace, version digests, statement text;
     no eighth dimension; no numeric/composite rating predicate;
  4. the nanopublication equals, quad for quad, a fresh rendering of those records (signature block excluded).
What this does NOT establish: that the records are true, that the reviewers are who the node says, that the node's clock is right, or anything about nature.
A match means: this file is exactly a faithful rendering of those records. Whether the records themselves can be trusted is the reader's decision.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .binding import REPO_URL, TEMP, build_trig, check_bundle
from .records import DIMENSIONS, NotPublishable

SCHEMA, PROV, DCT, NPX = "https://schema.org/", "http://www.w3.org/ns/prov#", "http://purl.org/dc/terms/", "http://purl.org/nanopub/x/"
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
SIGNER_PREDICATES = {NPX + "hasAlgorithm", NPX + "hasPublicKey", NPX + "hasSignature", NPX + "hasSignatureTarget", NPX + "signedBy"}
TOKEN = re.compile(r'''\s*(?:(?P<str>"(?:[^"\\]|\\.)*")(?:\^\^(?P<dt><[^>]*>|[A-Za-z_][\w\-]*:[\w\-]*))?|(?P<iri><[^>]*>)|(?P<prefix>@prefix)'''
                   r'''|(?P<pname>[A-Za-z_][\w\-]*:(?:[\w\-%]|\\.)*(?:\.+(?:[\w\-%]|\\.)+)*)|(?P<punct>[;,.{}])|(?P<a>a(?=\s)))''')
ESC = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\", "'": "'", "b": "\b", "f": "\f"}


def _unescape(s: str) -> str:
    def rep(m):
        t = m.group(1)
        if t[0] in "uU":
            return chr(int(t[1:], 16))
        return ESC[t]
    return re.sub(r"\\(u[0-9A-Fa-f]{4}|U[0-9A-Fa-f]{8}|.)", rep, s)


def parse_trig(text: str):
    """Minimal parser for the TriG subset that this layer and nanopub-rs emit. Returns (quads, prefixes); a quad is (graph, s, p, o) of
    ('i', iri) or ('l', value, datatype) terms. Anything it cannot read raises, so a file it cannot parse cannot silently pass."""
    toks, pos = [], 0
    while pos < len(text):
        if not text[pos:].strip():
            break
        m = TOKEN.match(text, pos)
        if not m:
            raise NotPublishable(f"unparseable TriG near: {text[pos:pos + 40]!r}")
        toks.append((m.lastgroup if m.lastgroup != "dt" else "str", m))
        pos = m.end()
    prefixes: dict[str, str] = {}

    def term(kind, m):
        if kind == "iri":
            return ("i", m.group("iri")[1:-1])
        if kind == "pname":
            pre, local = m.group("pname").split(":", 1)
            if pre not in prefixes:
                raise NotPublishable(f"undeclared prefix {pre!r}")
            return ("i", prefixes[pre] + re.sub(r"\\(.)", r"\1", local))        # PN_LOCAL_ESC: the backslash only escapes
        if kind == "str":
            dt = m.group("dt")
            if dt:
                dt = dt[1:-1] if dt.startswith("<") else prefixes[dt.split(":", 1)[0]] + dt.split(":", 1)[1]
            return ("l", _unescape(m.group("str")[1:-1]), dt)
        raise NotPublishable(f"unexpected token {kind}")

    quads, i = [], 0
    while i < len(toks):
        kind, m = toks[i]
        if kind == "prefix":
            name = toks[i + 1][1].group("pname")
            assert name.endswith(":")
            prefixes[name[:-1]] = toks[i + 2][1].group("iri")[1:-1]
            i += 4
            continue
        graph = term(kind, m)
        if toks[i + 1][0] != "punct" or toks[i + 1][1].group("punct") != "{":
            raise NotPublishable("expected a graph block")
        i += 2
        while not (toks[i][0] == "punct" and toks[i][1].group("punct") == "}"):
            subj = term(*toks[i])
            i += 1
            while True:
                pk, pm = toks[i]
                pred = ("i", RDF_TYPE) if pk == "a" else term(pk, pm)
                i += 1
                while True:
                    ok, om = toks[i]
                    quads.append((graph, subj, pred, term(ok, om)))
                    i += 1
                    if toks[i][0] == "punct" and toks[i][1].group("punct") == ",":
                        i += 1
                        continue
                    break
                sep = toks[i][1].group("punct")
                i += 1
                if sep == ";":
                    if toks[i][0] == "punct" and toks[i][1].group("punct") == ".":
                        i += 1
                        break
                    continue
                if sep == ".":
                    break
                raise NotPublishable("bad statement separator")
        i += 1
    return quads, prefixes


def _normalise(quads, prefixes):
    this = prefixes.get("this")
    signed = this is not None and this.startswith("https://w3id.org/np/")
    def n(t):
        if t[0] != "i":
            return t
        u = t[1]
        if signed:
            if u == this:
                return ("i", "THIS")
            if u.startswith(this + "/#"):
                return ("i", "LOCAL#" + u[len(this) + 2:])
        else:
            if u == TEMP:
                return ("i", "THIS")
            if u.startswith(TEMP + "#"):
                return ("i", "LOCAL#" + u[len(TEMP) + 1:])
        return t
    return {(n(g), n(s), n(p), n(o)) for g, s, p, o in quads}, this if signed else None


def _lit(quads, graph, subj, pred):
    return [o[1] for g, s, p, o in quads if g == ("i", graph) and s == ("i", subj) and p == ("i", pred) and o[0] == "l"]


def verify_receipt(signed: Path, bundle: dict, *, status_change: bool = False, verify=None) -> dict:
    checks, problems, info = {}, [], []
    if verify is None:
        from falsify.nanopub import verify_signed as verify
    sig = verify(Path(signed))
    checks["trusty_uri_and_signature"] = sig.get("exit") == 0
    if not checks["trusty_uri_and_signature"]:
        problems.append(f"trusty/signature verification failed: {sig}")
    try:
        v = check_bundle(bundle, status_change=status_change)
        checks["record_digests_and_node_rules"] = True
    except NotPublishable as e:
        checks["record_digests_and_node_rules"] = False
        problems.append(f"records fail re-verification: {e}")
        return {"ok": False, "checks": checks, "problems": problems, "info": info}
    raw, prefixes = parse_trig(Path(signed).read_text())
    quads, uri = _normalise(raw, prefixes)
    checks["trusty_uri_matches_file"] = bool(uri and sig.get("trusty_uri") == uri)
    if not checks["trusty_uri_matches_file"]:
        problems.append("file's own URI differs from the verified trusty URI")
    A, P, I = ("i", "LOCAL#assertion"), ("i", "LOCAL#provenance"), ("i", "LOCAL#pubinfo")
    NQ = [(g, s, p, o) for g, s, p, o in quads]

    def objs(g, s, p):
        return [o for gg, ss, pp, o in NQ if gg == g and ss == s and pp == ("i", p)]

    def lit(g, s, p):
        return [o[1] for o in objs(g, s, p) if o[0] == "l"]

    # ---- 3. direct field agreement, read from the records and from the file, not through the builder
    t, a, rev, prop = v["target"], v["assessment"], v["review_event"], v["proposal_event"]
    aspects = {s: lit(A, s, SCHEMA + "reviewAspect") for g, s, p, o in NQ if g == A and p == ("i", SCHEMA + "reviewAspect")}
    named = sorted(x[0] for x in aspects.values() if x)
    checks["exactly_seven_named_dimensions"] = named == sorted(DIMENSIONS)
    if not checks["exactly_seven_named_dimensions"]:
        problems.append(f"dimension set differs: file has {named}")
    ok_dims = True
    for s, names in aspects.items():
        d = names[0] if names else None
        if d not in v["dims"]:
            continue
        rating = objs(A, s, SCHEMA + "reviewRating")
        status = lit(A, rating[0], SCHEMA + "alternateName") if rating else []
        body = lit(A, s, SCHEMA + "reviewBody")
        if status != [v["dims"][d]["status"]] or body != [v["dims"][d]["rationale"]]:
            ok_dims = False
            problems.append(f"dimension {d}: file says {status}/{body!r}, records say {v['dims'][d]['status']}/{v['dims'][d]['rationale']!r}")
    checks["each_dimension_matches_its_record"] = ok_dims
    prov_lits = {o[1] for g, s, p, o in NQ if g == P and p == ("i", SCHEMA + "identifier") and o[0] == "l"}
    prov_versions = {o[1] for g, s, p, o in NQ if g == P and p == ("i", SCHEMA + "version") and o[0] == "l"}
    want_ids = {a["issuer"], t["issuer"], rev["payload"]["operator"], prop["payload"]["operator"], a["namespace"], t["namespace"]}
    checks["issuer_operator_namespace_present"] = want_ids <= prov_lits
    if not checks["issuer_operator_namespace_present"]:
        problems.append(f"missing in provenance: {sorted(want_ids - prov_lits)}")
    want_versions = {t["version"], a["version"], rev["version"], prop["version"]}
    checks["version_digests_present"] = want_versions <= prov_versions
    if not checks["version_digests_present"]:
        problems.append(f"missing digests: {sorted(x[:12] for x in want_versions - prov_versions)}")
    checks["no_numeric_or_composite_rating_predicate"] = not any(
        p[0] == "i" and re.search(r"(ratingValue|bestRating|worstRating|confidence|probability|score)$", p[1]) for g, s, p, o in NQ)
    if not checks["no_numeric_or_composite_rating_predicate"]:
        problems.append("a numeric/composite rating predicate is present")
    if t["kind"] == "Claim":
        checks["statement_equals_record"] = lit(A, ("i", "LOCAL#item"), SCHEMA + "text") == [t["payload"]["statement"]]
        if not checks["statement_equals_record"]:
            problems.append("quoted statement differs from the record")

    # ---- 4. quad-for-quad equality with a fresh rendering of the records
    created = lit(I, ("i", "THIS"), DCT + "created")
    sup = [o[1] for o in objs(I, ("i", "THIS"), NPX + "supersedes") if o[0] == "i"]
    commits = {m.group(1) for g, s, p, o in NQ if p == ("i", PROV + "wasDerivedFrom") and o[0] == "i"
               for m in [re.fullmatch(re.escape(REPO_URL) + r"/tree/([0-9a-f]{40})/frontier_pub", o[1])] if m}
    if len(created) != 1 or len(commits) != 1:
        checks["equals_fresh_rendering"] = False
        problems.append("cannot recover the rendering parameters (created / publication-layer commit) from the file")
    else:
        fresh_text = build_trig(bundle, code_commit=next(iter(commits)), created=created[0], supersedes=sup[0] if sup else None, status_change=status_change)
        fq, fp = parse_trig(fresh_text)
        expect, _ = _normalise(fq, fp)
        sig_subject = ("i", "LOCAL#sig")
        got = {q for q in quads if q[1] != sig_subject}
        missing, extra = expect - got, got - expect
        benign = {q for q in extra if q[0] == I and q[2][1] in SIGNER_PREDICATES}
        extra -= benign
        if benign:
            info.append(f"{len(benign)} signer-added pubinfo triple(s) (signature/key predicates) ignored")
        checks["equals_fresh_rendering"] = not missing and not extra
        for q in sorted(missing, key=repr)[:5]:
            problems.append(f"in a fresh rendering but not in the file: {q[1:]!r}")
        for q in sorted(extra, key=repr)[:5]:
            problems.append(f"in the file but not in a fresh rendering: {q[1:]!r}")
    return {"ok": all(checks.values()) and not problems, "checks": checks, "problems": problems, "info": info,
            "trusty_uri": uri, "limits": "Establishes that the file is a faithful, correctly signed rendering of these records. Not that the records are true, "
                                          "that the named reviewers are who the node says, or anything about nature."}
