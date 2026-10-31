"""Lean theorem-coverage evaluation of the shared verified commons, at matched COMPILER CALLS.

Inputs (written by the prover harness / other owners; this module only reads and scores):
  statements  rows {"statement_id","family"[, "source_claim_id"]}; the frozen catalogue. `family` is the independence
              unit (the model), not the statement. Optional sha256 file: mismatch aborts.
  results     rows {"statement_id","arm","proved":bool,"axioms_clean":bool,"compiler_calls":int[,"cross_family_lemma_uses":int,
              "tokens":int]}, at most one per (arm, statement). Only proved AND axioms_clean counts as covered.
  ledger      optional rows {"arm","compiler_calls":int}: the authoritative per-arm total (failed calls included). If absent
              the total falls back to the sum over result rows, flagged as possibly undercounting calls on statements with no row.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from . import arms as ARMS
from . import stats as ST
from .desk import DeskError, _rows, decide
from .report import _seed, clean

LEAN_PREREG = Path(__file__).with_name("prereg_lean.json")


def load_statements(path, sha_path=None, excluded=()):
    digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    ok = None
    if sha_path:
        if digest not in {t.lower() for t in Path(sha_path).read_text().split()}:
            raise DeskError(f"statements file sha256 {digest} not found in {sha_path}: the catalogue was altered after freezing")
        ok = True
    out = {}
    for r in _rows(path):
        i = r.get("statement_id")
        if not isinstance(i, str) or i in out or not r.get("family"):
            raise DeskError(f"statement id/family missing or duplicated: {i!r}")
        if (r.get("source_claim_id")) in excluded:
            raise DeskError(f"statement {i} cites excluded source claim {r['source_claim_id']!r}")
        out[i] = {"family": r["family"]}
    return out, {"path": str(path), "sha256": digest, "sha256_verified_against_file": ok, "n_statements": len(out)}


def run_lean(statements_path, results_path, ledger_path=None, sha_path=None, out_dir=None, prereg_path=LEAN_PREREG):
    cfg = json.loads(Path(prereg_path).read_text())
    prereg_sha = hashlib.sha256(Path(prereg_path).read_bytes()).hexdigest()
    stm, stm_info = load_statements(statements_path, sha_path, set(cfg["excluded_source_claims"]))
    ids = sorted(stm)
    fam = np.array([stm[i]["family"] for i in ids])
    res: dict[str, dict] = {}
    for r in _rows(results_path):
        if r.get("statement_id") not in stm:
            raise DeskError(f"result for unknown statement {r.get('statement_id')!r}")
        if not r.get("arm"):
            raise DeskError("result row without arm")
        slot = res.setdefault(r["arm"], {})
        if r["statement_id"] in slot:
            raise DeskError(f"arm {r['arm']}: duplicate result for {r['statement_id']}")
        slot[r["statement_id"]] = r
    ledger = None
    if ledger_path:
        ledger = {}
        for r in _rows(ledger_path):
            ledger[r["arm"]] = ledger.get(r["arm"], 0) + int(r["compiler_calls"])
    arms = {}
    cover = {}
    for a, rows in sorted(res.items()):
        cov = np.array([bool(rows.get(i, {}).get("proved")) and rows.get(i, {}).get("axioms_clean") is True for i in ids])
        attempted = np.array([i in rows for i in ids])
        rejected = np.array([bool(rows.get(i, {}).get("proved")) and rows.get(i, {}).get("axioms_clean") is not True for i in ids])
        cover[a] = cov
        sum_calls = int(sum(int(r.get("compiler_calls", 0)) for r in rows.values()))
        calls = ledger[a] if ledger is not None and a in ledger else sum_calls
        cl = ST.cluster_ratio_ci(cov.astype(float), np.ones(len(ids)), fam, cfg["bootstrap"]["resamples"], _seed(cfg["bootstrap"]["seed"], a + "/cov"), cfg["bootstrap"]["ci"])
        uses = [int(rows[i].get("cross_family_lemma_uses", 0)) for i in ids if cov[list(ids).index(i)] and "cross_family_lemma_uses" in rows[i]]
        arms[a] = {
            "coverage": {**ST.rate(int(cov.sum()), len(ids)), "cluster_lo": cl["lo"], "cluster_hi": cl["hi"]},
            "n_attempted": int(attempted.sum()), "n_proved_but_axioms_not_clean_rejected": int(rejected.sum()),
            "compiler_calls": calls, "compiler_calls_source": "ledger" if ledger is not None and a in ledger else "sum of result rows (may undercount)",
            "compiler_calls_sum_of_rows": sum_calls,
            "calls_per_covered_statement": (calls / int(cov.sum())) if cov.sum() else None,
            "tokens_reported_not_matched": int(sum(int(r.get("tokens", 0)) for r in rows.values())),
            "cross_family_lemma_uses_among_covered": ({"n_covered_reporting": len(uses), "mean": float(np.mean(uses)) if uses else None,
                                                       "share_with_at_least_one": float(np.mean([u > 0 for u in uses])) if uses else None}
                                                      if uses else "not reported by the harness"),
            "by_family": {f: ST.rate(int(cov[fam == f].sum()), int((fam == f).sum())) for f in sorted(set(fam.tolist()))},
        }
    budgets = {a: {"compiler_calls": v["compiler_calls"]} for a, v in arms.items()}
    comps = {}
    for x, y in cfg["comparisons"]:
        k = f"{x}_vs_{y}"
        if x not in cover or y not in cover:
            comps[k] = {"status": "NOT_RUN_ARM_MISSING"}
            continue
        exempt = {a for a, v in cfg["arms"].items() if v.get("budget_exempt")}
        chk = None if ({x, y} & exempt) else ARMS.check_budgets(budgets, [x, y], cfg["budget_tolerance"], "compiler_calls")
        if chk is not None and not chk["ok"]:
            comps[k] = {"status": "REFUSED_BUDGET_MISMATCH", "budget_check": chk, "note": "No win/loss statement between arms whose compiler-call budgets differ by more than tolerance."}
            continue
        d = cover[x].astype(float) - cover[y].astype(float)
        cl = ST.cluster_ratio_ci(d, np.ones(len(ids)), fam, cfg["bootstrap"]["resamples"], _seed(cfg["bootstrap"]["seed"], k), cfg["bootstrap"]["ci"])
        comps[k] = {"status": "COMPARED_MATCHED_BUDGET" if chk is not None else "COMPARED_UNMATCHED_BASELINE_EXEMPT_ARM", "budget_check": chk, "x_minus_y_coverage": cl["estimate"], "cluster_lo": cl["lo"], "cluster_hi": cl["hi"],
                    "n_families": cl["n_families"], "verdict": decide(cl["lo"], cl["hi"], False, f"arm {x}", f"arm {y}", cl["n_families"], cfg["min_families_for_verdict"]),
                    "mcnemar": ST.mcnemar_exact(cover[x], cover[y])}
    l3 = [comps.get("L3_vs_L2", {}), comps.get("L3_vs_L1", {})]
    supported = all(c.get("status") == "COMPARED_MATCHED_BUDGET" and c["verdict"].startswith("arm L3 BETTER") for c in l3)
    reuse = arms.get("L3", {}).get("cross_family_lemma_uses_among_covered")
    if supported:
        if isinstance(reuse, dict) and reuse.get("share_with_at_least_one"):
            mech = f"L3 gain accompanied by direct cross-agent lemma reuse in {reuse['share_with_at_least_one']:.0%} of its covered final proofs (mean {reuse['mean']:.2f} uses): consistent with, not proof of, reuse as the mechanism."
        else:
            mech = "L3 beats L2 and L1 but the harness reports NO direct cross-agent lemma reuse in final proofs (or does not report it): the gain is NOT attributed to reuse."
    else:
        mech = "No sharing benefit established; reuse diagnostic is descriptive only."
    report = {"title": "Lean commons coverage at matched compiler calls", "statements": stm_info, "prereg": {"path": str(prereg_path), "sha256": prereg_sha, "config": cfg},
              "n_families": len(set(fam.tolist())), "arms": arms, "comparisons": comps, "commons_benefit_supported": bool(supported), "mechanism_note": mech,
              "limitations": [cfg["within_arm_dependence_note"], "Few model families make cluster intervals wide or untrustworthy; below the preregistered minimum no verdict is issued.",
                              "Coverage counts only kernel-accepted proofs with clean axioms; statement fidelity and law-mutant rejection are audited elsewhere and are not scored here.",
                              "Compiler calls are as recorded by the harness; unrecorded calls are not matched."]}
    if report["n_families"] < cfg["min_families_for_verdict"]:
        report["limitations"].insert(0, f"Only {report['n_families']} catalogue families (< {cfg['min_families_for_verdict']}): no comparison can receive a verdict.")
    lines = ["## Lean commons: coverage of the frozen catalogue at matched compiler calls", ""]
    for a, v in arms.items():
        c = v["coverage"]
        lines.append(f"- **{a}**: covered {c['k']}/{c['n']} = {c['rate']:.3f} (cluster 95% [{c['cluster_lo']:.3f}, {c['cluster_hi']:.3f}]); compiler calls {v['compiler_calls']} ({v['compiler_calls_source']}); rejected-axioms {v['n_proved_but_axioms_not_clean_rejected']}")
    for k, e in comps.items():
        if e["status"] == "COMPARED_MATCHED_BUDGET":
            lines.append(f"- {k}{'' if e['status'] == 'COMPARED_MATCHED_BUDGET' else ' (deterministic baseline; calls not matched)'}: coverage diff {e['x_minus_y_coverage']:+.3f} [{e['cluster_lo']:+.3f}, {e['cluster_hi']:+.3f}] -> {e['verdict']} (McNemar exact p={e['mcnemar']['p_two_sided_exact']:.4f}, item-level)")
        else:
            lines.append(f"- {k}: **{e['status']}** {e.get('note', '')}")
    lines += ["", ("Sharing benefit SUPPORTED: L3 beats both the sequential persistent-library agent (L1) and the private-library agents (L2). " + mech if supported else
                   "Sharing benefit NOT established by the preregistered rule (L3 must beat both L1 and L2): report as a null or partial result."),
              "", "Credit and non-claims: " + cfg["novelty_statement"]]
    report["slide_markdown"] = "\n".join(lines) + "\n"
    if out_dir:
        out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
        (out / "lean_report.json").write_text(json.dumps(clean(report), indent=1, allow_nan=False))
        (out / "lean_slide.md").write_text(report["slide_markdown"])
    return clean(report)
