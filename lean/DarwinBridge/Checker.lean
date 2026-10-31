import DarwinBridge.Core
import DarwinBridge.Geno

/-!
# Executable checkers for dataset instances (the same functions the theorems are about)

An *instance* is
* `δ : Int` — an ASSUMED sensitivity bound (scaled integer, ≥ 0).  It is not a statistical
  confidence bound; two assay replicates cannot supply one.
* `tbl : List (Geno × Int × Int)` — for each declared genotype, the two replicate growth
  values, as exact scaled integers (value × 10^k, k recorded in the certificate JSON).
  Genotypes absent from `tbl` are UNKNOWN (missing, imputed, unmeasured or just not
  listed): no theorem here constrains them.
* the interval of a listed genotype is `[min r1 r2 − δ, max r1 r2 + δ]`.

`checkRoute`/`checkBlocked` are the Boolean checkers; `routeCert_sound` and
`blockedCert_sound` are the theorems relating `= true` to the mathematical statements of
`Core.lean`.  The `decide +kernel` proofs in generated instance files evaluate exactly these
functions.
-/

namespace DarwinBridge

abbrev Table := List (Geno × Int × Int)

/-- Interval table induced by observations and the assumed sensitivity bound.
First matching key wins (duplicates are additionally rejected by `tableOkB`). -/
def obsBounds (δ : Int) (tbl : Table) : Bounds Geno Int := fun g =>
  match tbl.find? (fun e => decide (e.1 = g)) with
  | some e => some (min e.2.1 e.2.2 - δ, max e.2.1 e.2.2 + δ)
  | none => none

def keysNodupB : Table → Bool
  | [] => true
  | e :: es => !(es.any (fun e' => decide (e'.1 = e.1))) && keysNodupB es

/-- Hygiene: assumed bound non-negative, listed genotypes inside the 20^4 library, no duplicate keys. -/
def tableOkB (δ : Int) (tbl : Table) : Bool :=
  decide (0 ≤ δ) && tbl.all (fun e => decide e.1.Valid) && keysNodupB tbl

/-- Route certificate: `route` runs from `s` to `t` (`s ≠ t`), consists of `Adj` edges and every
step satisfies `hi u ≤ lo v` with both intervals declared. -/
def routeCertB (δ : Int) (tbl : Table) (route : List Geno) (s t : Geno) : Bool :=
  tableOkB δ tbl && decide (s ≠ t) && decide (route.head? = some s) &&
  decide (route.getLast? = some t) && routeB adjB (obsBounds δ tbl) route

/-- Blocked certificate: finite set `S` (listing), `s ∈ S`, `t ∉ S`, and every one of the 76
neighbours of every member is either in `S` or certifiably lower (`hi v < lo u`). -/
def blockedCertB (δ : Int) (tbl : Table) (S : List Geno) (s t : Geno) : Bool :=
  tableOkB δ tbl && decide (s ≠ t) && decide s.Valid && decide t.Valid &&
  S.all (fun g => decide g.Valid) && blockedB nbrs (obsBounds δ tbl) S s t

/-- "No certifiable route" certificate: `S` is closed under the admissible-step relation of the
table.  Weaker than `blockedCertB` (see `Core.lean`); it is the cut matching `routeCertB`. -/
def admCertB (δ : Int) (tbl : Table) (S : List Geno) (s t : Geno) : Bool :=
  tableOkB δ tbl && decide (s ≠ t) && decide s.Valid && decide t.Valid &&
  S.all (fun g => decide g.Valid) && admBlockedB nbrs (obsBounds δ tbl) S s t

/-! ### Soundness -/

section
variable {α : Type} [LE α] [LT α]

/-- Reading of the empirical premise for an instance: the (scaled) true values `f` lie in the
sensitivity envelope of the listed observations.  ASSUMPTION, not a theorem. -/
abbrev SensitivityAssumption (ι : Int → α) (δ : Int) (tbl : Table) (f : Geno → α) : Prop :=
  Contains ι (obsBounds δ tbl) f

