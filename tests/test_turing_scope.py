"""Tests for turing_scope. Run bounded:
systemd-run --user --scope -p TasksMax=128 -p MemoryMax=4G -p MemorySwapMax=0 -p RuntimeMaxSec=600 \
  env OMP_NUM_THREADS=2 python -m pytest tests/test_turing_scope.py -q
"""
import copy
import importlib
import json
import random
import shutil
import subprocess
import sys
from fractions import Fraction as F
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from turing_scope import adapter  # noqa: E402
from turing_scope.adapter import analyze  # noqa: E402
from turing_scope.crosscheck import crosscheck  # noqa: E402
from turing_scope.source import BUNDLED_DIR, SourceStore, load_pins, parse_record  # noqa: E402

EX = ROOT / "turing_scope" / "examples"
ART = ROOT / "artifacts" / "turing_scope"


def req(r="1", **over):
    q = json.loads((EX / "short_L_pi.json").read_text())
    q["domain"]["length_over_pi"] = r
    for k, v in over.items():
        q[k] = v
    return q


def snap(tmp_path, edit=None):
    d = tmp_path / "snap"
    shutil.copytree(BUNDLED_DIR, d)
    if edit:
        edit(d)
    return SourceStore.from_dir(d)


# ---------------- independent reference (no adapter code) ----------------
J = [[F(1), F(-2)], [F(2), F(-3)]]
Du, Dv = F(1), F(10)


def ref_det(q):  # det(J - qD) expanded from the matrix, not from the dispersion polynomial
    return (J[0][0] - q * Du) * (J[1][1] - q * Dv) - J[0][1] * J[1][0]


def ref_tr(q):
    return (J[0][0] - q * Du) + (J[1][1] - q * Dv)


# ---------------- exact band and witnesses ----------------
def test_dispersion_polynomial_is_5q_minus_1_times_2q_minus_1():
    for q in [F(0), F(1, 4), F(1, 3), F(1), F(7, 3), F(-2, 5)]:
        assert ref_det(q) == (5 * q - 1) * (2 * q - 1) == 10 * q * q - 7 * q + 1
        assert ref_tr(q) == -2 - 11 * q


def test_exact_band_endpoints_and_open_interval():
    res = analyze(req("1"))
    b = res["band"]
    assert (b["q_lower"], b["q_upper"], b["exact"]) == ("1/5", "1/2", True)
    assert b["discriminant_S2_minus_4DuDv_detJ"] == "9" and b["S"] == "7"
    assert ref_det(F(1, 5)) == 0 == ref_det(F(1, 2))                     # endpoints are roots, so excluded
    assert ref_det(F(1, 5) + F(1, 1000)) < 0 and ref_det(F(1, 2) - F(1, 1000)) < 0
    assert ref_det(F(1, 5) - F(1, 1000)) > 0 and ref_det(F(1, 2) + F(1, 1000)) > 0
    assert res["derived"]["det_J"] == "1" and res["derived"]["trace_J"] == "-2"


def test_short_domain_pi_is_stable_every_mode():
    res = analyze(req("1"))
    assert res["verdict"] == "stable" and res["unstable_modes"] == []
    assert res["tail"]["first_tail_mode_n"] == 1
    assert res["band"]["band_exists"] is True      # continuum band is non-empty yet nothing admissible
    # independent reference over many modes
    for n in range(0, 300):
        q = F(n * n)
        assert ref_tr(q) < 0 and ref_det(q) > 0
    assert any("contains no admissible q_n" in x for x in res["reasons"])


def test_longer_domain_2pi_witness():
    res = analyze(req("2"))
    assert res["verdict"] == "linearly_unstable" and res["unstable_modes"] == [1]
    m1 = res["modes"][1]
    assert (m1["n"], m1["q"], m1["trace"], m1["determinant"]) == (1, "1/4", "-19/4", "-1/8")
    assert m1["eigenvalues_real"] and m1["max_eigenvalue_approx"] > 0
    assert m1["wavelength_over_pi"] == "4"          # 2L/n = 4 pi
    assert res["modes"][0]["class"] == "stable" and res["modes"][2]["class"] == "stable"
    assert res["tail"]["first_tail_mode_n"] == 2
    # matches the previously saved research artifact (exact strings)
    saved = json.loads((ROOT / "artifacts/research/turing-domain-counterexample.json").read_text())
    for case, r in zip(saved["cases"], ("1", "2")):
        got = analyze(req(r))["modes"]
        for row in case["checked_modes"]:
            g = got[row["n"]]
            assert (g["q"], g["trace"], g["determinant"]) == (row["q"], row["trace"], row["determinant"])
            assert (g["class"] == "unstable") == row["linearly_unstable"]


