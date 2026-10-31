"""Delphi deck/site/blog gates: numbers trace, pending stays pending, forbidden claims absent, links resolve."""
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
D = REPO / "presentation" / "delphi"
sys.path.insert(0, str(REPO / "presentation"))
import trace_numbers as TN  # noqa: E402

FORBIDDEN = [r"first[- ]ever", r"first (?:formal )?(?:biology )?library", r"biology has no", r"\bsolved\b", r"navier", r"universal(?:ly)?\b",
             r"bonus", r"commons gain", r"structure[- ]to[- ]diffusion", r"nanopub", r"disprov", r"\b(?:is|was|are|were) wrong\b",
             r"autonomous(?:ly)? detect", r"robustness cliff", r"above the (?:robustness )?cliff"]
NEG = re.compile(r"\b(?:not|no|never|none|nor|without|false|neither|n't)\b", re.I)


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def trace(root, deck="presentation/delphi/deck.html", out=None):
    r = run([sys.executable, str(D / "trace.py"), "--root", str(root), "--deck", deck, "--out", str(out)])
    return r.returncode, r.stdout


def test_committed_deck_traces(tmp_path):
    code, out = trace(REPO, out=tmp_path / "t.json")
    assert code == 0, out
    res = json.loads((tmp_path / "t.json").read_text())
    assert res["ok"] and res["claims_checked"] >= 20 and res["pdf_pages_checked"] == 6


def _copy(tmp_path):
    root = tmp_path / "root"
    shutil.copytree(REPO / "presentation", root / "presentation", ignore=shutil.ignore_patterns("screenshots", "video", "__pycache__", "tests"))
    for d in ("artifacts", "planning", "experiments", "tasks", "turing_scope", "docs", "site", "scopedesk", "lean_price"):
        shutil.copytree(REPO / d, root / d, ignore=shutil.ignore_patterns("*.mp4", "*.zip", "*.npz", "*.gz", ".lake", "build", "queries", "shards"))
    subprocess.run(["git", "init", "-q"], cwd=root)
    return root


def _mut(root, old, new):
    p = root / "presentation/delphi/deck.html"
    t = p.read_text(encoding="utf-8")
    assert old in t, old
    p.write_text(t.replace(old, new, 1), encoding="utf-8")


def test_changed_number_fails(tmp_path):
    root = _copy(tmp_path)
    _mut(root, "21 records: 6 linked", "22 records: 6 linked")
    code, out = trace(root, out=tmp_path / "t.json")
    assert code == 1 and "21 records" in out


def test_pending_replaced_by_a_number_fails(tmp_path):
    root = _copy(tmp_path)
    _mut(root, 'Misprediction map over a large ensemble: <span class="pend">pending</span>', "Misprediction map over a large ensemble: <b>7</b>")
    code, out = trace(root, out=tmp_path / "t.json")
    assert code == 1 and ("must read 'pending'" in out or "not traced" in out)


def test_unclaimed_number_and_fake_ledger_id_fail(tmp_path):
    root = _copy(tmp_path)
    _mut(root, "No wet-lab experiment; simulations only.", "No wet-lab experiment; simulations only (p = 0.04).")
    code, out = trace(root, out=tmp_path / "t.json")
    assert code == 1 and "not traced" in out
    root2 = _copy(tmp_path / "b")
    _mut(root2, "<b>Ledger</b> F01 F02", "<b>Ledger</b> F77 F02")
    code, out = trace(root2, out=tmp_path / "t2.json")
    assert code == 1 and "F77" in out


def test_changed_artifact_is_stale_or_mismatch(tmp_path):
    root = _copy(tmp_path)
    p = root / "artifacts/turing_scope/results.json"
    d = json.loads(p.read_text())
    d["length_scan"][3]["verdict"] = "stable"
    d["length_scan"][3]["unstable_modes"] = []
    d["length_scan"][3]["q_of_unstable_modes"] = []
    p.write_text(json.dumps(d))
    code, out = trace(root, out=tmp_path / "t.json")
    assert code == 1 and ("STALE" in out or "artifact gives" in out)


def _texts():
    import html
    out = {}
    deck = (D / "deck.html").read_text(encoding="utf-8")
    for i, s in enumerate(TN.parse_deck(D / "deck.html"), 1):
        out[f"deck slide {i}"] = " ".join([s["html"], s["fn"], s["notes"]])
    for f in ("index.html", "appendix.html", "blog.html"):
        t = (REPO / "site/delphi" / f).read_text(encoding="utf-8")
        t = re.sub(r"<style.*?</style>|<script.*?</script>", "", t, flags=re.S)
        out[f"site/{f}"] = html.unescape(re.sub(r"<[^>]+>", " ", t))
    for f in ("blog.md", "storyboard.md", "speaker-notes.md"):
        out[f] = (D / f).read_text(encoding="utf-8")
    return out


