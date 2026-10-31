import Mathlib

/-!
Price equation and a Hamilton-rule (Queller-form) corollary, finite-population algebra over ℝ.
Critic feasibility probe 2026-10-31. Elementary definitions (no measure theory). Statements are about the declared finite model only:
 * population indexed by a finite nonempty type ι, parent i has trait z i, fitness w i (any real; Price needs only Σ w ≠ 0),
   offspring trait mean of descendants of i is z i + dz i;
 * z̄' := Σ w i (z i + dz i) / Σ w i  (fitness-weighted mean of descendant traits).
These do NOT prove anything biological; they check an identity and its regression-partition corollary in the stated model.
-/

open Finset

namespace PriceProbe

variable {ι : Type*} [Fintype ι] [Nonempty ι]

noncomputable def n : ℝ := (Fintype.card ι : ℝ)

/-- mean over the population -/
noncomputable def E (f : ι → ℝ) : ℝ := (∑ i, f i) / (Fintype.card ι : ℝ)

/-- covariance, E(fg) - E(f)E(g) -/
noncomputable def Cov (f g : ι → ℝ) : ℝ := E (fun i => f i * g i) - E f * E g

/-- mean offspring trait: fitness-weighted mean of descendant traits -/
noncomputable def zprime (w z dz : ι → ℝ) : ℝ := (∑ i, w i * (z i + dz i)) / (∑ i, w i)

lemma card_ne : (Fintype.card ι : ℝ) ≠ 0 := by
  have : 0 < Fintype.card ι := Fintype.card_pos
  exact_mod_cast this.ne'

lemma E_def (f : ι → ℝ) : E f = (∑ i, f i) / (Fintype.card ι : ℝ) := rfl

lemma E_lin (a b1 b2 : ℝ) (z y e : ι → ℝ) :
    E (fun i => a + b1 * z i + b2 * y i + e i) = a + b1 * E z + b2 * E y + E e := by
  have hc := card_ne (ι := ι)
  simp only [E, Finset.sum_add_distrib, ← Finset.mul_sum, Finset.sum_const, Finset.card_univ, nsmul_eq_mul]
  field_simp

lemma E_lin_z (a b1 b2 : ℝ) (z y e : ι → ℝ) :
    E (fun i => (a + b1 * z i + b2 * y i + e i) * z i) = a * E z + b1 * E (fun i => z i * z i) + b2 * E (fun i => y i * z i) + E (fun i => e i * z i) := by
  have hc := card_ne (ι := ι)
  have : ∀ i, (a + b1 * z i + b2 * y i + e i) * z i = a * z i + b1 * (z i * z i) + b2 * (y i * z i) + e i * z i := by intro i; ring
  simp only [this, E, Finset.sum_add_distrib, ← Finset.mul_sum]
  field_simp

/-- Price equation: wbar * (zbar' - zbar) = Cov(w,z) + E(w * dz). -/
theorem price (w z dz : ι → ℝ) (hw : ∑ i, w i ≠ 0) :
    E w * (zprime w z dz - E z) = Cov w z + E (fun i => w i * dz i) := by
  have hc := card_ne (ι := ι)
  have h1 : ∑ i, w i * (z i + dz i) = (∑ i, w i * z i) + ∑ i, w i * dz i := by
    simp only [mul_add, Finset.sum_add_distrib]
  simp only [Cov, E_def, zprime, h1]
  field_simp
  ring

theorem queller (w z y e : ι → ℝ) (a b1 b2 : ℝ)
    (hw : ∀ i, w i = a + b1 * z i + b2 * y i + e i) (he : Cov e z = 0) :
    Cov w z = b1 * Cov z z - b2 * Cov y z := by
  have hwf : w = fun i => a + b1 * z i + b2 * y i + e i := funext hw
  subst hwf
  have h1 := E_lin_z a b1 b2 z y e
  have h2 := E_lin a b1 b2 z y e
  simp only [Cov] at he ⊢
  rw [h1, h2]
  linarith [he]

end PriceProbe
