"""Tests for evolve/evidence.py and the static site's graph logic (experience worker).

They read saved artifacts and the cached CSVs; no network access. Raw data location:
$EVOLVE_RAW, else data/raw/, else the coordinator's scout cache.
"""
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from evolve import evidence as ev

ROOT = Path(__file__).resolve().parent.parent


def raw_dir():
    for c in (os.environ.get("EVOLVE_RAW"), ROOT / "data" / "raw", ev.DEFAULT_RAW):
        if c and (Path(c) / "summary_AA.csv").exists():
            return Path(c)
    pytest.skip("raw TrpB CSV cache not available")


@pytest.fixture(scope="module")
def scores():
    return ev.load_scores(raw_dir())


# ---- landscape pack --------------------------------------------------------

def test_landscape_meta_counts_and_provenance():
    meta = json.loads((ev.SITE_DATA / "landscape.meta.json").read_text())
    c = meta["counts"]
    assert c["library_aa_genotypes"] == 160000
    assert c["measured_non_stop"] == 159129
    assert c["unmeasured_cells"] == 871
    assert c["measured_non_stop"] + c["unmeasured_cells"] == 160000
    assert c["measured_imputed_overlap"] == 0
    assert meta["source"]["license"].startswith("CC0")
    for f in meta["source"]["files"].values():
        assert re.fullmatch(r"[0-9a-f]{64}", f["sha256"])


def test_landscape_hash_matches_cache():
    meta = json.loads((ev.SITE_DATA / "landscape.meta.json").read_text())
    got = ev.sha256_file(raw_dir() / "summary_AA.csv")
    assert got == meta["source"]["files"]["summary_AA.csv"]["sha256"]


def test_packed_values_match_csv(scores):
    import base64
    import numpy as np

    js = (ev.SITE_DATA / "landscape.js").read_text()
    pack = json.loads(js[js.index("{"): js.rindex("}") + 1])
    r1 = np.frombuffer(base64.b64decode(pack["r1"]), "<i2")
    cnt = np.frombuffer(base64.b64decode(pack["cnt"]), "<u2")
    assert r1.shape == (160000,)
    missing = int((r1 == -32768).sum())
    assert missing == 871
    for g in ("VFVS", "AIKG", "VFMG", "CLKG"):
        i = ev.genotype_index(g)
        assert abs(r1[i] / 50000 - scores[g][0]) <= 1.1e-5
        assert cnt[i] == scores[g][2]
    # every unmeasured packed cell is absent from the measured table
    for g, imp in pack["unknown"].items():
        assert g not in scores


# ---- Python mirror of the route logic ---------------------------------------

def test_route_lengths_default_noise_model(scores):
    d = {k: ev.reachability(scores, "VFVS", "AIKG", k, "readnoise")[0][0] for k in (0.0, 2.0, 3.0)}
    assert d == {0.0: 5, 2.0: 6, 3.0: 7}


def test_mutant_edge_rule_changes_decision(scores):
    """Flipping the dominance inequality or inflating the bound must change acceptance."""
    # at kappa=0 the first step VFVS->VFMS is admitted; a huge assumed bound rejects it
    assert ev.edge_status(scores, "VFVS", "VFMS", 0.0, "readnoise") == "accepted"
    assert ev.edge_status(scores, "VFVS", "VFMS", 50.0, "readnoise") == "rejected"
    # reverse direction (a decrease) is rejected
    assert ev.edge_status(scores, "VFMS", "VFVS", 0.0, "readnoise") == "rejected"


