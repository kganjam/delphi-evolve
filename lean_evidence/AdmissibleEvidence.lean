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

/-- Linear asymptotic stability of a 2x2 mode: negative trace and positive determinant.
    This is the real stability predicate; `¬ Unstable` alone is strictly weaker. -/
def ModeStable (q : ℝ) : Prop := T S q < 0 ∧ 0 < D S q

/-- The trace is negative at EVERY nonnegative mode whenever the well-mixed trace is.
    Not vacuous: it uses `Du + Dv > 0` and `q ≥ 0`. -/
theorem trace_neg_of_wellmixed (hwm : WellMixedStable S) {q : ℝ} (hq : 0 ≤ q) :
    T S q < 0 := by
  have hD : 0 < S.Du + S.Dv := by have := S.hDu; have := S.hDv; linarith
  have h1 : S.a + S.d < 0 := hwm.1
  have h2 : 0 ≤ (S.Du + S.Dv) * q := by positivity
  unfold T; linarith

/-- **The finite-domain theorem, stated as actual linear stability.**
    If the well-mixed state is stable and every admissible Neumann mode has STRICTLY POSITIVE
    growth determinant, then every admissible mode is linearly asymptotically stable — both
    eigenvalues have negative real part.  The determinant hypothesis is a genuine assumption
    about the mode set, and the trace conclusion is derived, not assumed. -/
theorem finite_domain_linearly_stable (L : ℝ)
    (hwm : WellMixedStable S)
    (hdet : ∀ n : ℕ, 0 < D S (neumannMode L n)) :
    ∀ n : ℕ, ModeStable S (neumannMode L n) := by
  intro n
  exact ⟨trace_neg_of_wellmixed S hwm (neumannMode_nonneg L n), hdet n⟩

/-- Both eigenvalues of a 2x2 matrix with negative trace and positive determinant have
    negative real part: any real eigenvalue is negative.  This is what `ModeStable` buys. -/
theorem real_eigenvalue_neg_of_modeStable {q lam : ℝ} (h : ModeStable S q)
    (hroot : lam^2 - T S q * lam + D S q = 0) : lam < 0 := by
  obtain ⟨hT, hDpos⟩ := h
  by_contra hge
  push_neg at hge
  nlinarith [sq_nonneg lam]

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


/- ===== EVIDENCE EXTENSION (corpus session; NOT part of delphi-frontier) ===== -/

-- @@ N1_worked_hdet_pi
theorem worked_hdet_pi : ∀ n : ℕ, 0 < D worked (neumannMode Real.pi n) := by
  intro n
  have hpi : (0:ℝ) < Real.pi := Real.pi_pos
  have hq : neumannMode Real.pi n = (n : ℝ)^2 := by
    unfold neumannMode
    field_simp
  rw [hq, worked_D]
  rcases Nat.eq_zero_or_pos n with h | h
  · subst h; norm_num
  · have h1 : (1:ℝ) ≤ (n:ℝ) := by exact_mod_cast h
    have h2 : (1:ℝ) ≤ (n:ℝ)^2 := by nlinarith
    exact mul_pos (by linarith) (by linarith)

-- @@ N1b_worked_modeStable_pi
theorem worked_modeStable_pi : ∀ n : ℕ, ModeStable worked (neumannMode Real.pi n) :=
  finite_domain_linearly_stable worked Real.pi worked_wellmixed worked_hdet_pi

-- @@ N2_unstable_iff_hyps_satisfiable
theorem N2_hyps_satisfiable :
    ∃ q lam : ℝ, T worked q < 0 ∧ lam^2 - T worked q * lam + D worked q = 0 ∧ 0 < lam
      ∧ Unstable worked q := by
  refine ⟨25/108, 1/54, ?_, ?_, ?_, ?_⟩ <;> norm_num [T, D, Unstable, worked]

-- @@ N2b_converse_pos_eigenvalue
theorem pos_eigenvalue_of_unstable {q : ℝ} (hD : D S q < 0) :
    ∃ lam : ℝ, 0 < lam ∧ lam^2 - T S q * lam + D S q = 0 := by
  have hdisc : 0 ≤ T S q ^ 2 - 4 * D S q := by nlinarith [sq_nonneg (T S q)]
  set s := Real.sqrt (T S q ^ 2 - 4 * D S q) with hs
  have hs2 : s ^ 2 = T S q ^ 2 - 4 * D S q := Real.sq_sqrt hdisc
  have hs0 : 0 ≤ s := Real.sqrt_nonneg _
  refine ⟨(T S q + s) / 2, ?_, ?_⟩
  · by_contra hle
    push_neg at hle
    have h1 : s ≤ - T S q := by linarith
    nlinarith
  · nlinarith [hs2]

