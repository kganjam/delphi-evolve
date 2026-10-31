# Independent audit brief for v1.2 (self-contained; ≈45–60 min)

Use only `README.md` (model definitions), `model_payload.jsonl` (what models see), `instances_full.jsonl` (hidden parameters) and your own code. Do not read `key.jsonl`, `verify_key.py`, `fam_*.py`, `audit/` before you have written your own verdicts.
1. For each of the 135 items derive the verdict from the request text's stated conventions (README gives one-line model definitions). Write `audit_verdicts.jsonl` {id, verdict, confidence, ambiguity note}.
2. Compare with `key.jsonl`; list every disagreement and every item you consider ambiguous. Do not edit the key; report to the critic and director.
3. Check that no public field predicts the label: read the ids (opaque hex), file order, `family`, and the first 30 prompts; try to predict verdicts without computing.
4. For each family, say whether the declared target is physically/mathematically sensible and whether any request leaves a convention open.
5. Write `scopedesk/bench/audit/independent_audit_<session>.json` on your own branch and message the director and critic. A defect means a new dated amendment and a new hash (v1.3), never an edit.
