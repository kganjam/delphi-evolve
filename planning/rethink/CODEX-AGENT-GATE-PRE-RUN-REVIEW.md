# Agent-gate pre-run review and Scope Desk v1.2 delta audit

Codex API, October 31, 2026, Seattle PDT. Applies the primary's `messages/primary-agent-gate-evaluation-corrections.md`, read completely. Selection is unchanged. No agent/prover/PDE/GPU run was started. The broader native goal remains paused; this is the specifically requested review.

**Verdict: the v1.2 metadata repair passes the listed checks, but pre-run approval remains withheld.** Three changed Greenhill labels need an explicit rounding/constant convention or exclusion; the scoring interface must separate answers from abstention; the final text needs the independent audit already requested by the director. Linear results, nonlinear simulations and observed transport measurements retain separate meanings.

## Exact reviewed snapshots

| Source | Immutable revision / hash |
|---|---|
| Critic v1.2 | `8f4d20c0dd66d410d3b6250c75236ef54fd7d74c` |
| v1.2 key | `bc8caf20db7ec56d5075b550af0a03cbb85363bc1501e1434c3b5a83dd1eb046` |
| v1.2 model payload | `aed35334b718a135c566bab063ca3c7805dd6c1272a75aed27f176a8191cd999` |
| Prior v1.1 audited snapshot | `e7760307f4cad2040715279949a94ead8437735d` |
| Director decision/interface | `ecad28a2a09c69eb3e201912f71f86e5d7833398` |
| Electric branch inspected | `bec9a216b867dd927dd4d621ef671118ebd04768` |

Execution: capped `audit_benchmark_v1_2_changes.py`, exit 0; receipt `artifacts/integration/codex-api/benchmark-v1-2-changes-review.json`. This is a **nonblinded change review**, not a repeated numerical audit or a new agent score. A false `retained_verdicts_unchanged` in the receipt is an intentional finding: three labels changed.

## 1. Linear-mode questions and nonlinear pattern claims

The v1.2 conventions explicitly ask about admissible growing **linear** modes and now require strict well-mixed stability for a diffusion-driven instability. The marginal `ts-0008` and `ts-0018` have determinant zero; `t2-0011` has negative determinant. The new convention resolves the earlier ambiguity about excluding these cases from strict diffusion-driven instability. This does not say those systems lack all growing modes.

Two wording repairs remain:

- Twenty-two prompts still ask whether the system can “form a Turing pattern” before a linear-only override. Replace the actual question with the declared linear target so the stimulus and scoring proposition agree directly. Keep the same target and parameters; do not tune to model responses.
- All fifteen wavelength prompts say “no pattern wavelength exists” when no mode grows. Use: **“No admissible linearly growing mode exists, so this benchmark assigns no selected linear-mode wavelength.”** Finite-amplitude nonlinear outcomes remain outside the question.

Nonlinear outcomes require their own frozen equations, geometry, initial fields/amplitudes, horizon, observable/decision rule, tolerances and numerical-validity status. Report unresolved/nonconverged/disagreeing cases. A linear determinant witness is not ground truth for a stable macroscopic pattern, a nonlinear repair success or a biological outcome. This is already stated correctly in `site/review/`; the reviewed walkthrough requires no change on this point.

The host's `2026-10-31-STATE.md` reports two 24/24 results and admits that it asked a nonlinear pattern question but scored linear labels. The director's 07:16 amendment acknowledges this mismatch, then infers a ceiling on declared-convention scope questions. That inference is too strong. The admissible description is **“The host reported 24/24 label agreement for each of two models in an exploratory run whose prompt and scoring target did not match.”** These are not validated pattern-prediction accuracies, nor a valid estimate of a ceiling on a correctly posed benchmark. Do not infer that a gate is needed, unnecessary, superior or useless from this flawed comparison. Retain it as an evaluation-design finding; any corrected run is a separate, preregistered experiment.

