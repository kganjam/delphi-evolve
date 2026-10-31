import TuringScope
open TuringScope
/-! LAW MUTANT: Dv changed 10 -> 1 (equal diffusivities); the same L=2π instability claim must NOT compile. -/
def mutModel : Model := ⟨1, -2, 2, -3, 1, 1⟩
/-- claim: Neumann mode n = 1 is NOT Routh-Hurwitz stable on L = (2/1)π -/
theorem claim : ¬ ModeStable mutModel 2 1 1 := by decide
