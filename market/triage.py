"""Scorecard tally for the 21 math-domain Delphi claims (18 population-genetics + 3 Turing).

This module decides nothing about mathematics and proves nothing. It tallies verdict records supplied by whoever formalizes and
REFUSES bookkeeping that would inflate the scorecard. Four buckets, exactly:

  holds_as_stated                  the claim as stated is entailed
  holds_with_supplied_scope        entailed only under a scope condition WE had to supply (the condition must be written down)
  empirical_not_formalizable       an empirical claim, or one with no canonical formal statement; reason required
  unresolved                       not settled in the time we had; reason required

A verdict in the first two buckets stands only if ALL of these are recorded, otherwise it is DOWNGRADED to `unresolved`
(visibly, with the missing items listed, never dropped and never counted as a hold):
  * lean_artifact          path or hash of the compiled proof
  * axioms_clean is True   `#print axioms` shows no sorry / unexpected axiom
  * mutants_total >= 1 and mutants_rejected == mutants_total   every law/scope mutant fails the check
  * statement_reviewed_by_other is True   statement fidelity reviewed by someone who did not write it
  * scope_condition        (second bucket only) the supplied condition, in words

The known trap claims must sit in empirical_not_formalizable or unresolved; in a hold bucket the run aborts. The total is
checked against 21 and a mismatch is printed. A hold means proved about the MODEL in Lean; it is not a statement about biology.
If the scorecard is thin, `headline` says so with the number.

Row: {"claim_id","domain":"popgen|turing","bucket","reason","scope_condition","lean_artifact","axioms_clean",
      "mutants_total","mutants_rejected","statement_reviewed_by_other"}
"""
from __future__ import annotations

import json
from pathlib import Path

from . import stats as ST
from .desk import DeskError, _rows
from .report import clean

BUCKETS = ("holds_as_stated", "holds_with_supplied_scope", "empirical_not_formalizable", "unresolved")
HOLDS = BUCKETS[:2]
TRAPS = ("turing-morphogen-hypothesis", "kimura-neutral-theory")


def _missing_evidence(r):
    miss = []
    if not r.get("lean_artifact"):
        miss.append("compiled proof artifact")
    if r.get("axioms_clean") is not True:
        miss.append("clean axiom audit")
    mt, mr = r.get("mutants_total"), r.get("mutants_rejected")
    if not (isinstance(mt, int) and not isinstance(mt, bool) and mt >= 1 and mr == mt):
        miss.append("mutation test (every mutant must fail; at least one mutant)")
    if r.get("statement_reviewed_by_other") is not True:
        miss.append("non-author statement review")
    if r.get("bucket") == "holds_with_supplied_scope" and not (r.get("scope_condition") or "").strip():
        miss.append("written scope condition")
    return miss


def triage(rows, expected_total: int = 21, traps=TRAPS):
    seen, final, downgraded = {}, {}, {}
    for r in rows:
        cid = r.get("claim_id")
        if not isinstance(cid, str) or cid in seen:
            raise DeskError(f"claim_id missing or duplicated: {cid!r}")
        if r.get("bucket") not in BUCKETS:
            raise DeskError(f"{cid}: bucket {r.get('bucket')!r} not in {BUCKETS}")
        if r["bucket"] in BUCKETS[2:] and not (r.get("reason") or "").strip():
            raise DeskError(f"{cid}: {r['bucket']} needs a written reason")
        if cid in traps and r["bucket"] in HOLDS:
            raise DeskError(f"{cid} is a known trap and cannot be a hold; use empirical_not_formalizable or unresolved")
        seen[cid] = r
        bucket = r["bucket"]
        if bucket in HOLDS:
            miss = _missing_evidence(r)
            if miss:
                downgraded[cid] = {"claimed": bucket, "missing": miss}
                bucket = "unresolved"
        final[cid] = bucket
    n = len(seen)
    ids = {b: sorted(c for c, v in final.items() if v == b) for b in BUCKETS}
    counts = {b: len(v) for b, v in ids.items()}
    holds = counts["holds_as_stated"] + counts["holds_with_supplied_scope"]
    by_domain = {}
    for cid, r in seen.items():
        d = by_domain.setdefault(r.get("domain", "unknown"), {b: 0 for b in BUCKETS})
        d[final[cid]] += 1
    out = {"n_claims": n, "expected_total": expected_total, "total_matches_expected": n == expected_total,
           "missing_traps": [t for t in traps if t not in seen], "counts": counts, "ids": ids, "by_domain": by_domain,
           "downgraded_to_unresolved": downgraded,
           "holds_of_all_claims": ST.rate(holds, n),
           "note": "A hold = compiled proof + clean axioms + all mutants fail + non-author statement review, about the MODEL not biology. Interval is item-level exact, treats claims as independent, and is wide at this n."}
    flags = []
    if n != expected_total:
        flags.append(f"{n} claims supplied, {expected_total} expected: do not quote this as 'the 21 theorems'")
    if out["missing_traps"]:
        flags.append(f"trap claims absent: {out['missing_traps']}")
    if downgraded:
        flags.append(f"{len(downgraded)} claimed holds lacked required evidence and were counted as unresolved: {sorted(downgraded)}")
    out["flags"] = flags
    out["headline"] = (f"{holds} of {n} claims hold with full evidence ({counts['holds_as_stated']} as stated, {counts['holds_with_supplied_scope']} only with a scope condition we supplied); "
                       f"{counts['empirical_not_formalizable']} are empirical or not formalizable; {counts['unresolved']} unresolved in the time we had."
                       + (" The scorecard is thin and we say so." if n and holds / n < 0.5 else ""))
    return out


def run_triage(path, out_dir=None, expected_total: int = 21):
    res = triage(_rows(path), expected_total)
    md = ["## Validity-domain scorecard", res["headline"], ""] + [f"- FLAG: {f}" for f in res["flags"]]
    md += ["", "| bucket | claims |", "|---|---|"] + [f"| {b} | {', '.join(res['ids'][b]) or '-'} |" for b in BUCKETS]
    res["markdown"] = "\n".join(md) + "\n"
    if out_dir:
        o = Path(out_dir); o.mkdir(parents=True, exist_ok=True)
        (o / "scorecard.json").write_text(json.dumps(clean(res), indent=1, allow_nan=False))
        (o / "scorecard.md").write_text(res["markdown"])
    return clean(res)
