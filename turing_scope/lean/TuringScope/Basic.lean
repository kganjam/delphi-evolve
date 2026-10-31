/-!
# Finite-domain linear-instability regime for a two-species reaction-diffusion linearization

Self-contained, core-Lean only (no Mathlib), exact integer arithmetic.

## What is formalized (and what is not)

Model-to-Lean correspondence (mirrored by `turing_scope/adapter.py`):

* The linearized system about a declared homogeneous fixed point is
  `w_t = J w + diag(Du, Dv) w_xx`, with `J = [[a, b], [c, d]]`, `Du, Dv > 0`.
* On `[0, L]` with homogeneous Neumann conditions, the modes are `cos (n π x / L)`, `n = 0, 1, 2, …`,
  with squared wavenumber `q_n = (n π / L)^2`.
* Write `L = (p / s) π` with integers `p, s > 0`. Then `q_n = n² s² / p² = N / M` with
  `N = n² s²` and `M = p²`.  `M > 0`, `N ≥ 0` are integers, so everything is cleared of denominators.
* Mode matrix `A(q) = J - q diag(Du, Dv)`. We use the integer matrix `M · A(N/M)`.
  Its trace is `M · tr A` and its determinant is `M² · det A`, so signs agree with `tr A`, `det A`.

Lean proves, for **every** integer `a b c d`, `Du Dv`, `p s`:
1. the dispersion identities `modeTr = tr J · M − (Du+Dv) N` and
   `modeDet = Du Dv N² − S N M + det J · M²` with `S = a Dv + d Du`;
2. positivity/negativity of these for all modes beyond a cutoff (`neumann_tail_hurwitz`), which
   is an unbounded-in-`n` statement;
3. in `Instance.lean`: the specific example and the domain-length dependence.

**Not formalized:** the Routh–Hurwitz equivalence between “both eigenvalues of a real 2×2 matrix have
negative real part” and “trace < 0 ∧ det > 0” is treated as the definition `Hurwitz` below (it is a
textbook fact, not proved here); real eigenvalues, the intermediate value theorem, the PDE dynamics,
nonlinear pattern formation, and any biological claim are outside this file. Python (`numpy.linalg.eigvals`)
cross-checks eigenvalues numerically; that is a numerical check, not a Lean theorem.
-/
namespace TuringScope

/-- Integer data of a linearization: `J = [[a,b],[c,d]]` and diffusivities `Du, Dv`. -/
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
/-- `S = Dv·f_u + Du·g_v` in the Delphi record's notation (`a = f_u`, `d = g_v`). -/
def S (m : Model) : Int := m.a * m.Dv + m.d * m.Du

/-- Trace of `M · (J − (N/M) diag(Du,Dv))`. -/
def modeTr (m : Model) (N M : Int) : Int := (m.a * M - N * m.Du) + (m.d * M - N * m.Dv)
/-- Determinant of `M · (J − (N/M) diag(Du,Dv))`. -/
def modeDet (m : Model) (N M : Int) : Int :=
  (m.a * M - N * m.Du) * (m.d * M - N * m.Dv) - (m.b * M) * (m.c * M)

/-- Dispersion identity (trace). -/
theorem modeTr_eq (m : Model) (N M : Int) :
    m.modeTr N M = m.trJ * M - (m.Du + m.Dv) * N := by
  unfold modeTr trJ; grind

/-- Dispersion identity (determinant): `det = Du Dv N² − S N M + det J · M²`. -/
theorem modeDet_eq (m : Model) (N M : Int) :
    m.modeDet N M = m.Du * m.Dv * N ^ 2 - m.S * N * M + m.detJ * M ^ 2 := by
  unfold modeDet S detJ; grind

end Model

/-- Routh–Hurwitz sign condition for the characteristic polynomial `λ² − T λ + D`.
By definition here (textbook equivalence with “both roots have negative real part” is not proved in Lean). -/
def Hurwitz (T D : Int) : Prop := T < 0 ∧ 0 < D

/-- Neumann mode `n` on `L = (p/s) π`: `q_n = n² s² / p²`, as integers `(N, M)`. -/
def modeN (s : Int) (n : Nat) : Int := (n : Int) ^ 2 * s ^ 2
def modeM (p : Int) : Int := p ^ 2

/-- Mode `n` is linearly stable in the Routh–Hurwitz sense. -/
def ModeStable (m : Model) (p s : Int) (n : Nat) : Prop :=
  Hurwitz (m.modeTr (modeN s n) (modeM p)) (m.modeDet (modeN s n) (modeM p))

instance (m : Model) (p s : Int) (n : Nat) : Decidable (ModeStable m p s n) := by
  unfold ModeStable Hurwitz; infer_instance

private theorem sq_pos' {M : Int} (hM : 0 < M) : 0 < M ^ 2 := by
  have := Int.mul_pos hM hM; grind