theorem routeCert_sound {ι : Int → α} (hα : OrderLaws α) (hι : Embedding ι)
    {δ : Int} {tbl : Table} {route : List Geno} {s t : Geno}
    (h : routeCertB δ tbl route s t = true) {f : Geno → α}
    (hf : SensitivityAssumption ι δ tbl f) :
    NDRoute Adj f route ∧ NDReach Adj f s t ∧ f s ≤ f t ∧ (∀ x, x ∈ route → f s ≤ f x) := by
  unfold routeCertB at h
  simp only [Bool.and_eq_true, decide_eq_true_eq] at h
  obtain ⟨⟨⟨⟨_, _⟩, hhead⟩, hlast⟩, hr⟩ := h
  have hnd := route_sound (Adj := Adj) hα hι adjB_sound hf route hr
  cases route with
  | nil => simp at hhead
  | cons s' r =>
    have hs : s' = s := by simpa using hhead
    subst hs
    have ⟨hreach, hall⟩ := route_endpoints (Adj := Adj) hα hι adjB_sound hf s' r t hr hlast
    have hlast' : t ∈ s' :: r := List.mem_of_getLast? hlast
    exact ⟨hnd, hreach, hall t hlast', hall⟩

theorem blockedCert_sound {ι : Int → α} (hα : OrderLaws α) (hι : Embedding ι)
    {δ : Int} {tbl : Table} {S : List Geno} {s t : Geno}
    (h : blockedCertB δ tbl S s t = true) {f : Geno → α}
    (hf : SensitivityAssumption ι δ tbl f) : ¬ NDReach Adj f s t := by
  unfold blockedCertB at h
  simp only [Bool.and_eq_true] at h
  exact blocked_cut_sound hα hι nbrs_complete hf S s t h.2

end

theorem admCert_sound {δ : Int} {tbl : Table} {S : List Geno} {s t : Geno}
    (h : admCertB δ tbl S s t = true) : ¬ Reach (AdmEdge Adj (obsBounds δ tbl)) s t := by
  unfold admCertB at h
  simp only [Bool.and_eq_true] at h
  exact adm_cut_sound nbrs_complete S s t h.2

/-- Under the sensitivity assumption an admissible-cut certificate additionally rules out any
route that the route checker could accept; and an accepted route rules out the cut. -/
theorem route_adm_exclusive {δ : Int} {tbl : Table} {route S : List Geno} {s t : Geno}
    (hr : routeCertB δ tbl route s t = true) (ha : admCertB δ tbl S s t = true) : False := by
  unfold routeCertB at hr
  simp only [Bool.and_eq_true, decide_eq_true_eq] at hr
  obtain ⟨⟨⟨⟨_, _⟩, hhead⟩, hlast⟩, hrt⟩ := hr
  cases route with
  | nil => simp at hhead
  | cons s' r =>
    have hs : s' = s := by simpa using hhead
    subst hs
    exact admCert_sound ha (routeB_admReach adjB_sound s' r hrt t hlast)

/-! ### Non-vacuity and mutual exclusion -/

theorem obsBounds_wf {δ : Int} (hδ : 0 ≤ δ) (tbl : Table) :
    ∀ x l h, obsBounds δ tbl x = some (l, h) → l ≤ h := by
  intro x l h hx
  unfold obsBounds at hx
  split at hx
  · rename_i e _
    simp only [Option.some.injEq, Prod.mk.injEq] at hx
    obtain ⟨rfl, rfl⟩ := hx
    simp only [Int.min_def, Int.max_def]
    split <;> omega
  · simp at hx

/-- An accepted certificate is never vacuous: some assignment satisfies the assumption. -/
theorem sensitivity_satisfiable {δ : Int} {tbl : Table} (h : tableOkB δ tbl = true) :
    ∃ f : Geno → Int, SensitivityAssumption (fun x : Int => x) δ tbl f := by
  have hδ : 0 ≤ δ := by
    unfold tableOkB at h
    simp only [Bool.and_eq_true, decide_eq_true_eq] at h
    exact h.1.1
  exact contains_satisfiable (α := Int) (β := Int) (fun a => Int.le_refl a)
    (obsBounds_wf hδ tbl) (fun h => h)

/-- A route certificate and a blocked certificate for the same `(s, t)` and the same table can
never both be accepted. -/
theorem route_blocked_exclusive {δ : Int} {tbl : Table} {route S : List Geno} {s t : Geno}
    (hr : routeCertB δ tbl route s t = true) (hb : blockedCertB δ tbl S s t = true) : False := by
  have hok : tableOkB δ tbl = true := by
    unfold routeCertB at hr
    simp only [Bool.and_eq_true] at hr
    exact hr.1.1.1.1
  obtain ⟨f, hf⟩ := sensitivity_satisfiable hok
  exact blockedCert_sound intLaws Embedding.id hb hf
    (routeCert_sound intLaws Embedding.id hr hf).2.1

end DarwinBridge
