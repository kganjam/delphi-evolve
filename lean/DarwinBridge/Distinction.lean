import DarwinBridge.Checker

/-!
# The admissible cut is strictly weaker than the blocked cut (concrete counterexample)

Two adjacent genotypes with overlapping intervals `A = [0,2]`, `B = [1,3]` (δ = 0):

* the admissible-cut checker ACCEPTS `S = [A]` (no certified-dominance step A → B: `hi A = 2 > lo B = 1`),
* the blocked-cut checker REJECTS it (A → B is not certifiably descending either),
* and a true-value assignment satisfying the interval-containment hypothesis (`f A = 1`, `f B = 2`)
  has a non-decreasing edge A → B.

So "no certifiable route" (`adm_cut_sound`) must never be read as "no true route"; only
`blocked_cut_sound` supports the latter.  Everything is kernel-checked by `decide`/`omega`; no axioms.
-/

namespace DarwinBridge.Distinction
open DarwinBridge

def A : Geno := ⟨0, 0, 0, 0⟩
def B : Geno := ⟨1, 0, 0, 0⟩
def tbl : Table := [(A, 0, 2), (B, 1, 3)]

theorem adm_accepts : admCertB 0 tbl [A] A B = true := by decide +kernel
theorem blocked_rejects : blockedCertB 0 tbl [A] A B = false := by decide +kernel

/-- The adjacency edge A → B that the cut leaves open really exists. -/
theorem adj_AB : Adj A B := by
  refine ⟨by decide, by decide, Or.inl ⟨by decide, rfl, rfl, rfl⟩⟩

/-- A value assignment inside the declared intervals with a non-decreasing path A ⇒ B. -/
theorem true_route_exists_despite_adm_cut :
    ∃ f : Geno → Int, SensitivityAssumption (fun x : Int => x) 0 tbl f ∧ NDReach Adj f A B := by
  refine ⟨fun g => if g = A then 1 else 2, ?_, ?_⟩
  · intro x l h hx
    unfold obsBounds at hx
    by_cases hxA : x = A
    · subst hxA
      simp [tbl, A, B] at hx ⊢
      omega
    · by_cases hxB : x = B
      · subst hxB
        have : B ≠ A := by decide
        simp [tbl, A, B] at hx ⊢
        omega
      · have hA : decide (A = x) = false := decide_eq_false (fun h => hxA h.symm)
        have hB : decide (B = x) = false := decide_eq_false (fun h => hxB h.symm)
        simp only [tbl, List.find?, hA, hB] at hx
        simp at hx
  · exact Reach.step (b := B) ⟨adj_AB, by simp [A, B]⟩ (Reach.refl B)

end DarwinBridge.Distinction
