"""Gate-vs-judgement evaluation. A literal hand-worked fixture plus test-only simulated fixtures for the verdict logic."""
import json

import numpy as np
import pytest

from market import desk as D
from market import gate as G


def write(tmp, name, rows):
    p = tmp / name
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return p


def small(tmp):
    key = [{"id": "t1", "truth": "no_pattern", "trap": True}, {"id": "t2", "truth": "no_pattern", "trap": True},
           {"id": "n1", "truth": "pattern", "trap": False}, {"id": "n2", "truth": "no_pattern", "trap": False}]
    U = {"t1": ("pattern", "pattern"), "t2": ("pattern", "no_pattern"), "n1": ("pattern", "pattern"), "n2": ("pattern", "refuse")}
    Gc = {"t1": ("refuse", "refuse"), "t2": ("refuse", "refuse"), "n1": ("pattern", "pattern"), "n2": ("no_pattern", "no_pattern")}
    ans = [{"id": i, "condition": c, "model_family": mf, "answer": a} for c, d in (("U", U), ("G", Gc)) for i, pair in d.items() for mf, a in zip(("m1", "m2"), pair)]
    return write(tmp, "k.jsonl", key), write(tmp, "a.jsonl", ans)


def test_hand_computed_rates(tmp_path):
    k, a = small(tmp_path)
    r = G.run_gate(k, a)
    u, g = r["conditions"]["U"], r["conditions"]["G"]
    assert (u["trap_error_rate"]["k"], u["trap_error_rate"]["n"]) == (3, 4) and u["trap_error_rate"]["value"] == pytest.approx(0.75)
    assert u["nontrap_error_rate"]["value"] == pytest.approx(1 / 4) and u["nontrap_false_refusal_rate"]["value"] == pytest.approx(1 / 4)
    assert u["useful_correct_rate"]["value"] == pytest.approx(3 / 8) and u["trap_refusal_rate"]["value"] == 0.0
    assert g["trap_error_rate"]["value"] == 0.0 and g["trap_refusal_rate"]["value"] == 1.0
    assert g["nontrap_false_refusal_rate"]["value"] == 0.0 and g["useful_correct_rate"]["value"] == pytest.approx(0.5)
    assert u["by_model_family"]["m1"]["trap_error_rate"]["k"] == 2 and u["by_model_family"]["m2"]["trap_error_rate"]["k"] == 1
    assert r["items"]["n_trap"] == 2 and r["items"]["trap_fraction"] == 0.5
    # only 4 problem families here: no verdict may be issued, so support cannot be claimed
    assert r["comparison"]["trap_error_rate"]["verdict"].startswith("INSUFFICIENT FAMILIES") and r["gate_beats_judgement_supported"] is False


def sim(tmp, g_rule, seed=2, n_trap=8, n_non=8, fams=("m1", "m2", "m3")):
    rng = np.random.default_rng(seed)
    key, ans = [], []
    for j in range(n_trap + n_non):
        trap = j < n_trap
        truth = "no_pattern" if (trap or j % 2) else "pattern"
        key.append({"id": f"q{j}", "truth": truth, "trap": trap, "problem_family": f"pf{j}"})
        for mf in fams:
            # unguarded judgement: textbook-style `pattern` on traps 80% of the time; 90% right on others
            u = ("pattern" if rng.uniform() < 0.8 else "no_pattern") if trap else (truth if rng.uniform() < 0.9 else ("pattern" if truth == "no_pattern" else "no_pattern"))
            ans.append({"id": f"q{j}", "condition": "U", "model_family": mf, "answer": u})
            ans.append({"id": f"q{j}", "condition": "G", "model_family": mf, "answer": g_rule(trap, truth, u)})
    return write(tmp, "k.jsonl", key), write(tmp, "a.jsonl", ans)


def test_gate_that_refuses_traps_and_answers_the_rest_is_supported(tmp_path):
    k, a = sim(tmp_path, lambda trap, truth, u: "refuse" if trap else truth)
    r = G.run_gate(k, a, out_dir=tmp_path / "o")
    assert r["conditions"]["G"]["trap_error_rate"]["value"] == 0.0 and r["conditions"]["U"]["trap_error_rate"]["value"] > 0.5
    assert r["comparison"]["trap_error_rate"]["verdict"] == "G BETTER than U"
    assert r["gate_beats_judgement_supported"] is True and "Gate beats model judgement" in r["slide_markdown"]
    assert (tmp_path / "o" / "gate_report.json").exists()


def test_a_gate_that_refuses_everything_has_zero_trap_error_and_is_not_supported(tmp_path):
    k, a = sim(tmp_path, lambda trap, truth, u: "refuse")
    r = G.run_gate(k, a)
    assert r["conditions"]["G"]["trap_error_rate"]["value"] == 0.0
    assert r["comparison"]["nontrap_false_refusal_rate"]["verdict"] == "U BETTER than G"
    assert r["gate_beats_judgement_supported"] is False and "NOT established" in r["slide_markdown"]


def test_a_gate_identical_to_judgement_is_a_null(tmp_path):
    k, a = sim(tmp_path, lambda trap, truth, u: u)
    r = G.run_gate(k, a)
    assert r["comparison"]["trap_error_rate"]["verdict"].startswith("NO DETECTABLE DIFFERENCE") and r["gate_beats_judgement_supported"] is False


def test_a_gate_that_commits_wrong_answers_on_non_traps_is_not_supported(tmp_path):
    k, a = sim(tmp_path, lambda trap, truth, u: "refuse" if trap else ("pattern" if truth == "no_pattern" else "no_pattern"))
    r = G.run_gate(k, a)
    assert r["comparison"]["nontrap_error_rate"]["verdict"] == "U BETTER than G" and r["gate_beats_judgement_supported"] is False


def test_unanswered_stay_in_denominator_and_inputs_fail_closed(tmp_path):
    k, a = small(tmp_path)
    rows = [json.loads(l) for l in a.read_text().splitlines() if not (json.loads(l)["condition"] == "U" and json.loads(l)["id"] == "t1" and json.loads(l)["model_family"] == "m1")]
    a.write_text("\n".join(json.dumps(r) for r in rows))
    r = G.run_gate(k, a)
    u = r["conditions"]["U"]
    assert u["n_unanswered"] == 1 and (u["trap_error_rate"]["k"], u["trap_error_rate"]["n"]) == (2, 4)   # missing answer is not a trap error but still counts in n
    rows.append(dict(rows[0]))
    a.write_text("\n".join(json.dumps(r) for r in rows))
    with pytest.raises(D.DeskError, match="duplicate"):
        G.run_gate(k, a)
    bad = write(tmp_path, "bk.jsonl", [{"id": "x", "truth": "pattern", "trap": True}])
    with pytest.raises(D.DeskError, match="scope trap must have truth"):
        G.run_gate(bad, a)


def test_token_ratio_is_reported_not_gated(tmp_path):
    k, a = small(tmp_path)
    l = write(tmp_path, "l.jsonl", [{"condition": "U", "total_tokens": 1000}, {"condition": "G", "total_tokens": 600}])
    r = G.run_gate(k, a, l)
    assert r["tokens_by_condition"]["G_over_U"] == pytest.approx(0.6) and "comparison" in r
