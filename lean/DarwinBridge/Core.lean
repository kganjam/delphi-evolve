/-!
# Darwin's Bridge — generic conditional interval-path and cut theorems

No Mathlib, no `sorry`, no `native_decide`, no extra axioms.

Everything here is generic over an arbitrary vertex type `V`, an arbitrary
graph relation `Adj : V → V → Prop`, and an arbitrary ordered value type `α`
(the "true" fitness values).  Interval endpoints live in a (decidable) type
`β` (in practice `Int`, a scaled integer) and are mapped into `α` by a monotone
`ι : β → α`.

The *only* empirical premise is `Contains`: the true values lie in the declared
intervals **at the vertices that have a declared interval**.  The theorems say
nothing about whether that premise is true of a real assay.

Statements proved here
* `route_sound`      — a route whose every step is an `Adj` edge and satisfies
                       `hi u ≤ lo v` is non-decreasing in every assignment inside
                       the intervals; hence start ≤ every route vertex ≤ ... ≤ target.
* `route_floor`      — consequence: no vertex on the route falls below `lo start`.
* `closed_no_reach`  — a set closed under a relation, containing the start and
                       not the target, forbids reachability (generic cut lemma).
* `blocked_cut_sound`— a finite set `S` with start ∈ S, target ∉ S such that every
                       declared edge leaving `S` is *certifiably descending*
                       (`hi v < lo u`, both endpoints declared) forbids any
                       non-decreasing `Adj`-path from start to target, for every
                       assignment inside the intervals.
* `cut_complete_enumeration` hypotheses are explicit: the neighbour enumerator
  must be complete for `Adj` (proved for the concrete four-site graph elsewhere).
-/

set_option linter.unusedSectionVars false

namespace DarwinBridge

universe u v

/-- Minimal order laws on the value type (satisfied by `Int`, `Rat`, `Real`). -/
structure OrderLaws (α : Type u) [LE α] [LT α] : Prop where
  le_refl : ∀ a : α, a ≤ a
  le_trans : ∀ {a b c : α}, a ≤ b → b ≤ c → a ≤ c
  lt_of_le_of_lt : ∀ {a b c : α}, a ≤ b → b < c → a < c
  lt_of_lt_of_le : ∀ {a b c : α}, a < b → b ≤ c → a < c
  not_le_of_lt : ∀ {a b : α}, a < b → ¬ b ≤ a

theorem intLaws : OrderLaws Int where
  le_refl := fun a => Int.le_refl a
  le_trans := fun h1 h2 => Int.le_trans h1 h2
  lt_of_le_of_lt := fun h1 h2 => Int.lt_of_le_of_lt h1 h2
  lt_of_lt_of_le := fun h1 h2 => Int.lt_of_lt_of_le h1 h2
  not_le_of_lt := fun h => Int.not_le.mpr h

/-- Monotone, strictly monotone embedding of checker endpoints into the value type. -/
structure Embedding {β : Type u} {α : Type v} [LE β] [LT β] [LE α] [LT α]
    (ι : β → α) : Prop where
  mono : ∀ {a b : β}, a ≤ b → ι a ≤ ι b
  smono : ∀ {a b : β}, a < b → ι a < ι b

theorem Embedding.id {β : Type u} [LE β] [LT β] : Embedding (fun x : β => x) :=
  ⟨fun h => h, fun h => h⟩

variable {V : Type u} {α : Type v} {β : Type u}

/-- A partial interval table: `some (lo, hi)` where an interval is declared, `none` where
the vertex is unknown (missing, imputed, unmeasured, outside the table). -/
abbrev Bounds (V : Type u) (β : Type u) := V → Option (β × β)

/-- THE empirical premise: a true-value assignment `f` lies inside the declared interval at
every vertex that has one. Unknown vertices are unconstrained. -/
def Contains [LE α] (ι : β → α) (B : Bounds V β) (f : V → α) : Prop :=
  ∀ x l h, B x = some (l, h) → ι l ≤ f x ∧ f x ≤ ι h

/-! ### Decidable edge predicates -/

