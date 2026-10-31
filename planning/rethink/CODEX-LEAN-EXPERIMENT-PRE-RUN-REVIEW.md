# Lean experiment pre-run review

Codex API, October 31, 2026, Seattle PDT. **New 21-record Mathlib prover arms are not approved.** This is a nonblinded statement/protocol/code review and an offline verifier control, not a model evaluation. No model calls, prover arms or GPU jobs were launched.

The director's reassignment is recorded in `/data/artifacts/delphi-evolve-rethink/messages/director-needs-electric-recovery.md`. It requires an independently authored and hashed statement freeze and Codex review before any new arm. The proposed recipient is the existing dx-guilds session; host confirmation of that assignment remains separate. I have not edited its checkout.

## What was actually available

| Input | Exact revision | Finding |
|---|---|---|
| Admissible scorecard/module | `da8817529b41b3b4fb917a6cc5d7354662235cd9` | No change to `bench/bench-v1.1-freeze.json` or `lean/Admissible.lean` since reviewed `469874b2e5da8a5d503416be8bd071a6919e08a3`. Earlier full-target and correspondence findings remain open. |
| Guilds runner/targets/preregistration | `feb5dbd3b6b5613f47c73bbed6ff1a95ecc76e87` | Separate 19-target, core-Lean, integer-arithmetic experiment. Commit history records 12 completed same-model runs and Addendum A. This is not the requested 21-record Mathlib experiment. |
| Initial guilds registration | `c01af1c5cf7b7cf75373c42dd3770d9ca75e1bf2` | Preserves historical registration. Later additions must retain their timestamps and exposure history; this review cannot retroactively preregister those runs. |
| Electric runner | `bec9a216b867dd927dd4d621ef671118ebd04768` plus read-only uncommitted `scopedesk/arms/` | No independently frozen full 21-target Lean set was found in the inspected handoff. |

The guilds working tree also contains evolving uncommitted registration/adapter changes. The executable findings below apply to the pinned `feb5dbd` git objects, not an unversioned moving target. Re-review a new exact source SHA after fixes.

## Confirmed blocking verifier defect

`lean_commons/lean_check.py` scans submitted text, appends the frozen statement, compiles, and checks axioms. It does not compare the resulting constant's elaborated type to the independently frozen target. `agent.py` only extracts helper theorem names and checks name collisions; it does not enforce theorem-only helper syntax.

The allowed helper text can add a global variable and include it in subsequent declarations:

```lean
theorem review_helper : True := by trivial
variable (h : False)
include h
theorem review_target : False := by exact h
```

The checker accepts this. Lean correctly reports `review_target : False → False`, with no axioms. The frozen text said `False`, but the elaborated theorem has an extra assumption. **This is a verifier target-fidelity failure, not a Lean-kernel inconsistency.** A legitimate theorem before the variable declaration also satisfies the existing helper-name/publish parsing path.

Executed controls in [receipt.json](../../artifacts/integration/codex-api/lean-commons-review/receipt.json):

| Review control | Checker result | Compiler result |
|---|---|---|
| Frozen `True`, ordinary proof | accepted | exit 0 |
| Frozen `False`, no added premise | rejected | exit 1 |
| Frozen `False`, added premise as above | accepted | exit 0; actual type `False → False` |

Reproducer: [review_lean_commons.py](../../scripts/review_lean_commons.py), loading pinned git objects. Only `LEAN_BIN` is replaced by a wrapper fixing Lean 4.35.0 and `-j2`; acceptance policy is unchanged. The process ran with TasksMax=128, MemoryMax=4G, MemorySwapMax=0, RuntimeMaxSec=600 and CPU library threads=1; exit 0. This is an adversarial review input, not evidence that any historical model response used the loophole.

Required repair: restrict helpers to supported declarations, preserve a trusted target environment, and compare the fully elaborated type (including all implicit and explicit parameters) to the frozen target. Check every published helper and target with its complete dependency closure in a fresh environment. Audit historical accepted artifacts under the repaired checker before describing them as proofs of the intended frozen statements. Adding the two missing keywords to the regex alone is not a sufficient fidelity specification.

## Budget and mechanism findings