def test_unmeasured_edges_are_unknown_not_rejected(scores):
    pack = json.loads((ev.SITE_DATA / "landscape.meta.json").read_text())
    unmeasured = None
    for g in ("EEEE", "WWWW", "HHHH", "KKKK"):
        if g not in scores:
            unmeasured = g
            break
    if unmeasured is None:
        # search the packed map instead
        for i in range(160000):
            g = "".join(ev.AA[(i // w) % 20] for w in (8000, 400, 20, 1))
            if g not in scores:
                unmeasured = g
                break
    assert unmeasured is not None
    nb = next(ev.neighbors(unmeasured))
    assert ev.edge_status(scores, unmeasured, nb, 0.0) == "unknown"
    assert ev.edge_status(scores, nb, unmeasured, 0.0) == "unknown"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_js_matches_python_mirror(scores):
    js = r"""
const fs=require('fs'); const L=require(process.argv[1]+'/site/lib.js'); global.window={};
eval(fs.readFileSync(process.argv[1]+'/site/data/landscape.js','utf8').replace('window.TRPB_LANDSCAPE','global.PACK'));
const D=L.decode(PACK); const s=L.idxOf('VFVS'), t=L.idxOf('AIKG'); const out={};
for (const k of [0,2,3]) { const d=L.decide(D,s,t,k,'readnoise'); out['k'+k]=d.route?d.route.length-1:null; }
out.maxKappa=L.maxEps(D,s,t,'readnoise'); out.direct=L.directOrderings(D,s,t,0,'readnoise').filter(x=>x.accepted).length;
out.blocked=L.decide(D,s,t,6,'readnoise').status;
console.log(JSON.stringify(out));
"""
    r = subprocess.run(["node", "-e", js, str(ROOT)], capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    o = json.loads(r.stdout)
    assert (o["k0"], o["k2"], o["k3"]) == (5, 6, 7)
    assert o["direct"] == 0
    assert o["blocked"] == "blocked"
    # independent bisection in Python on the same measured graph
    lo, hi = 0.0, 8.0
    for _ in range(14):
        mid = (lo + hi) / 2
        if ev.reachability(scores, "VFVS", "AIKG", mid, "readnoise")[0][0] is not None:
            lo = mid
        else:
            hi = mid
    assert abs(o["maxKappa"] - lo) < 0.02


# ---- Delphi record ------------------------------------------------------------

def test_delphi_record_complete_and_sourced():
    d = json.loads((ev.EVIDENCE_DIR / "delphi_queries.json").read_text())
    assert d["n_error"] == 0 and d["n_ok"] == len(d["queries"])
    assert d["endpoint"].startswith("https://")
    for cid in ("darwin1859-ch06-08", "fisher-ftns"):
        for src in ("local", "network"):
            c = ev.extract_claim(d, cid, src)
            assert c and c["claim"].endswith("/" + cid) and c["source"] == src
    # the honest null: epistemic limits are recorded next to the query results
    assert any("not proof" in x for x in d["interpretation_limits"])
    hits = {(q["arguments"]["text"], q["arguments"]["source"]): len(q["response"])
            for q in d["queries"] if q["tool"] == "delphi_search_claims"}
    assert hits[("epistasis", "local")] == 0 and hits[("epistasis", "network")] == 0


def test_site_evidence_json_preserves_ids_and_sources():
    e = json.loads((ev.SITE_DATA / "evidence.json").read_text())
    ids = {c["id"] for c in e["claims"]}
    assert "darwin1859-ch06-08" in ids
    for c in e["claims"]:
        assert c["iri"] == "https://w3id.org/delphi/resource/claim/" + c["id"]
        assert c["role"] in ("motivation", "context")
        assert "not equivalent" in c["relation_to_trpb_test"]
        assert set(c["sources"]) <= {"local", "network"}
    assert e["overview"]["local"]["claims_total"] != e["overview"]["network"]["claims_total"]
    assert "UNSIGNED" in e["nanopub_status"]


# ---- nanopub drafts --------------------------------------------------------------

def drafts():
    return sorted((ev.EVIDENCE_DIR / "nanopubs").glob("*.trig"))


def test_drafts_exist_and_validate():
    assert len(drafts()) >= 3
    for p in drafts():
        r = ev.validate_trig(p)
        assert r["valid"], (p.name, r["problems"])
        assert set(r["graphs"]) and len(r["graphs"]) == 4


def test_drafts_are_unsigned_and_have_no_trusty_uri():
    for p in drafts():
        txt = p.read_text()
        assert "UNSIGNED DRAFT" in txt
        assert "http://purl.org/nanopub/temp/delphi-evolve/" in txt
        assert "npx:hasPublicKey" not in txt and "npx:hasSignature" not in txt
        # no fabricated trusty URI of our own: only the Delphi-owned IRIs we quote may appear
        for m in re.findall(r"https://w3id\.org/np/(\w+)", txt):
            assert m.startswith("RA")  # quoted from Delphi's network record, not minted here


def test_draft_hypothesis_links_darwin_as_motivation_only():
    txt = (ev.EVIDENCE_DIR / "nanopubs" / "operational-hypothesis-v1.trig").read_text()
    assert "de:motivatedBy <https://w3id.org/delphi/resource/claim/darwin1859-ch06-08>" in txt
    assert "equivalentTo" not in txt and "owl:sameAs" not in txt
    assert "NOT equivalent" in txt


def test_validator_rejects_mutants(tmp_path):
    good = (ev.EVIDENCE_DIR / "nanopubs" / "scope-limitation-v1.trig").read_text()
    # 1. missing unsigned marker
    p = tmp_path / "m1.trig"; p.write_text(good.replace("UNSIGNED DRAFT", "reviewed"))
    assert not ev.validate_trig(p)["valid"]
    # 2. head points at a missing assertion graph
    p = tmp_path / "m2.trig"; p.write_text(good.replace("np:hasAssertion sub:assertion", "np:hasAssertion sub:nothere"))
    assert not ev.validate_trig(p)["valid"]
    # 3. trusty-looking nanopub URI
    p = tmp_path / "m3.trig"
    p.write_text(good.replace("http://purl.org/nanopub/temp/delphi-evolve/scope-limitation-v1",
                              "https://w3id.org/np/RAfakefakefakefake"))
    assert not ev.validate_trig(p)["valid"]
    # 4. syntactically broken
    p = tmp_path / "m4.trig"; p.write_text(good + "\n sub:x sub:y")
    with pytest.raises(Exception):
        ev.validate_trig(p)


def test_validation_report_matches_files():
    rep = json.loads((ev.EVIDENCE_DIR / "nanopubs" / "validation.json").read_text())
    assert rep["all_valid"] and {r["file"] for r in rep["reports"]} == {p.name for p in drafts()}


# ---- blog template -----------------------------------------------------------------

def test_render_template_uses_fallback_for_missing():
    out = ev.render_template("a {{demo:benchmark.metrics.x|NOT RUN}} b {{core:status|none}}", {"core": {"status": "ok"}})
    assert out == "a NOT RUN b ok"
    assert ev.render_template("{{demo:a.b}}", {}) == "not available in saved artifacts"


def test_now_seattle_zone_labels():
    s = ev.now_seattle()
    assert s.endswith(("PDT", "PST")) or "UTC" in s


# ---- rendered docs --------------------------------------------------------------------

def test_docs_render_from_artifacts_without_unresolved_placeholders(tmp_path):
    outs = ev.render_docs(tmp_path)  # render to a temp dir; committed docs are re-rendered only by the CLI
    assert len(outs) == 3
    committed = {n: (ROOT / "docs" / f"{n}.md").read_text().split("\n---\n*Rendered")[0] for n in ev.DOC_TEMPLATES}
    for n in ev.DOC_TEMPLATES:
        fresh = (tmp_path / f"{n}.md").read_text().split("\n---\n*Rendered")[0]
        assert fresh == committed[n], f"docs/{n}.md is stale; run python -m evolve.evidence docs"
    route = json.loads((ev.EVIDENCE_DIR / "route_summary.json").read_text())
    meta = json.loads((ev.SITE_DATA / "landscape.meta.json").read_text())
    blog = (tmp_path / "blog.md").read_text()
    pitch = (tmp_path / "pitch.md").read_text()
    story = (tmp_path / "video-storyboard.md").read_text()
    for txt in (blog, pitch, story):
        assert "{{" not in txt and "}}" not in txt
    assert f"{meta['counts']['measured_non_stop']:,}" in blog and f"{meta['counts']['measured_non_stop']:,}" in pitch
    assert f"{route['break_points']['readnoise_kappa']:.4g}" in blog
    assert f"{route['break_points']['readnoise_kappa']:.4g}" in story
    # absent artifacts must read as absent, never as success
    if not (ROOT / "tasks" / "results" / "proof.json").exists():
        assert "not integrated into this checkout" in blog
    if not (ROOT / "site" / "data" / "demo.json").exists():
        assert "no demo.json integrated" in blog
        assert "do not quote results" in pitch


def test_docs_do_not_overclaim():
    for name in ("blog", "pitch", "novelty", "video-storyboard"):
        txt = (ROOT / "docs" / f"{name}.md").read_text().lower()
        for bad in ("we beat alde", "outperforms alde", "proves darwin", "published to the nanopub network",
                    "validated market", "customers include", "market size of"):
            assert bad not in txt, (name, bad)


# ---- differential test: JS decision vs Python mirror on seeded pairs --------------------

@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_js_python_differential_pairs(scores):
    import random

    rng = random.Random(20261031)
    gs = sorted(scores)
    # bounded work: panel pairs from the parent at moderate kappa, plus random and
    # unmeasured-adjacent pairs at large kappa where closed sets are small
    pairs = [("VFVS", t, k) for t in ("AIKG", "CLKG", "VLKG", "ALKG") for k in (2.0, 3.0)]
    pairs += [(rng.choice(gs), rng.choice(gs), k) for k in (6.0, 8.0) for _ in range(5)]
    unmeasured = [g for g in ("".join(ev.AA[(i // w) % 20] for w in (8000, 400, 20, 1)) for i in range(160000))
                  if g not in scores]
    for u in rng.sample(unmeasured, 4):
        nbs = [n for n in ev.neighbors(u) if n in scores]
        pairs.append((nbs[0], rng.choice(gs), 8.0))
    js = r"""
const fs=require('fs'); const L=require(process.argv[1]+'/site/lib.js'); global.window={};
eval(fs.readFileSync(process.argv[1]+'/site/data/landscape.js','utf8').replace('window.TRPB_LANDSCAPE','global.PACK'));
const D=L.decode(PACK); const pairs=JSON.parse(process.argv[2]);
console.log(JSON.stringify(pairs.map(([a,b,k])=>{const d=L.decide(D,L.idxOf(a),L.idxOf(b),k,'readnoise');
  return [d.status, d.route?d.route.length-1:null, d.route? d.route.filter(v=>!D.measured[v]).length : null];})));
"""
    r = subprocess.run(["node", "-e", js, str(ROOT), json.dumps(pairs)], capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr
    got = json.loads(r.stdout)
    seen = set()
    for (a, b, k), (status, length, n_unk) in zip(pairs, got):
        if a == b:
            continue
        (pd_, _), (od, _) = ev.reachability(scores, a, b, k, "readnoise")
        if pd_ is not None:
            assert (status, length) == ("open", pd_), (a, b, k)
        elif od is not None:
            assert status == "undetermined" and length == od and n_unk >= 1, (a, b, k)
        else:
            assert status == "blocked", (a, b, k)
        seen.add(status)
    assert "open" in seen and "blocked" in seen
    print("statuses exercised:", sorted(seen))