/-- Certified non-decreasing step `u → v`: both endpoints declared and `hi u ≤ lo v`. -/
def domB [LE β] [DecidableRel (α := β) (· ≤ ·)] (B : Bounds V β) (a b : V) : Bool :=
  match B a, B b with
  | some (_, ha), some (lb, _) => decide (ha ≤ lb)
  | _, _ => false

/-- Certified strictly descending step `u → v`: both declared and `hi v < lo u`. -/
def downB [LT β] [DecidableRel (α := β) (· < ·)] (B : Bounds V β) (a b : V) : Bool :=
  match B a, B b with
  | some (la, _), some (_, hb) => decide (hb < la)
  | _, _ => false

section Soundness
variable [LE α] [LT α] [LE β] [LT β]
variable [DecidableRel (α := β) (· ≤ ·)] [DecidableRel (α := β) (· < ·)]

theorem domB_sound {ι : β → α} (hα : OrderLaws α) (hι : Embedding ι) {B : Bounds V β}
    {f : V → α} (hf : Contains ι B f) {a b : V} (h : domB B a b = true) : f a ≤ f b := by
  unfold domB at h
  split at h
  · rename_i la ha lb hb hBa hBb
    have hd : ha ≤ lb := of_decide_eq_true h
    have h1 := (hf a la ha hBa).2
    have h2 := (hf b lb hb hBb).1
    exact hα.le_trans h1 (hα.le_trans (hι.mono hd) h2)
  · exact absurd h (by simp)

theorem downB_sound {ι : β → α} (hα : OrderLaws α) (hι : Embedding ι) {B : Bounds V β}
    {f : V → α} (hf : Contains ι B f) {a b : V} (h : downB B a b = true) : f b < f a := by
  unfold downB at h
  split at h
  · rename_i la ha lb hb hBa hBb
    have hd : hb < la := of_decide_eq_true h
    have h1 := (hf a la ha hBa).1
    have h2 := (hf b lb hb hBb).2
    exact hα.lt_of_le_of_lt h2 (hα.lt_of_lt_of_le (hι.smono hd) h1)
  · exact absurd h (by simp)

end Soundness

/-! ### Routes -/

/-- Route semantics: consecutive vertices are `Adj`-adjacent and `f` is non-decreasing. -/
def NDRoute [LE α] (Adj : V → V → Prop) (f : V → α) : List V → Prop
  | [] => True
  | [_] => True
  | a :: b :: rest => Adj a b ∧ f a ≤ f b ∧ NDRoute Adj f (b :: rest)

/-- Checker for a route: every step is an edge (by `adjB`) and is a certified dominance step. -/
def routeB [LE β] [DecidableRel (α := β) (· ≤ ·)] (adjB : V → V → Bool) (B : Bounds V β) :
    List V → Bool
  | [] => true
  | [_] => true
  | a :: b :: rest => adjB a b && domB B a b && routeB adjB B (b :: rest)

section RouteSound
variable [LE α] [LT α] [LE β] [LT β]
variable [DecidableRel (α := β) (· ≤ ·)] [DecidableRel (α := β) (· < ·)]

theorem route_sound {ι : β → α} (hα : OrderLaws α) (hι : Embedding ι) {B : Bounds V β}
    {Adj : V → V → Prop} {adjB : V → V → Bool} (hadj : ∀ a b, adjB a b = true → Adj a b)
    {f : V → α} (hf : Contains ι B f) :
    ∀ r : List V, routeB adjB B r = true → NDRoute Adj f r
  | [], _ => trivial
  | [_], _ => trivial
  | a :: b :: rest, h => by
    unfold routeB at h
    simp only [Bool.and_eq_true] at h
    obtain ⟨⟨h1, h2⟩, h3⟩ := h
    exact ⟨hadj a b h1, domB_sound hα hι hf h2, route_sound hα hι hadj hf (b :: rest) h3⟩

end RouteSound

/-- Every vertex after the head of a non-decreasing route has value ≥ the head's value. -/
theorem NDRoute.head_le [LE α] [LT α] (hα : OrderLaws α) (Adj : V → V → Prop) (f : V → α) :
    ∀ (s : V) (r : List V), NDRoute Adj f (s :: r) → ∀ x, x ∈ r → f s ≤ f x
  | _, [], _, x, hx => by simp at hx
  | s, b :: rest, h, x, hx => by
    obtain ⟨_, hsb, hrest⟩ := h
    rcases List.mem_cons.mp hx with rfl | hxr
    · exact hsb
    · exact hα.le_trans hsb (NDRoute.head_le hα Adj f b rest hrest x hxr)

