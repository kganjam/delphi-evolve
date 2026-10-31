# market: scoring and matched-budget comparison for the Scope Desk entry

This package **measures**; it builds no service and no market API (the director owns the Scope Desk interface). It holds no
data and no result. Every number it prints comes from files that other owners write: a hashed answer key, agent answers, a
token or compiler-call ledger, oracle repair verdicts, Lean proof records.

## What it answers
1. **Is the desk right?** `python -m market desk` scores answers against the key (`desk.py`, `prereg_desk.json`).
   - Headline order: **false-alarm rate on `applies` items first**, then false reassurance on `out_of_scope` items, accuracy, 3-class Brier, log loss.
   - Proved / simulated / descriptive strata are reported in **separate rows**; the descriptive stratum never enters accuracy.
   - An optional `TXT` arm (naive textbook criterion) gives "how often does the textbook criterion mispredict" with a family-clustered interval.
2. **Did sharing help?** `python -m market lean` (`lean.py`, `prereg_lean.json`). Four arms at matched **compiler calls**:
   `L0` deterministic tactics (exempt baseline), `L1` one sequential agent with a persistent verified library,
   `L2` agents with private libraries, `L3` agents with a shared library. Sharing is "supported" only if L3 beats **both** L2 and L1.
   A direct-reuse diagnostic says when a gain is not attributable to reuse.
3. **Is a probability calibrated?** `basin.py` scores Beta-Binomial basin posteriors on held-out runs and counts Lean-clamped nodes that still pattern (re-indexed, never averaged away).

4. **What does the 21-claim scorecard honestly say?** `python -m market triage --freeze bench-v1-freeze.json --records R.jsonl` (`triage.py`).
   It is built on the frozen file written before formalization (claim ids, buckets B0-B3, verdicts PROVED / REFUTED_AS_STATED / NEEDS_SCOPE_CONDITION / NOT_ATTEMPTED) and invents no vocabulary of its own.
   A verdict stands only with a compiled artifact, a clean axiom audit, a non-author statement review, every mutant failing (proofs), a written scope condition or counterexample where relevant, and the mandatory anti-triviality mutant on every B1 claim.
   Otherwise it is shown as `CLAIMED_BUT_UNVERIFIED` with the missing items. B0 claims (excluded by their own record) cannot receive a verdict, a record may not change a frozen bucket, and unknown or duplicate claims abort.
   Claims without a record are counted NOT_ATTEMPTED, B3 is never called "failed", and a thin scorecard is called thin. It tallies records; it proves and decides nothing.

## Rules baked into the code (each has a test that fails if it is removed)
- Arms are compared only if total budgets differ by <= 5% of the smaller arm (tokens for desk arms, compiler calls for Lean arms); otherwise `REFUSED_BUDGET_MISMATCH` with no win/loss text.
- Intervals are family-cluster bootstraps. Fewer than 6 families gives `INSUFFICIENT FAMILIES`, not a verdict (a 3-family bootstrap can have zero width).
- Unanswered items are wrong (accuracy) and are false alarms on `applies` items. Invalid probability vectors are excluded and counted, not repaired.
- A key whose sha256 does not match its hash file aborts. A key or catalogue citing an excluded Delphi claim aborts.
- A deterministic arm is compared but labelled unmatched. A comparison where one error rate improves while the other worsens is printed with both.
- Collective superiority needs better accuracy **and** fewer false alarms **and** no detectably worse false reassurance. Anything else is printed as a null or mixed result with the same prominence.

## The diversity decomposition (demoted, kept)
`diversity.py` implements crowd error = mean individual error - diversity and **raises** if the identity fails at 1e-12. It is an algebraic identity for the unweighted mean
and guarantees only that the crowd beats the *mean* individual. It says nothing about the *best* individual, so it is an appendix, not a headline.

## What this package does not say
It asserts no universal diffusion-ratio threshold, no validated structure-to-diffusion pipeline, and no claim that scope repair is unique to biology (all retracted or killed upstream). It measures; the science lives in the key, the oracles and the Lean artifacts.

## Input formats
See the docstrings of `desk.py` (key, instances, answers, ledger, repairs) and `lean.py` (statements, results, ledger), `triage.py` (freeze file + verdict records). **Assumptions to confirm with the owners:** the arms ledger rows carry `arm` plus `total_tokens` or token fields; Lean result rows carry `proved` and `axioms_clean`; `family` is the independence unit (the model, not a run).

## Retained, not on the Scope Desk path
`store.py` / `report.py` / `arms.py`: an immutable hash-chained binary-claim forecast store and report from the earlier market design (`python -m market forecast-report`). Tested, unused by the desk path.

## Run
```
systemd-run --user --scope -p TasksMax=128 -p MemoryMax=4G -p MemorySwapMax=0 -p RuntimeMaxSec=600 python3 -m pytest tests/test_market_*.py -q
```