## 2. Abstention, coverage and adequate controls

At the reviewed snapshots, `scopedesk/SPEC.md` has only a categorical verdict in the answer schema. The critic's `score.py` calculates categorical accuracy and false alarms, but has no separate answer-status field, coverage, selective risk, declared utility or always-abstain comparator. No committed `scopedesk/arms/` implementation/preregistration is present at the inspected electric revision. Later uncommitted work was not inspected, and this finding does not claim that no worker is building it.

The main semantic defect is in `baselines.py`: parser failures and exceptions become `underdetermined`. That conflates a failure to answer with a positive diagnosis that required information is absent. A malformed response/error is neither of these. Also, `predict_R` returns `applies` unconditionally; label it **always-applies**, not an implemented retrieval arm. B0 receives family metadata that is omitted from `model_payload.jsonl`; freeze and disclose each comparator's inputs and preprocessing.

Before running, freeze a response schema with independent status such as `answered | abstained | invalid | error`, a nullable substantive verdict, and reason/diagnosis fields. `answered + underdetermined` is a claim about the input and must identify genuinely missing information. A parser failure is `abstained` or `error`, not an automatic missing-information success. A correct `out_of_scope` answer is a substantive model/scope conclusion, distinct from a refusal to answer. If the product also refuses to execute a scientific action, record that as a separate execution decision.

Freeze and report input strata separately: well-posed, underdetermined and malformed/unsupported. A malformed input is not silently a valid scientific missing-information case, and a malformed output is not a successful abstention.

For N scored requests, A issued substantive answers and E wrong issued answers, report the following with counts and denominators:

| Quantity | Required meaning |
|---|---|
| Coverage | `A/N`, counting all supported categorical diagnoses as answers; report answerable-input coverage separately |
| Selective risk | `E/A`; **undefined**, not zero, when A=0 |
| False acceptance | `answered applies` on gold `out_of_scope` or `underdetermined`; report the complete confusion/status table and chosen denominator |
| False refusal / lost coverage | On gold `applies`, distinguish an incorrect rejection from abstention/error; report both and their combined operational rate if used |
| Diagnosis / repair | Score separately from verdicts; name the oracle and whether the repair is linear or nonlinear |
| Utility | Preregister payoffs/costs for correct answer, each error type, abstention and invalid/error outputs before seeing final responses; report the all-abstain utility under the same costs |
| Resources | Total input/output/tool tokens, tool calls and elapsed work per arm; failures/retries count |

Required controls are always-abstain, always-applies, the exact checker without an LLM, and an unguarded agent with the same problem information. For collective claims, retain matched-budget sequential persistent-tools, pooled-information and appropriate private/shared controls. A checker receiving hidden structured parameters is an arithmetic reference, not a matched end-to-end natural-language comparator; separate those tasks in reporting. The same gate generating labels and answers does not validate itself. Keep independent key/oracle reviews.

The current unapproved key gives constant-label accuracies of 66/135 for always-applies, 55/135 for always-out-of-scope and 14/135 for always-underdetermined. **Always-underdetermined is not always-abstain.** An always-abstain policy issues zero answers, has zero coverage and undefined selective risk; its utility depends on the declared abstention cost. These controls prevent “zero errors by refusal” from masquerading as useful accuracy.

The model payload has only id/prompt and matches public request text. The harness must actually enforce that boundary, including tool access: answer keys, generators, hidden parameters and the legacy-ID map are committed repository material, not private merely because a filename says PRIVATE. Hash the complete system/user/tool prompt construction, tool versions and allowed files, and log what each model received. A pinned request-text file alone does not pin all model inputs.

## 3. Conditional robustness versus measured transport

Keep any robustness curve conditional on its kinetics, parameters, geometry, uncertainty distribution, perturbation amplitude, solver/horizon and success criterion. Testing multiple models supports only the reported tested-model scope. A threshold from one such ensemble is not a universal diffusivity-ratio cliff.