1. **Pending calls are not reserved.** `TokenLedger.check` reads completed spend but does not lock/reserve pending usage. The offline receipt shows two checks of 60 tokens both passing a 100-token cap, followed by recorded spend 120. No API call was needed. Require an atomic reserve/commit/release mechanism, an explicit allowance for uncertain provider usage, and declared handling of failures/retries. A fixed 7,000-token guess does not upper-bound growing prompts plus output/reasoning.
2. **Thirty calls is a call-budget comparison.** A generous safety token cap does not make realized tokens equal, nor match aggregate compiler/tool time. The new director brief calls for matched total resources including library creation and retrieval. Preregister one primary budget, token/tool/compiler accounting and stop rules; report actual spend and censored unsolved tasks. A call-matched pilot may be reported under that name.
3. **Reuse is currently a source-text regex.** `agent.py` counts library names in helper/proof text. This can count comments or unused references and miss automation's implicit use. It is not the required proof-term constant-dependency measurement. Extract dependencies from the accepted elaborated proof, separate direct/transitive and same-/cross-agent use, and state which artifacts were exposed at each attempt. Observed reuse alone does not identify causal benefit.
4. **Freeze manifest is stale at the reviewed revision.** Target, definition, contract and reference-proof hashes pass; `PREREG.md` does not match `FREEZE.sha256` after the recorded amendment. This does not erase the original registration, but a new arm must identify the exact base registration plus append-only amendments and code/toolchain hashes. Fail closed on a mismatched required input before starting.
5. **Compiler/run bounds need adjustment.** The checker invokes the default Lean executable in a temporary directory without a pinned Mathlib project or `-j2`; version is recorded afterwards. The registered launcher's 1,500-second scope exceeds this project's 600-second per-run contract. Pin toolchain, lake manifest/cache and worker concurrency, and obey the run bound or obtain an explicit director/user amendment. Freeze aggregate compiler time as a resource, not only a per-call timeout.
6. **Failures need explicit run status.** Worker exceptions can end a thread while the outer runner still writes a normal summary. Count unique certified target IDs, distinguish unattempted/exhausted/timeout/infrastructure-failed items, retain all attempted runs, and record abort/rerun eligibility before observing scores. An infrastructure-failed run is not a clean null.

The existing shared/private/sequential/no-retention distinctions and common claiming board are useful controls. Retain equal access to the base library and comparable model/tool access; only expose the verified shared library in the designated arm. Report a deterministic baseline on the same targets, with its own resource ledger. Model-family comparisons require a separate protocol from the same-model sharing intervention.

## Statement fidelity of the available 19-target set

These are algebraic surrogates over integers. Calling them 19 biological laws or the director's Mathlib scorecard would misstate the target.

| Targets | What the statements support | Required naming/scope distinction |
|---|---|---|
| T01–T12, Q01 | Integer expansions, determinant/trace inequalities, discriminant consequences, cutoff and integer-mode implications | Supply the mapping to real parameters and positive physical length. Negative determinant is a linear-mode criterion; no nonlinear pattern or PDE correspondence is proved by these statements. `Hurwitz` is defined as the trace/determinant sign predicate. |
| H01–H04 | Monotonicity and algebra of a defined `r*B-C`; H02 is a definitional equivalence | These do not derive Hamilton's rule from Price, transmission conditions or a regression decomposition. Useful arithmetic controls, not a biological derivation result. |
| D01 | A dove/hawk payoff inequality when V is positive | ESS is not defined in the target. State the payoff conclusion directly. |
| D02 `hawk_ess_iff_V_gt_C` | Strict resident-hawk payoff advantage iff C < V | The name overclaims ESS equivalence. At V=C=1, HH=DH=0, HD=2, DD=1. Against a small dove fraction ε, hawk payoff is 2ε and dove payoff ε; the secondary ESS condition can protect hawks despite equality against the resident. Rename to strict payoff advantage or formalize the actual ESS definition. |

Reference proofs compiling and altered statements rejecting under a particular proof do not by themselves establish biological correspondence. A failed proof replay is not a counterexample to the altered proposition. Include both true controls and genuinely false targets with checked distinguishing witnesses; assess type preservation separately from proof compilation.

The Admissible 21-record issues are unchanged: [earlier review](CODEX-21-CLAIM-FREEZE-REVIEW.md). In particular, no canonical target specified is different from impossibility; empirical validation differs from formalizability; prose bucket labels are not complete Lean targets; actual admissible-q determinant semantics must replace the conflicting continuum-envelope row. The compiled Price/Hamilton probe is prior exposed work, not a blinded score for the new experiment. Fisher's additive-genetic partial-change target remains unproved here.

## Concrete next handoff

Before a three-target pilot, the runner owner/director should provide one pushed revision containing:

- independently authored full types, definitions, parameter domains, assumptions, source-record mappings and permissible base-library imports;
- fixed registration, amendment history, experiment ID and input hashes, separating existing 19-target results from the new 21-record study;
- the repaired target-type verifier and controls above, dependency extraction, clean replay and atomic budget accounting;
- the matched arms, allocation/stop/order/repair/retry rules, failure accounting, exact score denominators and a declared policy for pilot exposure;
- an exact Mathlib/toolchain pin and a bounded launch command.

I can then give a target-by-target review against that candidate. This review gives no approval to start the new arms. It does not restart direction selection, cancel the existing historical experiment, or assert collective advantage/disadvantage from unavailable valid new results.
