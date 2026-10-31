"""Assemble the full measurement report from a store. Everything printed is computed from recorded forecasts and
recorded oracle resolutions; there is no default data. Nulls are first-class: verdict strings say 'does NOT beat'
whenever the preregistered rule says so.
"""
from __future__ import annotations

import json
import math
import zlib
from pathlib import Path

import numpy as np

from . import aggregate as AG
from . import arms as ARMS
from . import calibration as CAL
from . import diversity as DIV
from . import scoring as SC
from . import store as ST

PREREG_PATH = Path(__file__).with_name("prereg.json")
THEOREM_LIMIT = ("The diversity prediction theorem guarantees only that the crowd's squared error is at most the MEAN "
                 "individual's squared error. It says nothing about beating the BEST individual; that is measured below "
                 "and may be negative.")


def _seed(base: int, label: str) -> int:
    return (int(base) * 1_000_003 + zlib.crc32(label.encode())) % (2**32)


def clean(o):
    """JSON-safe: numpy -> python, non-finite -> None."""
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, np.ndarray):
        return clean(o.tolist())
    if isinstance(o, (np.floating, float)):
        return float(o) if math.isfinite(float(o)) else None
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def boot_ci(d, B, seed, ci=0.95):
    d = np.asarray(d, float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(d), (B, len(d)))
    means = d[idx].mean(axis=1)
    a = (1 - ci) / 2
    lo, hi = np.quantile(means, [a, 1 - a])
    return {"mean": float(d.mean()), "lo": float(lo), "hi": float(hi), "n_claims": int(len(d))}


def verdict(ci: dict, name_x: str, name_y: str) -> str:
    if ci["hi"] < 0:
        return f"{name_x} BETTER than {name_y}"
    if ci["lo"] > 0:
        return f"{name_y} BETTER than {name_x}"
    return f"NO DETECTABLE DIFFERENCE between {name_x} and {name_y} (95% CI includes 0)"


def _loss_matrix(metric, P, o):
    return SC.brier(P, o) if metric == "brier" else SC.log_loss(P, o)


def _cv_best_loss(L, folds=10):
    """Per-claim loss of the unit chosen on the training folds, scored on the held-out fold."""
    n, m = L.shape
    out = np.empty(m)
    idx = np.arange(m)
    chosen = []
    for k in range(folds):
        te = idx % folds == k
        best = int(np.argmin(L[:, ~te].mean(axis=1)))
        out[te] = L[best, te]
        chosen.append(best)
    return out, chosen


def vs_best_individual(agg_losses: dict, L, cfg, label):
    """Compare every aggregate with (i) the ex-post best unit (conservative toward the individual) and
    (ii) a cross-validated best unit. Difference = aggregate - individual, so NEGATIVE means the aggregate is better."""
    B = cfg["bootstrap"]["resamples"]; ci = cfg["bootstrap"]["ci"]; base = cfg["bootstrap"]["seed"]
    n, m = L.shape
    best_i = int(np.argmin(L.mean(axis=1)))
    cv_loss, _ = _cv_best_loss(L, 10)
    rng = np.random.default_rng(_seed(base, label + "/vsbest"))
    a = (1 - ci) / 2
    res = {name: {"expost": [], "cv": []} for name in agg_losses}
    for start in range(0, B, 200):
        c = min(200, B - start)
        idx = rng.integers(0, m, (c, m))
        best = L[:, idx].mean(axis=2).min(axis=0)  # (c,) reselected best in each resample
        cvm = cv_loss[idx].mean(axis=1)
        for name, l in agg_losses.items():
            lm = l[idx].mean(axis=1)
            res[name]["expost"].append(lm - best)
            res[name]["cv"].append(lm - cvm)
    out = {"best_unit_index": best_i, "best_unit_mean_loss": float(L[best_i].mean()),
           "cv_best_individual_mean_loss": float(cv_loss.mean()),
           "unit_loss_min_median_max": [float(x) for x in (L.mean(1).min(), np.median(L.mean(1)), L.mean(1).max())]}
    for name, l in agg_losses.items():
        r = {}
        for kind, base_loss in (("expost", float(L[best_i].mean())), ("cv", float(cv_loss.mean()))):
            s = np.concatenate(res[name][kind])
            lo, hi = np.quantile(s, [a, 1 - a])
            d = {"aggregate_minus_individual": float(l.mean() - base_loss), "lo": float(lo), "hi": float(hi)}
            d["verdict"] = verdict(d, f"aggregate[{name}]", "best individual" + (" (ex post)" if kind == "expost" else " (cross-validated)"))
            r[kind] = d
        out[name] = r
    return out


