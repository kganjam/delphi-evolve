# Statement correspondence, trust base and limitations (proof worker)

Everything below is reproducible with `python scripts/check_proofs.py` (receipt:
`artifacts/proof/receipt.json`). Lean 4.35.0, no Mathlib, no `sorry`/`admit`/`native_decide`/new axioms.

## 1. What is proved (all in `lean/DarwinBridge/`)

| Plain-language statement | Lean theorem | Where |
|---|---|---|
| **Path soundness.** If every step `u→v` of a route is an edge of the graph and the interval of `u` lies entirely below the interval of `v` (`hi u ≤ lo v`), then for *every* assignment of true values that lies inside the declared intervals, the values are non-decreasing along the route; start ≤ target; every route vertex is ≥ the start value. | `route_sound`, `route_endpoints` | `Core.lean` |
| **No broken intermediate.** If the start's lower bound is ≥ θ then every vertex on the route is ≥ θ (in true value). | `route_floor` | `Core.lean` |
| **Closed-set lemma.** A set closed under a relation, containing the start and not the target, forbids reachability by that relation. | `closed_no_reach` | `Core.lean` |
| **Cut / blocked soundness.** A finite set `S ∋ start`, `target ∉ S`, such that *every* graph neighbour of every member is either in `S` or certifiably lower (`hi v < lo u`, both intervals declared), forbids any non-decreasing path from start to target, for every assignment inside the intervals. | `blocked_cut_sound` | `Core.lean` |
| **Admissible-cut soundness ("no certifiable route").** A finite `S ∋ start`, `target ∉ S`, such that every graph neighbour `v` of every member `u` is in `S` or the step `u→v` is not certified (`hi u ≤ lo v` fails, or an interval is unlisted), forbids any route of certified-dominance steps. This is the cut matching the *route* checker. It does **not** say no true non-decreasing path exists. | `adm_cut_sound`, `admCert_sound` | `Core.lean`, `Checker.lean` |
| **Admissible routes upgrade to true paths.** Under interval containment, every admissible-step path is a non-decreasing true-value path; a checked route is an admissible path. Hence a route certificate and an admissible-cut certificate for the same pair are never both accepted. | `admReach_nd`, `routeB_admReach`, `route_adm_exclusive` | `Core/Checker` |
| **Strictly weaker than blocked (counterexample, kernel-checked).** `A=[0,2]`, `B=[1,3]`, δ=0, adjacent: the admissible-cut checker accepts `S=[A]` (hi A=2 > lo B=1, so no certified step), the blocked checker rejects it, and the assignment `f A=1, f B=2` satisfies the containment hypothesis yet has a non-decreasing path A⇒B. | `Distinction.adm_accepts`, `blocked_rejects`, `true_route_exists_despite_adm_cut` | `Distinction.lean` |
| **Neighbour enumeration is complete for the declared graph** (this is what stops a cut from silently omitting an escape edge). | `nbrs_complete` (also `nbrs_sound`, `nbrs_length = 76`) | `Geno.lean` |
| **Checker ⇒ statement.** Acceptance of the executable Boolean checker `routeCertB` / `blockedCertB` implies the two soundness statements, for the concrete four-site graph and an arbitrary ordered value type `α` receiving the scaled-integer endpoints through any strictly monotone embedding `ι`. | `routeCert_sound`, `blockedCert_sound` | `Checker.lean` |
| **Non-vacuity.** An accepted table is satisfiable (some assignment lies inside all intervals), so the conditional theorems are not vacuously true. | `contains_satisfiable`, `sensitivity_satisfiable` | `Core/Checker` |
| **Consistency.** A route certificate and a blocked certificate for the same start/target/table are never both accepted. | `route_blocked_exclusive` | `Checker.lean` |
| **Instance theorems.** For each dataset instance the kernel evaluates the *same* Boolean checker: `cert_ok : routeCertB … = true := by decide +kernel`, and `instance_sound` instantiates the generic theorem on it. | `Certs/*.lean` | generated |

The theorems are **generic**: arbitrary vertex type, arbitrary graph relation `Adj`, arbitrary ordered value type with only
the minimal order laws (`OrderLaws`), endpoints mapped by a monotone embedding. They are not arithmetic on constants; the
generic statements are proved once and the instances are applications of them.

## 2. Correspondence between Lean, JSON and Python

* **Certificate JSON** (`artifacts/proof/trpb_*.json`) is the runtime input of record. It contains the source file SHA-256,
  scale exponent `k`, assumed bound δ (scaled), the table of listed genotypes with both replicate values as exact scaled
  integers *and* their exact source text, the route or closed set, assumptions and limitations, and its own digest.
* **Lean instance files** (`lean/DarwinBridge/Certs/*.lean`) are *rendered* from that JSON by `evolve.proof.render_lean`.
  `check_proofs.py` re-renders and requires byte equality (drift check) and requires the file to embed the certificate and
  source hashes. This JSON→Lean step is checked by equality, not formally verified.
* **Source → JSON**: `evolve.proof.verify_against_source` re-reads the original `summary_AA.csv`, checks its SHA-256, checks
  that each table row's text equals the source text for that genotype and that the scaled integers equal the exact decimal
  text × 10^k. Values here are exact (no rounding was needed: `outward_rounded_values = 0`). This step is Python, not Lean.
* **Python mirror** `check_certificate_python` is a *differential-testing* reimplementation of the Lean checker on exact
  integers. It is **not** a proof and never certifies anything; it agrees with Lean on all the 42 instance mutants as a consistency check
  on the tooling.
* Route / cut **search** is untrusted Python (BFS / closure). Lean only checks the finite object found.

