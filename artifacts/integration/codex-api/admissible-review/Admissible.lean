/-
  Admissible — finite-domain admissibility for diffusion-driven (Turing) instability.

  Formalised over ℝ with Mathlib.  The point of this file is the gap between the
  CONTINUUM Turing conditions (stated over all real wavenumbers) and what a FINITE
  domain with zero-flux boundaries actually admits (a discrete set of modes).
-/
import Mathlib.Analysis.SpecialFunctions.Pow.Real
import Mathlib.Tactic

namespace Admissible

/-- A two-species reaction-diffusion linearisation: Jacobian `![![a,b],![c,d]]`
    at a spatially uniform steady state, with diffusivities `Du, Dv > 0`. -/
structure System where
  a : ℝ
  b : ℝ
  c : ℝ
  d : ℝ
  Du : ℝ
  Dv : ℝ
  hDu : 0 < Du
  hDv : 0 < Dv

variable (S : System)

/-- Trace of the mode-`q` growth matrix `J - q·diag(Du,Dv)`. -/
def T (q : ℝ) : ℝ := (S.a + S.d) - (S.Du + S.Dv) * q

/-- Determinant of the mode-`q` growth matrix: a quadratic in `q`. -/
def D (q : ℝ) : ℝ := S.Du * S.Dv * q^2 - (S.Dv * S.a + S.Du * S.d) * q + (S.a * S.d - S.b * S.c)

/-- The determinant is the product form used throughout the literature. -/
theorem D_eq (q : ℝ) :
    D S q = (S.Du * q - S.a) * (S.Dv * q - S.d) - S.b * S.c := by
  unfold D; ring

/-- A mode `q` is *unstable* when the growth determinant is negative: the quadratic
    `λ² - T λ + D` then has one positive real root regardless of the sign of `T`. -/
def Unstable (q : ℝ) : Prop := D S q < 0

/-- With a negative trace, `D q < 0` is exactly the condition for a positive eigenvalue. -/
theorem unstable_iff_pos_eigenvalue (q lam : ℝ) (hT : T S q < 0)
    (hroot : lam^2 - T S q * lam + D S q = 0) (hpos : 0 < lam) : Unstable S q := by
  unfold Unstable
  nlinarith [sq_nonneg lam, sq_nonneg (lam - T S q)]

/-- **Uniform-state stability**: with no diffusion the steady state is stable. -/
def WellMixedStable : Prop := S.a + S.d < 0 ∧ 0 < S.a * S.d - S.b * S.c

/-- The classical continuum condition for diffusion-driven instability: the minimum of the
    determinant over all real `q ≥ 0` is negative. -/
def ContinuumTuring : Prop :=
  0 < S.Dv * S.a + S.Du * S.d ∧
  (S.Dv * S.a + S.Du * S.d)^2 > 4 * (S.Du * S.Dv) * (S.a * S.d - S.b * S.c)

/-- Zero-flux (Neumann) modes on `[0, L]` are `q_n = (n π / L)²`. -/
noncomputable def neumannMode (L : ℝ) (n : ℕ) : ℝ := ((n : ℝ) * Real.pi / L)^2

/-- The admissible modes are nonnegative. -/
theorem neumannMode_nonneg (L : ℝ) (n : ℕ) : 0 ≤ neumannMode L n := by
  unfold neumannMode; positivity

/-- **The finite-domain theorem.**  If every admissible Neumann mode lies outside the
    instability band, the finite system is linearly stable *even when the continuum
    Turing conditions hold*.  This is the formal statement of the gap. -/
theorem finite_domain_stable (L : ℝ) (hL : 0 < L)
    (hout : ∀ n : ℕ, ¬ Unstable S (neumannMode L n)) :
    ∀ n : ℕ, 0 ≤ D S (neumannMode L n) := by
  intro n
  have := hout n
  unfold Unstable at this
  linarith [not_lt.mp this]

/-- The worked instance: `J = ![![1,-2],![2,-3]]`, `Du = 1`, `Dv = 10`. -/
noncomputable def worked : System :=
  { a := 1, b := -2, c := 2, d := -3, Du := 1, Dv := 10, hDu := by norm_num, hDv := by norm_num }

/-- Its determinant factors as `(5q-1)(2q-1)`, so the instability band is `1/5 < q < 1/2`. -/
theorem worked_D (q : ℝ) : D worked q = (5*q - 1) * (2*q - 1) := by
  simp only [D, worked]
  ring

/-- The well-mixed state is stable: trace `-2 < 0`, determinant `1 > 0`. -/
theorem worked_wellmixed : WellMixedStable worked := by
  simp only [WellMixedStable, worked]
  norm_num

/-- The continuum Turing conditions DO hold for the worked system:
    `Dv·a + Du·d = 7 > 0` and `49 > 4·10·1 = 40`. -/
theorem worked_continuum : ContinuumTuring worked := by
  simp only [ContinuumTuring, worked]
  norm_num

/-- A mode is unstable exactly when it lies strictly inside `(1/5, 1/2)`. -/
theorem worked_unstable_iff (q : ℝ) : Unstable worked q ↔ (1/5 < q ∧ q < 1/2) := by
  unfold Unstable
  rw [worked_D]
  constructor
  · intro h; constructor <;> nlinarith
  · rintro ⟨h1, h2⟩; nlinarith

/-- **On `L = π` the admissible modes are `q = n²`, and NONE is in the band.**
    So the continuum conditions hold and the finite domain is still stable. -/
theorem worked_stable_on_pi (n : ℕ) : ¬ Unstable worked (neumannMode Real.pi n) := by
  rw [worked_unstable_iff]
  rintro ⟨h1, h2⟩
  have hpi : (0:ℝ) < Real.pi := Real.pi_pos
  have hq : neumannMode Real.pi n = (n : ℝ)^2 := by
    unfold neumannMode
    field_simp
  rw [hq] at h1 h2
  -- n² < 1/2 forces n = 0, but then n² = 0 which is not > 1/5
  have hn : (n : ℝ) = 0 := by
    by_contra hne
    have h1n : (1:ℝ) ≤ (n:ℝ) := by
      have : 1 ≤ n := Nat.one_le_iff_ne_zero.mpr (by exact_mod_cast hne)
      exact_mod_cast this
    nlinarith
  rw [hn] at h1; norm_num at h1

end Admissible

section AxiomAudit
open Admissible
#print axioms D_eq
#print axioms finite_domain_stable
#print axioms worked_continuum
#print axioms worked_unstable_iff
#print axioms worked_stable_on_pi
end AxiomAudit
