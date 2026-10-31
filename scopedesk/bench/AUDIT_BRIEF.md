# Independent audit brief (AT3) — for a session that did NOT write `scopedesk/bench/` (≈45–60 min)

Do not read `verify_key.py` or `fam_*.py` before step 2; the point is an independent derivation.

1. Fetch: `git show work/rethink-critic:scopedesk/bench/instances_full.jsonl` (hidden structured parameters), `key.jsonl`, `README.md` (model definitions per family only), `excluded.json`.
2. For each family, write your own decision code from the README's one-line model definitions and the hidden `structured` fields (Turing: det(J−qD)<0 over admissible modes; wavelength: 10% licence rule; Rayleigh–Plateau: kr<1 with k=nπ/l or 2πn/l; Kimura: exact haploid WF fixation vs 1/N or the diffusion formula, 10%; Hawk–Dove: C>V mixed ESS; Greenhill: tapered-column buckling vs the uniform formula; Hamilton: sign of selection with/without synergy; KPP: pulled vs pushed speeds). Compare to `key.jsonl`. Report every disagreement; do not "fix" the key — disagreements go to the critic.
3. Judge the 27 entries of `excluded.json` and 10 randomly chosen retained items near their thresholds: is each exclusion/label defensible?
4. Leakage: read 30 random `instances_public.jsonl` requests; try to predict the verdict from wording alone (without computing). Report accuracy by family; flag any phrase, number format or length cue that predicts the label.
5. Operationalisation check: for 8 items (one per family) say whether the verdict follows from the cited Delphi record plus the README's declared thresholds, or whether the threshold is arbitrary.
6. Write results to `scopedesk/bench/audit/independent_audit_<your-session>.json` on YOUR branch; message the director and the critic. The critic does not edit the key without a dated amendment note, and any amendment changes `KEY.sha256` (announce a new hash).

Oracle API audit (when `scopedesk/oracles/` lands): `python3 -I scopedesk/bench/audit/audit_oracle_api.py <oracle_checkout> OUT.json` runs `oracles.linear.check` on the 24 Turing items and the 16 wavelength items and reports disagreements with the key.
