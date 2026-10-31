"""Evidence tooling for Delphi Evolve (experience worker).

Subcommands (python -m evolve.evidence <cmd> --help):

  landscape  Pack the real TrpB four-site table into site/data/landscape.js
             (descriptive visualisation data, with source hashes).
  delphi     Query the hosted Delphi MCP live and store raw responses.
  nanopubs   Emit unsigned nanopublication TriG drafts and validate them.
  validate   Re-parse every draft TriG with rdflib and check structure.
  docs       Render docs/{blog,pitch,video-storyboard}.md from *.template.md and saved artifacts.

Nothing here invents measurements. Every number the site, blog or nanopub
drafts show is read from an artifact written by one of these commands or by
another worker. Missing artifacts render as "not available".

This module deliberately lives in the ``evolve`` namespace without owning
``evolve/__init__.py`` (owned by the core worker).
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_DIR = ROOT / "artifacts" / "evidence"
SITE_DATA = ROOT / "site" / "data"
AA = "ACDEFGHIKLMNPQRSTVWY"
DEFAULT_RAW = Path("/data/artifacts/v2-scout/data/caltech")
DATASET_DOI = "10.22002/h5rah-5z170"
DATASET_URL = "https://data.caltech.edu/records/h5rah-5z170"
PAPER_DOI = "10.1073/pnas.2400439121"
MCP_URL = "https://delphisci-mcp.fly.dev/mcp"
PDT = dt.timezone(dt.timedelta(hours=-7), "PDT")  # valid through 2026-11-01 02:00 local


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def now_seattle() -> str:
    """Seattle wall time. DST ends 2026-11-01 02:00 PDT -> PST (UTC-8)."""
    utc = dt.datetime.now(dt.timezone.utc)
    cutover = dt.datetime(2026, 11, 1, 9, 0, tzinfo=dt.timezone.utc)  # 02:00 PDT
    if utc >= cutover and utc.year == 2026:
        tz = dt.timezone(dt.timedelta(hours=-8), "PST")
    elif utc.year == 2026 and utc < cutover:
        tz = PDT
    else:  # outside the documented window: do not guess
        return utc.strftime("%Y-%m-%dT%H:%M:%SZ") + " (UTC; Seattle zone not computed)"
    return utc.astimezone(tz).strftime("%Y-%m-%d %H:%M:%S ") + tz.tzname(None)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def genotype_index(g: str) -> int:
    a = [AA.index(c) for c in g]
    return ((a[0] * 20 + a[1]) * 20 + a[2]) * 20 + a[3]


# --------------------------------------------------------------------------
# landscape
# --------------------------------------------------------------------------

def build_landscape(raw_dir: Path, out_dir: Path) -> dict:
    """Pack real replicate-level growth values for all 20^4 genotypes.

    Score semantics (descriptive only): mu_k-bg is the replicate growth-rate
    estimate minus the stop-codon background, NOT max-normalised (the source's
    '/max' columns use the whole-library maximum, a leakage hazard for any
    predictive use). 'Unknown' cells are the 871 genotypes absent from the
    measured file; the source ships KNN imputations for them, which are kept
    separate and never treated as observations.
    """
    import numpy as np
    import pandas as pd

    summary_p = raw_dir / "summary_AA.csv"
    knn_p = raw_dir / "KNN_imputed_TrpB.csv"
    s = pd.read_csv(summary_p)
    k = pd.read_csv(knn_p)
    measured = s[s["# Stop"] == 0]
    n_total = 20 ** 4
    assert len(measured) == measured["AAs"].nunique()
    overlap = set(measured["AAs"]) & set(k["AAs"])

    # Score definition matches the core worker's loader (evolve/data.py @ origin/work/core a8c0090):
    # raw growth mu_k minus the per-replicate mean over stop-codon rows. Not the source's row-specific
    # mu_k-bg columns and never the '/max' columns.
    stop = s["# Stop"] > 0
    bg1 = float(s.loc[stop, "mu_1"].mean())
    bg2 = float(s.loc[stop, "mu_2"].mean())
    SCALE = 50000  # int16 steps of 2e-5 growth units; |score| <= 0.36 << 0.655
    r1 = np.full(n_total, -32768, dtype="<i2")
    r2 = np.full(n_total, -32768, dtype="<i2")
    cnt = np.zeros(n_total, dtype="<u2")
    act = np.zeros(n_total, dtype="u1")
    idx = np.array([genotype_index(g) for g in measured["AAs"]])
    r1[idx] = np.rint((measured["mu_1"].to_numpy() - bg1) * SCALE).astype("<i2")
    r2[idx] = np.rint((measured["mu_2"].to_numpy() - bg2) * SCALE).astype("<i2")
    cnt[idx] = np.minimum(np.minimum(measured["InputCount_1"], measured["InputCount_2"]).to_numpy(), 65535).astype("<u2")
    act[idx] = measured["active"].to_numpy().astype("u1")

    unknown_idx = np.setdiff1d(np.arange(n_total), idx)
    unknown_genotypes = []
    for i in unknown_idx:
        a4, r = i % 20, i // 20
        a3, r = r % 20, r // 20
        a2, a1 = r % 20, r // 20
        unknown_genotypes.append(AA[a1] + AA[a2] + AA[a3] + AA[a4])
    knn_map = dict(zip(k["AAs"], np.round(k["fitness"].astype(float), 6)))
    unknown_imputed = {g: knn_map.get(g) for g in unknown_genotypes}

    def b64(a):
        return base64.b64encode(a.tobytes()).decode()

    meta = {
        "built_utc": now_utc(),
        "built_seattle": now_seattle(),
        "builder": "python -m evolve.evidence landscape",
        "source": {
            "dataset_url": DATASET_URL,
            "dataset_doi": DATASET_DOI,
            "paper_doi": PAPER_DOI,
            "license": "CC0 1.0 (per CaltechDATA record metadata)",
            "files": {
                p.name: {"sha256": sha256_file(p), "bytes": p.stat().st_size}
                for p in (summary_p, knn_p)
            },
            "member_paths_in_data_zip": {
                "summary_AA.csv": "data/figure_data/4-site_merged_replicates/20230827/four-site_summary_AA_data.csv",
                "KNN_imputed_TrpB.csv": "data/figure_data/4-site_imputed/20230828_KNN_imputed_TrpB.csv",
            },
        },
        "counts": {
            "library_aa_genotypes": n_total,
            "source_rows_incl_stop": int(len(s)),
            "measured_non_stop": int(len(measured)),
            "stop_containing_rows_excluded": int((s["# Stop"] > 0).sum()),
            "unmeasured_cells": int(len(unknown_idx)),
            "knn_imputed_rows_in_source_file": int(len(k)),
            "measured_imputed_overlap": len(overlap),
            "active_flag_true_among_measured": int(measured["active"].sum()),
        },
        "score": {
            "definition": "replicate growth rates mu_1, mu_2 minus the per-replicate mean over stop-codon rows (same as core loader); not max-normalised; not the source's row-specific mu_k-bg columns",
            "stop_codon_mean_mu": [bg1, bg2],
            "stored_as": "int16 little-endian, value x 50000 (resolution 2e-5), -32768 = not measured",
            "noise_model_constants": {
                "origin": "copied from evolve/data.py at origin/work/core a8c0090 (core worker's declared, frozen noise model); half-width eps_i = ceil(kappa * sd_bin / 2 * 1e6) / 1e6; kappa is an ASSUMED sensitivity multiplier, not a confidence level",
                "min_input_count_bin_edges": [20, 50, 200],
                "replicate_diff_sd_by_bin": [0.014953, 0.009995, 0.005851, 0.002992],
                "core_default_kappa": 2.0,
            },
        },
        "layout": {
            "kind": "projected sequence space, NOT molecular geometry",
            "tile_rows": "residue 1 (V183 in the TrpB numbering used by the source study) x residue 2",
            "tile_cols": "residue 3 x residue 4",
            "note": "index = ((a1*20+a2)*20+a3)*20+a4 with amino-acid order " + AA,
        },
        "cnt_array": "uint16 little-endian min(InputCount_1, InputCount_2), capped at 65535",
        "act_array": "uint8, source 'active' flag (above stop-codon mean + 1.96 SD)",
        "aa_order": AA,
    }
    out = {
        "meta": meta,
        "r1": b64(r1),
        "r2": b64(r2),
        "cnt": b64(cnt),
        "act": b64(act),
        "unknown": unknown_imputed,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    js = out_dir / "landscape.js"
    js.write_text(
        "/* Generated by `python -m evolve.evidence landscape`. Real TrpB data; see meta.source. */\n"
        "window.TRPB_LANDSCAPE = " + json.dumps(out, separators=(",", ":")) + ";\n"
    )
    (out_dir / "landscape.meta.json").write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n")
    return meta


# --------------------------------------------------------------------------
# reference route logic (Python mirror of site/app.js, used by tests)
# --------------------------------------------------------------------------

def neighbors(g: str):
    for p in range(4):
        for a in AA:
            if a != g[p]:
                yield g[:p] + a + g[p + 1:]


SD_BINS = (0.014953, 0.009995, 0.005851, 0.002992)  # core's declared replicate-difference SD by read-count bin
SD_EDGES = (20, 50, 200)


def load_scores(raw_dir: Path = DEFAULT_RAW):
    """Return {genotype: (score1, score2, min_input_count)} for the 159,129 measured genotypes.

    score_k = mu_k - mean(mu_k over stop-codon rows) (the core loader's definition)."""
    import pandas as pd

    s = pd.read_csv(raw_dir / "summary_AA.csv",
                    usecols=["AAs", "# Stop", "mu_1", "mu_2", "InputCount_1", "InputCount_2"])
    stop = s["# Stop"] > 0
    bg1, bg2 = s.loc[stop, "mu_1"].mean(), s.loc[stop, "mu_2"].mean()
    m = s[~stop]
    cm = m[["InputCount_1", "InputCount_2"]].min(axis=1)
    return {g: (a - bg1, b - bg2, int(c)) for g, a, b, c in zip(m["AAs"], m["mu_1"], m["mu_2"], cm)}


def noise_eps(count: int, kappa: float) -> float:
    import math
    b = sum(count >= e for e in SD_EDGES)
    return math.ceil(kappa * SD_BINS[b] / 2 * 1e6) / 1e6


def interval(rep, eps: float, mode: str):
    a, b, c = rep
    if mode == "envelope":
        return min(a, b) - eps, max(a, b) + eps
    m = (a + b) / 2
    if mode == "readnoise":  # eps is kappa
        e = noise_eps(c, eps)
        return m - e, m + e
    return m - eps, m + eps


def edge_status(scores, v: str, w: str, eps: float, mode: str = "readnoise") -> str:
    """accepted | rejected | unknown, for the directed step v -> w."""
    if v not in scores or w not in scores:
        return "unknown"
    _, hi = interval(scores[v], eps, mode)
    lo, _ = interval(scores[w], eps, mode)
    return "accepted" if lo >= hi else "rejected"


def reachability(scores, start: str, target: str, eps: float, mode: str = "readnoise"):
    """BFS over single substitutions.

    pessimistic: only accepted edges between measured genotypes.
    optimistic : additionally allow every edge touching an unmeasured genotype.
    Returns (pessimistic_dist, optimistic_dist) with None if unreachable.
    """
    from collections import deque

    def bfs(allow_unknown: bool):
        dist = {start: 0}
        q = deque([start])
        while q:
            v = q.popleft()
            if v == target:
                return dist[v], dist
            for w in neighbors(v):
                if w in dist:
                    continue
                st = edge_status(scores, v, w, eps, mode)
                if st == "accepted" or (allow_unknown and st == "unknown"):
                    dist[w] = dist[v] + 1
                    q.append(w)
        return None, dist

    return bfs(False), bfs(True)


# --------------------------------------------------------------------------
# Delphi MCP
# --------------------------------------------------------------------------

DELPHI_QUERIES = [
    # (tool, arguments)
    ("delphi_overview", {"source": "local"}),
    ("delphi_overview", {"source": "network"}),
    ("delphi_search_claims", {"text": "epistasis", "limit": 10, "source": "local"}),
    ("delphi_search_claims", {"text": "epistasis", "limit": 10, "source": "network"}),
    ("delphi_search_claims", {"text": "fitness landscape", "limit": 10, "source": "local"}),
    ("delphi_search_claims", {"text": "fitness landscape", "limit": 10, "source": "network"}),
    ("delphi_search_claims", {"text": "successive", "limit": 10, "source": "local"}),
    ("delphi_search_claims", {"text": "successive", "limit": 10, "source": "network"}),
    ("delphi_search_claims", {"text": "additive", "limit": 10, "source": "local"}),
    ("delphi_search_claims", {"text": "additive", "limit": 10, "source": "network"}),
    ("delphi_search_claims", {"text": "intermediate", "limit": 10, "source": "local"}),
    ("delphi_search_claims", {"text": "leaps", "limit": 10, "source": "local"}),
    ("delphi_get_claim", {"id": "darwin1859-ch06-08", "source": "local"}),
    ("delphi_get_claim", {"id": "darwin1859-ch06-08", "source": "network"}),
    ("delphi_get_claim", {"id": "darwin1859-ch06-16", "source": "local"}),
    ("delphi_get_claim", {"id": "darwin1859-ch06-16", "source": "network"}),
    ("delphi_get_claim", {"id": "darwin1859-ch01-17", "source": "local"}),
    ("delphi_get_claim", {"id": "darwin1859-ch01-17", "source": "network"}),
    ("delphi_get_claim", {"id": "fisher-ftns", "source": "local"}),
    ("delphi_get_claim", {"id": "fisher-ftns", "source": "network"}),
]


def mcp_call(tool: str, arguments: dict, timeout: int = 60) -> dict:
    body = json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": tool, "arguments": arguments},
    }).encode()
    req = urllib.request.Request(MCP_URL, data=body, headers={
        "content-type": "application/json",
        "accept": "application/json, text/event-stream",
    })
    raw = urllib.request.urlopen(req, timeout=timeout).read().decode()
    m = re.search(r"^data: (.*)$", raw, re.M)
    return json.loads(m.group(1) if m else raw)


