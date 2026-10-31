import TuringScope
open TuringScope
/-! CONTROL: unmutated law and L=2π; must compile (exit 0). -/
def mutModel : Model := ⟨1, -2, 2, -3, 1, 10⟩
/-- claim: Neumann mode n = 1 is NOT Routh-Hurwitz stable on L = (2/1)π -/
theorem claim : ¬ ModeStable mutModel 2 1 1 := by decide
