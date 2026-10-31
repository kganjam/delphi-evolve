import TuringScope
open TuringScope
/-! DOMAIN MUTANT: L=π instead of 2π; claiming mode 1 is unstable must NOT compile. -/
def mutModel : Model := ⟨1, -2, 2, -3, 1, 10⟩
/-- claim: Neumann mode n = 1 is NOT Routh-Hurwitz stable on L = (1/1)π -/
theorem claim : ¬ ModeStable mutModel 1 1 1 := by decide
