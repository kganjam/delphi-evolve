import Mathlib.Algebra.BigOperators.Group.Finset.Basic
import Mathlib.Tactic

/- Finite, normalized weighted Price identity. No biological data or dynamical
   sufficiency is claimed. Descendant means are fitness-reweighted parental
   family means. Nonzero mean fitness is required for this normalization. -/
namespace DelphiPrice
noncomputable section
open scoped BigOperators
variable {ι : Type*} [Fintype ι]

def mean (p x : ι → ℝ) : ℝ := ∑ i, p i * x i

def cov (p x y : ι → ℝ) : ℝ :=
  mean p (fun i => x i * y i) - mean p x * mean p y

def descendantMean (p w zDesc : ι → ℝ) : ℝ :=
  mean p (fun i => w i * zDesc i) / mean p w

theorem price (p w z zDesc : ι → ℝ) (hw : mean p w ≠ 0) :
    mean p w * (descendantMean p w zDesc - mean p z) =
      cov p w z + mean p (fun i => w i * (zDesc i - z i)) := by
  have hsplit : mean p (fun i => w i * (zDesc i - z i)) =
      mean p (fun i => w i * zDesc i) - mean p (fun i => w i * z i) := by
    simp only [mean, mul_sub, Finset.sum_sub_distrib]
  rw [hsplit]
  unfold descendantMean cov
  field_simp
  ring

/-- No transmission bias: family descendant trait equals parental trait.
This is the selection covariance corollary, not Fisher's additive-genetic FTNS. -/
theorem selection_only (p w z : ι → ℝ) (hw : mean p w ≠ 0) :
    mean p w * (descendantMean p w z - mean p z) = cov p w z := by
  have h := price p w z z hw
  simpa only [sub_self, mul_zero, mean, Finset.sum_const_zero, add_zero] using h

/-- With z=w and perfect transmission of that same assigned fitness,
selection-only mean change equals the population variance divided by mean.
This is a fixed-fitness selection identity, NOT the additive genetic FTNS. -/
theorem fitness_selection (p w : ι → ℝ) (hw : mean p w ≠ 0) :
    descendantMean p w w - mean p w = cov p w w / mean p w := by
  apply (eq_div_iff hw).2
  simpa only [mul_comm] using selection_only p w w hw

/-- A normalized finite population with nonnegative reproductive weights. -/
structure Population (ι : Type*) [Fintype ι] where
  p : ι → ℝ
  w : ι → ℝ
  p_nonneg : ∀ i, 0 ≤ p i
  p_sum : ∑ i, p i = 1
  w_nonneg : ∀ i, 0 ≤ w i
  mean_w_pos : 0 < mean p w

theorem population_price (P : Population ι) (z zDesc : ι → ℝ) :
    mean P.p P.w * (descendantMean P.p P.w zDesc - mean P.p z) =
      cov P.p P.w z + mean P.p (fun i => P.w i * (zDesc i - z i)) :=
  price P.p P.w z zDesc (ne_of_gt P.mean_w_pos)

theorem cov_add (p x y z : ι → ℝ) :
    cov p (fun i => x i + y i) z = cov p x z + cov p y z := by
  simp only [cov, mean, add_mul, mul_add, Finset.sum_add_distrib]
  ring

theorem cov_scale (p x z : ι → ℝ) (a : ℝ) :
    cov p (fun i => a * x i) z = a * cov p x z := by
  have h1 : (∑ i, p i * (a * x i * z i)) = a * ∑ i, p i * (x i * z i) := by
    rw [Finset.mul_sum]
    apply Finset.sum_congr rfl
    intro i _
    ring
  have h2 : (∑ i, p i * (a * x i)) = a * ∑ i, p i * x i := by
    rw [Finset.mul_sum]
    apply Finset.sum_congr rfl
    intro i _
    ring
  simp only [cov, mean]
  rw [h1, h2]
  ring

theorem cov_const (p z : ι → ℝ) (a : ℝ) (hp : ∑ i, p i = 1) :
    cov p (fun _ => a) z = 0 := by
  have h1 : (∑ i, p i * (a * z i)) = a * ∑ i, p i * z i := by
    rw [Finset.mul_sum]
    apply Finset.sum_congr rfl
    intro i _
    ring
  simp only [cov, mean]
  rw [h1, ← Finset.sum_mul, hp]
  ring

/-- Hamilton's statistical regression criterion, with perfectly transmitted
trait, positive mean fitness and trait variance, and residual orthogonality.
This does not establish a causal effect of an intervention. -/
theorem hamilton_regression
    (p z partner residual : ι → ℝ) (alpha b c r : ℝ)
    (hp : ∑ i, p i = 1)
    (hvar : 0 < cov p z z)
    (hres : cov p residual z = 0)
    (hrel : cov p partner z = r * cov p z z)
    (hw : 0 < mean p (fun i => alpha + (-c) * z i + b * partner i + residual i)) :
    0 < descendantMean p (fun i => alpha + (-c) * z i + b * partner i + residual i) z - mean p z
      ↔ 0 < r * b - c := by
  let w : ι → ℝ := fun i => alpha + (-c) * z i + b * partner i + residual i
  have hcov : cov p w z = cov p z z * (r * b - c) := by
    dsimp [w]
    rw [cov_add, cov_add, cov_add, cov_const p z alpha hp,
      cov_scale, cov_scale, hres, hrel]
    ring
  have h := selection_only p w z (ne_of_gt hw)
  rw [hcov] at h
  change 0 < descendantMean p w z - mean p z ↔ 0 < r * b - c
  constructor
  · intro hdelta
    have hh : 0 < cov p z z * (r * b - c) := by
      rw [← h]
      exact mul_pos hw hdelta
    exact (mul_pos_iff_of_pos_left hvar).mp hh
  · intro hcoef
    have hh : 0 < mean p w * (descendantMean p w z - mean p z) := by
      rw [h]
      exact mul_pos hvar hcoef
    exact (mul_pos_iff_of_pos_left hw).mp hh

#print axioms hamilton_regression
#print axioms population_price
#print axioms price
#print axioms selection_only
#print axioms fitness_selection
end
end DelphiPrice
