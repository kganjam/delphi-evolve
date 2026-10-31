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
             r"bonus", r"commons gain", r"structure[- ]to[- ]diffusion", r"nanopub", r"disprov", r"\bwas wrong\b", r"\bwrong\b",
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
    for d in ("artifacts", "planning", "experiments", "tasks", "turing_scope", "docs", "site"):
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
    _mut(root, "The scorecard of 21 candidate laws", "The scorecard of 22 candidate laws")
    code, out = trace(root, out=tmp_path / "t.json")
    assert code == 1 and "21 candidate laws" in out


def test_pending_replaced_by_a_number_fails(tmp_path):
    root = _copy(tmp_path)
    _mut(root, 'excluded, with reasons</td><td><span class="pend">pending</span>', "excluded, with reasons</td><td><b>7</b>")
    code, out = trace(root, out=tmp_path / "t.json")
    assert code == 1 and ("must read 'pending'" in out or "not traced" in out)


def test_unclaimed_number_and_fake_ledger_id_fail(tmp_path):
    root = _copy(tmp_path)
    _mut(root, "We ran no experiment.", "We ran no experiment (p = 0.04).")
    code, out = trace(root, out=tmp_path / "t.json")
    assert code == 1 and "not traced" in out
    root2 = _copy(tmp_path / "b")
    _mut(root2, "<b>Ledger</b> F01 F07", "<b>Ledger</b> F77 F07")
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
    assert idx.count('class="pend"') >= 6
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


HARD_BANNED = [r"no machine[- ]checked", r"did not find a prior machine", r"nobody has (?:a )?(?:gate|library|checked)", r"Arcuri", r"PMC9884266",
               r"Villar-Sepulveda", r"solved (?:the )?navier", r"navier[- ]stokes", r"prove2\.me"]


def test_hard_banned_claims_and_citations_absent_everywhere():
    """Not negation-aware: these strings must not appear at all (ATLAS exists; the two citations were wrong; prove2.me is not to be visited)."""
    bad = [(n, p) for n, t in _texts().items() for p in HARD_BANNED if re.search(p, t, re.I)]
    assert not bad, bad


def test_atlas_is_credited_and_misprediction_map_is_pending():
    t = _texts()
    assert "atlas-lean" in t["deck slide 6"] and "atlas-lean" in t["site/index.html"] and "atlas-lean" in t["site/blog.html"]
    s5 = t["deck slide 5"]
    m = re.search(r"over a large ensemble: (\S+)", s5)
    assert m and m.group(1).lower() == "pending"
    assert re.search(r"98\.3|0\.4 ?%", " ".join(t.values())) is None  # toy-ensemble figures are not shown
