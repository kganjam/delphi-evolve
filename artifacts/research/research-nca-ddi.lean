/-! Linear-instability lemmas for 2-species reaction-diffusion (Delphi `turing-ddi`) over ℚ,
core Lean only (no Mathlib). Scope: linear stability of the homogeneous steady state of the
linearised system. Nothing here concerns nonlinear patterns, numerical solvers, damage,
or biology. `stableMode` uses the 2x2 Hurwitz criterion as a DEFINITION (not re-proved). -/

namespace NcaDdi

/-- det (J - q D) for J = [[fu,fv],[gu,gv]], D = diag(Du,Dv). -/
def detMode (fu fv gu gv Du Dv q : Rat) : Rat :=
  (fu - Du * q) * (gv - Dv * q) - fv * gu

/-- trace (J - q D). -/
def trMode (fu gv Du Dv q : Rat) : Rat := fu + gv - (Du + Dv) * q

def stableMode (fu fv gu gv Du Dv q : Rat) : Prop :=
  trMode fu gv Du Dv q < 0 ∧ 0 < detMode fu fv gu gv Du Dv q

/-- Any q with 2·Du·Dv·q = Dv·fu + Du·gv makes det < 0 under the discriminant condition. -/
theorem det_neg_at_witness (fu fv gu gv Du Dv q : Rat)
    (hq : 2 * (Du * Dv) * q = Dv * fu + Du * gv)
    (hdisc : 4 * Du * Dv * (fu * gv - fv * gu) < (Dv * fu + Du * gv) ^ 2)
    (hP : 0 < Du * Dv) :
    detMode fu fv gu gv Du Dv q < 0 := by
  unfold detMode
  have h : 4 * (Du * Dv) * ((fu - Du * q) * (gv - Dv * q) - fv * gu) < 0 := by
    have e : 4 * (Du * Dv) * ((fu - Du * q) * (gv - Dv * q) - fv * gu)
        = 4 * Du * Dv * (fu * gv - fv * gu) - (Dv * fu + Du * gv) ^ 2 := by
      have : (Dv * fu + Du * gv) = 2 * (Du * Dv) * q := hq.symm
      rw [this]; grind
    rw [e]; grind
  by_cases hc : (fu - Du * q) * (gv - Dv * q) - fv * gu < 0
  · exact hc
  · have hc' : 0 ≤ (fu - Du * q) * (gv - Dv * q) - fv * gu := by grind
    have : 0 ≤ 4 * (Du * Dv) * ((fu - Du * q) * (gv - Dv * q) - fv * gu) :=
      Rat.mul_nonneg (by grind) hc'
    grind

/-- Continuum diffusion-driven instability (the linear half of `turing-ddi`):
exists q > 0 with det (J - qD) < 0. -/
theorem ddi_exists (fu fv gu gv Du Dv : Rat)
    (hDu : 0 < Du) (hDv : 0 < Dv)
    (hpos : 0 < Dv * fu + Du * gv)
    (hdisc : 4 * Du * Dv * (fu * gv - fv * gu) < (Dv * fu + Du * gv) ^ 2) :
    ∃ q : Rat, 0 < q ∧ detMode fu fv gu gv Du Dv q < 0 := by
  have hP : 0 < Du * Dv := Rat.mul_pos hDu hDv
  have hne : 2 * (Du * Dv) ≠ 0 := by grind
  refine ⟨(Dv * fu + Du * gv) / (2 * (Du * Dv)), ?_, ?_⟩
  · have h2 : 0 < 2 * (Du * Dv) := by grind
    have hinv : 0 < (2 * (Du * Dv))⁻¹ := Rat.inv_pos.2 h2
    have := Rat.mul_pos hpos hinv
    rwa [Rat.div_def]
  · apply det_neg_at_witness _ _ _ _ _ _ _ _ hdisc hP
    have : (2 * (Du * Dv)) * ((Dv * fu + Du * gv) / (2 * (Du * Dv))) = Dv * fu + Du * gv := by grind
    exact this

