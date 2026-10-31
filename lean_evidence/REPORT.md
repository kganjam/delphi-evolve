# Lean node evidence for the scorecard (corpus session, read-only support for the critic)

Written 2026-10-31 (Seattle PDT), model Claude Sonnet 5.5. Every "compiled" statement below was produced by me in this
session with `lake env lean` against the pinned toolchain (Lean 4.35.0, Mathlib rev `56a00585…`, the shared cache at
`/data/artifacts/mathlib-probe`), inside `systemd-run --user --scope -p MemoryMax=4G -p MemorySwapMax=0 -p TasksMax=128`.
Logs: `lean_evidence/outputs/`. Scratch proofs I added are in `lean_evidence/AdmissibleEvidence.lean` and
`lean_evidence/TuringScopeExtra.lean`. **They are my extensions, not part of any reviewed artifact.**

Rule I applied (from the ledger): "compiles + clean axioms" is not evidence. For each node I say what it rules out, and
whether a mutant fails. Where I give a mutant, I distinguish (i) the retained-proof mutant *fails to elaborate* from
(ii) a proof that the mutated statement is *false* (`*_neg`, which compiles). Only (ii) shows the mutant statement is wrong;
(i) can fail for an incidental reason, and I say where that happened.

## 0. What I did NOT do
* I did not compare any Lean statement to the Delphi record text, or to the source papers. Statement-to-record fidelity is
  unreviewed by me. I read the Lean docstrings and checked that the Lean says what the docstring says (it sometimes does not, §A3).
* I did not read the Delphi records, the bench, or any Python oracle. Nothing here speaks to the bench items.
* I did not compile atlas-lean. I fetched `Selection.lean` at the repo head (`0da94bf`, 2026-10-31T06:12:49Z) and read it (§D).
* I did not search other branches for Lean files. "No Lean node" below means none in the four artifacts I examined.

## A. `delphi-frontier` `lean/Admissible.lean` (commit `636919a`, sha256 `d63c4d60e63e81d45bec7bd68d70caee6e0a83f4f4a51566eb6983d29c42fbce`)

Reproduced: exit 0, one `push_neg` deprecation warning, no `sorry`. The file's own audit covers 7 of its 11 theorems; I audited
all 11 plus my additions: every one depends on `propext, Classical.choice, Quot.sound` only (35 audited names, 0 `sorryAx`).
**The repo ships no mutant files and no CI.** The README's "three mutation tests" cannot be reproduced from the repo; I recreated
them (M7, M4b, M9 below). Error counts differ from the README's, because my mutants are not their files.

What the file models: a 2x2 matrix `J - q·diag(Du,Dv)` over ℝ, with `q` ranging over the *defined* set `(nπ/L)²`.
`ModeStable := T<0 ∧ 0<D` and `ContinuumTuring` are **definitions**. Nothing connects `neumannMode` to a PDE, a Laplacian
eigenproblem, or zero-flux boundary conditions. Nothing is two-dimensional or nonlinear. Nothing is biological.