-- @@ N3a_continuum_implies_unstable_mode
theorem continuum_imp_exists (h : ContinuumTuring S) : ∃ q : ℝ, 0 < q ∧ D S q < 0 := by
  obtain ⟨h1, h2⟩ := h
  have hDD : 0 < S.Du * S.Dv := mul_pos S.hDu S.hDv
  have hu : S.Du ≠ 0 := S.hDu.ne'
  have hv : S.Dv ≠ 0 := S.hDv.ne'
  refine ⟨(S.Dv * S.a + S.Du * S.d) / (2 * (S.Du * S.Dv)), by positivity, ?_⟩
  have key : D S ((S.Dv * S.a + S.Du * S.d) / (2 * (S.Du * S.Dv)))
      = (4 * (S.Du * S.Dv) * (S.a * S.d - S.b * S.c) - (S.Dv * S.a + S.Du * S.d)^2)
        / (4 * (S.Du * S.Dv)) := by
    unfold D
    field_simp
    ring
  rw [key]
  apply div_neg_of_neg_of_pos
  · linarith
  · positivity

-- @@ N3b_unstable_mode_implies_continuum
theorem exists_imp_continuum (hwm : WellMixedStable S) {q : ℝ} (hq : 0 ≤ q) (hD : D S q < 0) :
    ContinuumTuring S := by
  obtain ⟨_, hdet⟩ := hwm
  have hDD : 0 < S.Du * S.Dv := mul_pos S.hDu S.hDv
  unfold D at hD
  have hs : 0 < S.Dv * S.a + S.Du * S.d := by
    by_contra hneg
    push_neg at hneg
    nlinarith [mul_nonneg hDD.le (sq_nonneg q), mul_nonneg (neg_nonneg.mpr hneg) hq]
  refine ⟨hs, ?_⟩
  nlinarith [sq_nonneg (2 * (S.Du * S.Dv) * q - (S.Dv * S.a + S.Du * S.d)),
    mul_pos hDD (neg_pos.mpr hD)]

-- @@ N4_complex_root_re_neg
theorem complex_root_re_neg {T0 D0 : ℝ} (hT : T0 < 0) (hD : 0 < D0) (lam : ℂ)
    (hroot : lam ^ 2 - (T0 : ℂ) * lam + (D0 : ℂ) = 0) : lam.re < 0 := by
  have hre := congrArg Complex.re hroot
  have him := congrArg Complex.im hroot
  simp [pow_two, Complex.mul_re, Complex.mul_im] at hre him
  by_cases hy : lam.im = 0
  · rw [hy] at hre
    by_contra hge
    push_neg at hge
    nlinarith [sq_nonneg lam.re]
  · have h2 : 2 * lam.re = T0 := by
      have : lam.im * (2 * lam.re - T0) = 0 := by linarith
      rcases mul_eq_zero.mp this with h | h
      · exact absurd h hy
      · linarith
    linarith

-- @@ N5_ledger3_ratio_1p1
noncomputable def ratio11 : System :=
  { a := 1, b := -1, c := 1011/1000, d := -101/100, Du := 1, Dv := 11/10,
    hDu := by norm_num, hDv := by norm_num }

theorem ratio11_wellmixed : WellMixedStable ratio11 := by
  norm_num [WellMixedStable, ratio11]

theorem ratio11_continuum : ContinuumTuring ratio11 := by
  norm_num [ContinuumTuring, ratio11]

theorem ratio11_mode1_5pi :
    neumannMode (5 * Real.pi) 1 = 1/25 := by
  have hpi : (0:ℝ) < Real.pi := Real.pi_pos
  unfold neumannMode
  field_simp
  norm_num

theorem ratio11_unstable :
    D ratio11 (neumannMode (5 * Real.pi) 1) = -21/25000
      ∧ Unstable ratio11 (neumannMode (5 * Real.pi) 1) := by
  rw [ratio11_mode1_5pi]
  constructor <;> norm_num [D, Unstable, ratio11]

-- @@ N6_two_pi_has_unstable_mode
theorem worked_unstable_on_2pi : Unstable worked (neumannMode (2 * Real.pi) 1) := by
  have hpi : (0:ℝ) < Real.pi := Real.pi_pos
  have hq : neumannMode (2 * Real.pi) 1 = 1/4 := by
    unfold neumannMode
    field_simp
    norm_num
  rw [worked_unstable_iff, hq]
  norm_num


-- @@ N7_continuum_needs_Du_ne_Dv
theorem continuum_needs_unequal (hwm : WellMixedStable S) (h : ContinuumTuring S) :
    S.Du ≠ S.Dv := by
  intro heq
  have h1 := h.1
  have h2 := hwm.1
  rw [← heq] at h1
  nlinarith [mul_pos S.hDu (neg_pos.mpr h2)]


