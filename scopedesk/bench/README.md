# Scope Desk bench v1 (critic) — frozen when `KEY.sha256` is committed

Built 2026-10-31 (Seattle PDT) by the critic worker, Claude Sonnet 5.5. Regenerate: `python3 -I scopedesk/bench/build.py scopedesk/bench` (deterministic; a test rebuilds into a temp dir and compares hashes).

## What is in it
136 natural-language requests, 8 families, verdict ∈ `applies | out_of_scope | underdetermined` (SPEC.md schema). 62 applies (45.6%, the benign/in-scope controls), 56 out_of_scope (each with a machine-found witness and condition IDs), 18 underdetermined. Files: `instances_public.jsonl` (agent-visible), `instances_full.jsonl` (+hidden structure, never shown), `key.jsonl`, `excluded.json` (27 listed exclusions), `split.json`, `KEY.sha256`.

| family | Delphi record the request is about | scope condition tested | oracle used for the key |
|---|---|---|---|
| turing_finite_domain (24) | turing-ddi | finite-domain admissible modes; Neumann/Dirichlet/periodic/unstated BC | exact Fractions: det(J−qD)<0 over modes |
| wavelength_formula_licence (16) | turing-wavelength | near onset AND large domain | float: 10% agreement of λ_c with fastest-growing continuum / admissible mode |
| rayleigh_plateau (16) | thompson1917-ch05-12 | pinned vs periodic ends (πr vs 2πr) | exact: instability iff k r<1, from Rayleigh's dispersion sign change |
| kimura_regime (16) | kimura-fixation-probability | neutral approx. / diffusion approx. regime | exact haploid Wright–Fisher absorbing chain |
| hawk_dove_ess (16) | maynardsmith-hawk-dove | C>V; payoff stated | exact: ESS identity E(p*,q)−E(q,q)=(C/2)(p*−q)² |
| greenhill_buckling (16) | thompson1917-ch02-02 (Greenhill limit) | uniform vs tapered column; E, ρ stated | Rayleigh–Ritz (Λ_uniform=7.83735 vs Greenhill 7.8373) |
| hamilton_rule_form (16) | hamilton-rule | additive vs synergistic payoffs; frequency stated | exact selection-differential sign in a haploid pairing model |
| fisher_kpp_speed (16) | fisher-kpp-speed | KPP vs pushed fronts (cubic, Allee); growth form stated | analytic speeds (checked by PDE, below) |

Condition IDs follow SPEC.md plus additions made 2026-10-31 (`BC_PINNED_ENDS, DRIFT_DOMINATED, SMALL_SELECTION_LIMIT, PAYOFF_REGIME, UNIFORM_COLUMN, HAMILTON_NONADDITIVE, KPP_NONLINEARITY`).

## Split
Dev (prompt/harness tuning allowed): `turing_finite_domain`, `hawk_dove_ess`. Held out: the other six families. Report held-out and family-clustered results; item-level intervals are descriptive because items within a family are not independent. **Effective sample size is 8 families.**

## Baselines (scores in `baseline_scores.json`; exact Clopper–Pearson 95% intervals)
- **B0 scope gate** (regex extraction + the family's exact rule): template-A items 68/68 [0.947, 1.000]; template-B items 14/68 [0.117, 0.321]; all 82/136 [0.516, 0.686]. B0's rule is the key's own arithmetic, so 68/68 only shows extraction on phrasings its author saw; it is **not** evidence the key is right. The collapse on template B (unseen paraphrases that fall back to `underdetermined`) is the extraction headroom for agents — but templates A and B were written by the same author as B0, so this is **not** an independent held-out phrasing test.
- **R retrieval always-applies**: 62/136 [0.370, 0.543] = the share of benign items.
- **Format-only** (length, digit count, comma count, parity; trained on dev, tested on held-out): 36/96 = 0.375 [0.278, 0.480] vs majority-class rate 0.448 on held-out → at or below chance, so surface length/format does not carry the label under this simple classifier. (It is one classifier, not proof of no leakage.)

## Independent check of the key (`verify_key.py` → `key_verification.json`)
Every item re-decided by a different method that does not import the family modules (eigenvalues of J−qD; Bessel-function dispersion; power-iteration of the WF chain; replicator dynamics; explicit Price covariance; cubic-Hermite finite elements for Greenhill, Λ_uniform=checked; PDE front-speed measurements for KPP). **136/136 agree.** One real disagreement surfaced during the first pass (kp-0009: pushed-front speed 0.6% above the KPP speed — analytically "out of scope", empirically indistinguishable); it was fixed by excluding pushed speeds within 3% of the KPP speed and listing them. That rule was added after seeing the verification output and before any agent run. The PDE also confirmed the pushed-front formula c=(2+α)/√(2α) for α=10/3 (2.062 vs 2.066 predicted) and α=4 (2.117 vs 2.121), and the Allee speeds (0.2817 vs 0.2828; 0.1417 vs 0.1414).
**The verifier was written by the same author as the generator. AT3 (audit by a session that did not write them) is NOT done**; the NCA oracle audit (`scopedesk/oracles/`) is also not done because that directory does not exist yet.

## Limitations (read before citing a number)
- All items are the **formal** stratum. No simulated-PDE and no descriptive (Tallo) strata are included in this version.
- The 10% (wavelength, Kimura) and 3% (Greenhill/KPP exclusion) thresholds are **declared operationalisations** of qualitative scope statements, not numbers from the source records. Items within 2–3% of a threshold are excluded and listed.
- Idealised models: haploid Wright–Fisher; haploid pairing model for Hamilton; inviscid Rayleigh dispersion with idealised pinned ends k=nπ/l; Greenhill with linear taper; linear fastest-growing mode for wavelength. Verdicts are about these declared models, not tissues.
- The Greenhill item tied to `thompson1917-ch02-02` tests the **buckling-limit** reading only; it says nothing about the Tallo regressions, and that claim is not in Delphi's both-assessor-agree set.
- Surface features were checked with one weak classifier; a stronger leakage audit (and a second reader of phrasing) is still needed.
- Requests are templated; real scientist phrasing is harder. Wording templates A/B come from one author.
- Delphi pins/hashes are not yet wired into the items; the family→record table above is a manual mapping.