def analyze_arm(arm, spec, keys, meta, P, o, cfg, label):
    eps = SC.LOG_EPS
    n, m = P.shape
    units = []
    for i, k in enumerate(keys):
        units.append({"unit": f"{k[0]}#{k[1]}", "guild": meta[k]["guild"], "model_family": meta[k]["model_family"],
                      "brier": float(SC.brier(P[i], o).mean()), "log_loss": float(SC.log_loss(P[i], o).mean()),
                      "n_clipped_for_log": SC.n_clipped(P[i])})

    def group(field):
        vals = sorted({meta[k][field] for k in keys})
        rows = []
        for v in vals:
            sel = [i for i, k in enumerate(keys) if meta[k][field] == v]
            mp = P[sel].mean(axis=0)
            rows.append({field: v, "n_units": len(sel),
                         "mean_individual_brier": float(np.mean([units[i]["brier"] for i in sel])),
                         "mean_individual_log_loss": float(np.mean([units[i]["log_loss"] for i in sel])),
                         "group_mean_forecast_brier": float(SC.brier(mp, o).mean()),
                         "group_mean_forecast_log_loss": float(SC.log_loss(mp, o).mean())})
        return rows

    aggs, ameta = AG.all_aggregates(P, o, cfg["aggregators"])
    agg_rows, agg_brier_vec, agg_log_vec = [], {}, {}
    mean_ind_brier = float(np.mean([u["brier"] for u in units]))
    for name, f in aggs.items():
        agg_brier_vec[name] = SC.brier(f, o)
        agg_log_vec[name] = SC.log_loss(f, o)
        agg_rows.append({"aggregator": name, "brier": float(agg_brier_vec[name].mean()), "log_loss": float(agg_log_vec[name].mean()),
                         "n_clipped_for_log": SC.n_clipped(f),
                         "gain_vs_mean_individual_brier": float(mean_ind_brier - agg_brier_vec[name].mean()),
                         "uses_outcomes_out_of_fold": name == "recalibrated_cv"})
    dec = DIV.decompose(P, o)
    per_claim = dec.pop("per_claim")
    Lb, Ll = _loss_matrix("brier", P, o), _loss_matrix("log_loss", P, o)
    bests = {"brier": vs_best_individual(agg_brier_vec, Lb, cfg, label + "/brier"),
             "log_loss": vs_best_individual(agg_log_vec, Ll, cfg, label + "/log")}

    out_vec, out_id = ARMS.primary_output(arm, spec, keys, P, aggs)
    result = {
        "n_units": n, "n_claims": m, "units": units,
        "by_guild": group("guild"), "by_model_family": group("model_family"),
        "aggregators": agg_rows, "aggregator_meta": ameta,
        "diversity_decomposition_mean_aggregator": dec,
        "vs_best_individual": bests,
        "primary_output": {"spec": spec, "id": out_id if isinstance(out_id, str) else f"{out_id[0]}#{out_id[1]}",
                           "brier": float(SC.brier(out_vec, o).mean()), "log_loss": float(SC.log_loss(out_vec, o).mean())},
        "calibration_primary_output": CAL.calibration_table(out_vec, o, cfg["calibration_bins"]),
        "calibration_mean_aggregate": CAL.calibration_table(aggs["mean"], o, cfg["calibration_bins"]),
        "calibration_units_pooled": CAL.calibration_table(P.reshape(-1), np.tile(o, n), cfg["calibration_bins"]),
    }
    fams = sorted({meta[k]["model_family"] for k in keys})
    if len(fams) >= 2:
        F = {f: P[[i for i, k in enumerate(keys) if meta[k]["model_family"] == f]].mean(axis=0) for f in fams}
        result["family_error_correlation"] = CAL.error_correlation(F, o)
        result["unit_error_correlation_same_vs_cross_family"] = CAL.within_vs_cross_family(
            {f"{k[0]}#{k[1]}": P[i] for i, k in enumerate(keys)},
            {f"{k[0]}#{k[1]}": meta[k]["model_family"] for i, k in enumerate(keys)}, o)
    else:
        result["family_error_correlation"] = {"unavailable": f"only {len(fams)} model family in this arm"}
    return result, out_vec, aggs