def test_no_forbidden_claims_outside_negations():
    bad = []
    for name, text in _texts().items():
        for sent in re.split(r"(?<=[.!?;:])\s+|\n+|\|", re.sub(r"\s+", " ", text)):
            for pat in FORBIDDEN:
                if re.search(pat, sent, re.I) and not NEG.search(sent):
                    bad.append((name, pat, sent[:140]))
    assert not bad, bad


def test_site_pages_have_pending_and_review_link_resolves():
    idx = (REPO / "site/delphi/index.html").read_text(encoding="utf-8")
    assert idx.count('class="pend"') >= 5
    for f in ("index.html", "appendix.html", "blog.html"):
        t = (REPO / "site/delphi" / f).read_text(encoding="utf-8")
        assert not re.search(r'(?:href|src)="https?://', t), "external resource"
        for u in re.findall(r'(?:href|src)="([^"#:]+)', t):
            assert (REPO / "site/delphi" / u).exists(), (f, u)


def test_site_assets_equal_sources():
    for n in ("deck.pdf", "deck.html", "speaker-notes.md"):
        assert hashlib.sha256((REPO / "site/delphi/assets" / n).read_bytes()).hexdigest() == hashlib.sha256((D / n).read_bytes()).hexdigest(), n


def test_site_numbers_are_accounted_for():
    """Every number on the site pages and blog is a number that is on the deck, in facts.json, or in a cited artifact."""
    facts = json.loads((D / "facts.json").read_text())
    rob = json.loads((REPO / "artifacts/gpuops/robustness_tax_check.json").read_text())
    pool = set()
    for s in TN.parse_deck(D / "deck.html"):
        pool |= {t.replace(",", "") for t in TN.tokens(" ".join([s["html"], s["svg"], s["fn"]]))}
    pool |= {t.replace(",", "") for t in TN.tokens(json.dumps(facts, ensure_ascii=False))}
    pool |= {t.replace(",", "") for t in TN.tokens(json.dumps(rob))}
    texts = _texts()
    ok_extra = {"31", "2026"}  # the dated status line
    commit = json.loads((D / "deck.provenance.json").read_text())["git"]["head"]
    left = {}
    for name in ("site/index.html", "site/appendix.html", "site/blog.html"):
        t = re.sub(r"\b" + commit[:8] + r"\b", " ", texts[name])
        t = re.sub(r"\b[0-9a-f]{7}\b", " ", t)  # short git hashes
        toks = [x.replace(",", "") for x in TN.tokens(t)]
        miss = sorted({x for x in toks if x not in pool and x not in ok_extra})
        if miss:
            left[name] = miss
    assert not left, left


HARD_BANNED = [r"no sponsor", r"sponsor[- ](?:use )?points", r"sponsor bonus",r"More agents did not help", r"more agents did not help", r"\b17 of 20\b", r"\b17 were caught", r"20 ledger rows", r"exact answers", r"Codex reviewed the corrected", r"sourced open problems", r"we ran no experiment", r"Codex's metadata and text check",
               r"132 of 136(?! items of the v1)",r"near-vacuous", r"not_lt", r"saying nothing", r"tautolog", r"19 biological laws", r"Hamilton[/ -]ESS derived", r"compute-matched (?:collective )?advantage", r"Mathlib biology benchmark",
               r"131[- ]item key|eab23bff(?!.*superseded)",r"no machine[- ]checked", r"did not find a prior machine", r"nobody has (?:a )?(?:gate|library|checked)", r"Arcuri", r"PMC9884266",
               r"Villar-Sepulveda", r"solved (?:the )?navier", r"navier[- ]stokes", r"prove2\.me"]


def test_hard_banned_claims_and_citations_absent_everywhere():
    """Not negation-aware: these strings must not appear at all (ATLAS exists; the two citations were wrong; prove2.me is not to be visited)."""
    bad = [(n, p) for n, t in _texts().items() for p in HARD_BANNED if re.search(p, t, re.I)]
    assert not bad, bad


def test_scorecard_uses_only_the_approved_wording():
    t = _texts()
    for k in ("deck slide 6", "site/index.html"):
        assert "6 linked to scope-check benchmark families" in t[k] and "1 related formal lemma (target unestablished)" in t[k], k
        assert "2 empirical/framework" in t[k] and "12 without a corresponding check" in t[k], k
        assert re.search(r"Single-reader statuses", t[k]), k
    bad = [(n, p_) for n, x in t.items() for p_ in (r"\b7 attempted", r"5 (?:with a )?scope", r"scope[- ]found", r"not attempted") if re.search(p_, x, re.I)]
    assert not bad, bad


