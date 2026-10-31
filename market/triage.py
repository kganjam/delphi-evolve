"""Scorecard tally for the 21 frozen math-domain Delphi claims, built on bench-v1-freeze.json (not on any frame of ours).

The freeze file is authoritative and was written BEFORE formalization: claim ids, buckets B0-B3 (by what decides each claim),
declared counts, and the verdict vocabulary PROVED | REFUTED_AS_STATED | NEEDS_SCOPE_CONDITION | NOT_ATTEMPTED. This module reads it,
fixes nothing in it, and tallies verdict records supplied by the formalizers. It proves and decides nothing.

Checks that abort the run:
  * the verdict records name a claim not in the freeze, or one claim twice, or a bucket different from the freeze
  * a B0 claim (excluded by its own record) carries any verdict other than NOT_ATTEMPTED
  * a verdict outside the freeze vocabulary
  * declared freeze counts disagree with its own claim list
A claim in the freeze with no record is reported as `no_record` and counted NOT_ATTEMPTED, never dropped.

A verdict other than NOT_ATTEMPTED stands only with all of: lean_artifact (compiled proof or checked counterexample), axioms_clean is True,
statement_reviewed_by_other is True; PROVED and NEEDS_SCOPE_CONDITION also need mutants_total >= 1 with mutants_rejected == mutants_total;
NEEDS_SCOPE_CONDITION needs a written scope_condition; REFUTED_AS_STATED needs a written counterexample; every B1 verdict needs
anti_triviality_mutant_rejected is True (the freeze makes this mandatory). Otherwise it is shown as CLAIMED_BUT_UNVERIFIED with the
missing items listed (our bookkeeping label, not a verdict), never counted as a result.
B3 claims left NOT_ATTEMPTED are labelled attempted-and-unreached only if the record says attempted=true, never "failed".
A PROVED verdict is about the stated MODEL in Lean. It certifies neither translation fidelity nor anything about an organism.

Row: {"claim_id","verdict","bucket"(optional, must match),"reason","attempted","scope_condition","counterexample","lean_artifact",
      "axioms_clean","mutants_total","mutants_rejected","anti_triviality_mutant_rejected","statement_reviewed_by_other"}
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import stats as ST
from .desk import DeskError, _rows
from .report import clean

VERDICTS = ("PROVED", "REFUTED_AS_STATED", "NEEDS_SCOPE_CONDITION", "NOT_ATTEMPTED")
BUCKETS = ("B0", "B1", "B2", "B3")


def load_freeze(path, expected_sha256=None):
    raw = Path(path).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if expected_sha256 and digest != expected_sha256.lower():
        raise DeskError(f"freeze sha256 {digest} != expected {expected_sha256}; the frozen claim set was altered")
    d = json.loads(raw)
    if tuple(d.get("verdict_vocabulary", ())) != VERDICTS:
        raise DeskError(f"freeze verdict vocabulary {d.get('verdict_vocabulary')} differs from {VERDICTS}")
    claims = {}
    for c in d["claims"]:
        if c["claim_id"] in claims or c.get("bucket") not in BUCKETS:
            raise DeskError(f"freeze claim {c.get('claim_id')!r}: duplicate id or bucket {c.get('bucket')!r}")
        claims[c["claim_id"]] = {"bucket": c["bucket"]}
    computed = {b: sum(1 for c in claims.values() if c["bucket"] == b) for b in BUCKETS}
    computed["total"] = len(claims)
    declared = {k: v for k, v in d.get("counts", {}).items() if k in computed}
    if declared != computed:
        raise DeskError(f"freeze declared counts {declared} disagree with its claim list {computed}")
    return claims, {"path": str(path), "sha256": digest, "version": d.get("version"), "frozen_at_utc": d.get("frozen_at_utc"),
                    "counts": computed, "sha256_checked_against_expected": expected_sha256 is not None}


def _missing(r, bucket, verdict):
    miss = []
    if not r.get("lean_artifact"):
        miss.append("compiled artifact (proof or checked counterexample)")
    if r.get("axioms_clean") is not True:
        miss.append("clean axiom audit")
    if r.get("statement_reviewed_by_other") is not True:
        miss.append("non-author statement review")
    if verdict in ("PROVED", "NEEDS_SCOPE_CONDITION"):
        mt, mr = r.get("mutants_total"), r.get("mutants_rejected")
        if not (isinstance(mt, int) and not isinstance(mt, bool) and mt >= 1 and mr == mt):
            miss.append("mutation test (every mutant must fail; at least one mutant)")
    if verdict == "NEEDS_SCOPE_CONDITION" and not (r.get("scope_condition") or "").strip():
        miss.append("written scope condition")
    if verdict == "REFUTED_AS_STATED" and not (r.get("counterexample") or "").strip():
        miss.append("written counterexample")
    if bucket == "B1" and r.get("anti_triviality_mutant_rejected") is not True:
        miss.append("anti-triviality mutant (mandatory for every B1 verdict)")
    return miss


def triage(freeze_claims: dict, rows):
    recs = {}
    for r in rows:
        cid = r.get("claim_id")
        if cid not in freeze_claims:
            raise DeskError(f"record for claim {cid!r} which is not in the freeze")
        if cid in recs:
            raise DeskError(f"claim {cid} has two records")
        if r.get("verdict") not in VERDICTS:
            raise DeskError(f"{cid}: verdict {r.get('verdict')!r} not in {VERDICTS}")
        b = freeze_claims[cid]["bucket"]
        if r.get("bucket") is not None and r["bucket"] != b:
            raise DeskError(f"{cid}: record says bucket {r['bucket']} but the freeze says {b}; buckets are fixed before formalization")
        if b == "B0" and r["verdict"] != "NOT_ATTEMPTED":
            raise DeskError(f"{cid} is B0 (excluded by its own record) and cannot be {r['verdict']}")
        recs[cid] = r
    final, detail, downgraded, no_record = {}, {}, {}, []
    for cid, c in sorted(freeze_claims.items()):
        b, r = c["bucket"], recs.get(cid)
        if r is None:
            no_record.append(cid)
            final[cid] = "EXCLUDED_BY_RECORD" if b == "B0" else "NOT_ATTEMPTED"
            continue
        v = r["verdict"]
        if b == "B0":
            final[cid] = "EXCLUDED_BY_RECORD"
        elif v == "NOT_ATTEMPTED":
            final[cid] = "NOT_ATTEMPTED"
            if b == "B3" and r.get("attempted") is True:
                detail[cid] = "attempted-and-unreached"
        else:
            miss = _missing(r, b, v)
            if miss:
                downgraded[cid] = {"claimed": v, "missing": miss}
                final[cid] = "CLAIMED_BUT_UNVERIFIED"
            else:
                final[cid] = v
    cats = ("PROVED", "NEEDS_SCOPE_CONDITION", "REFUTED_AS_STATED", "NOT_ATTEMPTED", "CLAIMED_BUT_UNVERIFIED", "EXCLUDED_BY_RECORD")
    counts = {k: sum(1 for v in final.values() if v == k) for k in cats}
    table = {b: {k: sum(1 for cid, v in final.items() if freeze_claims[cid]["bucket"] == b and v == k) for k in cats} for b in BUCKETS}
    n = len(freeze_claims)
    evaluable = n - counts["EXCLUDED_BY_RECORD"]
    settled = counts["PROVED"] + counts["NEEDS_SCOPE_CONDITION"] + counts["REFUTED_AS_STATED"]
    ids = {k: sorted(c for c, v in final.items() if v == k) for k in cats}
    head = (f"Of {n} frozen claims, {counts['EXCLUDED_BY_RECORD']} are excluded by their own record; of the {evaluable} evaluable, {settled} have a verified verdict "
            f"({counts['PROVED']} PROVED, {counts['NEEDS_SCOPE_CONDITION']} NEEDS_SCOPE_CONDITION, {counts['REFUTED_AS_STATED']} REFUTED_AS_STATED); "
            f"{counts['NOT_ATTEMPTED']} not attempted or unreached; {counts['CLAIMED_BUT_UNVERIFIED']} claimed but missing required evidence.")
    if evaluable and settled / evaluable < 0.5:
        head += " The scorecard is thin and we say so."
    out = {"n_claims": n, "counts": counts, "by_bucket": table, "ids": ids, "no_record": no_record, "detail": detail,
           "downgraded_to_claimed_but_unverified": downgraded, "verified_of_evaluable": ST.rate(settled, evaluable), "headline": head,
           "note": "A verified verdict is about the stated MODEL in Lean; it certifies neither translation fidelity nor anything about an organism. Interval is item-level exact, treats claims as independent, wide at this n."}
    flags = []
    if no_record:
        flags.append(f"{len(no_record)} frozen claims have no record yet and are counted NOT_ATTEMPTED: {no_record}")
    if downgraded:
        flags.append(f"{len(downgraded)} claimed verdicts lacked required evidence and are NOT counted: {sorted(downgraded)}")
    out["flags"] = flags
    return out


def run_triage(freeze_path, records_path, out_dir=None, expected_sha256=None):
    claims, info = load_freeze(freeze_path, expected_sha256)
    res = triage(claims, _rows(records_path) if records_path else [])
    res["freeze"] = info
    md = ["## Validity-domain scorecard", res["headline"], ""] + [f"- FLAG: {f}" for f in res["flags"]]
    md += ["", "| bucket | " + " | ".join(res["counts"]) + " |", "|---|" + "---|" * len(res["counts"])]
    md += [f"| {b} | " + " | ".join(str(v) for v in row.values()) + " |" for b, row in res["by_bucket"].items()]
    res["markdown"] = "\n".join(md) + "\n"
    if out_dir:
        o = Path(out_dir); o.mkdir(parents=True, exist_ok=True)
        (o / "scorecard.json").write_text(json.dumps(clean(res), indent=1, allow_nan=False))
        (o / "scorecard.md").write_text(res["markdown"])
    return clean(res)