/-- Determinant is positive for any `q = N/M ≥ S/(Du Dv)` when `det J > 0` (no condition on signs of `S`). -/
theorem modeDet_pos_of_tail (m : Model) (hdet : 0 < m.detJ) {N M : Int} (hM : 0 < M) (hN : 0 ≤ N)
    (hq : m.S * M ≤ m.Du * m.Dv * N) : 0 < m.modeDet N M := by
  rw [Model.modeDet_eq]
  have h1 : 0 ≤ N * (m.Du * m.Dv * N - m.S * M) := Int.mul_nonneg hN (by omega)
  have h2 : 0 < m.detJ * M ^ 2 := Int.mul_pos hdet (sq_pos' hM)
  have h3 : m.Du * m.Dv * N ^ 2 - m.S * N * M + m.detJ * M ^ 2
      = N * (m.Du * m.Dv * N - m.S * M) + m.detJ * M ^ 2 := by grind
  rw [h3]; exact Int.add_pos_of_nonneg_of_pos h1 h2

/-- Trace is negative for every mode when `tr J < 0` and `Du, Dv > 0`. -/
theorem modeTr_neg (m : Model) (htr : m.trJ < 0) (hDu : 0 < m.Du) (hDv : 0 < m.Dv)
    {N M : Int} (hM : 0 < M) (hN : 0 ≤ N) : m.modeTr N M < 0 := by
  rw [Model.modeTr_eq]
  have h1 : m.trJ * M < 0 := Int.mul_neg_of_neg_of_pos htr hM
  have h2 : 0 ≤ (m.Du + m.Dv) * N := Int.mul_nonneg (by omega) hN
  omega

/-- Unbounded-in-`n` tail statement: if the homogeneous state is stable without diffusion
(`tr J < 0`, `det J > 0`), `Du, Dv > 0`, and `n0` is a mode index with `S p² ≤ Du Dv n0² s²`
(i.e. `q_{n0} ≥ S/(Du Dv)`), then **every** Neumann mode `n ≥ n0` (all infinitely many) is stable. -/
theorem neumann_tail_hurwitz (m : Model) (hdet : 0 < m.detJ) (htr : m.trJ < 0)
    (hDu : 0 < m.Du) (hDv : 0 < m.Dv) {p s : Int} (hp : 0 < p) (hs : 0 < s) (n0 : Nat)
    (hcut : m.S * p ^ 2 ≤ m.Du * m.Dv * ((n0 : Int) ^ 2 * s ^ 2)) :
    ∀ n : Nat, n0 ≤ n → ModeStable m p s n := by
  intro n hn
  have hM : 0 < modeM p := sq_pos' hp
  have hN : 0 ≤ modeN s n := by
    unfold modeN
    exact Int.mul_nonneg (by grind) (by have := sq_pos' hs; omega)
  refine ⟨modeTr_neg m htr hDu hDv hM hN, modeDet_pos_of_tail m hdet hM hN ?_⟩
  -- q_n ≥ q_{n0}: n² ≥ n0², then multiply by Du·Dv·s² ≥ 0
  have hnn : (n0 : Int) ^ 2 ≤ (n : Int) ^ 2 := by
    have : (n0 : Int) ≤ n := by exact_mod_cast hn
    have h0 : (0 : Int) ≤ n0 := by omega
    have := Int.mul_le_mul this this h0 (by omega)
    grind
  have hDD : 0 ≤ m.Du * m.Dv * s ^ 2 := Int.mul_nonneg (Int.mul_nonneg (by omega) (by omega)) (by have := sq_pos' hs; omega)
  have := Int.mul_le_mul_of_nonneg_left hnn hDD
  unfold modeN modeM
  grind

/-- The constant mode (`n = 0`) is stable exactly when the well-mixed state is. -/
theorem mode_zero_stable (m : Model) (hdet : 0 < m.detJ) (htr : m.trJ < 0) {p s : Int}
    (hp : 0 < p) : ModeStable m p s 0 := by
  have hM : 0 < modeM p := sq_pos' hp
  have hN : modeN s 0 = 0 := by unfold modeN; simp
  unfold ModeStable
  rw [hN, Model.modeTr_eq, Model.modeDet_eq]
  have h1 : m.trJ * modeM p < 0 := Int.mul_neg_of_neg_of_pos htr hM
  have h2 : 0 < m.detJ * modeM p ^ 2 := Int.mul_pos hdet (sq_pos' hM)
  constructor <;> grind

/-- Sign-change certificate for the characteristic polynomial `λ² − T λ + D` when `D < 0`:
`p(0) = D < 0` and `p(Λ) > 0` at `Λ = |T| + |D| + 1`. An intermediate-value argument (not formalized
here) then gives a positive real root; Python checks eigenvalues numerically. -/
theorem charpoly_sign_change (T D : Int) (hD : D < 0) :
    ∃ Λ : Int, 0 < Λ ∧ (0 : Int) ^ 2 - T * 0 + D < 0 ∧ 0 < Λ ^ 2 - T * Λ + D := by
  refine ⟨T.natAbs + D.natAbs + 1, by omega, by omega, ?_⟩
  have hΛ : (0 : Int) < (T.natAbs : Int) + (D.natAbs : Int) + 1 := by omega
  have hT : T ≤ (T.natAbs : Int) := Int.le_natAbs
  have hD' : (D.natAbs : Int) = -D := by omega
  have h1 : T * ((T.natAbs : Int) + (D.natAbs : Int) + 1)
      ≤ (T.natAbs : Int) * ((T.natAbs : Int) + (D.natAbs : Int) + 1) :=
    Int.mul_le_mul_of_nonneg_right hT (by omega)
  have h2 : ((T.natAbs : Int) + (D.natAbs : Int) + 1) ^ 2
      - (T.natAbs : Int) * ((T.natAbs : Int) + (D.natAbs : Int) + 1) = ((D.natAbs : Int) + 1) * ((T.natAbs : Int) + (D.natAbs : Int) + 1) := by grind
  have h3 : (D.natAbs : Int) + 1 ≤ ((D.natAbs : Int) + 1) * ((T.natAbs : Int) + (D.natAbs : Int) + 1) := by
    have := Int.mul_le_mul_of_nonneg_left (show (1 : Int) ≤ (T.natAbs : Int) + (D.natAbs : Int) + 1 by omega)
      (show (0 : Int) ≤ (D.natAbs : Int) + 1 by omega)
    grind
  omega

end TuringScope