def test_headroom_and_pilot_are_scoped():
    t = _texts()
    s5 = t["deck slide 5"]
    assert "121/127" in s5 and "110/127" in s5 and "Checker-tool arm not run" in s5 and "judgement, not derivation" in s5
    assert "ceiling" in s5 and "Call-matched, not compute-matched" in s5 and "after the outcomes" in s5
    assert not re.search(r"24/24|24 of 24", " ".join(t.values())), "the host's mismatched 24/24 run stays out"


def test_atlas_is_credited_and_misprediction_map_is_pending():
    t = _texts()
    assert "ATLAS" in t["deck slide 3"] and all("atlas-lean" in t[k] for k in ("deck slide 6", "site/index.html", "site/blog.html"))
    s6 = t["deck slide 6"]
    m = re.search(r"Misprediction map over a large ensemble: (\S+)", s6)
    assert m and m.group(1).lower() == "pending"
    assert re.search(r"98\.3|0\.4 ?%", " ".join(t.values())) is None  # toy-ensemble figures are not shown


def test_video_captions_follow_the_same_rules():
    caps = json.loads((D / "video/captions.json").read_text())
    txt = " ".join(list(caps["deck_slide_captions"].values()) + [caps["site_ledger_caption"], caps["persistent_tag"]])
    assert not [p for p in HARD_BANNED if re.search(p, txt, re.I)]
    for sent in re.split(r"(?<=[.!?])\s+", txt):
        assert not any(re.search(p, sent, re.I) and not NEG.search(sent) for p in FORBIDDEN), sent
    assert "not frozen" not in txt.lower()  # the test set is frozen; stale caption guard


def test_video_manifest_is_pinned_and_silent():
    m = json.loads((D / "video/manifest.json").read_text())
    assert m["ok"] and m["video"]["audio"] == "none" and 60 <= m["video"]["duration_s"] <= 95 and m["page_errors"] == []
    assert subprocess.run(["git", "-C", str(REPO), "cat-file", "-e", m["source"]["git_head"] + "^{commit}"], capture_output=True).returncode == 0
    mp4 = D / "video" / m["video"]["file"]
    assert hashlib.sha256(mp4.read_bytes()).hexdigest() == m["video"]["sha256"], "video changed after its manifest was written"


def test_bundle_manifest_hashes_match_current_files_when_present():
    bm = D / "dist/bundle-manifest.json"
    if not bm.exists():
        return
    m = json.loads(bm.read_text())
    stale = [f for f, h in m["files"].items() if (REPO / f).exists() and hashlib.sha256((REPO / f).read_bytes()).hexdigest() != h]
    # files regenerated after the bundle (video manifest, rehearsal sheet) are expected to differ until the final cut; the deck and facts must not
    assert not [f for f in stale if f.startswith(("presentation/delphi/deck.", "presentation/delphi/facts", "site/delphi/index"))], stale


def test_rehearsal_sheet_says_no_human_rehearsal_yet():
    t = (D / "REHEARSAL.md").read_text()
    assert "no human rehearsal has been done" in t


def test_every_slide_footnote_carries_a_review_status_and_unreviewed_items_say_single_reader():
    sl = TN.parse_deck(D / "deck.html")
    for i, s in enumerate(sl, 1):
        assert "Review" in s["fn"], f"slide {i} footnote has no review status"
    for i in (2, 4, 5, 6):
        assert "single-reader" in sl[i - 1]["fn"], f"slide {i} must label its unreviewed items single-reader"


def test_frontier_example_is_absent_until_its_result_is_committed_in_tree_and_carries_its_limits(tmp_path):
    sys.path.insert(0, str(D))
    import facts as FA
    old = FA.ROOT
    try:
        FA.ROOT = tmp_path
        (tmp_path / "planning/frontier").mkdir(parents=True)
        assert FA.frontier_example_facts()["present"] is False
        p = tmp_path / FA.FRONTIER_EXAMPLE
        base = "Preregistration f497073, result 9f237ae. Single-reader. n=1 per population, haploid assemblies, nothing causal, Pachon not tested."
        p.write_text(base.replace("Pachon", "another population"))
        try:
            FA.frontier_example_facts()
            raise AssertionError("must require the Pachon limit")
        except AssertionError as e:
            assert "pachon" in str(e).lower()
        p.write_text(base)
        fx = FA.frontier_example_facts()
        assert fx["present"] and fx["prereg_commit"] == "f497073" and fx["result_commit"] == "9f237ae"
        p.write_text(base.replace("f497073", "0000000"))
        try:
            FA.frontier_example_facts()
            raise AssertionError("must require both commit ids")
        except AssertionError as e:
            assert "commit" in str(e).lower()
    finally:
        FA.ROOT = old


def test_site_has_no_cavefish_text_while_the_result_is_not_in_the_tree():
    if (REPO / "planning/frontier/oca2-exon21-molino-RESULT.md").exists():
        return
    for k, x in _texts().items():
        assert not re.search(r"cavefish|oca2|exon 21", x, re.I), k