/-- If the homogeneous state is stable (trace J < 0, nonneg D) then trace(J - qD) < 0 for q ≥ 0,
so a mode is unstable exactly when det ≤ 0. -/
theorem trace_neg (fu gv Du Dv q : Rat) (htr : fu + gv < 0)
    (hDu : 0 ≤ Du) (hDv : 0 ≤ Dv) (hq : 0 ≤ q) : trMode fu gv Du Dv q < 0 := by
  unfold trMode
  have : 0 ≤ (Du + Dv) * q := Rat.mul_nonneg (by grind) hq
  grind

/-! ## Finite domain (homogeneous Neumann): admissible modes are q = n²·s, s = (π/L)².
`s` is passed as a rational parameter (a rational bound on the true value), so these are
statements about the rational-parameter model, not about π. Example from the sibling
checkpoint `turing-domain-counterexample.json`: J = [[1,-2],[2,-3]], D = diag(1,10). -/

/-- Exact: det(J - qD) = 10 q² - 7 q + 1 for the example. -/
theorem example_det (q : Rat) : detMode 1 (-2) 2 (-3) 1 10 q = 10 * q ^ 2 - 7 * q + 1 := by
  unfold detMode; grind

/-- Short domain (s ≥ 1, i.e. L ≤ π): every admissible mode n ≥ 0 is linearly stable. -/
theorem example_short_domain_all_stable (s : Rat) (hs : 1 ≤ s) (n : Nat) :
    stableMode 1 (-2) 2 (-3) 1 10 ((n : Rat) ^ 2 * s) := by
  have hq : 0 ≤ (n : Rat) ^ 2 * s := by
    have hn : (0 : Rat) ≤ (n : Rat) := by exact_mod_cast Nat.zero_le n
    have : (0 : Rat) ≤ (n : Rat) ^ 2 := by
      have := Rat.mul_nonneg hn hn
      grind
    exact Rat.mul_nonneg this (by grind)
  refine ⟨?_, ?_⟩
  · have := trace_neg 1 (-3) 1 10 ((n : Rat) ^ 2 * s) (by grind) (by grind) (by grind) hq
    exact this
  · rw [example_det]
    cases n with
    | zero => grind
    | succ m =>
      have h1 : (1 : Rat) ≤ ((m + 1 : Nat) : Rat) ^ 2 := by
        have h0 : (1 : Rat) ≤ ((m + 1 : Nat) : Rat) := by grind
        have h00 : (0 : Rat) ≤ ((m + 1 : Nat) : Rat) - 1 := by grind
        have := Rat.mul_nonneg h00 h00
        grind
      have hx : (0 : Rat) ≤ ((m + 1 : Nat) : Rat) ^ 2 - 1 := by grind
      have hy : (0 : Rat) ≤ s - 1 := by grind
      have hxy := Rat.mul_nonneg hx hy
      have hq1 : (1 : Rat) ≤ ((m + 1 : Nat) : Rat) ^ 2 * s := by grind
      have hq2 : (0 : Rat) ≤ ((m + 1 : Nat) : Rat) ^ 2 * s - 1 := by grind
      have hsq := Rat.mul_nonneg hq2 hq2
      generalize ((m + 1 : Nat) : Rat) ^ 2 * s = q at *
      grind

/-- Long domain (s = 1/4, i.e. L = 2π): mode n = 1 has det = -1/8 < 0, hence is unstable. -/
theorem example_long_domain_unstable :
    detMode 1 (-2) 2 (-3) 1 10 ((1 : Rat) ^ 2 * (1 / 4)) < 0 := by
  rw [example_det]; grind

/-- The instability interval is 1/5 < q < 1/2: det < 0 there. -/
theorem example_continuum_interval (q : Rat) (h1 : 1 / 5 < q) (h2 : q < 1 / 2) :
    detMode 1 (-2) 2 (-3) 1 10 q < 0 := by
  rw [example_det]
  have ha : (0 : Rat) < q - 1 / 5 := by grind
  have hb : (0 : Rat) < 1 / 2 - q := by grind
  have := Rat.mul_pos ha hb
  grind

end NcaDdi