def _fmt(x, nd=4):
    return "n/a" if x is None else f"{x:.{nd}f}"


def run_report(store_dir, resolutions_path=None, out_dir=None, prereg_path=PREREG_PATH, require_matched_budgets=True):
    store_dir = Path(store_dir)
    cfg = json.loads(Path(prereg_path).read_text())
    prereg_sha = ST.sha256(Path(prereg_path).read_text())
    if abs(cfg["log_eps"] - SC.LOG_EPS) > 0:
        raise ST.StoreError("prereg log_eps differs from scoring.LOG_EPS")
    identity_selftest = DIV.self_test()

    res_store = ST.ResolutionStore(resolutions_path or store_dir / "resolutions.jsonl")
    fs = ST.ForecastStore(store_dir, res_store)
    integrity = fs.verify()
    claims = ST.load_claims(store_dir)
    forecasts = fs.forecasts()
    overhead = fs.overhead()
    resolutions = res_store.load()

    late = [r["seq"] for r in forecasts if r["claim_id"] in resolutions and r["timestamp"] >= resolutions[r["claim_id"]]["revealed_at"]]
    if late:
        raise ST.LateForecast(f"{len(late)} forecasts were submitted at/after their claim's resolution reveal (seq {late[:10]}); scoring refused")

    resolved_ids = sorted(c for c in resolutions if c in {x["claim_id"] for x in claims["claims"]})
    tier_of = {c["claim_id"]: c["tier"] for c in claims["claims"]}
    unresolved = sorted(set(tier_of) - set(resolved_ids))
    o = np.array([resolutions[c]["outcome"] for c in resolved_ids], float)
    forecasts = [r for r in forecasts if r["claim_id"] in set(resolved_ids)]

    report = {
        "title": "Collective capability measurement (forecast market)",
        "theorem_limit": THEOREM_LIMIT,
        "prereg": {"path": str(prereg_path), "sha256": prereg_sha, "config": cfg},
        "integrity": integrity,
        "identity_self_test": identity_selftest,
        "claims": {"n_frozen": claims["n_claims"], "n_resolved_scored": len(resolved_ids), "n_unresolved_excluded": len(unresolved),
                   "by_tier_scored": {t: sum(1 for c in resolved_ids if tier_of[c] == t) for t in sorted(set(tier_of.values()))},
                   "base_rate_of_yes": float(o.mean()) if len(o) else None},
        "reference_scores": SC.constant_reference(o) if len(o) else None,
        "arms": {}, "limitations": [
            "Bootstrap resamples claims as exchangeable; claims within a tier/family may be correlated, so intervals can be too narrow.",
            "Agents with incomplete coverage of the scored claims are dropped from analysis and listed; dropping could bias results.",
            "The store is a tamper-evident honest-process ledger, not protection against an adversary with file access.",
            "Token budgets count only tokens recorded in forecast and overhead entries; unrecorded spend is not matched.",
            "Ex-post best individual is selected on the same claims it is scored on and is therefore optimistic for the individual (conservative against the crowd); the cross-validated figure is the fairer comparison of the two.",
        ],
    }
    if len(resolved_ids) == 0:
        report["status"] = "NO_RESOLVED_CLAIMS"
        return clean(report), {}, ""

    prim: dict[str, np.ndarray] = {}
    arm_aggs: dict[str, dict] = {}
    for arm, spec in cfg["arms"].items():
        keys, meta, P, dropped = ARMS.arm_matrix(forecasts, arm, resolved_ids)
        if len(keys) == 0:
            report["arms"][arm] = {"status": "NO_COMPLETE_UNITS", "dropped_incomplete_units": dropped}
            continue
        a, vec, aggs = analyze_arm(arm, spec, keys, meta, P, o, cfg, f"arm{arm}")
        a["dropped_incomplete_units"] = dropped
        a["status"] = "OK"
        if arm == "A" and len({k[0] for k in keys}) > 1:
            a["warning"] = "arm A contains more than one agent id; it is not a single sequential agent"
        report["arms"][arm] = a
        prim[arm] = vec
        arm_aggs[arm] = aggs

    budgets = ARMS.arm_budgets(forecasts, overhead)
    report["budgets"] = budgets
    report["comparisons"] = {}
    B, ci, base = cfg["bootstrap"]["resamples"], cfg["bootstrap"]["ci"], cfg["bootstrap"]["seed"]
    for x, y in cfg["comparisons"]:
        key = f"{x}_vs_{y}"
        if x not in prim or y not in prim:
            report["comparisons"][key] = {"status": "REFUSED_ARM_MISSING"}
            continue
        chk = ARMS.check_budgets(budgets, [x, y], cfg["budget_tolerance"])
        if require_matched_budgets and not chk["ok"]:
            report["comparisons"][key] = {"status": "REFUSED_BUDGET_MISMATCH", "budget_check": chk,
                                          "note": "Arms are not comparable at matched token budget; no win/loss statement is made."}
            continue
        entry = {"status": "COMPARED", "budget_check": chk}
        for metric in ("brier", "log_loss"):
            lx = _loss_matrix(metric, prim[x][None, :], o)[0]
            ly = _loss_matrix(metric, prim[y][None, :], o)[0]
            d = lx - ly
            c = boot_ci(d, B, _seed(base, f"{key}/{metric}"), ci)
            c["verdict"] = verdict(c, f"arm {x}", f"arm {y}")
            c[f"loss_{x}"], c[f"loss_{y}"] = float(lx.mean()), float(ly.mean())
            entry[metric] = c
        entry["metrics_agree"] = entry["brier"]["verdict"] == entry["log_loss"]["verdict"]
        report["comparisons"][key] = entry

    # sensitivity table, all aggregators x arms (anti-cherry-picking); descriptive only
    report["all_arms_all_aggregators_brier"] = {arm: {r["aggregator"]: r["brier"] for r in report["arms"][arm]["aggregators"]}
                                                for arm in report["arms"] if report["arms"][arm].get("status") == "OK"}
    report["headline"] = headline(report, cfg)

    per_claim = [{"claim_id": c, "tier": tier_of[c], "outcome": int(o[i]), **{f"arm{a}_primary": float(v[i]) for a, v in prim.items()},
                  **{f"arm{a}_mean": float(arm_aggs[a]["mean"][i]) for a in arm_aggs}} for i, c in enumerate(resolved_ids)]
    md = to_markdown(report)
    if out_dir:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "report.json").write_text(json.dumps(clean(report), indent=1, allow_nan=False))
        (out_dir / "per_claim.json").write_text(json.dumps(clean(per_claim), indent=1, allow_nan=False))
        (out_dir / "report.md").write_text(md)
        (out_dir / "slide.md").write_text(report["headline"]["slide_markdown"])
        panels = {f"arm {a}": (prim[a], o) for a in prim}
        CAL.reliability_figure(panels, out_dir / "reliability_arms.png", "Reliability: each arm's preregistered output", cfg["calibration_bins"])
    return clean(report), {"prim": prim, "o": o, "aggs": arm_aggs, "claim_ids": resolved_ids}, md