/- ===================== MUTANTS: each M<k> must FAIL to elaborate;
   each M<k>_neg must COMPILE (the mutated statement is false) ===================== -/

-- @@ M1_drop_trace_hyp
theorem M1 (q lam : ℝ) (hroot : lam^2 - T S q * lam + D S q = 0) (hpos : 0 < lam) :
    Unstable S q := by
  unfold Unstable
  nlinarith [sq_nonneg lam, sq_nonneg (lam - T S q)]

-- @@ M1_neg
theorem M1_neg : ¬ (∀ (S : System) (q lam : ℝ),
    lam^2 - T S q * lam + D S q = 0 → 0 < lam → Unstable S q) := by
  intro h
  have := h ⟨1, 0, 0, 1, 1, 1, by norm_num, by norm_num⟩ 0 1
    (by norm_num [T, D]) (by norm_num)
  norm_num [Unstable, D] at this

-- @@ M2_not_lt_original_bug
theorem M2 (L : ℝ) (hwm : WellMixedStable S)
    (hdet : ∀ n : ℕ, ¬ D S (neumannMode L n) < 0) :
    ∀ n : ℕ, ModeStable S (neumannMode L n) := by
  intro n
  exact ⟨trace_neg_of_wellmixed S hwm (neumannMode_nonneg L n), hdet n⟩

-- @@ M2_neg
theorem M2_neg :
    ∃ L : ℝ, WellMixedStable worked ∧ (∀ n : ℕ, ¬ Unstable worked (neumannMode L n))
      ∧ ¬ ModeStable worked (neumannMode L 1) := by
  have hpi : (0:ℝ) < Real.pi := Real.pi_pos
  have h5 : (0:ℝ) < Real.sqrt 5 := Real.sqrt_pos.mpr (by norm_num)
  have hs : Real.sqrt 5 ^ 2 = 5 := Real.sq_sqrt (by norm_num)
  have hq : ∀ n : ℕ, neumannMode (Real.pi * Real.sqrt 5) n = (n:ℝ)^2 / 5 := by
    intro n
    unfold neumannMode
    field_simp
    rw [hs]
  refine ⟨Real.pi * Real.sqrt 5, worked_wellmixed, ?_, ?_⟩
  · intro n
    rw [worked_unstable_iff, hq]
    rintro ⟨h1, h2⟩
    have hn2 : 2 ≤ n := by
      by_contra hlt
      push_neg at hlt
      interval_cases n <;> norm_num at h1
    have : (2:ℝ) ≤ (n:ℝ) := by exact_mod_cast hn2
    nlinarith
  · rw [hq]
    rintro ⟨_, h⟩
    rw [worked_D] at h
    norm_num at h

-- @@ M3_drop_q_nonneg
theorem M3 (hwm : WellMixedStable S) (q : ℝ) : T S q < 0 := by
  have hD : 0 < S.Du + S.Dv := by have := S.hDu; have := S.hDv; linarith
  have h1 : S.a + S.d < 0 := hwm.1
  unfold T
  nlinarith

-- @@ M3_neg
theorem M3_neg : ¬ (T worked (-1) < 0) := by
  norm_num [T, worked]

-- @@ M4_closed_band
theorem M4 (q : ℝ) : Unstable worked q ↔ (1/5 ≤ q ∧ q ≤ 1/2) := by
  unfold Unstable
  rw [worked_D]
  constructor
  · intro h; constructor <;> nlinarith
  · rintro ⟨h1, h2⟩; nlinarith

-- @@ M4_neg
theorem M4_neg : ¬ (∀ q : ℝ, Unstable worked q ↔ (1/5 ≤ q ∧ q ≤ 1/2)) := by
  intro h
  have := (h (1/5)).mpr ⟨le_refl _, by norm_num⟩
  rw [Unstable, worked_D] at this
  norm_num at this

-- @@ M4b_wide_band_1_6
theorem M4b (q : ℝ) : Unstable worked q ↔ (1/6 < q ∧ q < 1/2) := by
  unfold Unstable
  rw [worked_D]
  constructor
  · intro h; constructor <;> nlinarith
  · rintro ⟨h1, h2⟩; nlinarith

-- @@ M4b_neg
theorem M4b_neg : ¬ (∀ q : ℝ, Unstable worked q ↔ (1/6 < q ∧ q < 1/2)) := by
  intro h
  have := (h (3/16)).mpr ⟨by norm_num, by norm_num⟩
  rw [Unstable, worked_D] at this
  norm_num at this

-- @@ M5_wrong_L_2pi
theorem M5 (n : ℕ) : ¬ Unstable worked (neumannMode (2 * Real.pi) n) := by
  rw [worked_unstable_iff]
  rintro ⟨h1, h2⟩
  have hpi : (0:ℝ) < Real.pi := Real.pi_pos
  have hq : neumannMode (2 * Real.pi) n = (n : ℝ)^2 := by
    unfold neumannMode
    field_simp
  rw [hq] at h1 h2
  nlinarith