Interval rule used by the instances: `[min(r1,r2) − δ, max(r1,r2) + δ]` computed on scaled exact integers inside Lean
(`obsBounds`). Rows absent from the table are **UNKNOWN**: the theorems never constrain them; an unknown neighbour of a cut
member makes the checker reject.

## 3. Assumptions (the theorem is conditional on these)

* **A1 interval containment** — the true scaled growth value of every listed genotype lies in its interval. This is an
  *assumption about the assay*, expressed in Lean as the hypothesis `SensitivityAssumption`. It is not proved and not tested
  by the theorem.
* **δ is an assumed sensitivity bound**, in growth-rate (`mu-bg`) units. Two replicates cannot support rigorous simultaneous
  95 % bounds across 159 129 variants; no confidence level is claimed. `δ = 0` means only the envelope of the two replicates
  (descriptive); larger δ widens it. `sensitivity_sweep.json` shows where each certificate stops existing.
* **A2 scope** — unlisted genotypes (imputed, unmeasured, stop-containing, merely not listed) are unknown.
* **A3 graph** — vertices are the 20^4 four-letter genotypes over `ACDEFGHIKLMNPQRSTVWY`; edges are single substitutions at
  the four sites. A blocked certificate is a statement about that finite graph only. Missing edges/vertices outside it, other
  residues, other positions, insertions/deletions and recombination are not covered, so "no route" never implies "no
  evolutionary route in sequence space".

## 4. Trust base and what is *not* verified formally

Trusted: the Lean 4.35.0 kernel and elaborator; `decide +kernel` evaluates the Boolean checker in the kernel and adds no axiom
(the 32-theorem audit lists only `propext`, `Quot.sound` and, for the `Distinction.true_route_exists_despite_adm_cut` counterexample alone, `Classical.choice` from `simp`; no `sorryAx`, no `Lean.ofReduceBool`).
Untrusted but checked by tests/equality: CSV parsing and exact scaling (`verify_against_source`), JSON→Lean rendering (drift
check), the letter↔index alphabet map (the theorems hold for any relabelling, but the letters in the JSON/comments are the
Python tooling's claim). Not formalized: the connection between growth-rate fitness and enzyme function; that measured
replicate envelopes contain the true value; that the Lean `Int` table equals a real number (generic `ι` embedding lets any
ordered `α`, e.g. the reals via `Int.cast` scaled by 10^k, be the value type, but no real-number instance is constructed here).

## 5. Mutation evidence (`receipt.json`)

* Instance-level (42 mutants over all five certificates): the dominance inequality violated by one scaled unit; reversed route;
  skipped (non-adjacent) vertex; unknown intermediate; negative δ; duplicate key; start = target; wrong target; cut-edge
  made equal / higher / unknown; target put inside S; start removed from S; closure member removed. All **rejected by the
  kernel's `decide`** (error text recorded). Boundary controls (`lo(next) = hi(current)`; `hi(v) = lo(u) − 1`) are
  **accepted**, proving the comparison is `≤`/`<` as stated and not over-rejecting.
* Source-level (10 mutants of the Lean checker/graph, e.g. flipped dominance inequality, dominance using `lo(u)`, unknown
  vertices treated as dominated, strict-descent flipped, cut ignoring descent, target-in-S check removed, neighbour
  enumerator omitting a position, adjacency ignoring a position): each makes the soundness proofs stop compiling (exit 1).

## 6. Prior art and novelty

Interval-dominance reasoning on graphs and reachability/cut duality are elementary. The contribution here is engineering and
evidential: a small kernel-checked bridge from replicate assay rows to an explicit conditional decision certificate
(route or blocked cut) with its scope, assumptions and failure tests. It is not a new mathematical result and not a claim
about biology. See `planning/PLAN.md` on ALDE and related work before any novelty statement.

## 7. Core κ=2 interval-model bridge (`core_kappa2_adm_cut_htgr_gtvn`) and scale limits

* **Instance.** Core's `cut_HTGR_GTVN_kappa2` (one-node closed set `{HTGR}`; all 76 neighbours measured; edge rule
  `lower[v] ≥ upper[u]`; core `body_sha256` 9ad27d69…) is re-expressed as an `adm_blocked` certificate with `δ = 0`,
  `r1 = lower`, `r2 = upper`, scale 10^6, so Lean's `obsBounds` reproduces core's exact integer intervals. 77 table rows,
  1 member, 76 crossing edges. Lean statement: **no route of certified-dominance steps from HTGR to GTVN** in the full 20^4
  graph relative to the listed table. It is **not** a proof that no true non-decreasing path exists, and
  the core interval is core's *assumed* κ=2 sensitivity model, not a confidence interval.
* **What Lean does not see.** The intervals are core's integers taken as given; `evolve.proof.verify_core_origin`
  re-derives them from the raw `summary_AA.csv` (hash-pinned) with independent code: all 77 intervals agree within 1 unit
  (1e-6 growth-rate; float summation order), and the number that agree exactly is recorded in the receipt. It also checks that
  every neighbour of the closed set is either listed or absent from the measured non-stop rows. This is Python, not Lean.
* **Omitted large instance.** A second admissible closure (parent `VFVS` → `AIKG` at assumed δ = 0.01; 23 members; 1092 table
  rows; 288 KB JSON) was generated, but its single `decide +kernel` ran together with other work inside a 5 GB scope and
  the scope was oom-killed (2026-10-31 00:25:41 PDT). It is **not part of the verified build or the receipt**. The JSON and the
  rendered Lean text are kept under `artifacts/proof/optional_unverified/` (the Lean file has a `.txt` suffix so lake never
  compiles it), explicitly **unchecked**. The cause was not diagnosed (list-based `find?` lookups over 1092 rows of 23-digit integers are one suspect). Splitting the closed set into one theorem per member would reduce per-theorem work; not attempted. Do not cite that certificate as verified.