def test_changing_length_changes_answer_nonmonotonically():
    v = {r: analyze(req(r))["verdict"] for r in ["1/2", "1", "3/2", "2", "5/2", "3"]}
    assert v == {"1/2": "stable", "1": "stable", "3/2": "linearly_unstable", "2": "linearly_unstable",
                 "5/2": "stable", "3": "linearly_unstable"}
    assert analyze(req("3"))["unstable_modes"] == [2]      # q=4/9 in (1/5,1/2)


def test_infinite_mode_tail_rule_against_bruteforce_random_models():
    """The tail rule is claimed for ALL n>=n_cut. Verify the claimed cutoff on random stable-kinetics models by
    exact brute force far past the cutoff (finite check; the all-n statement is the analytic rule + Lean)."""
    rng = random.Random(7)
    done = 0
    while done < 150:
        a, b, c, d = (rng.randint(-6, 6) for _ in range(4))
        Du_, Dv_ = rng.randint(1, 8), rng.randint(1, 40)
        if not (a + d < 0 and a * d - b * c > 0):
            continue
        r = F(rng.randint(1, 30), rng.randint(1, 6))
        q = req(str(r))
        q["system"]["jacobian"] = [[str(a), str(b)], [str(c), str(d)]]
        q["system"]["diffusivities"] = [str(Du_), str(Dv_)]
        res = analyze(q)
        assert res["verdict"] in ("stable", "linearly_unstable", "refused")
        if res["verdict"] == "refused":
            assert res["refusal"]["code"] == "marginal_non_hyperbolic"
            done += 1
            continue
        n_cut = res["tail"]["first_tail_mode_n"]
        unstable_ref = []
        for n in range(0, n_cut + 400):
            qq = F(n * n) / (r * r)
            tr = (a - qq * Du_) + (d - qq * Dv_)
            det = (a - qq * Du_) * (d - qq * Dv_) - b * c
            if det < 0 or tr > 0:
                unstable_ref.append(n)
            if n >= n_cut:
                assert det > 0 and tr < 0, (a, b, c, d, Du_, Dv_, r, n)
        assert unstable_ref == res["unstable_modes"]
        done += 1


def test_cutoff_is_minimal_not_just_sufficient():
    # n_cut-1 must violate S*p^2 <= DuDv*n^2*s^2 (so the exhaustive part is never skipped needlessly)
    for r in ["1", "2", "3", "7/2"]:
        res = analyze(req(r))
        n_cut, rr = res["tail"]["first_tail_mode_n"], F(r)
        S, P = F(res["derived"]["S"]), F(res["derived"]["DuDv"])
        assert S * rr * rr <= P * n_cut ** 2
        if n_cut > 1:
            assert S * rr * rr > P * (n_cut - 1) ** 2


def test_resource_cap_refuses_instead_of_truncating():
    res = analyze(req("10000000"))
    assert res["verdict"] == "refused" and res["refusal"]["code"] == "resource_limit"


# ---------------- numeric cross-check independent of formulas ----------------
def test_numpy_eigenvalues_agree_with_exact_classification():
    np = pytest.importorskip("numpy")
    for r in ("1", "2", "3", "5/2"):
        res = analyze(req(r))
        rr = float(F(r))
        Jm = np.array([[1.0, -2.0], [2.0, -3.0]])
        for n in range(0, 400):
            q = n * n / (rr * rr)
            ev = np.linalg.eigvals(Jm - q * np.diag([1.0, 10.0]))
            assert (ev.real.max() > 1e-12) == (n in res["unstable_modes"]), (r, n)
        cc = crosscheck(res, n_sweep=300)
        assert cc["agrees"] and cc["mismatches"] == []
        assert "tail rule" in cc["limitation"]          # finite-cutoff limitation stated


def test_matrix_exponential_growth_at_witness_mode():
    sp = pytest.importorskip("scipy.linalg")
    np = pytest.importorskip("numpy")
    A = np.array([[1.0, -2.0], [2.0, -3.0]]) - 0.25 * np.diag([1.0, 10.0])
    growth = np.linalg.norm(sp.expm(A * 400.0), 2)
    assert growth > 1e3                                     # exp(0.0262*400) ~ 3.6e4 : genuine growth
    B = np.array([[1.0, -2.0], [2.0, -3.0]]) - 1.0 * np.diag([1.0, 10.0])
    assert np.linalg.norm(sp.expm(B * 400.0), 2) < 1e-6


