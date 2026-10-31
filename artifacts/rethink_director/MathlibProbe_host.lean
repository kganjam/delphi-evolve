import Mathlib.Analysis.SpecialFunctions.Pow.Real
import Mathlib.Analysis.Calculus.Deriv.Basic
import Mathlib.Tactic

open Real

/-- Hill function: a real, biological object. -/
noncomputable def hill (K n x : ℝ) : ℝ := x ^ n / (K ^ n + x ^ n)

/-- Michaelis-Menten saturates strictly below Vmax for all finite positive substrate. -/
theorem mm_lt_vmax (Vmax Km S : ℝ) (hV : 0 < Vmax) (hK : 0 < Km) (hS : 0 ≤ S) :
    Vmax * S / (Km + S) < Vmax := by
  have hpos : 0 < Km + S := by linarith
  rw [div_lt_iff₀ hpos]
  nlinarith

/-- Turing: for a 2-species system the dispersion determinant is a quadratic in q
    whose instability band is bounded; here the exact algebraic core over ℚ-valued reals. -/
theorem turing_det (Du Dv a b c d q : ℝ) :
    (Du * Dv) * q ^ 2 - (Dv * a + Du * d) * q + (a * d - b * c)
      = (Du * q - a) * (Dv * q - d) - b * c := by ring

/-- The worked instance: det(q) = 10q^2 - 7q + 1 = (5q-1)(2q-1), so the band is 1/5 < q < 1/2. -/
example (q : ℝ) : (10:ℝ) * q ^ 2 - 7 * q + 1 = (5 * q - 1) * (2 * q - 1) := by ring

/-- On L = π the admissible Neumann modes are q = n², and none lies in (1/5, 1/2). -/
theorem no_unstable_mode_on_pi (n : ℕ) (hn : 1 ≤ n) :
    ¬ ((1:ℝ)/5 < (n:ℝ)^2 ∧ ((n:ℝ))^2 < 1/2) := by
  rintro ⟨_, h2⟩
  have : (1:ℝ) ≤ (n:ℝ) := by exact_mod_cast hn
  nlinarith