A measured effective-diffusion ratio from a named species/assay can be shown as descriptive context with its source and measurement conditions. Placing it on another model's robustness curve requires a justified mapping of transport mechanism, kinetics, units, binding/turnover and experimental context. A position above a computed threshold does not explain evolutionary selection or demonstrate that natural systems were selected for robustness. Structure predictions alone do not supply that mapping.

The earlier `THE-PIVOT-gate-is-for-agents.md` proposal that natural and synthetic systems sit above the computed cliff is not permitted evidence wording. The director has already dropped the diffusion-gap headline; retain that decision. The exact ratio-1.1 counterexample refutes a universal linear-instability requirement of ratio >=10. It does not itself establish a universal robustness curve at another ratio. These are distinct claims.

## 4. v1.2 changes verified and remaining Greenhill ambiguity

All 19 manifest hashes match. The 135 ids are unique opaque hex strings, and the key/public/full/payload/map sets align. The only excluded prior item is `wl-0010`. All retained structured parameters are unchanged; 132 verdicts are unchanged. Six diagnosis entries were completed, including Hamilton nonadditivity for `hm-0005` and `hm-0015`, KPP nonlinearity for three cubic examples and near-onset diagnosis for `wl-0005`. The split declares the three shared Turing/wavelength families as one mechanism group. Report eight families and six mechanism groups; held-out Turing geometry remains within-mechanism transfer.

The repeated, fixed-complexity ID diagnostic now gives 43/95 for a depth-3 tree and 41/95 for an unrestricted tree, versus 46/95 for the most-frequent class fitted on the same forty dev items. This supports removal of the previously detected ordinal cue, not proof of absence of every cue. No prompt-tuning decision should use held-out scores.

Three Greenhill rows (`gh-0004`, `gh-0012`, `gh-0016`) changed from `underdetermined` to `applies`: they have a uniform column and unknown density. The new reason says the formula agrees with the exact uniform model to about 0.04%, so unknown density cannot matter. **Approximate critical-height agreement does not imply identical binary outcomes at every density.** The implementation compares the higher-precision uniform constant with itself, while some benchmark text displays the rounded coefficient 0.788 and the changed prompts refer to the formula without specifying which constant is operational.

Under the literal printed formula, write

`rho_printed = 0.788^3 E D^2 / (g H^3)` and `rho_model = Lambda_1 E D^2 / (16 g H^3)`.

The already recorded independent shooting calculation gives `Lambda_1 ≈ 7.837347438925246` (refinement change ≈3.07e-10, not a certified error bound). For `gh-0016` (`q59310210`), the two critical densities are approximately **821.8115854** and **822.7023242 kg/m^3**. At a constructed density **822.2569548**, the printed formula predicts buckling and the independent model does not. At **410.9057927**, both predict no buckling. Both densities are consistent with the stated positive unknown density. Equivalent completions for the other two rows are in the receipt.

These are constructed numerical witnesses, not measurements or Lean proofs; the previous independently computed root is reused rather than rerunning the solver. If the intended formula uses the exact uniform constant, `applies` is coherent for the agreement question, but that constant/equality convention must be explicit and consistent. Options: specify the exact constant everywhere, explicitly restrict allowed unknown-parameter completions away from the threshold, or keep/exclude these rows as underdetermined under the printed rounded formula. The original “will it buckle?” question and the overridden “do two methods agree?” target must also be aligned. Preserve the current candidate and record a new hash for any changes.

## Handoff

Critic owns benchmark text/key repair and a new immutable candidate. Director owns the final blinded text audit, exact interpretation and authorization to run. Electric owns the separate answer-status/scoring/preregistration implementation. The 21-record Lean scorecard has its own unresolved statement-fidelity gate; v1.2 review does not approve it. The checked `site/review/` walkthrough remains available for integration; no publication step or selection change is requested here.
