import TuringScope.Basic
/-!
# Instance: J = [[1,-2],[2,-3]], Du = 1, Dv = 10, 1-D Neumann domain

`exModel` is the linearization used in the Python adapter and in `artifacts/turing_scope/`.
Domain length `L = (p/s)π`.  Short domain: `p = s = 1` (L = π).  Longer domain: `p = 2, s = 1` (L = 2π).
Every general lemma from `Basic` is instantiated by discharging its hypotheses; the sign facts are then
unbounded in the mode index `n`.
-/
namespace TuringScope

open Model

def exModel : Model := ⟨1, -2, 2, -3, 1, 10⟩

theorem ex_detJ : exModel.detJ = 1 := by decide
theorem ex_trJ : exModel.trJ = -2 := by decide
theorem ex_S : exModel.S = 7 := by decide

/-- For this J, the mode determinant factors: `det = (5N − M)(2N − M)`, i.e. `(5q − 1)(2q − 1)·M²`. -/
theorem ex_modeDet_factor (N M : Int) :
    exModel.modeDet N M = (5 * N - M) * (2 * N - M) := by
  unfold Model.modeDet exModel; grind

theorem ex_modeTr_formula (N M : Int) : exModel.modeTr N M = -2 * M - 11 * N := by
  unfold Model.modeTr exModel; grind

/-- The continuum unstable band, in integers: with `M > 0`, `det < 0 ↔ 1/5 < N/M < 1/2`. -/
theorem ex_det_neg_iff (N M : Int) (hM : 0 < M) :
    exModel.modeDet N M < 0 ↔ (M < 5 * N ∧ 2 * N < M) := by
  rw [ex_modeDet_factor]
  constructor
  · intro h
    by_cases h1 : 0 < 5 * N - M
    · have : 2 * N - M < 0 := by
        by_cases h2 : 0 ≤ 2 * N - M
        · have := Int.mul_nonneg (Int.le_of_lt h1) h2; omega
        · omega
      omega
    · have h1' : 5 * N - M ≤ 0 := by omega
      by_cases h2 : 0 < 2 * N - M
      · have := Int.mul_nonneg (by omega : 0 ≤ -(5 * N - M)) (Int.le_of_lt h2)
        have : -(5 * N - M) * (2 * N - M) = -((5 * N - M) * (2 * N - M)) := by grind
        omega
      · have := Int.mul_nonneg (by omega : 0 ≤ -(5 * N - M)) (by omega : 0 ≤ -(2 * N - M))
        have : -(5 * N - M) * -(2 * N - M) = (5 * N - M) * (2 * N - M) := by grind
        omega
  · rintro ⟨h1, h2⟩
    exact Int.mul_neg_of_pos_of_neg (by omega) (by omega)

/-- Mode `n` on `L = (p/s)π` is determinant-negative iff `p² < 5 n² s²` and `2 n² s² < p²`. -/
theorem ex_mode_det_neg_iff (p s : Int) (hp : 0 < p) (n : Nat) :
    exModel.modeDet (modeN s n) (modeM p) < 0 ↔ (p ^ 2 < 5 * ((n : Int) ^ 2 * s ^ 2) ∧ 2 * ((n : Int) ^ 2 * s ^ 2) < p ^ 2) := by
  have hM : 0 < modeM p := by unfold modeM; have := Int.mul_pos hp hp; grind
  have := ex_det_neg_iff (modeN s n) (modeM p) hM
  unfold modeN modeM at *
  exact this

/-! ### Short domain L = π  (p = s = 1): all modes stable, for every n -/

theorem short_all_modes_stable : ∀ n : Nat, ModeStable exModel 1 1 n := by
  intro n
  cases n with
  | zero => exact mode_zero_stable exModel (by decide) (by decide) (by decide)
  | succ k =>
    exact neumann_tail_hurwitz exModel (by decide) (by decide) (by decide) (by decide)
      (by decide) (by decide) 1 (by decide) (k + 1) (by omega)

/-! ### Longer domain L = 2π  (p = 2, s = 1): exactly mode n = 1 is unstable -/

theorem long_mode1_det : exModel.modeDet (modeN 1 1) (modeM 2) = -2 := by decide
/-- Rationally: `det A(1/4) = -2 / 4² = -1/8`. -/
theorem long_mode1_unstable : ¬ ModeStable exModel 2 1 1 := by
  intro ⟨_, h⟩
  have := long_mode1_det
  omega

theorem long_modes_ge2_stable : ∀ n : Nat, 2 ≤ n → ModeStable exModel 2 1 n :=
  neumann_tail_hurwitz exModel (by decide) (by decide) (by decide) (by decide)
    (by decide) (by decide) 2 (by decide)

theorem long_mode0_stable : ModeStable exModel 2 1 0 :=
  mode_zero_stable exModel (by decide) (by decide) (by decide)

/-- On `L = 2π`, a Neumann mode is unstable (Routh–Hurwitz sense) iff `n = 1`. -/
theorem long_unstable_iff (n : Nat) : ¬ ModeStable exModel 2 1 n ↔ n = 1 := by
  constructor
  · intro h
    by_cases h0 : n = 0
    · subst h0; exact absurd long_mode0_stable h
    · by_cases h1 : n = 1
      · exact h1
      · exact absurd (long_modes_ge2_stable n (by omega)) h
  · intro h; subst h; exact long_mode1_unstable

/-- Sign-change certificate for the positive real eigenvalue at `L = 2π`, `n = 1`. -/
theorem long_mode1_sign_change :
    ∃ Λ : Int, 0 < Λ ∧ (0 : Int) ^ 2 - exModel.modeTr (modeN 1 1) (modeM 2) * 0
      + exModel.modeDet (modeN 1 1) (modeM 2) < 0 ∧
      0 < Λ ^ 2 - exModel.modeTr (modeN 1 1) (modeM 2) * Λ + exModel.modeDet (modeN 1 1) (modeM 2) :=
  charpoly_sign_change _ _ (by rw [long_mode1_det]; decide)

/-! ### The applicability statement

The continuum band is non-empty (`q = 1/3` has negative determinant), yet on `L = π` there is no admissible
unstable mode, while on `L = 2π` there is one. The only change between the two conclusions is the domain. -/
theorem band_nonempty : ∃ N M : Int, 0 < M ∧ 0 ≤ N ∧ exModel.modeDet N M < 0 :=
  ⟨1, 3, by decide, by decide, by decide⟩

theorem domain_changes_answer :
    (∃ N M : Int, 0 < M ∧ 0 ≤ N ∧ exModel.modeDet N M < 0) ∧
    (∀ n : Nat, ModeStable exModel 1 1 n) ∧
    (∃ n : Nat, ¬ ModeStable exModel 2 1 n) :=
  ⟨band_nonempty, short_all_modes_stable, ⟨1, long_mode1_unstable⟩⟩

end TuringScope
