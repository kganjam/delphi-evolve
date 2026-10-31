"""Scope Desk evaluation: does the DESK give the right verdict, and what does it cost to be right?

Inputs (written by others; this module only reads and scores; it builds no service and no market API):
  key       scopedesk key rows {"id","verdict","condition_ids","witness","expected_repairs"} (JSON list or JSONL),
            verdict in applies|out_of_scope|underdetermined, settled by exact arithmetic / Lean, never an LLM.
            Optionally verified against a sha256 file (KEY.sha256); a mismatch is an error, not a warning.
  instances rows with id, family, stratum (formal|simulated|descriptive) and hidden.benign (or those fields on key rows).
  answers   JSONL; each row is the frozen agent answer {"id","verdict","p":{applies,out_of_scope,underdetermined},
            "diagnosis":{"condition_ids":[...]},"repair":{...}} plus "arm", optional "agent_id","model_family",
            optional "role": "output" (default; the scored arm output, exactly one per arm per id) or "unit"
            (a single sampled agent inside the arm; used only for error-correlation / diversity appendix).
  ledger    JSONL token ledger with "arm" and either total_tokens or (input/output/tool token fields); see _ledger_tokens.
  repairs   optional JSONL {"id","arm","repair_ok": bool} produced by the oracle layer.

Headline numbers: false-alarm rate on applies items FIRST (a desk that cries out-of-scope everywhere is useless),
then false reassurance, accuracy, Brier, log score; arms compared only at matched total tokens.
Everything is reported against the KEY, so declaring a request out of scope to dodge it is penalised, not rewarded.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np

from . import arms as ARMS
from . import calibration as CAL
from . import diversity as DIV
from . import scoring as SC
from . import stats as ST
from .report import THEOREM_LIMIT, _seed, clean

DESK_PREREG = Path(__file__).with_name("prereg_desk.json")
V = ("applies", "out_of_scope", "underdetermined")


class DeskError(Exception):
    pass


# ----------------------------------------------------------------------------- loading
def _rows(path):
    text = Path(path).read_text(encoding="utf-8").strip()
    if not text:
        return []
    if text[0] == "[":
        return json.loads(text)
    if text[0] == "{" and "\n" not in text:
        obj = json.loads(text)
        for k in ("items", "key", "rows", "instances"):
            if isinstance(obj.get(k), list):
                return obj[k]
        return [obj]
    return [json.loads(l) for l in text.splitlines() if l.strip()]


def load_key(key_path, instances_path=None, sha_path=None, excluded=()):
    raw = Path(key_path).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    verified = None
    if sha_path:
        tokens = {t.lower() for t in Path(sha_path).read_text().split()}
        if digest not in tokens:
            raise DeskError(f"key file sha256 {digest} not found in {sha_path}; refusing to score against an altered key")
        verified = True
    meta = {}
    if instances_path:
        for r in _rows(instances_path):
            h = r.get("hidden") or {}
            meta[r["id"]] = {"family": r.get("family"), "stratum": r.get("stratum"),
                             "benign": r.get("benign", h.get("benign", (h.get("structured") or {}).get("benign")))}
    key = {}
    for r in _rows(key_path):
        i = r.get("id")
        if not isinstance(i, str) or i in key:
            raise DeskError(f"key id missing or duplicated: {i!r}")
        if r.get("verdict") not in V:
            raise DeskError(f"key {i}: verdict {r.get('verdict')!r} not in {V}")
        src = r.get("source_claim_id") or r.get("claim_id")
        if src in excluded:
            raise DeskError(f"key {i} cites excluded source claim {src!r}; it must not be in the scored set")
        m = dict(meta.get(i, {}))
        for f in ("family", "stratum", "benign"):
            if r.get(f) is not None:
                m[f] = r[f]
        if not m.get("family") or not m.get("stratum"):
            raise DeskError(f"key {i}: family/stratum unknown (provide instances file or fields on key rows)")
        key[i] = {"verdict": r["verdict"], "conds": sorted(r.get("condition_ids") or []), "family": m["family"],
                  "stratum": m["stratum"], "benign": bool(m.get("benign"))}
    return key, {"path": str(key_path), "sha256": digest, "sha256_verified_against_file": verified, "n_items": len(key)}


def parse_p(p, tol):
    if not isinstance(p, dict) or set(p) != set(V):
        return None
    try:
        v = [float(p[k]) for k in V]
    except (TypeError, ValueError):
        return None
    if any((not math.isfinite(x)) or x < 0 or x > 1 for x in v) or abs(sum(v) - 1.0) > tol:
        return None
    return v


def _ledger_tokens(r):
    if isinstance(r.get("total_tokens"), (int, float)):
        return int(r["total_tokens"])
    parts = [r.get(k) for k in ("tokens_in", "input_tokens", "tokens_out", "output_tokens", "tool_tokens")]
    nums = [x for x in parts if isinstance(x, (int, float))]
    if not nums:
        raise DeskError(f"ledger row has no recognised token field: keys={sorted(r)}")
    return int(sum(nums))


def desk_budgets(ledger_rows):
    out = {}
    for r in ledger_rows:
        if not r.get("arm"):
            raise DeskError("ledger row without arm")
        b = out.setdefault(r["arm"], {"total_tokens": 0, "n_ledger_rows": 0})
        b["total_tokens"] += _ledger_tokens(r)
        b["n_ledger_rows"] += 1
    return out


# ----------------------------------------------------------------------------- per-arm scoring
class ArmData:
    def __init__(self, arm, ids, key, answers, repairs, cfg):
        n = len(ids)
        self.arm, self.ids, self.n = arm, ids, n
        self.fam = np.array([key[i]["family"] for i in ids])
        self.stratum = np.array([key[i]["stratum"] for i in ids])
        self.benign = np.array([key[i]["benign"] for i in ids])
        self.key_v = np.array([key[i]["verdict"] for i in ids])
        self.verdict = np.array([answers[i]["verdict"] if i in answers and answers[i].get("verdict") in V else "" for i in ids])
        self.answered = self.verdict != ""
        self.correct = self.verdict == self.key_v
        P = np.full((n, 3), np.nan)
        self.consistent = np.ones(n, bool)
        for j, i in enumerate(ids):
            if i in answers:
                v = parse_p(answers[i].get("p"), cfg["prob_sum_tolerance"])
                if v is not None:
                    P[j] = v
                    if self.answered[j] and V[int(np.argmax(v))] != self.verdict[j]:
                        self.consistent[j] = False
        self.P = P
        self.valid_p = ~np.isnan(P[:, 0])
        yk = np.array([V.index(k) for k in self.key_v])
        onehot = np.eye(3)[yk]
        self.brier3 = np.where(self.valid_p, ((P - onehot) ** 2).sum(axis=1), np.nan)
        eps = cfg["log_eps"]
        py = np.clip(P[np.arange(n), yk], eps, 1 - eps)
        self.log3 = np.where(self.valid_p, -np.log(py), np.nan)
        self.event = (self.key_v == "applies").astype(float)
        self.p_applies = P[:, 0]
        self.diag_exact = np.zeros(n, bool)
        self.diag_overlap = np.zeros(n, bool)
        for j, i in enumerate(ids):
            if key[i]["verdict"] == "out_of_scope" and self.verdict[j] == "out_of_scope":
                got = sorted(((answers[i].get("diagnosis") or {}).get("condition_ids")) or [])
                self.diag_exact[j] = got == key[i]["conds"]
                self.diag_overlap[j] = bool(set(got) & set(key[i]["conds"]))
        self.repair_ok = np.array([bool(repairs.get((arm, i))) if repairs is not None else False for i in ids])
        self.repairs_scored = repairs is not None
        self.repair_attempted = np.array([bool((answers.get(i) or {}).get("repair")) for i in ids])
        self.repair_has_oracle_verdict = np.array([(repairs is not None and (arm, i) in repairs) for i in ids])

    # metric vectors: (numerator, denominator) per item for ratio estimators
    def vec(self, metric):
        k = self.key_v
        if metric == "accuracy":
            return self.correct.astype(float), np.ones(self.n)
        if metric == "false_alarm_rate":
            m = k == "applies"
            return (m & (self.verdict != "applies")).astype(float), m.astype(float)
        if metric == "false_reassurance_rate":
            m = k == "out_of_scope"
            return (m & (self.verdict == "applies")).astype(float), m.astype(float)
        if metric == "right_flag_rate":
            m = k == "out_of_scope"
            return (m & (self.verdict == "out_of_scope")).astype(float), m.astype(float)
        if metric == "brier3":
            return np.nan_to_num(self.brier3), self.valid_p.astype(float)
        if metric == "log_loss3":
            return np.nan_to_num(self.log3), self.valid_p.astype(float)
        raise KeyError(metric)


LOWER_BETTER = {"accuracy": False, "false_alarm_rate": True, "false_reassurance_rate": True, "right_flag_rate": False,
                "brier3": True, "log_loss3": True}
RATE_METRICS = ("accuracy", "false_alarm_rate", "false_reassurance_rate", "right_flag_rate")


def metric_ci(a: ArmData, metric, mask, cfg, label):
    num, den = a.vec(metric)
    num, den = num * mask, den * mask
    sel = den > 0
    cl = ST.cluster_ratio_ci(num[sel], den[sel], a.fam[sel], cfg["bootstrap"]["resamples"], _seed(cfg["bootstrap"]["seed"], label + metric), cfg["bootstrap"]["ci"])
    out = {"value": cl["estimate"], "cluster_lo": cl["lo"], "cluster_hi": cl["hi"], "n": int(den.sum()) if metric in RATE_METRICS else int(sel.sum()),
           "n_families": cl["n_families"]}
    if metric in RATE_METRICS:
        k = int(round(num.sum()))
        r = ST.rate(k, int(den.sum()))
        out.update({"k": k, "item_level_exact_lo": r["cp_lo"], "item_level_exact_hi": r["cp_hi"]})
    return out


def trivial_references(a: ArmData, mask):
    kv = a.key_v[mask]
    n = len(kv)
    if n == 0:
        return {}
    out = {}
    for pol in V:
        out[f"always_{pol}"] = {"accuracy": float(np.mean(kv == pol)),
                                "false_alarm_rate": (None if not np.any(kv == "applies") else float(pol != "applies")),
                                "false_reassurance_rate": (None if not np.any(kv == "out_of_scope") else float(pol == "applies"))}
    return out


def block(a: ArmData, mask, cfg, label):
    out = {"n_items": int(mask.sum()), "n_families": int(len(set(a.fam[mask].tolist()))),
           "coverage_answered": float(np.mean(a.answered[mask])) if mask.any() else None,
           "n_valid_p": int(np.sum(a.valid_p & mask)), "n_verdict_disagrees_with_argmax_p": int(np.sum(~a.consistent & mask & a.valid_p))}
    for m in ("accuracy", "false_alarm_rate", "false_reassurance_rate", "right_flag_rate", "brier3", "log_loss3"):
        out[m] = metric_ci(a, m, mask.astype(float), cfg, label)
    oos = mask & (a.key_v == "out_of_scope")
    got = oos & (a.verdict == "out_of_scope")
    out["diagnosis_exact"] = {**ST.rate(int(np.sum(a.diag_exact & mask)), int(got.sum())), "note": "given the item was correctly flagged out_of_scope"}
    out["diagnosis_overlap_any"] = ST.rate(int(np.sum(a.diag_overlap & mask)), int(got.sum()))
    if a.repairs_scored:
        out["repair_success"] = {**ST.rate(int(np.sum(a.repair_ok & oos)), int(oos.sum())),
                                 "n_repairs_with_oracle_verdict": int(np.sum(a.repair_has_oracle_verdict & oos)),
                                 "n_repairs_proposed": int(np.sum(a.repair_attempted & oos)),
                                 "note": "denominator = all KEY out_of_scope items; no proposal or no oracle verdict counts as not successful"}
    else:
        out["repair_success"] = {"status": "NOT_SCORED_no_oracle_repair_verdicts_supplied"}
    out["confusion_key_by_answer"] = {k: {v: int(np.sum(mask & (a.key_v == k) & (a.verdict == v))) for v in V + ("",)} for k in V}
    out["confusion_key_by_answer"]["_note"] = "'' = unanswered"
    out["trivial_policies"] = trivial_references(a, mask)
    # applies-vs-not as a binary forecast
    vm = mask & a.valid_p
    if vm.any():
        pa, ev = a.p_applies[vm], a.event[vm]
        out["binary_applies"] = {"brier": float(SC.brier(pa, ev).mean()), "log_loss": float(SC.log_loss(pa, ev).mean()),
                                 "auc_p_applies_ranks_applies_above_not": ST.auc(pa[ev == 1], pa[ev == 0]),
                                 "calibration": CAL.calibration_table(pa, ev, cfg["calibration_bins"])}
        rows = []
        for t in cfg["operating_thresholds_flag_if_p_applies_below"]:
            flag = pa < t
            na, nn = int(np.sum(ev == 1)), int(np.sum(ev == 0))
            rows.append({"flag_if_p_applies_below": t,
                         "false_alarm_rate": (float(np.sum(flag & (ev == 1)) / na) if na else None),
                         "flag_rate_on_not_applies": (float(np.sum(flag & (ev == 0)) / nn) if nn else None)})
        out["binary_applies"]["operating_curve"] = rows
    else:
        out["binary_applies"] = {"status": "no valid probability vectors"}
    return out


# ----------------------------------------------------------------------------- comparisons
def decide(lo, hi, lower_better, nx, ny, n_families=None, min_families=None):
    if min_families is not None and n_families is not None and n_families < min_families:
        return f"INSUFFICIENT FAMILIES ({n_families} < {min_families}): cluster bootstrap is not trustworthy, no verdict between {nx} and {ny}"
    if lo is None or hi is None or (isinstance(lo, float) and math.isnan(lo)):
        return "UNDEFINED (no data)"
    x_better = hi < 0 if lower_better else lo > 0
    y_better = lo > 0 if lower_better else hi < 0
    return f"{nx} BETTER than {ny}" if x_better else (f"{ny} BETTER than {nx}" if y_better else f"NO DETECTABLE DIFFERENCE between {nx} and {ny}")


def compare_arms(x: ArmData, y: ArmData, mask, cfg, label):
    nx_, ny_ = f"arm {x.arm}", f"arm {y.arm}"
    out = {}
    for m in cfg["headline_metric_order"]:
        nx, dx = x.vec(m)
        ny, dy = y.vec(m)
        both = (dx > 0) & (dy > 0) & mask
        if m in RATE_METRICS:
            # paired difference of rates over the same denominator items
            num = (nx - ny)[both]
            den = dx[both]
        else:
            num = (nx - ny)[both]
            den = np.ones(int(both.sum()))
        cl = ST.cluster_ratio_ci(num, den, x.fam[both], cfg["bootstrap"]["resamples"], _seed(cfg["bootstrap"]["seed"], label + m), cfg["bootstrap"]["ci"])
        e = {"x_minus_y": cl["estimate"], "cluster_lo": cl["lo"], "cluster_hi": cl["hi"], "n_items": int(both.sum()), "n_families": cl["n_families"],
             "lower_is_better": LOWER_BETTER[m], "verdict": decide(cl["lo"], cl["hi"], LOWER_BETTER[m], nx_, ny_, cl["n_families"], cfg["min_families_for_verdict"])}
        if m in ("accuracy", "false_alarm_rate"):
            if m == "accuracy":
                xr, yr = x.correct[both], y.correct[both]
            else:
                xr, yr = (x.verdict[both] == "applies"), (y.verdict[both] == "applies")  # "right" = cleared an applies item
            e["mcnemar"] = ST.mcnemar_exact(xr, yr)
        out[m] = e
    acc, fa = out["accuracy"]["verdict"], out["false_alarm_rate"]["verdict"]
    out["metrics_agree_on_accuracy_and_false_alarm"] = acc == fa
    return out


# ----------------------------------------------------------------------------- unit-level appendix
def unit_appendix(unit_rows, ids, key, cfg):
    by_arm = {}
    for r in unit_rows:
        by_arm.setdefault(r["arm"], {}).setdefault(r.get("agent_id") or "?", {})[r["id"]] = r
    ev = np.array([1.0 if key[i]["verdict"] == "applies" else 0.0 for i in ids])
    out = {}
    for arm, units in by_arm.items():
        P, names, fams = [], [], {}
        for u, rows in sorted(units.items()):
            if all(i in rows and parse_p(rows[i].get("p"), cfg["prob_sum_tolerance"]) for i in ids):
                P.append([parse_p(rows[i]["p"], cfg["prob_sum_tolerance"])[0] for i in ids])
                names.append(u)
                fams[u] = rows[ids[0]].get("model_family") or "unknown"
        if len(P) < 2:
            out[arm] = {"status": f"{len(P)} complete unit(s); need >=2"}
            continue
        P = np.array(P)
        dec = DIV.decompose(P, ev)
        dec.pop("per_claim")
        fam_set = sorted(set(fams.values()))
        res = {"n_units": len(names), "decomposition_on_p_applies": dec,
               "note": "descriptive algebra, NOT a headline: " + THEOREM_LIMIT}
        if len(fam_set) >= 2:
            F = {f: P[[k for k, nme in enumerate(names) if fams[nme] == f]].mean(axis=0) for f in fam_set}
            res["family_error_correlation"] = CAL.error_correlation(F, ev)
            res["same_vs_cross_family"] = CAL.within_vs_cross_family(dict(zip(names, P)), fams, ev)
        else:
            res["family_error_correlation"] = {"unavailable": f"{len(fam_set)} model family among units"}
        out[arm] = res
    return out


# ----------------------------------------------------------------------------- driver
def run_desk(key_path, answers_path, instances_path=None, ledger_path=None, repairs_path=None, sha_path=None,
             out_dir=None, prereg_path=DESK_PREREG):
    cfg = json.loads(Path(prereg_path).read_text())
    prereg_sha = hashlib.sha256(Path(prereg_path).read_bytes()).hexdigest()
    key, key_info = load_key(key_path, instances_path, sha_path, set(cfg.get("excluded_source_claims", [])))
    ids = sorted(key)
    ident = DIV.self_test()
    rows = _rows(answers_path)
    outputs, units = {}, []
    for r in rows:
        if r.get("id") not in key:
            raise DeskError(f"answer for unknown instance id {r.get('id')!r}")
        if not r.get("arm"):
            raise DeskError("answer row without arm")
        if r.get("role", "output") == "unit":
            units.append(r)
            continue
        slot = outputs.setdefault(r["arm"], {})
        if r["id"] in slot:
            raise DeskError(f"arm {r['arm']}: duplicate output answer for {r['id']}")
        slot[r["id"]] = r
    derived = {}
    for arm in {u["arm"] for u in units} - set(outputs):
        slot = {}
        for i in ids:
            us = [u for u in units if u["arm"] == arm and u["id"] == i and parse_p(u.get("p"), cfg["prob_sum_tolerance"])]
            if us:
                mp = np.mean([parse_p(u["p"], cfg["prob_sum_tolerance"]) for u in us], axis=0)
                slot[i] = {"id": i, "verdict": V[int(np.argmax(mp))], "p": dict(zip(V, mp.tolist()))}
        outputs[arm] = slot
        derived[arm] = "derived by mean-probability pooling of unit rows; no runner output supplied"
    repairs = None
    if repairs_path:
        repairs = {(r["arm"], r["id"]): r.get("repair_ok") for r in _rows(repairs_path)}
    budgets = desk_budgets(_rows(ledger_path)) if ledger_path else None

    data = {arm: ArmData(arm, ids, key, outputs[arm], repairs, cfg) for arm in sorted(outputs)}
    any_arm = next(iter(data.values()), None)
    if any_arm is None:
        raise DeskError("no arm outputs")
    strat = any_arm.stratum
    head_mask = np.isin(strat, cfg["headline_strata"])
    report = {
        "title": "Scope Desk evaluation: is the desk right, and what does it cost?",
        "prereg": {"path": str(prereg_path), "sha256": prereg_sha, "config": cfg},
        "key": key_info, "identity_self_test": ident, "output_derivations": derived,
        "items": {"n_key_items": len(ids), "headline_strata": cfg["headline_strata"], "n_headline_items": int(head_mask.sum()),
                  "by_stratum": {s: int(np.sum(strat == s)) for s in sorted(set(strat.tolist()))},
                  "key_verdict_counts_headline": {v: int(np.sum(any_arm.key_v[head_mask] == v)) for v in V},
                  "n_families_headline": int(len(set(any_arm.fam[head_mask].tolist()))),
                  "n_benign_controls_headline": int(np.sum(any_arm.benign & head_mask))},
        "arms": {}, "budgets": budgets, "comparisons": {},
        "limitations": [
            "Family-cluster bootstrap with few families gives wide intervals; item-level exact intervals ignore clustering and are shown only as a reference.",
            "Truth labels are only as good as the oracles and the key audit; this module scores against the key and cannot detect a wrong key.",
            "Unanswered items count as wrong (accuracy) and as false alarms (on applies items); abstaining is never rewarded.",
            "Token totals are exactly what the runner ledger records; unrecorded tool or retry spend is not matched.",
            "The descriptive stratum is reported separately and never mixed into the headline accuracy.",
            "Diversity/error-correlation output is descriptive algebra over unit answers, not a test of collective superiority.",
        ],
    }
    if report["items"]["n_families_headline"] < cfg["min_families_warning"]:
        report["limitations"].insert(0, f"Only {report['items']['n_families_headline']} independent families in the headline set (< {cfg['min_families_warning']}); cluster intervals are very wide and may not cover. {cfg['independence_note']}")
    report["evidence_labels"] = cfg["evidence_labels"]
    for arm, a in data.items():
        report["arms"][arm] = {"headline": block(a, head_mask, cfg, f"{arm}/head"),
                               "by_stratum": {s: block(a, strat == s, cfg, f"{arm}/{s}") for s in sorted(set(strat.tolist()))},
                               "by_family": {f: {"n": int(np.sum(a.fam == f)), "accuracy": ST.rate(int(np.sum(a.correct & (a.fam == f))), int(np.sum(a.fam == f))),
                                                 "false_alarm_rate": ST.rate(int(np.sum((a.fam == f) & (a.key_v == "applies") & (a.verdict != "applies"))), int(np.sum((a.fam == f) & (a.key_v == "applies"))))}
                                             for f in sorted(set(a.fam.tolist()))},
                               "budget_tokens": (budgets or {}).get(arm, {}).get("total_tokens")}
    exempt = {k for k, v in cfg["arms"].items() if v.get("budget_exempt")}
    for x, y in cfg["comparisons"]:
        key_name = f"{x}_vs_{y}"
        if x not in data or y not in data:
            report["comparisons"][key_name] = {"status": "NOT_RUN_ARM_MISSING", "missing": [a for a in (x, y) if a not in data]}
            continue
        status, chk = "COMPARED_MATCHED_BUDGET", None
        agent_arms = [a for a in (x, y) if a not in exempt]
        if len(agent_arms) == 2:
            if budgets is None or any(a not in budgets for a in agent_arms):
                report["comparisons"][key_name] = {"status": "REFUSED_NO_LEDGER", "note": "cannot verify matched token budgets for " + ", ".join(agent_arms)}
                continue
            chk = ARMS.check_budgets({a: budgets[a] for a in agent_arms}, agent_arms, cfg["budget_tolerance"])
            if not chk["ok"]:
                report["comparisons"][key_name] = {"status": "REFUSED_BUDGET_MISMATCH", "budget_check": chk,
                                                   "note": "No win/loss statement is made between arms whose total token budgets differ by more than tolerance."}
                continue
        else:
            status = "COMPARED_UNMATCHED_BASELINE_EXEMPT_ARM"
        res = compare_arms(data[x], data[y], head_mask, cfg, f"{x}~{y}/{key_name}")
        res.update({"status": status, "budget_check": chk})
        report["comparisons"][key_name] = res
    # cross-arm error overlap: do two arms err on the same items?
    names = sorted(data)
    wrong = {a: ~data[a].correct & head_mask for a in names}
    overlap = {}
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            ca, cb = data[a].correct[head_mask].astype(float), data[b].correct[head_mask].astype(float)
            phi = None if ca.std() == 0 or cb.std() == 0 else float(np.corrcoef(ca, cb)[0, 1])
            union = int(np.sum(wrong[a] | wrong[b]))
            overlap[f"{a}|{b}"] = {"phi_of_correctness": phi, "n_wrong_a": int(wrong[a].sum()), "n_wrong_b": int(wrong[b].sum()),
                                   "n_wrong_both": int(np.sum(wrong[a] & wrong[b])), "jaccard_of_wrong_sets": (float(np.sum(wrong[a] & wrong[b]) / union) if union else None)}
    report["arm_error_overlap_headline_items"] = overlap
    report["unit_appendix_diversity_and_family_error_correlation"] = unit_appendix(units, ids, key, cfg) if units else {"status": "no unit rows supplied"}
    report["headline"] = desk_headline(report, cfg)
    md = desk_markdown(report)
    if out_dir:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "desk_report.json").write_text(json.dumps(clean(report), indent=1, allow_nan=False))
        (out / "desk_report.md").write_text(md)
        (out / "slide.md").write_text(report["headline"]["slide_markdown"])
        panels = {f"arm {a}": (data[a].p_applies[head_mask & data[a].valid_p], data[a].event[head_mask & data[a].valid_p]) for a in names if np.any(head_mask & data[a].valid_p)}
        if panels:
            CAL.reliability_figure(panels, out / "reliability_p_applies.png", "Reliability of P(applies), headline strata", cfg["calibration_bins"])
    return clean(report), md


def _f(x, nd=3):
    return "n/a" if x is None else f"{x:.{nd}f}"


def _ci(m):
    return f"{_f(m['value'])} [{_f(m['cluster_lo'])}, {_f(m['cluster_hi'])}]"


def desk_headline(r, cfg):
    L = ["## Scope Desk: false alarms first", ""]
    it = r["items"]
    L.append(f"{it['n_headline_items']} headline items in {it['n_families_headline']} families ({it['key_verdict_counts_headline']}); intervals are family-cluster bootstrap 95%.")
    L.append("")
    L.append(f"Evidence columns are never merged. Pooled row = {cfg['headline_pooled_label']}.")
    for arm, a in r["arms"].items():
        for s_name in cfg["headline_strata"]:
            b = a["by_stratum"].get(s_name)
            if not b or not b["n_items"]:
                continue
            fa = b["false_alarm_rate"]
            L.append(f"- **{arm} / {s_name}** [{cfg['evidence_labels'].get(s_name, s_name)}], n={b['n_items']}: false-alarm {_ci(fa)} ({fa.get('k')}/{fa['n']} applies items); false reassurance {_ci(b['false_reassurance_rate'])}; accuracy {_ci(b['accuracy'])}")
        h = a["headline"]
        fa = h["false_alarm_rate"]
        L.append(f"- **{arm} / pooled** (mixed evidence): false-alarm {_ci(fa)} ({fa.get('k')}/{fa['n']}); false reassurance {_ci(h['false_reassurance_rate'])}; accuracy {_ci(h['accuracy'])}; Brier3 {_f(h['brier3']['value'])}; log-score loss {_f(h['log_loss3']['value'])}"
                 + (f"; tokens {a['budget_tokens']}" if a.get("budget_tokens") is not None else ""))
    if "TXT" in r["arms"]:
        t = r["arms"]["TXT"]["headline"]
        L.append(f"- **How often does the textbook criterion mispredict?** error rate {_f(1 - t['accuracy']['value'])} (accuracy {_ci(t['accuracy'])}); it reassures on {_ci(t['false_reassurance_rate'])} of genuinely out-of-scope items. Per-stratum rows above; interval is family-clustered.")
    first = next(iter(r["arms"].values()))["headline"]["trivial_policies"] if r["arms"] else {}
    if first:
        L.append(f"- Reference: a desk that answers out_of_scope everywhere has false-alarm rate {first.get('always_out_of_scope', {}).get('false_alarm_rate')} and accuracy {_f(first.get('always_out_of_scope', {}).get('accuracy'))}; always applies has accuracy {_f(first.get('always_applies', {}).get('accuracy'))}.")
    L += ["", "## Collective test (matched total tokens)", "Each line shows accuracy, false-alarm AND false-reassurance: either error rate alone is gameable (answer 'applies' everywhere or 'out_of_scope' everywhere)."]
    notrun = []
    for k, e in r["comparisons"].items():
        if e["status"] == "NOT_RUN_ARM_MISSING":
            notrun.append(k)
            continue
        if not e["status"].startswith("COMPARED"):
            L.append(f"- {k}: **{e['status']}** {e.get('note', '')}")
            continue
        tag = "" if e["status"] == "COMPARED_MATCHED_BUDGET" else " (exempt deterministic arm; tokens not matched)"
        parts = []
        for m, nm in (("accuracy", "accuracy"), ("false_alarm_rate", "false-alarm"), ("false_reassurance_rate", "false-reassurance")):
            c = e[m]
            parts.append(f"{nm} diff {_f(c['x_minus_y'])} [{_f(c['cluster_lo'])}, {_f(c['cluster_hi'])}] -> {c['verdict']}")
        L.append(f"- {k}{tag}: " + "; ".join(parts))
    if notrun:
        L.append(f"- Not run (arm absent from the answers): {', '.join(notrun)}")
    p = "_vs_".join(cfg["primary_comparison"])
    pe = r["comparisons"].get(p, {})
    if pe.get("status") == "COMPARED_MATCHED_BUDGET":
        x0, y0 = cfg["primary_comparison"]
        better = lambda m: pe[m]["verdict"].startswith(f"arm {x0} BETTER")
        worse = lambda m: pe[m]["verdict"].startswith(f"arm {y0} BETTER")
        sup = better("accuracy") and better("false_alarm_rate") and not worse("false_reassurance_rate")
        L += ["", ("Primary comparison SUPPORTS a commons benefit: better accuracy AND fewer false alarms, with no detectable rise in false reassurance." if sup else
                   "Primary comparison does NOT establish a commons benefit (preregistered rule: better accuracy and fewer false alarms and no worse false reassurance): this is a reportable null or mixed result.")]
    else:
        L += ["", f"Primary comparison {p} not available: {pe.get('status', 'NOT_RUN')}. No collective claim is made."]
    L += ["", "Credit and non-claims: " + cfg["novelty_statement"]]
    return {"slide_markdown": "\n".join(L) + "\n"}


def desk_markdown(r):
    L = ["# Scope Desk evaluation", "", r["headline"]["slide_markdown"],
         f"- prereg sha256 `{r['prereg']['sha256'][:16]}…`; key sha256 `{r['key']['sha256'][:16]}…` (verified against file: {r['key']['sha256_verified_against_file']})", ""]
    for arm, a in r["arms"].items():
        h = a["headline"]
        L += [f"## Arm {arm}", f"coverage {_f(h['coverage_answered'])}; valid probability vectors {h['n_valid_p']}/{h['n_items']}; verdict≠argmax p on {h['n_verdict_disagrees_with_argmax_p']}",
              "", "confusion (key rows × answer columns, '' = unanswered): " + json.dumps(h["confusion_key_by_answer"]),
              f"diagnosis exact among correctly flagged: {h['diagnosis_exact']['k']}/{h['diagnosis_exact']['n']}; repair: {h['repair_success']}",
              "", "| stratum | n | accuracy | false-alarm | false reassurance |", "|---|---|---|---|---|"]
        for s, b in a["by_stratum"].items():
            L.append(f"| {s} | {b['n_items']} | {_ci(b['accuracy'])} | {_ci(b['false_alarm_rate'])} | {_ci(b['false_reassurance_rate'])} |")
        ba = h["binary_applies"]
        if "auc_p_applies_ranks_applies_above_not" in ba:
            L.append(f"\nP(applies): binary Brier {_f(ba['brier'])}, AUC {_f(ba['auc_p_applies_ranks_applies_above_not'])}, ECE {_f(ba['calibration']['ece'])}. Operating curve (flag if p_applies < t): " +
                     "; ".join(f"t={o['flag_if_p_applies_below']}: FA {_f(o['false_alarm_rate'])}, flags {_f(o['flag_rate_on_not_applies'])} of not-applies" for o in ba["operating_curve"]))
        L.append("")
    L += ["## Error overlap between arms (headline items)"] + [f"- {k}: {v}" for k, v in r["arm_error_overlap_headline_items"].items()]
    L += ["", "## Appendix: diversity decomposition and family error correlation (descriptive, not a headline)", json.dumps(clean(r["unit_appendix_diversity_and_family_error_correlation"]))[:4000]]
    L += ["", "## Limitations"] + [f"- {x}" for x in r["limitations"]]
    return "\n".join(L) + "\n"
