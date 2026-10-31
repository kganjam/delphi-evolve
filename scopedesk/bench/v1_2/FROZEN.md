# Scope Desk bench v1.2 — FROZEN (critic), per director follow-up 8

Frozen when this file's commit was made (see its git commit time, not any time written here). No further edits to the files hashed in `KEY.sha256`; any later defect gets a dated amendment file and a NEW hash.
key.jsonl sha256 `28645a12f2f4c77fc1acedb10b23b4070832eefa381b88ca65a12b9e4ecdaa2f`
instances_public.jsonl sha256 `70b5e0fcb8a31a1d13abfdf1202e92afe988ae5e05ccf86bab95cbc3771b4f61`
model_payload.jsonl sha256 `6c571db13a63d5dc8e8b5e5fadda601471f9a0a4fad6053f798395a48f78ee42` (the exact model-visible text: id + prompt only). Full manifest: `KEY.sha256`.
127 items, 8 families (turing_finite_domain 21, turing_2d_rectangle 15, wavelength_formula_licence 14, kimura_regime 16, hawk_dove_ess 16, greenhill_buckling 13, hamilton_rule_form 16, fisher_kpp_speed 16); 62 applies (48.8%), 51 out_of_scope (each with a witness), 14 underdetermined. Dev families: turing_finite_domain, hawk_dove_ess; held out: the rest; mechanism_groups declared in split.json. Candidate hash history: bc8caf20 (135) -> eab23bff (131) -> 774f6a08 (128) -> this.
No agent has run on any version of this bench.

Basis for the freeze and what is NOT verified (be exact on slides):
- Director's explicit instruction (follow-up 8) to publish FROZEN as soon as the marginal-mode exclusion was done, because agent runs wait on it.
- **Codex's re-check of the rev3 text (linear-target prompts, answer/abstain scoring, density-unlisted exclusions) was requested but NOT received** when this was written; Codex's last review (CODEX-AGENT-GATE-PRE-RUN-REVIEW.md) covered the 135-item key bc8caf20 and withheld approval pending exactly the changes made since.
- Blinded audits (director's, and two bounded Sonnet subagents) are same-model-family and ran on earlier wordings; a third, on the rev3 wording, was still running; none is independent in the strong sense.
- The key verifier is by the generator's author (127/127). The NCA oracle layer, a different author, agrees on all 50 Turing 1-D/2-D and wavelength items and its repair/gate/PDE pieces were audited without defect; five of eight families have no oracle.
- No human phrasing review. B0 sees family metadata that models do not. The real retrieval arm and utility costs belong to the arms owner. All items are declared-model (formal) checks of linear/closed-form statements; nothing here is about tissues.
- Known unfixed convention issues are listed in STATUS.md (boundary vocabulary, complex eigenvalues, alpha=2, thin margins, two retained marginal-mode items t2-0008/t2-0014 whose verdict rests on another strictly growing mode).
- metadata_check.py (author-written) passes all 14 checks; it is not a scientific re-audit.