/-- Non-decreasing `Adj`-reachability (the thing a "blocked" certificate denies). -/
inductive Reach (R : V → V → Prop) : V → V → Prop
  | refl (x : V) : Reach R x x
  | step {a b c : V} : R a b → Reach R b c → Reach R a c

/-- Reachability along `Adj` edges on which `f` does not decrease. -/
def NDReach [LE α] (Adj : V → V → Prop) (f : V → α) : V → V → Prop :=
  Reach (fun a b => Adj a b ∧ f a ≤ f b)

theorem NDRoute.reach [LE α] (Adj : V → V → Prop) (f : V → α) :
    ∀ (s : V) (r : List V), NDRoute Adj f (s :: r) →
      ∀ t, (s :: r).getLast? = some t → NDReach Adj f s t
  | s, [], _, t, ht => by
    simp at ht; subst ht; exact Reach.refl _
  | s, b :: rest, h, t, ht => by
    obtain ⟨hadj, hle, hrest⟩ := h
    have ht' : (b :: rest).getLast? = some t := by
      simpa [List.getLast?_cons_cons] using ht
    exact Reach.step ⟨hadj, hle⟩ (NDRoute.reach Adj f b rest hrest t ht')

/-- Route + endpoints: if the checker accepts `s :: r` ending at `t`, then for every assignment
inside the intervals, `t` is `NDReach`-reachable from `s`, `f s ≤ f t`, and every route vertex is
at least `f s`. -/
theorem route_endpoints [LE α] [LT α] [LE β] [LT β]
    [DecidableRel (α := β) (· ≤ ·)] [DecidableRel (α := β) (· < ·)]
    {ι : β → α} (hα : OrderLaws α) (hι : Embedding ι) {B : Bounds V β}
    {Adj : V → V → Prop} {adjB : V → V → Bool} (hadj : ∀ a b, adjB a b = true → Adj a b)
    {f : V → α} (hf : Contains ι B f) (s : V) (r : List V) (t : V)
    (hr : routeB adjB B (s :: r) = true) (ht : (s :: r).getLast? = some t) :
    NDReach Adj f s t ∧ (∀ x, x ∈ s :: r → f s ≤ f x) := by
  have hnd := route_sound hα hι hadj hf (s :: r) hr
  refine ⟨NDRoute.reach Adj f s r hnd t ht, ?_⟩
  intro x hx
  rcases List.mem_cons.mp hx with rfl | hxr
  · exact hα.le_refl _
  · exact NDRoute.head_le hα Adj f s r hnd x hxr

/-- No-broken-intermediate corollary: if the start is certified at or above a floor `θ`
(`ι θ ≤ f s` follows from `θ ≤ lo s`), every vertex on the route is at least `ι θ`. -/
theorem route_floor [LE α] [LT α] [LE β] [LT β]
    [DecidableRel (α := β) (· ≤ ·)] [DecidableRel (α := β) (· < ·)]
    {ι : β → α} (hα : OrderLaws α) (hι : Embedding ι) {B : Bounds V β}
    {Adj : V → V → Prop} {adjB : V → V → Bool} (hadj : ∀ a b, adjB a b = true → Adj a b)
    {f : V → α} (hf : Contains ι B f) (s : V) (r : List V) (t : V)
    (hr : routeB adjB B (s :: r) = true) (ht : (s :: r).getLast? = some t)
    (θ lo hi : β) (hs : B s = some (lo, hi)) (hθ : θ ≤ lo) :
    ∀ x, x ∈ s :: r → ι θ ≤ f x := by
  intro x hx
  have h1 : ι θ ≤ f s := hα.le_trans (hι.mono hθ) (hf s lo hi hs).1
  exact hα.le_trans h1 ((route_endpoints hα hι hadj hf s r t hr ht).2 x hx)

/-! ### Closed sets and cuts -/

/-- Generic cut lemma: a set closed under `R`, containing the start and not the target,
forbids `R`-reachability. -/
theorem closed_no_reach {R : V → V → Prop} {S : V → Prop}
    (hclosed : ∀ a b, S a → R a b → S b) {s t : V} (hs : S s) (ht : ¬ S t) :
    ¬ Reach R s t := by
  intro h
  have : ∀ a b, Reach R a b → S a → S b := by
    intro a b hr
    induction hr with
    | refl _ => exact fun h => h
    | step hab _ ih => exact fun ha => ih (hclosed _ _ ha hab)
  exact ht (this s t h hs)

/-- Checker for a finite set `S` (a list) with an explicit neighbour enumerator `nbrs`:
every enumerated neighbour of a member is a member, or the edge is certified descending. -/
def cutB [DecidableEq V] [LT β] [DecidableRel (α := β) (· < ·)]
    (nbrs : V → List V) (B : Bounds V β) (S : List V) : Bool :=
  S.all (fun a => (nbrs a).all (fun b => decide (b ∈ S) || downB B a b))

def blockedB [DecidableEq V] [LT β] [DecidableRel (α := β) (· < ·)]
    (nbrs : V → List V) (B : Bounds V β) (S : List V) (s t : V) : Bool :=
  decide (s ∈ S) && !(decide (t ∈ S)) && cutB nbrs B S

/-- **Blocked-cut soundness.** If `nbrs` enumerates *every* `Adj`-neighbour (completeness
hypothesis `hcomplete`) and the checker accepts, then for every assignment inside the
declared intervals there is NO non-decreasing `Adj`-path from `s` to `t`. -/
theorem blocked_cut_sound [DecidableEq V] [LE α] [LT α] [LE β] [LT β]
    [DecidableRel (α := β) (· ≤ ·)] [DecidableRel (α := β) (· < ·)]
    {ι : β → α} (hα : OrderLaws α) (hι : Embedding ι) {B : Bounds V β}
    {Adj : V → V → Prop} {nbrs : V → List V}
    (hcomplete : ∀ a b, Adj a b → b ∈ nbrs a)
    {f : V → α} (hf : Contains ι B f) (S : List V) (s t : V)
    (h : blockedB nbrs B S s t = true) : ¬ NDReach Adj f s t := by
  unfold blockedB at h
  simp only [Bool.and_eq_true, Bool.not_eq_true'] at h
  obtain ⟨⟨hs, ht⟩, hcut⟩ := h
  have hs' : s ∈ S := of_decide_eq_true hs
  have ht' : t ∉ S := by simpa using ht
  unfold cutB at hcut
  have hclosed : ∀ a b, (a ∈ S) → (Adj a b ∧ f a ≤ f b) → (b ∈ S) := by
    intro a b ha ⟨hab, hle⟩
    have h1 := List.all_eq_true.mp hcut a ha
    have h2 := List.all_eq_true.mp h1 b (hcomplete a b hab)
    simp only [Bool.or_eq_true] at h2
    rcases h2 with h2 | h2
    · exact of_decide_eq_true h2
    · exact absurd hle (hα.not_le_of_lt (downB_sound hα hι hf h2))
  exact closed_no_reach (S := fun x => x ∈ S) hclosed hs' ht'

/-! ### Admissible-route cuts ("no certifiable route")

`AdmEdge` is the relation the route checker accepts.  A cut that is closed under `AdmEdge` shows
that NO CERTIFIABLE route exists from `s` to `t` relative to the table `B`.  This is strictly
weaker than `blocked_cut_sound`: it says the certifier cannot succeed (e.g. an edge may have
overlapping intervals), not that every true path is blocked.  Unknown vertices (no interval) can
never be on an admissible route.  Completeness of `B` with respect to the underlying dataset is
NOT a Lean fact. -/

def AdmEdge (Adj : V → V → Prop) (B : Bounds V β) [LE β] [DecidableRel (α := β) (· ≤ ·)]
    (a b : V) : Prop := Adj a b ∧ domB B a b = true

def admBlockedB [DecidableEq V] [LE β] [DecidableRel (α := β) (· ≤ ·)]
    (nbrs : V → List V) (B : Bounds V β) (S : List V) (s t : V) : Bool :=
  decide (s ∈ S) && !(decide (t ∈ S)) &&
    S.all (fun a => (nbrs a).all (fun b => decide (b ∈ S) || !(domB B a b)))

theorem adm_cut_sound [DecidableEq V] [LE β] [DecidableRel (α := β) (· ≤ ·)]
    {B : Bounds V β} {Adj : V → V → Prop} {nbrs : V → List V}
    (hcomplete : ∀ a b, Adj a b → b ∈ nbrs a) (S : List V) (s t : V)
    (h : admBlockedB nbrs B S s t = true) : ¬ Reach (AdmEdge Adj B) s t := by
  unfold admBlockedB at h
  simp only [Bool.and_eq_true, Bool.not_eq_true'] at h
  obtain ⟨⟨hs, ht⟩, hcut⟩ := h
  have hs' : s ∈ S := of_decide_eq_true hs
  have ht' : t ∉ S := by simpa using ht
  have hclosed : ∀ a b, (a ∈ S) → AdmEdge Adj B a b → (b ∈ S) := by
    intro a b ha ⟨hab, hdom⟩
    have h1 := List.all_eq_true.mp hcut a ha
    have h2 := List.all_eq_true.mp h1 b (hcomplete a b hab)
    simp only [Bool.or_eq_true, Bool.not_eq_true'] at h2
    rcases h2 with h2 | h2
    · exact of_decide_eq_true h2
    · rw [hdom] at h2; exact absurd h2 (by simp)
  exact closed_no_reach (S := fun x => x ∈ S) hclosed hs' ht'

/-- Admissible routes are exactly what the true-value theorem upgrades: admissible reachability
implies non-decreasing reachability under containment. -/
theorem admReach_nd [LE α] [LT α] [LE β] [LT β]
    [DecidableRel (α := β) (· ≤ ·)] [DecidableRel (α := β) (· < ·)]
    {ι : β → α} (hα : OrderLaws α) (hι : Embedding ι) {B : Bounds V β}
    {Adj : V → V → Prop} {f : V → α} (hf : Contains ι B f) {a b : V}
    (h : Reach (AdmEdge Adj B) a b) : NDReach Adj f a b := by
  induction h with
  | refl x => exact Reach.refl x
  | step hab _ ih => exact Reach.step ⟨hab.1, domB_sound hα hι hf hab.2⟩ ih

/-- A checked route is an admissible path. -/
theorem routeB_admReach [LE β] [DecidableRel (α := β) (· ≤ ·)]
    {B : Bounds V β} {Adj : V → V → Prop} {adjB : V → V → Bool}
    (hadj : ∀ a b, adjB a b = true → Adj a b) :
    ∀ (s : V) (r : List V), routeB adjB B (s :: r) = true →
      ∀ t, (s :: r).getLast? = some t → Reach (AdmEdge Adj B) s t
  | s, [], _, t, ht => by simp at ht; subst ht; exact Reach.refl _
  | s, b :: rest, h, t, ht => by
    unfold routeB at h
    simp only [Bool.and_eq_true] at h
    obtain ⟨⟨h1, h2⟩, h3⟩ := h
    have ht' : (b :: rest).getLast? = some t := by simpa [List.getLast?_cons_cons] using ht
    exact Reach.step ⟨hadj s b h1, h2⟩ (routeB_admReach hadj b rest h3 t ht')

/-! ### Non-vacuity -/

/-- The hypothesis `Contains` is satisfiable whenever every declared interval is
well formed (`lo ≤ hi`), so the theorems above are not vacuous for well-formed tables. -/
theorem contains_satisfiable [LE α] [LE β] [Inhabited α] {ι : β → α} (hα : ∀ a : α, a ≤ a)
    {B : Bounds V β} (hwf : ∀ x l h, B x = some (l, h) → l ≤ h) (hι : ∀ {a b : β}, a ≤ b → ι a ≤ ι b) :
    ∃ f : V → α, Contains ι B f := by
  refine ⟨fun x => match B x with | some (l, _) => ι l | none => default, ?_⟩
  intro x l h hx
  simp only [hx]
  exact ⟨hα _, hι (hwf x l h hx)⟩

end DarwinBridge