# ---------------- source identity ----------------
def test_unchanged_bundled_source_computes_and_is_pinned():
    res = analyze(req("2"))
    assert [c["ok"] for c in res["source_checks"]] == [True, True]
    pins = load_pins()
    for c in res["source_checks"]:
        assert c["content_sha256"] == c["pinned_content_sha256"] == pins[c["claim"]]["content_sha256"]
        assert c["source"] == "local" and c["nanopubs"][0].endswith("unsigned/%s.trig" % c["claim"])
    assert not any("w3id.org/np/" in n for c in res["source_checks"] for n in c["nanopubs"])   # no invented network ID


def test_missing_source_refuses(tmp_path):
    store = snap(tmp_path, lambda d: (d / "turing-ddi.local.mcp.json").unlink())
    res = analyze(req("2"), store)
    assert res["verdict"] == "refused" and res["refusal"]["code"] == "source_missing"


def test_withdrawn_source_refuses(tmp_path):
    def w(d):
        m = json.loads((d / "manifest.json").read_text()); m["claims"]["turing-ddi"]["status"] = "withdrawn"
        (d / "manifest.json").write_text(json.dumps(m))
    res = analyze(req("2"), snap(tmp_path, w))
    assert res["verdict"] == "refused" and res["refusal"]["code"] == "source_withdrawn"


def _edit_ddi(d, key, fn):
    p = d / "turing-ddi.local.mcp.json"
    raw = json.loads(p.read_text())
    inner = json.loads(raw["result"]["content"][0]["text"])
    inner["fields"][key] = fn(inner["fields"][key])
    raw["result"]["content"][0]["text"] = json.dumps(inner)
    p.write_text(json.dumps(raw))


@pytest.mark.parametrize("key", ["delphi:context", "skos:notation", "dct:description", "rdfs:label"])
def test_changed_pinned_field_refuses_and_names_field(tmp_path, key):
    store = snap(tmp_path, lambda d: _edit_ddi(d, key, lambda v: v + " (edited)"))
    res = analyze(req("2"), store)
    assert res["verdict"] == "refused" and res["refusal"]["code"] == "claim_changed"
    assert res["source_checks"][0]["changed_fields"] == [key]


def test_changed_assumption_text_refused_even_if_someone_repins(tmp_path):
    # a re-pinned (reviewer-approved) record whose context lost the required assumptions is still refused
    from turing_scope.source import make_pins
    d = tmp_path / "snap"
    shutil.copytree(BUNDLED_DIR, d)
    _edit_ddi(d, "delphi:context", lambda v: "Assumptions: anything goes.")
    pins = make_pins(SourceStore.from_dir(d))
    assert pins["turing-ddi"]["content_sha256"] != load_pins()["turing-ddi"]["content_sha256"]
    res = analyze(req("2"), SourceStore.from_dir(d), pins)
    assert res["verdict"] == "refused" and res["refusal"]["code"] == "assumption_text_missing"


def test_source_with_wrong_iri_or_garbage_refuses(tmp_path):
    def swap(d):
        (d / "turing-ddi.local.mcp.json").write_bytes((d / "turing-wavelength.local.mcp.json").read_bytes())
    res = analyze(req("2"), snap(tmp_path, swap))
    assert res["refusal"]["code"] == "iri_mismatch"
    res = analyze(req("2"), snap(tmp_path.parent / (tmp_path.name + "x"), lambda d: (d / "turing-ddi.local.mcp.json").write_text("not json")))
    assert res["refusal"]["code"] == "source_malformed"


def test_wavelength_source_withdrawn_keeps_stability_verdict_but_refuses_wavelength(tmp_path):
    def w(d):
        m = json.loads((d / "manifest.json").read_text()); m["claims"]["turing-wavelength"]["status"] = "withdrawn"
        (d / "manifest.json").write_text(json.dumps(m))
    res = analyze(req("2"), snap(tmp_path, w))
    assert res["verdict"] == "linearly_unstable"
    assert res["wavelength"]["status"] == "refused" and res["wavelength"]["code"] == "source_withdrawn"


def test_name_only_is_not_enough_other_source_identity_checked():
    # same claim name, but pins for a different content hash -> refused
    pins = copy.deepcopy(load_pins())
    pins["turing-ddi"]["content_sha256"] = "0" * 64
    res = analyze(req("2"), pins=pins)
    assert res["refusal"]["code"] == "claim_changed"


