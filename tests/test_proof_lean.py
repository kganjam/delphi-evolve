"""Real Lean kernel checks. Bounded subprocesses; skip is NOT used: absent Lean is a failure."""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evolve import proof as P  # noqa: E402

ART = ROOT / "artifacts" / "proof"
CERTS = {p.stem: P.read_json(p) for p in sorted(ART.glob("trpb_*.json"))}


@pytest.fixture(scope="module")
def built():
    r = P.run_cmd([P.find_tool("lake"), "build"], cwd=P.LEAN_DIR, scope=False)
    assert r["exit_code"] == 0, r["stdout"] + r["stderr"]
    return r


def test_lean_version_pinned():
    assert "4.35.0" in P.lean_version()


def test_original_compiles_and_axioms_are_clean(built):
    r = P.run_cmd([P.find_tool("lake"), "env", P.find_tool("lean"), "DarwinBridge/Audit.lean"], cwd=P.LEAN_DIR)
    assert r["exit_code"] == 0
    ax = P.parse_axiom_report(r["stdout"] + r["stderr"])
    assert "DarwinBridge.route_sound" in ax and "DarwinBridge.blocked_cut_sound" in ax
    for label in CERTS:
        assert f"{P.module_name(CERTS[label])}.cert_ok" in ax
    assert all(set(v) <= P.ALLOWED_AXIOMS for v in ax.values()), ax
    assert not any("sorryAx" in v or "ofReduceBool" in " ".join(v) for v in ax.values())
    assert "sorry" not in (r["stdout"] + r["stderr"])


def test_generated_lean_matches_certificate_json():
    for c in CERTS.values():
        f = P.LEAN_DIR / "DarwinBridge" / "Certs" / (P.module_name(c).rsplit(".", 1)[1] + ".lean")
        assert f.read_text() == P.render_lean(c)
        assert c["certificate_sha256"] in f.read_text() and c["source"]["sha256"] in f.read_text()


def test_no_forbidden_constructs_in_lean_sources():
    sys.path.insert(0, str(ROOT / "scripts"))
    import check_proofs
    assert check_proofs.forbidden_tokens(P.LEAN_DIR) == []


def _compile(cert, name, built_):
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / f"{name}.lean"
        f.write_text(P.render_lean({**cert, "label": name}))
        return P.lean_compile_file(f)


@pytest.mark.parametrize("label,mutant", [
    ("trpb_route_delta005", "dominance_tight_equal"),
    ("trpb_blocked_delta005", "cut_edge_tight_strict"),
])
def test_boundary_controls_are_accepted(built, label, mutant):
    m = next(m for m in P.data_mutants(CERTS[label]) if m["name"].endswith(mutant))
    assert _compile(m["cert"], "ctl_" + mutant, built)["exit_code"] == 0


@pytest.mark.parametrize("label,mutant", [
    ("trpb_route_delta005", "dominance_violated_by_one"),   # dominance inequality invalidated
    ("trpb_route_delta005", "unknown_intermediate"),
    ("trpb_route_delta005", "skipped_vertex_nonadjacent"),
    ("trpb_blocked_delta005", "open_cut_edge_equal"),       # a cut edge opened
    ("trpb_blocked_delta005", "neighbour_unknown"),
    ("trpb_blocked_multi_delta005", "member_removed_opens_edge"),
])
def test_scientific_mutants_are_rejected_by_the_kernel_decision(built, label, mutant):
    m = next(m for m in P.data_mutants(CERTS[label]) if m["name"].endswith(mutant))
    r = _compile(m["cert"], "mut_" + mutant, built)
    assert r["exit_code"] != 0
    assert re.search(r"decide.*proved that the proposition", r["stdout"] + r["stderr"], re.S)


def test_source_mutant_breaking_the_comparison_stops_the_theorem_compiling():
    mut = next(m for m in P.SOURCE_MUTANTS if m[0] == "core_flip_dominance")
    with tempfile.TemporaryDirectory() as td:
        tree = P.copy_lean_tree(Path(td) / "lean")
        P.apply_source_mutant(tree, mut)
        r = P.run_cmd([P.find_tool("lake"), "build"], cwd=tree)
        assert r["exit_code"] != 0
        assert "Core.lean" in (r["stdout"] + r["stderr"])
