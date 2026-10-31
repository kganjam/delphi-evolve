"""Evaluate whether a deterministic precondition check (the gate) stops agents from applying a law outside its scope.

Inputs (written by others):
  key      rows {"id","truth":"pattern"|"no_pattern","trap":bool[, "problem_family","evidence":"formal"|"simulated"]}; trap => truth no_pattern.
  answers  rows {"id","condition":"U"|"G","model_family","answer":"pattern"|"no_pattern"|"refuse"}; one per (id, condition, model_family).
  ledger   optional rows {"condition", tokens...} (see desk._ledger_tokens); reported, not a refusal gate (see prereg_gate.json).
Reports trap error, refusal and false-refusal rates per condition and per model family, trivial reference policies (always-refuse is
shown to have zero trap error and total false refusal), and the paired G-vs-U comparison with family-cluster intervals.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from . import stats as ST
from .desk import DeskError, _ledger_tokens, _rows, decide
from .report import _seed, clean

GATE_PREREG = Path(__file__).with_name("prereg_gate.json")
ANS = ("pattern", "no_pattern", "refuse")


def run_gate(key_path, answers_path, ledger_path=None, out_dir=None, prereg_path=GATE_PREREG):
    cfg = json.loads(Path(prereg_path).read_text())
    sha = hashlib.sha256(Path(prereg_path).read_bytes()).hexdigest()
    key = {}
    for r in _rows(key_path):
        i = r.get("id")
        if not isinstance(i, str) or i in key or r.get("truth") not in ("pattern", "no_pattern") or not isinstance(r.get("trap"), bool):
            raise DeskError(f"bad or duplicate key row {i!r}")
        if r["trap"] and r["truth"] != "no_pattern":
            raise DeskError(f"{i}: a scope trap must have truth no_pattern")
        key[i] = {"truth": r["truth"], "trap": r["trap"], "fam": r.get("problem_family") or i, "evidence": r.get("evidence", "unspecified")}
    ids = sorted(key)
    obs: dict[str, dict] = {"U": {}, "G": {}}
    for r in _rows(answers_path):
        if r.get("id") not in key:
            raise DeskError(f"answer for unknown id {r.get('id')!r}")
        if r.get("condition") not in obs or not r.get("model_family"):
            raise DeskError(f"answer row needs condition U|G and model_family: {r}")
        a = r.get("answer")
        k = (r["id"], r["model_family"])
        if k in obs[r["condition"]]:
            raise DeskError(f"duplicate answer for {k} in condition {r['condition']}")
        obs[r["condition"]][k] = a if a in ANS else ""   # invalid answer counts as unanswered
    fams = sorted({mf for c in obs.values() for (_, mf) in c})
    grid = [(i, mf) for i in ids for mf in fams]
    trap = np.array([key[i]["trap"] for i, _ in grid])
    cl = np.array([key[i]["fam"] for i, _ in grid])
    truth = np.array([key[i]["truth"] for i, _ in grid])
    mfv = np.array([mf for _, mf in grid])

    def arr(cond):
        return np.array([obs[cond].get(k, "") for k in grid])

    def vecs(a):
        nt = ~trap
        return {
            "trap_error_rate": ((trap & (a == "pattern")).astype(float), trap.astype(float)),
            "trap_refusal_rate": ((trap & (a == "refuse")).astype(float), trap.astype(float)),
            "nontrap_error_rate": ((nt & np.isin(a, ["pattern", "no_pattern"]) & (a != truth)).astype(float), nt.astype(float)),
            "nontrap_false_refusal_rate": ((nt & (a == "refuse")).astype(float), nt.astype(float)),
            "useful_correct_rate": ((a == truth).astype(float), np.ones(len(a))),
        }

    B, ci, seed = cfg["bootstrap"]["resamples"], cfg["bootstrap"]["ci"], cfg["bootstrap"]["seed"]
    rep = {"title": "Gate versus model judgement", "prereg": {"path": str(prereg_path), "sha256": sha, "config": cfg},
           "items": {"n_items": len(ids), "n_trap": int(sum(key[i]["trap"] for i in ids)), "trap_fraction": float(np.mean([key[i]["trap"] for i in ids])),
                     "n_model_families": len(fams), "model_families": fams, "n_problem_families": len(set(cl.tolist())),
                     "evidence_kinds": sorted({key[i]["evidence"] for i in ids})},
           "conditions": {}, "comparison": {}}
    A = {c: arr(c) for c in obs if obs[c]}
    for c, a in A.items():
        v = vecs(a)
        d = {"n_observations": len(a), "n_unanswered": int(np.sum(a == "")), "coverage_committed": float(np.mean(np.isin(a, ["pattern", "no_pattern"])))}
        for m, (num, den) in v.items():
            sel = den > 0
            q = ST.cluster_ratio_ci(num[sel], den[sel], cl[sel], B, _seed(seed, c + m), ci)
            d[m] = {"value": q["estimate"], "cluster_lo": q["lo"], "cluster_hi": q["hi"], **{k: x for k, x in ST.rate(int(num.sum()), int(den.sum())).items() if k in ("k", "n")}}
        d["by_model_family"] = {}
        for mf in fams:
            sel = mfv == mf
            d["by_model_family"][mf] = {m: ST.rate(int(num[sel].sum()), int(den[sel].sum())) for m, (num, den) in v.items() if m in ("trap_error_rate", "nontrap_false_refusal_rate")}
        rep["conditions"][c] = d
    rep["trivial_policies"] = {
        "always_refuse": {"trap_error_rate": 0.0, "nontrap_false_refusal_rate": 1.0, "useful_correct_rate": 0.0},
        "always_pattern (textbook inequality applied blindly)": {"trap_error_rate": 1.0 if trap.any() else None, "useful_correct_rate": float(np.mean(truth == "pattern"))}}
    if ledger_path:
        tot = {}
        for r in _rows(ledger_path):
            c = r.get("condition") or r.get("arm")
            tot[c] = tot.get(c, 0) + _ledger_tokens(r)
        rep["tokens_by_condition"] = tot
        if tot.get("G") and tot.get("U"):
            rep["tokens_by_condition"]["G_over_U"] = tot["G"] / tot["U"]
    g, u = cfg["comparison"]
    if g in A and u in A:
        vg, vu = vecs(A[g]), vecs(A[u])
        lower = {"trap_error_rate": True, "trap_refusal_rate": False, "nontrap_error_rate": True, "nontrap_false_refusal_rate": True, "useful_correct_rate": False}
        for m in vg:
            num = vg[m][0] - vu[m][0]
            den = vg[m][1]
            sel = den > 0
            q = ST.cluster_ratio_ci(num[sel], den[sel], cl[sel], B, _seed(seed, "cmp" + m), ci)
            rep["comparison"][m] = {"G_minus_U": q["estimate"], "cluster_lo": q["lo"], "cluster_hi": q["hi"], "n_problem_families": q["n_families"],
                                    "verdict": decide(q["lo"], q["hi"], lower[m], "G", "U", q["n_families"], cfg["min_families_for_verdict"])}
        c = rep["comparison"]
        sup = (c["trap_error_rate"]["verdict"] == "G BETTER than U" and c["nontrap_false_refusal_rate"]["verdict"] != "U BETTER than G"
               and c["nontrap_error_rate"]["verdict"] != "U BETTER than G")
        rep["gate_beats_judgement_supported"] = bool(sup)
    else:
        rep["gate_beats_judgement_supported"] = False
        rep["comparison"] = {"status": "NOT_RUN_condition_missing"}
    rep["limitations"] = [cfg["circularity_note"], cfg["trap_definition"],
                          "Few problem families give wide or undecidable intervals; below the preregistered minimum no verdict is issued.",
                          "Observations for different model families on the same item are paired, not independent; clustering is by problem family.",
                          "A gate answer of `refuse` is correct behaviour on a trap but is not a scientific answer; the useful_correct_rate row exists so that cannot be hidden."]
    lines = ["## Gate vs model judgement", f"{rep['items']['n_items']} items ({rep['items']['n_trap']} scope traps, {rep['items']['trap_fraction']:.0%}), {len(fams)} model families, {rep['items']['n_problem_families']} problem families.", ""]
    for c, d in rep["conditions"].items():
        t, f_, u_ = d["trap_error_rate"], d["nontrap_false_refusal_rate"], d["useful_correct_rate"]
        lines.append(f"- **{c}**: said `pattern` on {t['k']}/{t['n']} traps = {t['value']:.3f} [{t['cluster_lo']:.3f}, {t['cluster_hi']:.3f}]; refused {f_['k']}/{f_['n']} non-trap = {f_['value']:.3f}; useful-correct {u_['value']:.3f}")
    for m, e in rep["comparison"].items():
        if isinstance(e, dict) and "verdict" in e:
            lines.append(f"- {m}: G-U {e['G_minus_U']:+.3f} [{e['cluster_lo']:+.3f}, {e['cluster_hi']:+.3f}] -> {e['verdict']}")
    lines += ["", ("Gate beats model judgement on this item set: fewer trap errors without a detectable rise in false refusals or non-trap errors." if rep["gate_beats_judgement_supported"]
                   else "Gate beating model judgement is NOT established by the preregistered rule: report as a null or mixed result."),
              "Reference: always-refuse has trap error 0 and false refusal 1; a zero trap error alone is therefore not evidence.",
              "Circularity: " + cfg["circularity_note"], "Credit and non-claims: " + cfg["novelty_statement"]]
    rep["slide_markdown"] = "\n".join(lines) + "\n"
    if out_dir:
        o = Path(out_dir); o.mkdir(parents=True, exist_ok=True)
        (o / "gate_report.json").write_text(json.dumps(clean(rep), indent=1, allow_nan=False))
        (o / "gate_slide.md").write_text(rep["slide_markdown"])
    return clean(rep)