def headline(report, cfg) -> dict:
    lines, h = [], {}
    c = report["arms"].get("C", {})
    if c.get("status") == "OK":
        d = c["diversity_decomposition_mean_aggregator"]
        h["arm_C_diversity"] = d["diversity"]
        h["arm_C_decomposition"] = {k: d[k] for k in ("crowd_brier", "mean_individual_brier", "diversity", "identity_max_abs_residual")}
        vb = c["vs_best_individual"]["brier"]["mean"]
        h["arm_C_mean_vs_best_individual_brier"] = vb
        lines += [
            "## Does organizing agents add measurable capability?",
            f"Arm C (n_units={d['n_units']}, n_claims={d['n_claims']}): crowd Brier {_fmt(d['crowd_brier'])} = mean individual Brier {_fmt(d['mean_individual_brier'])} - DIVERSITY {_fmt(d['diversity'])}  (identity residual {d['identity_max_abs_residual']:.1e}).",
            "",
            "**LIMIT:** " + THEOREM_LIMIT,
            f"Against the best individual (Brier, aggregate minus best; negative = aggregate better): ex post {_fmt(vb['expost']['aggregate_minus_individual'])} [{_fmt(vb['expost']['lo'])}, {_fmt(vb['expost']['hi'])}] -> {vb['expost']['verdict']}; cross-validated {_fmt(vb['cv']['aggregate_minus_individual'])} [{_fmt(vb['cv']['lo'])}, {_fmt(vb['cv']['hi'])}] -> {vb['cv']['verdict']}.",
        ]
    else:
        lines += ["Arm C has no complete units; no diversity number can be reported."]
    for key, e in report["comparisons"].items():
        x, y = key.split("_vs_")
        if e["status"] == "COMPARED":
            b = e["brier"]
            lines.append(f"Arm {x} vs arm {y} at matched budget ({e['budget_check']['max_over_min_minus_1']:.1%} spread): Brier {_fmt(b['mean'], 4)} [{_fmt(b['lo'])}, {_fmt(b['hi'])}] -> {b['verdict']}"
                         + ("" if e["metrics_agree"] else f"; BUT log loss says: {e['log_loss']['verdict']}"))
        else:
            lines.append(f"Arm {x} vs arm {y}: {e['status']} - {e.get('note', '')}")
    h["slide_markdown"] = "\n".join(lines) + "\n"
    return h