| Theorem | What it rules out | Mutant (expected: fails) and falsity proof | Verdict |
|---|---|---|---|
| `D_eq` | a determinant that is not `(Du q−a)(Dv q−d)−bc` | M8 flips `+bc`: fails; `M8_neg` compiles | proved; `unfold; ring`, definitional |
| `unstable_iff_pos_eigenvalue` | a positive real eigenvalue with `T<0` and `D≥0` | M1 drops `hT`: fails; `M1_neg` compiles (counterexample diag(1,1), q=0) | proved, **one direction only** despite "iff" in the name |
| `neumannMode_nonneg` | negative `q` | none | proved; `positivity`, no content beyond the definition |
| `trace_neg_of_wellmixed` | a nonnegative mode with `T≥0` when the well-mixed trace is negative | M3 drops `q≥0`: fails; `M3_neg` compiles (`T worked (-1) > 0`) | proved, non-vacuous |
| `finite_domain_linearly_stable` | stable well-mixed + all mode dets `>0` but some mode with `T≥0` or `D≤0` | M2 is the original `¬(D<0)` bug: fails with a type mismatch; `M2_neg` compiles: a system with a mode where `D=0`, `¬Unstable` at every mode, and `¬ModeStable` (L=π√5, n=1) | proved, **but see A1** |
| `real_eigenvalue_neg_of_modeStable` | a nonnegative *real* eigenvalue when `T<0`, `D>0` | M6 uses `D≥0`: fails; `M6_neg` compiles (λ=0, q=1/5) | proved; real roots only |
| `worked_D`, `worked_wellmixed` | arithmetic on one system | M10 wrong factor: fails, `M10_neg`; M9 flipped trace sign: fails, `M9_neg` | proved |
| `worked_continuum` | that the continuum inequalities hold for the worked system (7>0, 49>40) | M7 sets `Dv:=1`: fails; `M7_neg` compiles | proved; it only checks two numeric inequalities of a *definition* |
| `worked_unstable_iff` | any unstable `q` outside `(1/5,1/2)` and any stable `q` inside | M4 closed band: fails, `M4_neg`; M4b band `1/6<q`: fails, `M4b_neg` | proved, real iff |
| `worked_stable_on_pi` | an **unstable** mode at L=π | M5 (L=2π, same proof shape): fails at an incidental `field_simp` step; **the real evidence is `M5_neg`**, which compiles, and `worked_unstable_on_2pi` (mine) | proved, but concludes `¬Unstable`, i.e. `D≥0`, **not** stability |

### A1. `finite_domain_linearly_stable` is a near-tautology
Its conclusion is `⟨trace_neg…, hdet n⟩`: the second conjunct is the hypothesis, passed through. The only derived content
is `trace_neg_of_wellmixed`. The hypothesis is satisfiable and the theorem applies: I proved
`worked_hdet_pi : ∀ n, 0 < D worked (neumannMode π n)` and so `worked_modeStable_pi : ∀ n, ModeStable worked (neumannMode π n)`.
Those two are **not in the repo**. In the repo, L=π gives only `¬Unstable`.

### A2. Things the repo does not prove, which I proved in scratch (all compile, axioms clean, in `AdmissibleEvidence.lean`)
* `pos_eigenvalue_of_unstable`: converse of `unstable_iff_pos_eigenvalue` (`D<0` ⇒ a positive root exists). Without it the name "iff" is an overclaim.
* `complex_root_re_neg`: for `T<0, D>0`, every **complex** root of `λ²−Tλ+D` has negative real part.
* `continuum_imp_exists` and `exists_imp_continuum`: `ContinuumTuring S` ⇒ some `q>0` with `D<0`, and the converse given well-mixed stability. The repo's `ContinuumTuring` is an algebraic definition with no theorem tying it to "exists an unstable q".
* `continuum_needs_unequal`: well-mixed stable ∧ `ContinuumTuring` ⇒ `Du≠Dv`. The record states "requires Du≠Dv"; the repo has no such theorem. The well-mixed hypothesis is needed: `M11` drops it and fails, `M11_neg` gives `Du=Dv` with `ContinuumTuring`.
* `ratio11_*`: ledger row 3. `J=[[1,−1],[1011/1000,−101/100]]`, `Du=1`, `Dv=11/10`, `L=5π`, mode 1 gives well-mixed stable, `ContinuumTuring`, `D = −21/25000`, `Unstable`. **The ledger calls this a "Lean counterexample", but no Lean file in `delphi-frontier` or `admissible-seed` contains it** (I checked `git log -S` on both repos; the ledger commit touches only `ledger/README.md`). It is now compiled, by me. I inferred `Du=1, Dv=11/10`; the match to `−21/25000` confirms it.
* `worked_unstable_on_2pi`: the worked system has an unstable Neumann mode at L=2π. The README's "unstable at 3π/2, 2π, stable again at 5π/2, unstable at 3π, 4π" is from Python exact arithmetic, **not** Lean. I proved only L=π (stable) and L=2π (unstable).

