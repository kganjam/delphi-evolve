import TuringScope
open TuringScope

-- X1: mutant of mode_zero_stable with the hypothesis detJ>0 dropped (retained proof shape). Must FAIL.
theorem X1 (m : Model) (htr : m.trJ < 0) {p s : Int} (hp : 0 < p) : ModeStable m p s 0 := by
  have hM : 0 < modeM p := by unfold modeM; have := Int.mul_pos hp hp; grind
  have hN : modeN s 0 = 0 := by unfold modeN; simp
  unfold ModeStable
  rw [hN, Model.modeTr_eq, Model.modeDet_eq]
  have h1 : m.trJ * modeM p < 0 := Int.mul_neg_of_neg_of_pos htr hM
  constructor <;> grind

-- X1_neg: the dropped-hypothesis statement is FALSE (detJ = -7, trJ = -2): must COMPILE.
theorem X1_neg : ¬ (∀ (m : Model) (p s : Int), 0 < p → m.trJ < 0 → ModeStable m p s 0) := by
  intro h
  have := h ⟨1, 2, 2, -3, 1, 10⟩ 1 1 (by decide) (by decide)
  revert this
  decide

-- X2_neg: the cutoff hypothesis `hcut` of neumann_tail_hurwitz is load-bearing: without it the tail
-- claim (n0 = 1, L = 2π) is FALSE because mode 1 is unstable there. Must COMPILE.
theorem X2_neg : ¬ (∀ n : Nat, 1 ≤ n → ModeStable exModel 2 1 n) :=
  fun h => long_mode1_unstable (h 1 (Nat.le_refl 1))

-- X3: the strict claim at L=π is exactly "all modes Hurwitz", checked on a concrete large mode.
example : ModeStable exModel 1 1 1000 := by decide
-- X3 control: at L=2π mode 1 is not stable, mode 2 is.
example : ¬ ModeStable exModel 2 1 1 := by decide
example : ModeStable exModel 2 1 2 := by decide