def to_markdown(r) -> str:
    L = ["# Collective capability report", "", "**Limit that governs every number below:** " + THEOREM_LIMIT, ""]
    L += [f"- prereg sha256 `{r['prereg']['sha256'][:16]}…`; claims freeze `{r['integrity']['claims_sha256'][:16]}…`; forecast chain head `{r['integrity']['forecast_chain_head'][:16]}…`",
          f"- claims: {r['claims']['n_frozen']} frozen, {r['claims']['n_resolved_scored']} resolved and scored, {r['claims']['n_unresolved_excluded']} unresolved excluded; by tier {r['claims']['by_tier_scored']}; base rate of 'yes' {_fmt(r['claims']['base_rate_of_yes'])}",
          f"- reference Brier of constant 0.5 = {_fmt(r['reference_scores']['brier_p0.5'])}; hindsight base-rate Brier = {_fmt(r['reference_scores']['brier_base_rate_hindsight'])}", ""]
    L += ["## Headline", r["headline"]["slide_markdown"], "## Token budgets (matched TOTAL tokens, not wall clock)", "",
          "| arm | forecasts | forecast tokens | overhead tokens | total |", "|---|---|---|---|---|"]
    for a, b in sorted(r["budgets"].items()):
        L.append(f"| {a} | {b['n_forecasts']} | {b['forecast_tokens']} | {b['overhead_tokens']} | {b['total_tokens']} |")
    for a in sorted(r["arms"]):
        A = r["arms"][a]
        L += ["", f"## Arm {a}"]
        if A.get("status") != "OK":
            L.append(f"No complete units ({A.get('status')}); dropped: {A.get('dropped_incomplete_units')}")
            continue
        if A.get("warning"):
            L.append("**WARNING:** " + A["warning"])
        d = A["diversity_decomposition_mean_aggregator"]
        L += [f"Primary output `{A['primary_output']['id']}`: Brier {_fmt(A['primary_output']['brier'])}, log loss {_fmt(A['primary_output']['log_loss'])}.",
              "", f"Diversity decomposition (unweighted mean crowd, {d['n_units']} units): crowd {_fmt(d['crowd_brier'], 5)} = mean individual {_fmt(d['mean_individual_brier'], 5)} - diversity {_fmt(d['diversity'], 5)}; residual {d['identity_max_abs_residual']:.1e}. Log-loss Jensen gap {_fmt(d['log_loss_jensen_gap'], 5)}.",
              "", "| aggregator | Brier | log loss | gain vs mean individual (Brier) | clipped |", "|---|---|---|---|---|"]
        for g in A["aggregators"]:
            L.append(f"| {g['aggregator']}{' (out-of-fold)' if g['uses_outcomes_out_of_fold'] else ''} | {_fmt(g['brier'])} | {_fmt(g['log_loss'])} | {_fmt(g['gain_vs_mean_individual_brier'])} | {g['n_clipped_for_log']} |")
        vb = A["vs_best_individual"]["brier"]
        L += ["", f"Individual Brier min/median/max: {[round(x, 4) for x in vb['unit_loss_min_median_max']]}; CV-selected individual {_fmt(vb['cv_best_individual_mean_loss'])}.",
              "", "| aggregate | minus ex-post best [CI] | verdict | minus CV best [CI] | verdict |", "|---|---|---|---|---|"]
        for g in A["aggregators"]:
            e, c = vb[g["aggregator"]]["expost"], vb[g["aggregator"]]["cv"]
            L.append(f"| {g['aggregator']} | {_fmt(e['aggregate_minus_individual'])} [{_fmt(e['lo'])}, {_fmt(e['hi'])}] | {e['verdict']} | {_fmt(c['aggregate_minus_individual'])} [{_fmt(c['lo'])}, {_fmt(c['hi'])}] | {c['verdict']} |")
        fc = A["family_error_correlation"]
        if "unavailable" in fc:
            L += ["", "Error correlation between model families: " + fc["unavailable"]]
        else:
            L += ["", f"Mean pairwise family error correlation: raw {_fmt(fc['mean_offdiag_raw'])}, within-outcome {_fmt(fc['mean_offdiag_within_outcome'])}; N_eff (equicorrelation assumption) raw {_fmt(fc['n_eff_equicorr_raw'], 2)} / within-outcome {_fmt(fc['n_eff_equicorr_within_outcome'], 2)} of {len(fc['names'])} families.",
                  f"Same- vs cross-family unit error correlation (raw): {A['unit_error_correlation_same_vs_cross_family']['raw']}"]
        cal = A["calibration_primary_output"]
        L += ["", f"Calibration of primary output: ECE {_fmt(cal['ece'])}, n={cal['n']}. Bins with data: " +
              ", ".join(f"[{b['lo']:.1f},{b['hi']:.1f}) n={b['n']} fcst {_fmt(b['mean_forecast'], 2)} obs {_fmt(b['observed_frequency'], 2)}" for b in cal["bins"] if b["n"])]
    L += ["", "## Arm comparisons (paired bootstrap over claims; negative = first arm better)"]
    for k, e in r["comparisons"].items():
        if e["status"] != "COMPARED":
            L.append(f"- **{k}: {e['status']}** {e.get('note', '')} {e.get('budget_check', {}).get('reason') or ''}")
        else:
            L.append(f"- **{k}**: Brier {_fmt(e['brier']['mean'])} [{_fmt(e['brier']['lo'])}, {_fmt(e['brier']['hi'])}] -> {e['brier']['verdict']}; log loss {_fmt(e['log_loss']['mean'])} [{_fmt(e['log_loss']['lo'])}, {_fmt(e['log_loss']['hi'])}] -> {e['log_loss']['verdict']}")
    L += ["", "## Limitations"] + [f"- {x}" for x in r["limitations"]]
    return "\n".join(L) + "\n"
