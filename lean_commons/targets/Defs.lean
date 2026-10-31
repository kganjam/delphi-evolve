/-! Frozen shared base library (both experimental arms receive exactly this text).
Core Lean only (no Mathlib), exact integer arithmetic. Definitions mirror
`turing_scope/lean/TuringScope/Basic.lean` for the Turing family; the other families are
integer models of the stated textbook conditions. Nothing here asserts any biology. -/
namespace Scope

/-- Linearization `J = [[a,b],[c,d]]` of a two-species reaction-diffusion system, diffusivities `Du Dv`. -/
structure Model where
  a : Int
  b : Int
  c : Int
  d : Int
  Du : Int
  Dv : Int

namespace Model
def trJ (m : Model) : Int := m.a + m.d
def detJ (m : Model) : Int := m.a * m.d - m.b * m.c
def S (m : Model) : Int := m.a * m.Dv + m.d * m.Du
/-- Trace of `M * (J - (N/M) diag(Du,Dv))` (mode with squared wavenumber `N/M`). -/
def modeTr (m : Model) (N M : Int) : Int := (m.a * M - N * m.Du) + (m.d * M - N * m.Dv)
/-- Determinant of `M * (J - (N/M) diag(Du,Dv))`. -/
def modeDet (m : Model) (N M : Int) : Int :=
  (m.a * M - N * m.Du) * (m.d * M - N * m.Dv) - (m.b * M) * (m.c * M)
end Model

/-- Routh-Hurwitz sign condition for `lambda^2 - T lambda + D` (taken as the definition of stability here). -/
def Hurwitz (T D : Int) : Prop := T < 0 ∧ 0 < D

/-- Neumann mode `n` on a domain of length `(p/s) pi`: squared wavenumber `n^2 s^2 / p^2` as `modeN / modeM`. -/
def modeN (s : Int) (n : Nat) : Int := (n : Int) ^ 2 * s ^ 2
def modeM (p : Int) : Int := p ^ 2

/-- Hamilton's rule gain for integer relatedness-scaled terms: `r*B - C` (r is a scaled relatedness). -/
def hamGain (r B C : Int) : Int := r * B - C
/-- The altruistic allele is favoured when the gain is positive. -/
def Favoured (r B C : Int) : Prop := 0 < hamGain r B C

/-- Hawk-Dove payoff matrix scaled by 2: `A(H,H) = V-C`, `A(H,D) = 2V`, `A(D,H) = 0`, `A(D,D) = V`. -/
def hdHH (V C : Int) : Int := V - C
def hdHD (V _C : Int) : Int := 2 * V
def hdDH (_V _C : Int) : Int := 0
def hdDD (V _C : Int) : Int := V

end Scope