def run_delphi(out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for tool, args in DELPHI_QUERIES:
        rec = {"tool": tool, "arguments": args, "at_utc": now_utc()}
        try:
            resp = mcp_call(tool, args)
            text = resp["result"]["content"][0]["text"]
            rec["response_sha256"] = hashlib.sha256(text.encode()).hexdigest()
            try:
                rec["response"] = json.loads(text)
            except json.JSONDecodeError:
                rec["response_text"] = text
            rec["status"] = "ok"
        except Exception as e:  # keep failures as evidence, do not hide
            rec["status"] = "error"
            rec["error"] = f"{type(e).__name__}: {e}"
        records.append(rec)
    summary = {
        "endpoint": MCP_URL,
        "server": "delphisci 0.2.0 (initialize response)",
        "run_utc": now_utc(),
        "run_seattle": now_seattle(),
        "queries": records,
        "n_ok": sum(r["status"] == "ok" for r in records),
        "n_error": sum(r["status"] == "error" for r in records),
        "interpretation_limits": [
            "Absence of a text hit for 'epistasis' or 'fitness landscape' is a limited text-match result "
            "over claim title/statement/math, not proof that Delphi lacks related knowledge.",
            "Local and network sources differ; each record names its source.",
            "Delphi assessment scores are elicited LLM judgments, not posterior probabilities.",
        ],
    }
    (out_dir / "delphi_queries.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return summary


def extract_claim(summary: dict, claim_id: str, source: str):
    for r in summary["queries"]:
        if r["tool"] == "delphi_get_claim" and r["arguments"]["id"] == claim_id \
                and r["arguments"]["source"] == source and r["status"] == "ok":
            return r["response"]
    return None


# --------------------------------------------------------------------------
# nanopublication drafts
# --------------------------------------------------------------------------

NP_PREFIXES = """\
@prefix this: <http://purl.org/nanopub/temp/delphi-evolve/{name}> .
@prefix sub: <http://purl.org/nanopub/temp/delphi-evolve/{name}/> .
@prefix np: <http://www.nanopub.org/nschema#> .
@prefix npx: <http://purl.org/nanopub/x/> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix dct: <http://purl.org/dc/terms/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix schema: <https://schema.org/> .
@prefix spdx: <http://spdx.org/rdf/terms#> .
@prefix delphi: <https://w3id.org/delphi/ontology/> .
@prefix de: <urn:x-delphi-evolve:vocab#> .

"""


def lit(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)


def trig_draft(name: str, label: str, assertion_ttl: str, provenance_ttl: str,
               nptype: str, created: str) -> str:
    return NP_PREFIXES.format(name=name) + f"""\
sub:Head {{
  this: a np:Nanopublication ;
    np:hasAssertion sub:assertion ;
    np:hasProvenance sub:provenance ;
    np:hasPublicationInfo sub:pubinfo .
}}

sub:assertion {{
{assertion_ttl}
}}

sub:provenance {{
  sub:assertion prov:wasAttributedTo sub:softwareAgent ;
    prov:wasGeneratedBy sub:generation .
  sub:softwareAgent a prov:SoftwareAgent ;
    rdfs:label "Delphi Evolve experience worker (Claude Sonnet 5.5 driving evolve/evidence.py)" .
  sub:generation a prov:Activity ;
    prov:wasAssociatedWith sub:softwareAgent ;
    rdfs:comment "Generated by `python -m evolve.evidence nanopubs`; see repository for the exact commit." .
{provenance_ttl}
}}

sub:pubinfo {{
  this: dct:created "{created}"^^xsd:dateTime ;
    rdfs:label {lit(label)} ;
    npx:hasNanopubType {nptype} ;
    de:signatureStatus "UNSIGNED DRAFT: no trusty URI assigned, not published to any nanopub network" ;
    rdfs:comment "Draft only. Temporary URIs (purl.org/nanopub/temp) are replaced when signed by a real key holder. No scientist identity or endorsement is asserted." .
}}
"""


def make_drafts(raw_dir: Path, delphi_path: Path, benchmark_hint: dict | None = None) -> dict[str, str]:
    """Return {filename: trig}. Content is limited to what artifacts support."""
    created = now_utc()
    meta = json.loads((SITE_DATA / "landscape.meta.json").read_text())
    summary = json.loads(delphi_path.read_text())
    src = meta["source"]
    cnt = meta["counts"]
    sums = src["files"]["summary_AA.csv"]["sha256"]

    local_c = extract_claim(summary, "darwin1859-ch06-08", "local")
    net_c = extract_claim(summary, "darwin1859-ch06-08", "network")
    net_np = (net_c or {}).get("nanopubs", [None])[0]
    claim_iri = "https://w3id.org/delphi/resource/claim/darwin1859-ch06-08"

    drafts: dict[str, str] = {}

    # 1. Operational hypothesis, linked to Darwin only by motivation.
    name = "operational-hypothesis-v1"
    assertion = f"""\
  sub:hypothesis a delphi:Claim, delphi:TestableHypothesis ;
    rdfs:label "Operational TrpB step-dominance question (four-site landscape)" ;
    dct:description {lit(
        "On the finite measured four-site TrpB landscape (positions 183, 184, 227, 228 of the source study), "
        "does a route of single amino-acid substitutions from the parent VFVS to the highest measured genotype AIKG "
        "exist in which every step is non-decreasing in measured growth under a stated assumed error bound? "
        "This is a statement about a measured, finite graph and a growth-selection proxy, not about organisms, "
        "kcat/KM, or biological impossibility.")} ;
    dct:type "operational-hypothesis" ;
    de:evidenceKind "observed measurements, descriptive graph analysis; assumed error bound is a parameter, not a measured confidence level" ;
    de:motivatedBy <{claim_iri}> ;
    de:relationToMotivation "motivation-by-analogy; NOT equivalent to, entailed by, or a test of the Darwin 1859 statement" .
"""
    prov = f"""\
  <{claim_iri}> rdfs:label "Darwin 1859 ch. VI claim: theory fails if a complex organ could not arise by slight steps" ;
    de:observedInDelphiSource "local", "network" ;
    de:delphiNetworkNanopub {('<' + net_np + '>') if net_np else '"not-resolved-in-this-run"'} .
  sub:assertion prov:wasDerivedFrom <https://doi.org/{src['paper_doi']}>, <{src['dataset_url']}> .
  <{src['dataset_url']}> dct:license <https://creativecommons.org/publicdomain/zero/1.0/> ;
    rdfs:label "CaltechDATA record h5rah-5z170 (Johnston et al. TrpB combinatorial landscape)" ;
    spdx:checksum [ spdx:algorithm spdx:checksumAlgorithm_sha256 ; spdx:checksumValue "{sums}" ;
                    rdfs:comment "SHA-256 of summary_AA.csv as retrieved by this project" ] .
"""
    drafts[f"{name}.trig"] = trig_draft(
        name, "Draft: operational TrpB route hypothesis", assertion, prov, "delphi:Claim", created)

    # 2. Observed landscape counts (observation, descriptive).
    name = "observed-landscape-counts-v1"
    assertion = f"""\
  sub:observation a delphi:Claim ;
    rdfs:label "Counts in the TrpB four-site source tables as retrieved" ;
    dct:description {lit(
        f"Of {cnt['library_aa_genotypes']} amino-acid genotypes, {cnt['measured_non_stop']} are present with replicate "
        f"measurements in summary_AA.csv (non-stop rows); {cnt['unmeasured_cells']} are absent. The source ships "
        f"{cnt['knn_imputed_rows_in_source_file']} KNN-imputed rows for the absent genotypes; overlap with measured rows "
        f"is {cnt['measured_imputed_overlap']}. Imputed values are not observations.")} ;
    dct:type "observation" ;
    de:measuredNonStop {cnt['measured_non_stop']} ;
    de:unmeasured {cnt['unmeasured_cells']} ;
    de:imputedRowsInSource {cnt['knn_imputed_rows_in_source_file']} ;
    de:measuredImputedOverlap {cnt['measured_imputed_overlap']} .
"""
    prov = f"""\
  sub:assertion prov:wasDerivedFrom <{src['dataset_url']}> .
  <{src['dataset_url']}> spdx:checksum [ spdx:algorithm spdx:checksumAlgorithm_sha256 ;
      spdx:checksumValue "{sums}" ; rdfs:comment "summary_AA.csv" ],
    [ spdx:algorithm spdx:checksumAlgorithm_sha256 ;
      spdx:checksumValue "{src['files']['KNN_imputed_TrpB.csv']['sha256']}" ; rdfs:comment "KNN_imputed_TrpB.csv" ] .
"""
    drafts[f"{name}.trig"] = trig_draft(
        name, "Draft: observed landscape counts", assertion, prov, "delphi:Claim", created)

    # 3. Interpretation/limitation nanopub linking Fisher FTNS reading honestly.
    fisher = extract_claim(summary, "fisher-ftns", "network")
    fisher_np = (fisher or {}).get("nanopubs", [None])[0]
    name = "scope-limitation-v1"
    assertion = f"""\
  sub:limitation a delphi:Claim ;
    rdfs:label "Scope limitation for any TrpB route certificate" ;
    dct:description {lit(
        "A route or cut certificate on the four-site graph is conditional on (i) the declared graph scope, "
        "(ii) an interval or error-bound assumption about replicate measurements, and (iii) treating growth in the assay as a proxy for function. "
        "Absence of a measurement is not evidence of absence of a path. A finite four-residue graph says nothing about the full sequence space, "
        "and the cellular growth assay is not a purified-enzyme catalytic constant.")} ;
    dct:type "interpretation" ;
    de:motivatedBy {('<' + fisher_np + '>') if fisher_np else '<https://w3id.org/delphi/resource/claim/fisher-ftns>'} ;
    de:relationToMotivation "context only: Delphi's own fisher-ftns record states the partial-change reading is false for total change under epistasis" .
"""
    prov = f"""\
  sub:assertion prov:wasDerivedFrom <https://w3id.org/delphi/resource/claim/fisher-ftns> .
  <https://w3id.org/delphi/resource/claim/fisher-ftns> de:observedInDelphiSource "network" .
"""
    drafts[f"{name}.trig"] = trig_draft(
        name, "Draft: scope limitation", assertion, prov, "delphi:Claim", created)

    # 4. Benchmark result placeholder only if real numbers were supplied.
    if benchmark_hint:
        name = "benchmark-result-v1"
        assertion = f"""\
  sub:result a delphi:Claim ;
    rdfs:label "Retrospective query-to-certify replay result (simulated selection replay)" ;
    dct:description {lit(benchmark_hint['description'])} ;
    dct:type "simulated-selection-replay" ;
    de:sourceArtifact {lit(benchmark_hint['artifact'])} ;
    de:sourceArtifactSha256 "{benchmark_hint['sha256']}" .
"""
        prov = f"""  sub:assertion prov:wasDerivedFrom <{src['dataset_url']}> ."""
        drafts[f"{name}.trig"] = trig_draft(
            name, "Draft: replay result", assertion, prov, "delphi:Claim", created)
    return drafts


def validate_trig(path: Path) -> dict:
    """Parse with rdflib and check nanopub structure. Returns report dict."""
    import rdflib
    from rdflib import Dataset, Namespace, RDF

    NP = Namespace("http://www.nanopub.org/nschema#")
    ds = Dataset()
    ds.parse(str(path), format="trig")
    graphs = {str(g.identifier): len(g) for g in ds.graphs() if len(g)}
    head = None
    for g in ds.graphs():
        for s in g.subjects(RDF.type, NP.Nanopublication):
            head = (g.identifier, s)
    problems = []
    if head is None:
        problems.append("no np:Nanopublication head")
    else:
        hg, np_uri = head
        parts = {}
        for key, prop in (("assertion", NP.hasAssertion), ("provenance", NP.hasProvenance),
                          ("pubinfo", NP.hasPublicationInfo)):
            vals = list(ds.graph(hg).objects(np_uri, prop))
            if len(vals) != 1:
                problems.append(f"head must have exactly one {key}, has {len(vals)}")
            else:
                parts[key] = vals[0]
                if len(ds.graph(vals[0])) == 0:
                    problems.append(f"{key} graph is empty")
        text = path.read_text()
        if "UNSIGNED DRAFT" not in text:
            problems.append("missing explicit unsigned-draft marker")
        if "RA" in str(np_uri).rsplit("/", 1)[-1][:2]:
            problems.append("nanopub URI looks like a trusty URI; drafts must use temp URIs")
        if not str(np_uri).startswith("http://purl.org/nanopub/temp/"):
            problems.append("nanopub URI is not a temp URI")
    return {"file": path.name, "rdflib": rdflib.__version__, "graphs": graphs,
            "triples": sum(graphs.values()), "valid": not problems, "problems": problems}


def write_drafts(out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    drafts = make_drafts(DEFAULT_RAW, EVIDENCE_DIR / "delphi_queries.json")
    reports = []
    for fn, text in drafts.items():
        p = out_dir / fn
        p.write_text(text)
        reports.append(validate_trig(p))
    rep = {"validated_utc": now_utc(), "reports": reports,
           "all_valid": all(r["valid"] for r in reports),
           "note": "Structural validation with rdflib only. Drafts are unsigned; nothing was submitted to any nanopub server."}
    (out_dir / "validation.json").write_text(json.dumps(rep, indent=2) + "\n")
    return rep


def site_evidence(out_dir: Path) -> dict:
    """Condense saved Delphi records + nanopub drafts into site/data/evidence.json."""
    import shutil

    summary = json.loads((EVIDENCE_DIR / "delphi_queries.json").read_text())
    claims = []
    for cid, role in (("darwin1859-ch06-08", "motivation"),
                      ("darwin1859-ch06-16", "motivation"),
                      ("darwin1859-ch01-17", "motivation"),
                      ("fisher-ftns", "context")):
        entry = {"id": cid, "iri": "https://w3id.org/delphi/resource/claim/" + cid,
                 "role": role, "relation_to_trpb_test": "motivation/context only; not equivalent to the TrpB operational hypothesis",
                 "sources": {}}
        for src in ("local", "network"):
            c = extract_claim(summary, cid, src)
            if not c:
                continue
            f = c.get("fields", {})
            entry["label"] = f.get("rdfs:label", entry.get("label"))
            entry["statement"] = f.get("dct:description", entry.get("statement"))
            entry["sources"][src] = {
                "nanopubs": c.get("nanopubs", []),
                "assessments": [
                    {"type": a.get("type"), "score": a.get("score"), "verdict": a.get("verdict"),
                     "assessor": str(a.get("assessor", "")).rsplit("/", 1)[-1]}
                    for a in c.get("assessments", [])],
            }
        claims.append(entry)
    searches = []
    for r in summary["queries"]:
        if r["tool"] == "delphi_search_claims" and r["status"] == "ok":
            searches.append({"text": r["arguments"]["text"], "source": r["arguments"]["source"],
                             "hits": len(r["response"]), "at_utc": r["at_utc"]})
    overview = {}
    for r in summary["queries"]:
        if r["tool"] == "delphi_overview" and r["status"] == "ok":
            doms = r["response"].get("domains", [])
            overview[r["arguments"]["source"]] = {
                "claims_total": sum(d["claims"] for d in doms), "domains": len(doms)}
    np_dir = out_dir / "nanopubs"
    np_dir.mkdir(parents=True, exist_ok=True)
    validation = json.loads((EVIDENCE_DIR / "nanopubs" / "validation.json").read_text())
    drafts = []
    for rep in validation["reports"]:
        shutil.copy(EVIDENCE_DIR / "nanopubs" / rep["file"], np_dir / rep["file"])
        drafts.append({"file": "data/nanopubs/" + rep["file"], "valid_rdflib": rep["valid"],
                       "triples": rep["triples"]})
    ev = {"built_utc": now_utc(), "delphi_run_utc": summary["run_utc"],
          "delphi_endpoint": summary["endpoint"], "claims": claims, "searches": searches,
          "overview": overview, "nanopub_drafts": drafts,
          "nanopub_status": "UNSIGNED local drafts; not published to any nanopub network; no trusty URI",
          "limits": summary["interpretation_limits"]}
    (out_dir / "evidence.json").write_text(json.dumps(ev, indent=2) + "\n")
    # contract-shaped claims block so the integrator can merge it into demo.json["claims"]
    contract_claims = []
    for c in claims:
        for src, v in c["sources"].items():
            contract_claims.append({
                "id": f"{c['id']}@{src}", "source_uri": c["iri"],
                "statement": c.get("statement"),
                "relation_to_test": "motivation-by-analogy; not equivalentTo and not a test of this claim" if c["role"] == "motivation"
                                    else "context only (partial-change theorem; Delphi notes it fails for total change under epistasis)",
                "status": f"unresolved; Delphi {src} source" + (f"; nanopub {v['nanopubs'][0]}" if v["nanopubs"] else "")})
    (EVIDENCE_DIR / "demo_claims.json").write_text(json.dumps(
        {"note": "Merge into demo.json['claims']. IDs preserve Delphi claim IDs with the queried source appended after '@'.",
         "claims": contract_claims}, indent=2) + "\n")
    return ev


# --------------------------------------------------------------------------
# blog rendering
# --------------------------------------------------------------------------

def dig(obj, path: str):
    for part in path.split("."):
        if isinstance(obj, list):
            try:
                obj = obj[int(part)]
            except (ValueError, IndexError):
                return None
        elif isinstance(obj, dict) and part in obj:
            obj = obj[part]
        else:
            return None
    return obj


def render_template(text: str, sources: dict[str, dict]) -> str:
    """Replace {{src:dot.path|fallback}}. Unknown values print the fallback."""
    def sub(m):
        src, path, fb = m.group(1), m.group(2), m.group(3) or "not available in saved artifacts"
        v = dig(sources.get(src, {}), path)
        if v is None:
            return fb
        if isinstance(v, bool):
            return "yes" if v else "no"
        if isinstance(v, float):
            return f"{v:.4g}"
        if isinstance(v, int) and abs(v) >= 10000:
            return f"{v:,}"
        return str(v)
    return re.sub(r"\{\{(\w+):([^|}]+)(?:\|([^}]*))?\}\}", sub, text)


DOC_TEMPLATES = ("blog", "pitch", "video-storyboard")


def render_docs(out_dir: Path | None = None) -> list[str]:
    """Render docs/<name>.template.md -> docs/<name>.md from saved artifacts only."""
    sources: dict[str, dict] = {}
    for key, rel in (("landscape", "site/data/landscape.meta.json"),
                     ("demo", "site/data/demo.json"),
                     ("results", "site/data/results.json"),
                     ("delphi", "artifacts/evidence/delphi_queries.json"),
                     ("nano", "artifacts/evidence/nanopubs/validation.json"),
                     ("route", "artifacts/evidence/route_summary.json"),
                     ("claimreuse", "artifacts/claim_reuse/reuse_benchmark.json"),
                     ("claimcheck", "artifacts/claim_reuse/verification_receipt.json"),
                     ("evsite", "site/data/evidence.json")):
        p = ROOT / rel
        if p.exists():
            sources[key] = json.loads(p.read_text())
    # Name policies explicitly: adding an arm must not silently change a positional citation.
    sources["policies"] = {p["id"]: p["by_family"] for p in sources.get("results", {}).get("policies", [])}
    for role in ("core", "proof", "gpu", "experience", "integrator"):
        p = ROOT / "tasks" / "results" / f"{role}.json"
        if p.exists():
            sources[role] = json.loads(p.read_text())
    outs = []
    for name in DOC_TEMPLATES:
        tp = ROOT / "docs" / f"{name}.template.md"
        if not tp.exists():
            continue
        body = render_template(tp.read_text(), sources)
        footer = (f"\n\n---\n*Rendered {now_seattle()} by `python -m evolve.evidence docs` from: "
                  f"{', '.join(sorted(sources)) or 'no artifacts'}. Edit `docs/{name}.template.md`, not this file.*\n")
        out = (out_dir or ROOT / "docs") / f"{name}.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(body + footer)
        outs.append(str(out))
    return outs


# --------------------------------------------------------------------------

def route_summary(raw_dir: Path, out: Path) -> dict:
    """Descriptive full-data route summary (NOT a benchmark) used by the blog/site."""
    scores = load_scores(raw_dir)
    start, target = "VFVS", "AIKG"
    rows = []
    grid = {"readnoise": (0.0, 1.0, 2.0, 3.0, 4.0), "envelope": (0.0, 0.005, 0.01), "point": (0.0, 0.005, 0.01)}
    for mode, vals in grid.items():
        for eps in vals:
            (pd_, _), (od, _) = reachability(scores, start, target, eps, mode)
            rows.append({"mode": mode, "assumed_parameter": eps,
                         "parameter_meaning": "kappa" if mode == "readnoise" else "eps",
                         "measured_only_distance": pd_, "optimistic_distance": od})
    def bisect_max(mode, hi, tol):
        lo = 0.0
        while hi - lo > tol:
            mid = (lo + hi) / 2
            if reachability(scores, start, target, mid, mode)[0][0] is not None:
                lo = mid
            else:
                hi = mid
        return lo

    breaks = {
        "readnoise_kappa": bisect_max("readnoise", 8.0, 0.005),
        "envelope_eps": bisect_max("envelope", 0.03, 1e-5),
        "point_eps": bisect_max("point", 0.03, 1e-5),
        "method": "bisection over measured-only BFS reachability; value is the largest parameter with a route, to the stated tolerance",
    }
    direct = None
    # direct 4-substitution orderings (shortest possible routes) at the lowest assumption
    import itertools
    subs = [(p, target[p]) for p in range(4) if start[p] != target[p]]
    admitted = 0
    for perm in itertools.permutations(subs):
        g, ok = start, True
        for p, a in perm:
            n = g[:p] + a + g[p + 1:]
            ok &= edge_status(scores, g, n, 0.0, "readnoise") == "accepted"
            g = n
        admitted += ok
    direct = {"orderings": len(list(itertools.permutations(subs))), "admitted_at_parameter_0": admitted}
    res = {"kind": "descriptive full-data analysis; not a predictive benchmark",
           "break_points": breaks, "direct_orderings": direct,
           "start": start, "target": target,
           "score_scale": "mu_k minus per-replicate stop-codon mean, averaged over 2 replicates (see landscape.meta.json)",
           "rows": rows, "built_utc": now_utc()}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=2) + "\n")
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m evolve.evidence")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("landscape"); p.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    sub.add_parser("delphi")
    sub.add_parser("nanopubs")
    p = sub.add_parser("validate"); p.add_argument("paths", nargs="*", type=Path)
    sub.add_parser("site-data")
    sub.add_parser("docs")
    p = sub.add_parser("route-summary"); p.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    a = ap.parse_args(argv)
    if a.cmd == "landscape":
        m = build_landscape(a.raw, SITE_DATA)
        print(json.dumps(m["counts"], indent=2))
    elif a.cmd == "delphi":
        s = run_delphi(EVIDENCE_DIR)
        print(f"ok={s['n_ok']} error={s['n_error']}")
        return 0 if s["n_error"] == 0 else 1
    elif a.cmd == "nanopubs":
        rep = write_drafts(EVIDENCE_DIR / "nanopubs")
        print(json.dumps(rep, indent=2))
        return 0 if rep["all_valid"] else 1
    elif a.cmd == "validate":
        paths = a.paths or sorted((EVIDENCE_DIR / "nanopubs").glob("*.trig"))
        reps = [validate_trig(p) for p in paths]
        print(json.dumps(reps, indent=2))
        return 0 if reps and all(r["valid"] for r in reps) else 1
    elif a.cmd == "site-data":
        ev = site_evidence(SITE_DATA)
        print(json.dumps({"claims": len(ev["claims"]), "drafts": len(ev["nanopub_drafts"])}))
    elif a.cmd == "docs":
        print("\n".join(render_docs()))
    elif a.cmd == "route-summary":
        print(json.dumps(route_summary(a.raw, EVIDENCE_DIR / "route_summary.json"), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
