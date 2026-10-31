import TuringScope
open TuringScope
/-! Auto-generated receipt. boundary=neumann; Neumann-equivalent L=(5/1)*pi; J,D scaled by 1000. -/
def mdl : Model := ⟨1000, -1000, 1011, -1010, 1000, 1100⟩
def U : List Nat := [1]
theorem tail : ∀ n : Nat, 2 ≤ n → ModeStable mdl 5 1 n :=
  neumann_tail_hurwitz mdl (by decide) (by decide) (by decide) (by decide) (by decide) (by decide) 2 (by decide)
theorem head : ∀ n : Nat, n < 2 → (¬ ModeStable mdl 5 1 n ↔ n ∈ U) := by decide
theorem U_lt : ∀ k ∈ U, k < 2 := by decide
theorem classification : ∀ n : Nat, (¬ ModeStable mdl 5 1 n ↔ n ∈ U) := by
  intro n
  by_cases h : n < 2
  · exact head n h
  · have h' := tail n (by omega)
    constructor
    · intro hn; exact absurd h' hn
    · intro hm; exact absurd (U_lt n hm) h
#print axioms classification
