"""Score forecasts of frontier events, reusing the Scope Desk scoring code unchanged.

What is different from a plain Brier run, and why:
  * An event that EXPIRES unresolved or is VOID is never silently dropped. Scores cover resolved events only, so
    the report prints how many events fell out and says the scored subset may differ systematically.
  * A forecast counts only if it was submitted before the event resolved and by the horizon.
  * A resolver who also forecast the event is a conflict; that resolution is excluded and listed.
  * Forecasters are not independent just because they are different accounts. Model-family and operator labels
    drive a family-first aggregate and the pairwise error correlation, printed next to the plain aggregates.
    Nothing here estimates a probability that a hypothesis is true; the forecast is of a defined event.
"""
from __future__ import annotations

import numpy as np

from market.aggregate import agg_mean, all_aggregates
from market.calibration import calibration_table, error_correlation
from market.scoring import brier, constant_reference, log_loss
from .schema import parse_time


def _classify(specs: list[dict], resolutions: list[dict], now: str) -> dict:
    t_now = parse_time(now)
    res = {r["spec_id"]: r for r in resolutions}
    out = {"resolved": [], "void": [], "expired_unresolved": [], "pending": []}
    for s in specs:
        r = res.get(s["id"])
        if r is not None and r["outcome"] == "void":
            out["void"].append(s["id"])
        elif r is not None and r["outcome"] in (0, 1):
            out["resolved"].append(s["id"])
        elif parse_time(s["horizon"]) <= t_now:
            out["expired_unresolved"].append(s["id"])
        else:
            out["pending"].append(s["id"])
    return out


def family_first_mean(P: np.ndarray, families: list[str]) -> np.ndarray:
    """Mean within each family, then mean across families. A dependence-aware HEURISTIC: it stops a family that
    contributes many correlated samples from dominating. It does not remove dependence between families."""
    fams = sorted(set(families))
    return np.mean([P[[i for i, f in enumerate(families) if f == g]].mean(axis=0) for g in fams], axis=0)


def score_events(specs: list[dict], forecasts: list[dict], resolutions: list[dict], now: str) -> dict:
    """forecasts: {spec_id, forecaster, family, probability, submitted_at}
    resolutions: {spec_id, outcome in {0,1,'void'}, resolved_at, resolver}"""
    status = _classify(specs, resolutions, now)
    spec = {s["id"]: s for s in specs}
    res = {r["spec_id"]: r for r in resolutions}
    excluded = {"resolver_conflict": [], "late_forecast": [], "after_horizon": []}
    keep: dict[str, dict[str, dict]] = {}
    forecasters_of: dict[str, set] = {}
    for f in forecasts:
        forecasters_of.setdefault(f["spec_id"], set()).add(f["forecaster"])
    for f in forecasts:
        sid = f["spec_id"]
        if sid not in spec or sid not in status["resolved"]:
            continue
        r = res[sid]
        if r["resolver"] in forecasters_of[sid]:
            if sid not in excluded["resolver_conflict"]:
                excluded["resolver_conflict"].append(sid)
            continue
        if parse_time(f["submitted_at"]) >= parse_time(r["resolved_at"]):
            excluded["late_forecast"].append((sid, f["forecaster"])); continue
        if parse_time(f["submitted_at"]) > parse_time(spec[sid]["horizon"]):
            excluded["after_horizon"].append((sid, f["forecaster"])); continue
        keep.setdefault(sid, {})[f["forecaster"]] = f
    scored_ids = sorted(sid for sid in keep if sid not in excluded["resolver_conflict"])
    report = {"event_status": {k: len(v) for k, v in status.items()}, "excluded": excluded,
              "selection_note": ("scores cover RESOLVED events only; %d void and %d expired-unresolved events are not scored and may differ "
                                 "systematically from the scored ones" % (len(status["void"]), len(status["expired_unresolved"]))),
              "n_scored_events": len(scored_ids)}
    if not scored_ids:
        return {**report, "per_forecaster": None, "reason": "no resolved events with admissible forecasts"}
    names = sorted({n for sid in scored_ids for n in keep[sid]})
    complete = [sid for sid in scored_ids if all(n in keep[sid] for n in names)]
    o = np.array([res[sid]["outcome"] for sid in scored_ids], float)
    per = {}
    for n in names:
        ids = [sid for sid in scored_ids if n in keep[sid]]
        p = np.array([keep[sid][n]["probability"] for sid in ids]); oo = np.array([res[sid]["outcome"] for sid in ids], float)
        per[n] = {"family": next(keep[sid][n]["family"] for sid in ids), "n": len(ids),
                  "brier": float(brier(p, oo).mean()), "log_loss": float(log_loss(p, oo).mean())}
    report.update({"per_forecaster": per, "reference": constant_reference(o),
                   "calibration_pooled_forecasts": calibration_table(
                       [keep[sid][n]["probability"] for sid in scored_ids for n in keep[sid]],
                       [res[sid]["outcome"] for sid in scored_ids for n in keep[sid]]),
                   "calibration_n_events": len(scored_ids)})
    if len(names) >= 2 and len(complete) >= 1:
        P = np.array([[keep[sid][n]["probability"] for sid in complete] for n in names])
        oc = np.array([res[sid]["outcome"] for sid in complete], float)
        fams = [per[n]["family"] for n in names]
        agg, _ = all_aggregates(P)
        agg["family_first_mean"] = family_first_mean(P, fams)
        report["aggregates"] = {k: {"brier": float(brier(v, oc).mean()), "log_loss": float(log_loss(v, oc).mean())} for k, v in agg.items()}
        report["aggregates_over_events"] = complete
        report["error_correlation"] = error_correlation({n: P[i] for i, n in enumerate(names)}, oc) if len(complete) >= 3 else None
        report["distinct_families"] = len(set(fams))
        report["dependence_note"] = ("forecasters sharing a model family or operator are not independent; distinct_families is an UPPER bound "
                                     "on independent voices, and the family-first mean is a heuristic, not a correction")
    else:
        report["aggregates"] = None
        report["aggregates_note"] = "aggregates need >=2 forecasters who all forecast >=1 common resolved event"
    # what a card may print next to a prior taken from these forecasts
    report["calibration_summary_for_cards"] = {"n_resolved_events": len(scored_ids),
                                                "calibrated_claim_allowed": False,
                                                "note": "a handful of events cannot establish calibration; the table is shown, no claim is made"}
    return report
