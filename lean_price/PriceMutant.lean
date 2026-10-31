import Mathlib
open Finset
namespace PriceProbe
variable {ι : Type*} [Fintype ι] [Nonempty ι]
noncomputable def E (f : ι → ℝ) : ℝ := (∑ i, f i) / (Fintype.card ι : ℝ)
noncomputable def Cov (f g : ι → ℝ) : ℝ := E (fun i => f i * g i) - E f * E g
noncomputable def zprime (w z dz : ι → ℝ) : ℝ := (∑ i, w i * (z i + dz i)) / (∑ i, w i)
lemma card_ne : (Fintype.card ι : ℝ) ≠ 0 := by
  have : 0 < Fintype.card ι := Fintype.card_pos
  exact_mod_cast this.ne'
/-- MUTANT: drops the transmission term E(w dz). Must NOT compile. -/
theorem price_mutant (w z dz : ι → ℝ) (hw : ∑ i, w i ≠ 0) :
    E w * (zprime w z dz - E z) = Cov w z := by
  have hc := card_ne (ι := ι)
  unfold E Cov zprime
  simp only [mul_add, Finset.sum_add_distrib]
  field_simp
  ring
end PriceProbe
