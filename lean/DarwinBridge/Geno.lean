import DarwinBridge.Core

/-!
# The declared finite graph: four-site, 20-letter, single-substitution

Vertices are quadruples of residue indices `0..19` (index ↔ one-letter code is the fixed
alphabet `ACDEFGHIKLMNPQRSTVWY`; the theorems are invariant under any relabelling).
Genotypes containing a stop codon or any other symbol are OUTSIDE this graph.  This graph is
the full 20^4 = 160 000-vertex library graph, *not* sequence space.
-/

namespace DarwinBridge

structure Geno where
  a : Nat
  b : Nat
  c : Nat
  d : Nat
deriving DecidableEq, Repr

def Geno.Valid (g : Geno) : Prop := g.a < 20 ∧ g.b < 20 ∧ g.c < 20 ∧ g.d < 20

/-- Single-substitution adjacency inside the 20^4 library: both ends valid, exactly one
position differs. -/
def Adj (g h : Geno) : Prop :=
  g.Valid ∧ h.Valid ∧
  ((g.a ≠ h.a ∧ g.b = h.b ∧ g.c = h.c ∧ g.d = h.d) ∨
   (g.b ≠ h.b ∧ g.a = h.a ∧ g.c = h.c ∧ g.d = h.d) ∨
   (g.c ≠ h.c ∧ g.a = h.a ∧ g.b = h.b ∧ g.d = h.d) ∨
   (g.d ≠ h.d ∧ g.a = h.a ∧ g.b = h.b ∧ g.c = h.c))

instance (g : Geno) : Decidable g.Valid := by unfold Geno.Valid; infer_instance
instance (g h : Geno) : Decidable (Adj g h) := by unfold Adj; infer_instance

def adjB (g h : Geno) : Bool := decide (Adj g h)

theorem adjB_sound : ∀ g h, adjB g h = true → Adj g h := fun _ _ h => of_decide_eq_true h

/-- All 4 × 19 = 76 single-substitution neighbours of a valid genotype. -/
def nbrs (g : Geno) : List Geno :=
  ((List.range 20).filter (· ≠ g.a)).map (fun x => ⟨x, g.b, g.c, g.d⟩) ++
  ((List.range 20).filter (· ≠ g.b)).map (fun x => ⟨g.a, x, g.c, g.d⟩) ++
  ((List.range 20).filter (· ≠ g.c)).map (fun x => ⟨g.a, g.b, x, g.d⟩) ++
  ((List.range 20).filter (· ≠ g.d)).map (fun x => ⟨g.a, g.b, g.c, x⟩)

/-- COMPLETENESS of the enumerator: every `Adj` neighbour is listed.  This is what stops a
cut certificate from silently omitting an escape edge. -/
theorem nbrs_complete : ∀ g h : Geno, Adj g h → h ∈ nbrs g := by
  intro ⟨a, b, c, d⟩ ⟨a', b', c', d'⟩ ⟨_, ⟨ha', hb', hc', hd'⟩, hcase⟩
  simp only [nbrs, List.mem_append, List.mem_map, List.mem_filter, List.mem_range,
    decide_eq_true_eq]
  rcases hcase with ⟨h1, h2, h3, h4⟩ | ⟨h1, h2, h3, h4⟩ | ⟨h1, h2, h3, h4⟩ | ⟨h1, h2, h3, h4⟩
  · simp only at h1 h2 h3 h4 ha'
    subst h2 h3 h4
    exact Or.inl (Or.inl (Or.inl ⟨a', ⟨ha', fun e => h1 e.symm⟩, rfl⟩))
  · simp only at h1 h2 h3 h4 hb'
    subst h2 h3 h4
    exact Or.inl (Or.inl (Or.inr ⟨b', ⟨hb', fun e => h1 e.symm⟩, rfl⟩))
  · simp only at h1 h2 h3 h4 hc'
    subst h2 h3 h4
    exact Or.inl (Or.inr ⟨c', ⟨hc', fun e => h1 e.symm⟩, rfl⟩)
  · simp only at h1 h2 h3 h4 hd'
    subst h2 h3 h4
    exact Or.inr ⟨d', ⟨hd', fun e => h1 e.symm⟩, rfl⟩

/-- Sanity (non-triviality): the enumerator has the expected 76 entries and each is `Adj`
for valid inputs.  Soundness direction of `nbrs`. -/
theorem nbrs_length (g : Geno) (hg : g.Valid) : (nbrs g).length = 76 := by
  obtain ⟨ha, hb, hc, hd⟩ := hg
  have key : ∀ n, n < 20 → ((List.range 20).filter (· ≠ n)).length = 19 := by
    intro n hn
    revert n
    decide
  have k1 := key _ ha
  have k2 := key _ hb
  have k3 := key _ hc
  have k4 := key _ hd
  simp only [nbrs, List.length_append, List.length_map]
  omega

theorem nbrs_sound : ∀ g h : Geno, g.Valid → h ∈ nbrs g → Adj g h := by
  intro ⟨a, b, c, d⟩ h hv hh
  simp only [nbrs, List.mem_append, List.mem_map, List.mem_filter, List.mem_range,
    decide_eq_true_eq] at hh
  obtain ⟨ha, hb, hc, hd⟩ := hv
  rcases hh with ((⟨x, ⟨hx, hne⟩, rfl⟩ | ⟨x, ⟨hx, hne⟩, rfl⟩) | ⟨x, ⟨hx, hne⟩, rfl⟩) | ⟨x, ⟨hx, hne⟩, rfl⟩
  · exact ⟨⟨ha, hb, hc, hd⟩, ⟨hx, hb, hc, hd⟩, Or.inl ⟨fun e => hne e.symm, rfl, rfl, rfl⟩⟩
  · exact ⟨⟨ha, hb, hc, hd⟩, ⟨ha, hx, hc, hd⟩, Or.inr (Or.inl ⟨fun e => hne e.symm, rfl, rfl, rfl⟩)⟩
  · exact ⟨⟨ha, hb, hc, hd⟩, ⟨ha, hb, hx, hd⟩, Or.inr (Or.inr (Or.inl ⟨fun e => hne e.symm, rfl, rfl, rfl⟩))⟩
  · exact ⟨⟨ha, hb, hc, hd⟩, ⟨ha, hb, hc, hx⟩, Or.inr (Or.inr (Or.inr ⟨fun e => hne e.symm, rfl, rfl, rfl⟩))⟩

end DarwinBridge