-- @@ M5_neg
theorem M5_neg : ¬ (∀ n : ℕ, ¬ Unstable worked (neumannMode (2 * Real.pi) n)) :=
  fun h => h 1 worked_unstable_on_2pi

-- @@ M6_nonstrict_det
theorem M6 {q lam : ℝ} (hT : T S q < 0) (hD : 0 ≤ D S q)
    (hroot : lam^2 - T S q * lam + D S q = 0) : lam < 0 := by
  by_contra hge
  push_neg at hge
  nlinarith [sq_nonneg lam]

-- @@ M6_neg
theorem M6_neg : ¬ (∀ (q lam : ℝ), T worked q < 0 → 0 ≤ D worked q →
    lam^2 - T worked q * lam + D worked q = 0 → lam < 0) := by
  intro h
  have := h (1/5) 0 (by norm_num [T, worked]) (by norm_num [D, worked])
    (by norm_num [T, D, worked])
  norm_num at this

-- @@ M7_equal_diffusivity
noncomputable def workedDv1 : System :=
  { a := 1, b := -2, c := 2, d := -3, Du := 1, Dv := 1,
    hDu := by norm_num, hDv := by norm_num }

theorem M7 : ContinuumTuring workedDv1 := by
  norm_num [ContinuumTuring, workedDv1]

-- @@ M7_neg
theorem M7_neg : ¬ ContinuumTuring workedDv1 := by
  norm_num [ContinuumTuring, workedDv1]

-- @@ M8_flip_bc_sign
theorem M8 (q : ℝ) : D S q = (S.Du * q - S.a) * (S.Dv * q - S.d) + S.b * S.c := by
  unfold D; ring

-- @@ M8_neg
theorem M8_neg : ¬ (D worked 0 = (worked.Du * 0 - worked.a) * (worked.Dv * 0 - worked.d)
    + worked.b * worked.c) := by
  norm_num [D, worked]

-- @@ M9_flip_trace
theorem M9 : 0 < worked.a + worked.d ∧ 0 < worked.a * worked.d - worked.b * worked.c := by
  norm_num [worked]

-- @@ M9_neg
theorem M9_neg : ¬ (0 < worked.a + worked.d ∧ 0 < worked.a * worked.d - worked.b * worked.c) := by
  norm_num [worked]

-- @@ M10_wrong_factor
theorem M10 (q : ℝ) : D worked q = (6 * q - 1) * (2 * q - 1) := by
  simp only [D, worked]; ring

-- @@ M10_neg
theorem M10_neg : ¬ (∀ q : ℝ, D worked q = (6 * q - 1) * (2 * q - 1)) := by
  intro h
  have := h 1
  norm_num [D, worked] at this

-- @@ M11_drop_wellmixed_from_Du_ne_Dv
theorem M11 (h : ContinuumTuring S) : S.Du ≠ S.Dv := by
  intro heq
  have h1 := h.1
  rw [← heq] at h1
  nlinarith [S.hDu]

-- @@ M11_neg
theorem M11_neg : ∃ S : System, ContinuumTuring S ∧ S.Du = S.Dv :=
  ⟨⟨2, 0, 0, 1, 1, 1, by norm_num, by norm_num⟩, by norm_num [ContinuumTuring], rfl⟩

-- @@ END
end Admissible

section AxiomAudit2
open Admissible
#print axioms D_eq
#print axioms unstable_iff_pos_eigenvalue
#print axioms neumannMode_nonneg
#print axioms trace_neg_of_wellmixed
#print axioms finite_domain_linearly_stable
#print axioms real_eigenvalue_neg_of_modeStable
#print axioms worked_D
#print axioms worked_wellmixed
#print axioms worked_continuum
#print axioms worked_unstable_iff
#print axioms worked_stable_on_pi
#print axioms worked_hdet_pi
#print axioms worked_modeStable_pi
#print axioms N2_hyps_satisfiable
#print axioms pos_eigenvalue_of_unstable
#print axioms continuum_imp_exists
#print axioms exists_imp_continuum
#print axioms complex_root_re_neg
#print axioms ratio11_wellmixed
#print axioms ratio11_continuum
#print axioms ratio11_unstable
#print axioms worked_unstable_on_2pi
#print axioms M1_neg
#print axioms M2_neg
#print axioms M3_neg
#print axioms M4_neg
#print axioms M4b_neg
#print axioms M5_neg
#print axioms M6_neg
#print axioms M7_neg
#print axioms M8_neg
#print axioms M9_neg
#print axioms M10_neg
#print axioms continuum_needs_unequal
#print axioms M11_neg
end AxiomAudit2