def test_explicit_local_snapshot_file_and_unwrapped_form(tmp_path):
    raw = (BUNDLED_DIR / "turing-ddi.local.mcp.json").read_bytes()
    store = SourceStore.from_files({"turing-ddi": BUNDLED_DIR / "turing-ddi.local.mcp.json"})
    assert analyze(req("2"), store)["verdict"] == "linearly_unstable"
    inner = json.loads(json.loads(raw)["result"]["content"][0]["text"])
    p = tmp_path / "inner.json"
    p.write_text(json.dumps(inner))
    res = analyze(req("2"), SourceStore.from_files({"turing-ddi": p}))
    assert res["verdict"] == "linearly_unstable"               # same content hash, different raw bytes
    assert res["source_checks"][0]["response_sha256"] != res["source_checks"][0]["pinned_response_sha256"]


# ---------------- declarations and scope ----------------
@pytest.mark.parametrize("bnd", ["periodic_ring", "dirichlet", "robin", None, "neumann"])
def test_wrong_or_missing_boundary_refused(bnd):
    q = req("2")
    if bnd is None:
        del q["domain"]["boundary"]
    else:
        q["domain"]["boundary"] = bnd
    res = analyze(q)
    assert res["verdict"] == "refused" and res["refusal"]["code"] == "unsupported_boundary"


@pytest.mark.parametrize("mut,code", [
    (lambda q: q["domain"].__setitem__("dimension", 2), "unsupported_domain"),
    (lambda q: q["assumptions"].__setitem__("fixed_domain_no_growth", False), "assumption_not_declared"),
    (lambda q: q.pop("assumptions"), "assumption_not_declared"),
    (lambda q: q["system"].__setitem__("fixed_point", {"declared": False}), "fixed_point_not_declared"),
    (lambda q: q["domain"].__setitem__("length_over_pi", 2.0), "invalid_input"),
    (lambda q: q["domain"].__setitem__("length_over_pi", "0"), "invalid_input"),
    (lambda q: q["system"].__setitem__("diffusivities", ["1", "-10"]), "invalid_input"),
    (lambda q: q["system"].__setitem__("jacobian", [["1", "2", "3"], ["2", "3"]]), "unsupported_system"),
    (lambda q: q["system"].__setitem__("jacobian", [["1", "2"], ["2", "3"]]), "claim_precondition_failed"),
])
def test_scope_refusals(mut, code):
    q = req("2")
    mut(q)
    res = analyze(q)
    assert res["verdict"] == "refused" and res["refusal"]["code"] == code, res.get("refusal")


def test_source_law_mutations_change_acceptance():
    base = {r: analyze(req(r))["verdict"] for r in ("1", "2")}
    assert base == {"1": "stable", "2": "linearly_unstable"}
    eq = req("2"); eq["system"]["diffusivities"] = ["1", "1"]                  # diffusion contrast removed
    r = analyze(eq)
    assert r["verdict"] == "stable" and r["band"]["band_exists"] is False
    cc = req("2"); cc["system"]["jacobian"][1][1] = "-2"                        # reaction law changed
    r = analyze(cc)
    assert r["verdict"] == "stable" and r["band"]["band_exists"] is False
    dv30 = req("1"); dv30["system"]["diffusivities"] = ["1", "30"]
    assert analyze(dv30)["verdict"] == "stable"
    dv30["domain"]["length_over_pi"] = "2"
    assert analyze(dv30)["verdict"] == "linearly_unstable"


# ---------------- wavelength gate ----------------
def test_wavelength_claim_not_licensed_on_either_domain_and_needs_declared_thresholds():
    for r in ("1", "2"):
        wl = analyze(req(r))["wavelength"]
        assert wl["status"] == "not_licensed"
        assert wl["conditions"][0]["passed"] is True and wl["conditions"][1]["passed"] is False   # near onset yes, domain large no
        assert wl["conditions"][1]["value_approx"] < 1
    q = req("2"); q["wavelength"] = {}
    assert analyze(q)["wavelength"]["status"] == "refused"
    q = req("2"); del q["wavelength"]
    assert analyze(q)["wavelength"]["status"] == "not_requested"
    # exact check: r=40, m=1: r^4 detJ/(DuDv) = 256000 >= (4 m^2)^2 = 16, and still near onset -> licensed
    q = req("40"); q["wavelength"]["min_domain_over_wavelength"] = "1"
    assert analyze(q)["wavelength"]["status"] == "licensed"