### A3. Docstring versus theorem
The docstring of `finite_domain_linearly_stable` says "both eigenvalues have negative real part". The proved conclusion is `T<0 ∧ 0<D` (the definition of `ModeStable`), plus the real-root-only lemma. The complex case is closed only by my `complex_root_re_neg`.

## B. `rethink-critic` `turing_scope/lean` (HEAD `0c2d4f2`, tree clean; the artifact the scorecard cites for turing-ddi)
Core Lean only, no Mathlib, integers, `L=(p/s)π`. I deleted `.lake` and rebuilt: `lake build` exit 0. The shipped `Audit.lean` covers 9
theorems; `outputs/turingscope_fullaudit.txt` audits 7 more of the file's theorems (`modeDet_pos_of_tail`, `modeTr_neg`, `mode_zero_stable`, `ex_mode_det_neg_iff`, `long_modes_ge2_stable`, `long_mode1_unstable`, `band_nonempty`) plus 3 repeats: all `propext, Classical.choice, Quot.sound`, except `long_mode1_unstable` (`propext, Quot.sound`)
and `band_nonempty` (none). No `sorry`, `native_decide` or `axiom`.
* Proved for **every** integer model: dispersion identities `modeTr_eq`, `modeDet_eq`; `modeTr_neg`; `neumann_tail_hurwitz` (all modes `n≥n0` stable, unbounded in `n`, under `hcut`); `mode_zero_stable`.
* Proved for the worked instance: `short_all_modes_stable` (**every** mode stable at L=π, a strict Hurwitz statement, stronger than Admissible's `worked_stable_on_pi`); `long_unstable_iff` (at L=2π a mode is unstable **iff** `n=1`); `domain_changes_answer`; `long_mode1_sign_change`, an integer sign-change certificate for a positive root, with the IVT step *not* formalized.
* Shipped mutants: control exit 0; M1 (reaction law), M2 (`Dv:=1`), M3 (L=π) exit 1, each with "`decide` proved that the proposition [is false]". These are the strong kind: the mutated *claim* is shown false.
* My extra checks (`TuringScopeExtra.lean`): dropping `detJ>0` from `mode_zero_stable` fails (X1) and `X1_neg` compiles (counterexample `detJ=−7`); `hcut` is load-bearing (`X2_neg`: the tail claim at `n0=1`, L=2π is false).
* **Not formalized (its own header says so):** Routh–Hurwitz equivalence (`Hurwitz` is a definition), real/complex eigenvalues, the IVT, the PDE, mode quantisation from a boundary problem, any nonlinear or biological claim. Its statement of *what a mode is* is a docstring, mirrored by `adapter.py`, not a theorem.

## C. Price / Hamilton (two separate artifacts)
**C1. `rethink-critic/lean_price/Price.lean`** (sha256 `c429c8f4…`; last touched `5eaceb8`). exit 0; `price`, `queller`, `hamilton_form` clean axioms.
* `price`: `E w·(z̄′−E z) = Cov(w,z)+E(w·dz)` when `Σw≠0`. Rules out a missing or sign-flipped transmission term (`PriceMutant`: fails; its statement is false whenever `E(w·dz)≠0`).
* `queller`, `hamilton_form`: `Cov(w,z) = Var(z)·(r·b−c)` for **exactly linear** `w` with `Cov(e,z)=0`, `r := Cov(y,z)/Var(z)` by definition. `PriceMutant2` (sign of the partner term) fails at the `linarith` step in `queller`, which is where the sign enters.
* **Not stated in this file:** any sign equivalence, any link from `price` to `hamilton_form` (so no statement that a trait/frequency *change* is positive iff `rb−c>0`), and no Fisher theorem. The README says the same about Fisher. Definitions are the critic's own, not Mathlib's `covariance`.

**C2. `codex-api/experiments/price_probe/Price.lean`** (sha256 `a5d38f13…`, equals the receipt's `source_sha256` in `artifacts/integration/codex-api/price-probe.json`; last touched `3ea28a2`). I re-ran Codex's mutants and witnesses: original exit 0; both mutants exit 1; witnesses exit 0. Axioms clean for all 9 theorems.
* `hamilton_regression` is the **stronger** Hamilton node: given perfect transmission, `∑p=1`, `Var(z)>0`, mean fitness `>0`, orthogonal residual, `Cov(partner,z)=r·Var(z)`: `0 < descendantMean − mean ↔ 0 < r·b − c`. It combines `selection_only` with the covariance identity. **The scorecard cites C1 for hamilton-rule, not C2.** C2 is the node that actually states the sign equivalence.
* Mutant honesty: the transmission-sign mutant fails inside `price` (intended). The **cost-sign mutant fails at a `change` tactic, a pattern mismatch**, not at the logic. That alone does not show `r·b+c` is false. What does is the witness `reversed_cost_is_false`, a single two-type instance. `residual_assumption_is_needed` and `transmission_is_needed` also compile.
* `fitness_selection` is the `z=w` case: `descendantMean p w w − mean p w = cov p w w / mean p w` (total variance, perfect transmission of the assigned fitness). **Not additive-genetic Fisher**, as Codex states.
* `z` is an arbitrary real trait, and `r` is defined by `Cov(partner,z)=r·Var(z)`. Neither file proves that this `r` is Hamilton's pedigree relatedness, or says anything about allele frequency specifically. Any such reading is an interpretation, not a theorem.

## D. atlas-lean `MathlibExt/Biology/PopulationGenetics/Selection.lean` (read, not compiled)
224 lines, no `sorry`. `meanFitness_select_sub`: haploid, `w̄(p′)−w̄(p) = Var_p(w)/w̄(p)` (its docstring: "Fisher's diploid statement in terms of the additive genetic variance is not covered here"). `price`: same finite-population Price equation. The critic's description is accurate. I cannot vouch that it compiles. It uses `module`/`public import` syntax.

## E. Row-by-row (only the rows with a Lean question)
| claim | Lean node proved today | not proved |
|---|---|---|
| turing-ddi | A and B (two independent formalizations of one instance) | PDE equivalence, mode quantisation, nonlinear patterning, biology. The record's "iff" is proved only in my scratch (A2). The scorecard row cites only B. |
| turing-wavelength | **none** in these four artifacts | `λ_c = 2π/k_c`, fastest-growing admissible mode |
| hamilton-rule | C2 `hamilton_regression` (sign iff, conditional); C1 `hamilton_form` (identity) | real populations; non-linear fitness; the pedigree meaning of `r` |
| fisher-ftns | Price identity (C1, C2, atlas-lean); haploid `Var(w)/w̄` form (C2 `fitness_selection`, atlas-lean) | **additive** genetic variance, diploid, multilocus; no node anywhere in my four artifacts + atlas |
| fisher-kpp-speed, kimura-fixation-probability, maynardsmith-hawk-dove | **none** | everything |
| the 12 (e) rows | **none** | everything |

## F. Reproduce
```
cd /data/artifacts/mathlib-probe   # pinned Mathlib cache
systemd-run --user --scope -p MemoryMax=4G -p MemorySwapMax=0 -p TasksMax=128 -p RuntimeMaxSec=580 \
  lake env lean -j2 <abs path>/lean_evidence/AdmissibleEvidence.lean    # exit 1 by design: the 12 mutant theorems M1..M11 must error; every other theorem must print the 3 standard axioms
```
Expected errors, by marker name: `M1_drop_trace_hyp, M2_not_lt_original_bug, M3_drop_q_nonneg, M4_closed_band, M4b_wide_band_1_6, M5_wrong_L_2pi (2 errors), M6_nonstrict_det, M7_equal_diffusivity, M8_flip_bc_sign, M9_flip_trace, M10_wrong_factor, M11_drop_wellmixed_from_Du_ne_Dv`. Nothing else may error. `grep -c sorryAx` of the log must be 0.

## G. Limits of this report
Single reader. The `*_neg` theorems and the scratch proofs are mine and unreviewed by a second reader. Mutants test sensitivity to the changes I chose, not all changes. I did not check whether the Lean `Unstable`/`ModeStable` matches the bench's operational definition of "admissible unstable mode".