# ---------------- evidence typing / honesty ----------------
def test_results_are_typed_model_derived_never_observed():
    for r in ("1", "2"):
        res = analyze(req(r))
        assert res["evidence_type"] == "model-derived" and res["observed"] is None
        assert res["epistemic_labels"]["observed"].startswith("none")
        assert any("nonlinear" in x for x in res["not_established"])
        assert any("Neumann" in x for x in res["assumptions"]["added_by_adapter"])
        txt = json.dumps(res).lower()
        assert "verified biology" not in txt


# ---------------- CLI ----------------
def run_cli(*args):
    return subprocess.run([sys.executable, "-m", "turing_scope", *args], cwd=ROOT, capture_output=True, text=True, timeout=120)


def test_cli_offline_default_and_exit_codes(tmp_path):
    p = run_cli("check", "turing_scope/examples/long_L_2pi.json", "--crosscheck")
    assert p.returncode == 0, p.stderr
    out = json.loads(p.stdout)
    assert out["verdict"] == "linearly_unstable" and out["numeric_crosscheck"]["agrees"]
    q = req("2"); q["domain"]["boundary"] = "dirichlet"
    f = tmp_path / "r.json"; f.write_text(json.dumps(q))
    p = run_cli("check", str(f))
    assert p.returncode == 2 and json.loads(p.stdout)["verdict"] == "refused"
    p = run_cli("check", "turing_scope/examples/long_L_2pi.json", "--source",
                f"turing-ddi={BUNDLED_DIR / 'turing-ddi.local.mcp.json'}")
    assert p.returncode == 0 and json.loads(p.stdout)["wavelength"]["status"] == "refused"   # wavelength record not supplied
    assert run_cli("sources").returncode == 0


# ---------------- artifacts, claim_runtime hash compatibility, Lean receipt ----------------
def test_recorded_results_match_a_fresh_run():
    rec = json.loads((ART / "results.json").read_text())
    for key, r in (("short_domain", "1"), ("long_domain", "2")):
        fresh = analyze(req(r))
        fresh.pop("request_id"); old = dict(rec[key]); old.pop("request_id")
        assert fresh == old
    data_js = (ROOT / "turing_scope/site/data.js").read_text()
    assert data_js.startswith("// Recorded") and '"linearly_unstable"' in data_js
    assert json.loads(data_js.split("window.TURING_DATA = ", 1)[1].rstrip().rstrip(";"))["long"]["unstable_modes"] == [1]


def test_hash_convention_matches_claim_runtime_when_available():
    try:
        cr = importlib.import_module("claim_runtime.common")
    except Exception:
        pytest.skip("claim_runtime not in this branch (it lives on work/claim-reuse / work/release)")
    for cid in ("turing-ddi", "turing-wavelength"):
        raw = (BUNDLED_DIR / f"{cid}.local.mcp.json").read_bytes()
        assert cr.parse_mcp_response(raw).content_sha256() == parse_record(raw).content_sha256()


def test_lean_sources_have_no_forbidden_tokens_and_receipt_matches_files():
    import re
    from turing_scope.source import sha_file
    lean = ROOT / "turing_scope" / "lean"
    files = list((lean / "TuringScope").glob("*.lean")) + [lean / "TuringScope.lean"]
    for f in files:
        body = re.sub(r"/-.*?-/", "", f.read_text(), flags=re.S)
        assert not re.search(r"\b(sorry|admit|native_decide)\b", body), f
        assert "Mathlib" not in body
    rec = json.loads((ART / "lean_receipt.json").read_text())
    assert rec["ok"] and rec["build"]["exit"] == 0 and rec["forbidden_tokens_in_source"] == []
    for rel, h in rec["sources"].items():
        assert sha_file(ROOT / rel) == h, f"{rel} changed after the recorded Lean compile"
    assert all(m["as_expected"] for m in rec["mutants"])
    assert any(m["exit"] == 0 for m in rec["mutants"]) and sum(m["exit"] != 0 for m in rec["mutants"]) == 3
    assert all(m["proved_false_by_decide"] for m in rec["mutants"] if m["exit"] != 0)


@pytest.mark.skipif(not shutil.which("lake"), reason="lake not installed")
def test_lean_project_compiles_and_mutants_fail():
    import os
    if not os.environ.get("TURING_SCOPE_RUN_LEAN"):
        pytest.skip("set TURING_SCOPE_RUN_LEAN=1 to rebuild Lean (recorded receipt is checked above)")
    from turing_scope.lean_check import run
    assert run()["ok"]
