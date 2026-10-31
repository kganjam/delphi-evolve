# SPEC-009 — Verification Ladder and the Anti-Triviality Gate

**Status:** Draft · **Version:** 0.1.0 · **Owner:** G5

## Scope

Covers how a MorphoSwarm claim earns a verification level, how equations become machine-checked
Lean 4 theorems, and how vacuous proofs are rejected automatically.

In scope: the L0–L5 ladder and what each level does and does not prove; the autoformalization
pipeline; the anti-triviality gate; proof receipts; the informal↔formal correspondence record.

Not in scope: `validation_status` for a whole model (SPEC-014, which delegates its Lean check to
this spec); publication of verification results (SPEC-007); the schema that stores them
(SPEC-008, table `verification`).

> **Verified checkers, [SPEC-050](SPEC-050-causal-factors-belief-graph.md) and [ADR-0017](../docs/decisions/ADR-0017-lean-verified-checkers.md)
> (proposed 2026-10-20).** A Lean result built as *checker plus proved soundness theorem* is
> evaluated with `decide +kernel` on literal data, which G3 rejects as written. ADR-0017 proposes
> amended G1–G4 for that result kind only:
> - template-emitted files;
> - graph-mutation sensitivity;
> - a registered soundness theorem whose conclusion is the registered statement;
> - a constructed witness model.
>
> The amendment takes effect with M110. Until then nothing changes, and an unproved checker never
> reaches L2.

> **Statement audits are measured before they are trusted (added 2026-10-20, from
> [research/science-agent-benchmarks.md](../docs/research/science-agent-benchmarks.md) §3–§4 and P2).**
> CausalSmith (Tan & Syrgkanis, arXiv:2607.22511 v4, `full-text`; repo `a7085d8`, Apache-2.0)
> has the best-specified statement audit the report found. Its authors write that they "do not
> estimate how often they err". No other source read for that report or for
> [formalization-correctness.md](../docs/research/formalization-correctness.md) measures the
> error rate of an auditor of scientific statements either. This spec therefore adds two things:
> - **Mechanical statement checks** that need no trust (§Mechanical statement checks, rules 13
>   and 14): the axiom allow-list and keyword scan run over the dependency cone, and an
>   unused-hypothesis flag.
> - **A planted-drift benchmark** (§Statement-audit drift benchmark, rule 15) that measures any
>   statement auditor, blind or sighted, before its output may be cited.
>
> Open question 6 is not resolved by this. It gains a measurement plan.

> **The gate must see the original theorem compile (added 2026-10-21, from the studio demo,
> [docs/demo/studio-runbook.md](../docs/demo/studio-runbook.md)).** Read from
> `verify/anti_triviality.py` on main: `verify_anti_triviality` never kernel-checks the
> unmutated module. Its Lean calls are G4's hypothesis probe and, per mutant, a `sorry` probe and
> a proof under a fallback script. Rule 16 makes the gate check the original itself, and a note
> under it says what a gate pass is while the correspondence is unreviewed. The **L1** acceptance
> row is corrected, because as written it could only be passed by special-casing the scaled
> Gray–Scott card.

## Motivation

"Verified" is the most over-claimed word in computational science. A system that says only
"verified / not verified" is useless, because the interesting question is always *what exactly was
checked*. A dimensional check and a Bitcoin-anchored empirical replication are both "verification"
and they are not remotely the same claim.

This spec exists because of a documented, concrete failure. MorphoLib's
`morphoeval/lean/loops/Loop_0393_acanthometra_pellucida_clock_wavefront.lean` is advertised as
machine-checked formal verification of the clock-and-wavefront mechanism. It kernel-checks with
`0 sorry`. Here is its entire mathematical content, verbatim:

```lean
/-- Law 2: Kuramoto-Delta-Notch Synchronization Rate (d(delta_phi)/dt = -(K_c - omega_tau) sin(delta_phi)) -/
def law2_balance (p q : Int) : Int := p + q - q

theorem law2_exact_cancellation (p q : Int) :
    law2_balance p q = p := by
  dsimp [law2_balance]
  omega

/-- Law 3: Kinematic Phase-Gradient Doppler Shift (omega_ant / omega_post = 1 + u_wf * |nabla_x phi| / omega_0) -/
def law3_threshold_margin (lhs rhs : Int) : Int := lhs - rhs

theorem law3_instability_criterion :
    law3_threshold_margin 70 19 > 0 := by
  decide
```

The docstrings name real mechanisms. The Lean proves that `p + q - q = p` and that `70 - 19 > 0`.
Both proofs are valid. Neither has anything to do with Kuramoto coupling or Doppler shift.

This is exactly the failure mode Sundial identifies: **a Lean proof can be perfectly valid while
proving the wrong translation of the author's statement.** The kernel cannot catch it, because the
kernel was never shown the biology. Only a gate that compares the formal statement against the
model it claims to be about can catch it — and that gate is the centrepiece of this spec.

For contrast, `Loop_002_limit_cycle_turing.lean` (hand-built, 8 KB versus 1.1 KB) states the
Schnakenberg reaction terms with the paper's own variables and cites Eqs. (15)–(20) and (24):

```lean
def schnakenberg_react_u (a u flux : Int) : Int := a - u + flux
def schnakenberg_react_v (b flux : Int)   : Int := b - flux

theorem schnakenberg_equilibrium_zero_flux (a b u flux : Int) :
    schnakenberg_react_u a (a + b) b = 0 ∧
    schnakenberg_react_v b b = 0 ∧
    schnakenberg_react_u a u flux + schnakenberg_react_v b flux = a + b - u := by
  simp [schnakenberg_react_u, schnakenberg_react_v]
  omega
```

The gate must accept the second and reject the first, mechanically.

## Schema

### The ladder

| Level | Question | Engine | Proves | **Does not prove** |
|---|---|---|---|---|
| **L0** Structural | Is the artifact well-formed? | pySHACL **≥ 0.40.1** + Pydantic | Required fields present, types and cardinalities correct, IRIs resolve in shape | Anything about content being right |
| **L1** Dimensional | Do units and dimensions balance? | Pint + QUDT | Every equation is dimensionally homogeneous; parameters carry compatible units | That the magnitudes, signs or the equation itself are correct |
| **L2** Logical | Does a stated property follow from stated assumptions? | **Lean 4** kernel | The theorem is a consequence of its hypotheses, with `0 sorry` | That the formal statement **is** the biological claim; that the assumptions hold of any real organism |
| **L3** Model | Does the system satisfy a temporal/behavioural property? | **Two instrument families, see [SPEC-043](SPEC-043-verification-languages.md) and [ADR-0010](../docs/decisions/ADR-0010-l3-continuous-models.md)**: `discrete-model-checking` (BIOCHAM 4, PRISM/STAMINA, CRNT-Lean) and `validated-reachability` for continuous systems | A sound claim over a **set** of states, not sampled points, under the stated parameter regime | That the model is the organism |
| **L4** Numerical | Are the computed trajectories and bounds reliable? | Interval arithmetic, UQ, convergence/refinement tests | Discretisation error is bounded; the result is not a numerical artefact | That the continuous model is right |
| **L5** Empirical | Does the real system behave this way? | Held-out observations, prospective experiment | A prediction matched measurement under stated conditions, with controls | That it generalises to another organism, strain or context |

Normative reading: levels are **independent evidence, not a totally ordered pipeline**. A claim may
hold L0, L1 and L5 while failing L2 because nobody has formalised it. A claim that holds L2 and
nothing else is a mathematical statement about a model, and MUST be described as such.

### `VerificationResult`

| Field | Type | Required | Description |
|---|---|---|---|
| `subject_kind` | enum | yes | `model_card` \| `design` \| `claim` |
| `subject_ref` | string | yes | The thing verified |
| `level` | enum | yes | `L0`…`L5` |
| `passed` | bool | yes | Outcome |
| `engine` | string | yes | Tool and version, e.g. `lean4:4.15.0` |
| `statement_ref` | string | L2/L3 only | Declaration name, e.g. `schnakenberg_equilibrium_zero_flux` |
| `correspondence_ref` | string | L2/L3 only | The informal↔formal record (below) |
| `gate_report` | object | L2 only | Anti-triviality gate output |
| `receipt_hash` | sha256 | yes | Proof-receipt hash |
| `detail` | object | no | Engine-specific output |

### The informal↔formal correspondence record

The artifact that would have caught Loop_0393. One per formalised law, reviewed as its own object.

| Field | Type | Required | Description |
|---|---|---|---|
| `law_id` | string | yes | Stable id, e.g. `cooke-clock-and-wavefront-1` |
| `model_card_ref` | string | yes | Which ModelCard this law belongs to |
| `informal_statement` | string | yes | The law as the paper states it, with its source equation number |
| `source_locus` | string | yes | DOI + equation/section, e.g. `10.1016/S0022-5193(76)80131-2 §2 Eq. 3` |
| `formal_statement` | string | yes | The Lean declaration, verbatim |
| `symbol_map` | map | yes | Paper symbol → Lean binder, e.g. `{"S": "segment_len", "u_wf": "wavefront_speed", "T": "clock_period"}` |
| `scope_caveats` | string[] | yes | What the formalisation deliberately does not capture |
| `reviewed_by` | string | yes | Who checked the correspondence — MUST NOT be the agent that wrote the Lean |
| `reviewed_at` | ISO-8601 | yes | |

`symbol_map` is what makes the gate possible: it is the machine-checkable bridge between the
model's parameters and the theorem's binders.

### Proof receipt

Adopted from `resources/research/catalogue-proof-receipts-grounding-2026-10-17.md` §2.2 in
`kganjam/scienceclaw-hackathon-ideas`.

| Field | Type | Description |
|---|---|---|
| `ontology_commit` | sha | Commit of the ontology the claim is expressed in |
| `shape_hash` | sha256 | Hash of the SHACL shapes used at L0 |
| `lean_toolchain` | string | `leanprover/lean4:v4.x.y` exactly as pinned in `lean-toolchain` |
| `proof_hash` | sha256 | Hash of the `.lean` source checked |
| `mathlib_rev` | sha | If Mathlib is used |
| `result` | enum | `YES` \| `NO` \| `INDETERMINATE` |
| `checked_at` | ISO-8601 | |

`INDETERMINATE` is a first-class outcome. A gate that cannot decide MUST say so rather than defaulting to pass.

## Protocol — autoformalization pipeline

```
1. extract        paper equation + symbols   -> informal_statement, source_locus, symbol_map
2. formalise      informal + symbol_map      -> Lean def(s) + >=1 theorem
3. kernel-check   .lean                      -> exit 0, 0 sorry, 0 errors
4. GATE           theorem + symbol_map + model -> pass | fail | indeterminate   (<< the new part)
5. correspond     informal vs formal         -> correspondence record, independently reviewed
6. register       law                        -> MATH_LAWS_REGISTRY entry
7. receipt        all of the above           -> proof receipt, hashed
8. link           receipt                    -> verification row (SPEC-008) + KG claim (SPEC-007)
```

Lean **is now installed and pinned** — `scripts/install_lean.sh` (task M15) provisions `elan` and
the toolchain named in `lean-toolchain`, writing the pin on first bootstrap so every later machine
is reproducible. Installed and verified 2026-10-20 **[read: ran it]**:
**Lean 4.35.0** (`eb6cafb7290e8bd5f2937522d8d804f58f02bafc`), **Lake 5.0.0**. The toolchain version
goes into every receipt. Mathlib is deliberately **not** built by that script — it costs hours and
gigabytes, and the gate below does not need it. That has a consequence recorded in the next
section.

#### The triviality claims, checked rather than asserted

This spec previously described MorphoLib's generated Lean as trivial on the strength of reading
it. With a toolchain available the claims were **run** **[read: `lean` on Lean 4.35.0,
2026-10-20]**, and one of them needed correcting:

| Claim | Result |
|---|---|
| `law2_balance p q := p + q - q`, theorem `= p`, is provable with no model content | **Confirmed.** Compiles in **core** Lean with `dsimp [law2_balance]; omega` — the form the corpus itself uses; 0 errors, 0 `sorry`. **The unfold is required:** plain `omega` FAILS, because it does not unfold a definition and instead reports a counterexample over the opaque term. An earlier version of this row said `omega` alone, which reads as a broken gate rather than a missing tactic |
| …and is *definitionally* trivial, i.e. `rfl` | **Wrong, corrected.** `rfl` **fails** on `Int`: `law2_balance p q` is not definitionally equal to `p`, because `Int` subtraction does not reduce that way. The theorem is content-free about biology, which is the point, but it is not a definitional identity and this spec should not have implied it was |
| `by decide` on literals (`(70 : Nat) - 19 > 0`) compiles with no model symbol | **Confirmed**, 0 errors |
| **Gate G2 (mutation sensitivity) actually discriminates** | **Confirmed.** Mutating the law to `p + q + q` makes the same theorem **unprovable** — `omega` reports a counterexample satisfying `q ≤ -1`. The gate separates the two, which is the property it was specified for |
| The binder `q` is wholly free | **Confirmed.** `law2_balance 999 (-7) = 999` and `law2_balance (-3) 100000 = -3` both close `by decide`, so `q` is unconstrained by the law — exactly what grounding gate G1 is meant to catch |

**Operational consequence of the no-Mathlib decision:** `ring` is **not available** in core Lean,
so gate implementations and generated proofs MUST restrict themselves to core tactics (`omega`,
`decide`, `simp`, `rfl`) unless and until a project explicitly takes a Mathlib dependency and
fetches it with `lake exe cache get`. A gate that shells out to `ring` would fail on a clean
install of this toolchain, and would fail in a way that looks like a proof failure rather than a
missing dependency.

**What changed after that decision, measured 2026-10-26.** The paragraph above is still true of
`lean/morphoswarm-core`. It is no longer true of the host. A second Lake package,
`lean/morphoswarm-causal` (SPEC-050, M110), requires Mathlib at the revision its `lakefile.toml`
pins, on Causalean's toolchain, Lean 4.33.0. The store it builds in, `morphoswarm-causalean` under
the clone's git common directory, holds a **built** Mathlib: 8,322 `.olean` files under
`packages/mathlib` **[read: `find`, 2026-10-26]**, about 15 GB for the whole store **[read: `du`,
the same day]**. M109 measured one Mathlib-importing check at 3,273,816 KB peak RSS (about
3.1 GiB) and 4.4 s warm. So the repository has two Lean environments:

| Package | Toolchain | Mathlib | Checked by |
|---|---|---|---|
| `lean/morphoswarm-core` | 4.35.0 (`lean-toolchain`) | none | the anti-triviality gate, `attacks/formalize.py`, the mechanism theorems |
| `lean/morphoswarm-causal` | 4.33.0 (Causalean's pin) | built, in the store | `verify/coherence_lean.py`, `verify/causal_identify_lean.py` |

**The consequence for mechanism theorems.** Both mechanism theorems in core are stated over
surrogates: `GiererMeinhardt.lean` over `Rat` and `PolarAuxinConservation.lean` over `Int`.
`verify/entailment.py` carries the caveat that *"the extension to the real parameter space is by
the algebraic form of the proof and is not kernel-checked"*. That caveat was forced while no
Mathlib existed here. It is now a placement choice, because a kernel-checked statement over `ℝ` is
buildable on this host. The two cases differ:

- The polar-auxin proof reindexes a finite sum, so a statement over any commutative ring covers
  `ℝ` with nothing new to prove.
- The Gierer–Meinhardt proof uses division, inverses and order, where moving from `Rat` to `ℝ`
  is not a formality.

M2422 owns both proofs. They run in the Mathlib package, under M2421's capped launcher, and each
receipt records the 4.33 toolchain and the Mathlib revision (rule 8).

Two toolchains do not break rule 8, since each receipt names its own. A theorem must still not
be cited across them: a 4.35 core proof and a 4.33 Mathlib proof of "the same" statement are two
receipts, and neither stands in for the other.

### The anti-triviality gate (step 4)

Four independent criteria. A theorem earns L2 only if it passes **all four**.

#### G1 — Model-symbol grounding

The theorem's statement MUST reference at least one binder that `symbol_map` maps to a declared
parameter or state variable of the ModelCard.

- Loop_0393 `law2_exact_cancellation (p q : Int)` — binders `p`, `q` map to nothing. **Fail.**
- Loop_002 `schnakenberg_equilibrium_zero_flux (a b u flux : Int)` — `a`, `b` are the Schnakenberg
  feed rates, `u` the activator, `flux` the autocatalytic term `u²v`. **Pass.**

Implementation: parse the declaration signature with the Lean frontend (`lake env lean --json` or
`#eval` of a metaprogram emitting the declaration's binder names and type), intersect with
`symbol_map` values, require a non-empty intersection.

#### G2 — Mutation sensitivity

The theorem MUST FAIL when the law it is about is mutated. This is the strongest criterion: a
theorem insensitive to the model is not about the model.

Mutation operators applied to the `def` bodies the theorem depends on:

| Operator | Example |
|---|---|
| `SWAP_OP` | `+` ↔ `-`, `*` ↔ `/` |
| `NEGATE_TERM` | `a - u + flux` → `a - u - flux` |
| `DROP_TERM` | `a - u + flux` → `a - u` |
| `PERMUTE_ARGS` | `f a b` → `f b a` (when types allow) |
| `CONST_PERTURB` | numeric literal `k` → `k + 1` |
| `IDENTITY_COLLAPSE` | replace the body with its first binder |

Procedure: generate mutants, re-run the kernel on each, record which still compile **and** still
prove the theorem. A mutant that compiles and still proves it is a **survivor**.

Required: **kill rate ≥ 0.80** over applicable mutants, and `IDENTITY_COLLAPSE` MUST be killed
unconditionally.

`law2_balance p q := p + q - q` collapses to `p` under `IDENTITY_COLLAPSE`, and the theorem `= p`
still holds. Survivor. **Fail.**

**What "applicable" means, defined 2026-10-21.** A survivor that is a **proved-equivalent mutant**
is outside the denominator. Three conditions, all required:

1. **The equivalence proof is a compiled replay and nothing else counts.** A mutation-control
   theorem, kernel-checked with `0 sorry`, showing the *mutated* law still satisfies the property.
   A declaration that a mutant "looks equivalent" is not a proof and MUST NOT exclude it.
2. **The proofs are recorded on the verdict**, one per excluded mutant, so a reader re-checks them
   rather than trusting the count.
3. **At most half the applicable mutants may be excluded.** Without a cap, a theorem passes by
   declaring most of its mutants equivalent, which converts the gate into a formality.

**Why this is a correction and not a relaxation**, which matters because `AGENTS.md` §1 rule 5
forbids relaxing a criterion to make a task pass. M319's core-Lean auxin conservation theorem
passes G0, G1, G3 and G4, kills both one-sided-flux mutants, and scores **9/13 = 0.69**. All four
survivors are equivalent, each with a kernel-compiled replay proving the mutated law still
conserves: `J i j - J i j` and `J j i - J j i` (zero transport), `D / l i j * (a i - a j)` (a
symmetric coefficient), and `D * l j i * …` (`l` symmetric by hypothesis). **So any bare
conservation law fails G2**, while §8c routes conservation to L2. Reaching 0.80 would mean padding
the theorem with conjuncts that restate definitions — **the gaming this entire gate exists to
forbid**. A gate that pushes toward the behaviour it forbids is the defect, not the theorem.

Equivalent-mutant exclusion is the standard treatment in mutation testing, and its standard
failure is that "equivalent" becomes an escape hatch. Conditions 1–3 are what stop that, and the
check on them is a mutation of its own: **count an unproved survivor as equivalent and the gate
must fail.** Reported by the session running M319; the implementation is M349.

**A replay-based equivalence test is sound in one direction only.** A found proof means the mutant
is equivalent; a *missing* proof does **not** mean it is inequivalent — it may mean the replay
script was too weak. M319's builder reports one such case among its nine kills: the mutant
`D * l i j / (a i - a j)` is in fact a true law, because `Int` `ediv` is odd in its divisor, but
the replay does not find that proof and the gate counts it as a kill. So the kill side of the
count carries false positives that condition 1 cannot remove, and M349 MUST NOT report its
classification as exact in either direction. *Reported by that session; the `ediv` parity is the
part to re-derive before citing it.* The asymmetry favours the strict direction — a mutant wrongly
counted as killed inflates the kill rate, which is the direction that lets a weak theorem pass, so
it is a real limit on what a 0.80 means and not a conservative margin.

**So a mutant carries one of four labels, but only two of them are scoring-neutral** (added
2026-10-21, from ADR-0025 gap K12 via ubuntu-bd):

| label | what it means | effect on the rate |
|---|---|---|
| `killed` | the mutant compiles and the theorem no longer proves | numerator and denominator |
| `survived` | compiles, still proves, **no** compiled equivalence replay | denominator only — counts against |
| `proved-equivalent` | survivor with a compiled replay meeting conditions 1–3 | outside both (capped at half) |
| `equivalence-unknown` | an equivalence replay was **attempted and did not compile** | **unchanged from its side** — `killed` or `survived` as measured |

The last row is the one to get right, and it is a reporting change rather than a scoring one.
Absence of a proof is not evidence either way, so it MUST NOT move a mutant out of the denominator
— that is condition 1, and relaxing it here would reopen the escape hatch from the other side.

**This repository already states the principle one level down**, which is why the rule above is an
application rather than an invention: [SPEC-043](SPEC-043-verification-languages.md) rule 4 —
*"`inconclusive` MUST NOT be reported, aggregated or rendered as `satisfied`. Any claim depending
on an `inconclusive` property MUST be blocked, not downgraded silently."* An unproved equivalence
is an `inconclusive`, and **both** ways of mis-sorting it are that forbidden promotion: excluding a
survivor renders it `satisfied` on the survivor side, and counting an unproved kill renders it
`satisfied` on the kill side. The denominator rule and `kill_rate_lower_bound` are the two halves
of not doing it.

The trade is worth stating plainly, from ADR-0025: keeping `equivalence-unknown` in the
denominator costs **false rejections, which are visible and reversible** — a reviewer promotes a
mutant to `proved-equivalent` later by supplying the proof, so the label is a to-do rather than a
verdict — whereas counting it as killed would pass vacuous laws **invisibly**.
What it MUST do is be visible: the count of `equivalence-unknown` mutants is reported beside the
rate, because a rate resting on failed searches is weaker than the same rate resting on none.

On the kill side that visibility is quantifiable, so the gate MUST also report

```
kill_rate_lower_bound = (killed − equivalence_unknown_kills) / (applicable − equivalence_unknown_kills)
```

which is the rate that would hold if **every** unproved kill turned out to be an equivalent mutant.
It is a genuine lower bound: for `killed < applicable`, removing a mutant from both sides lowers
the ratio. A verdict whose `kill_rate` clears 0.80 but whose `kill_rate_lower_bound` does not is
a **pass that depends on a failed search**, and MUST be recorded as such on the verdict so the
dependence is legible rather than inferred by whoever reads it next.

> **This bound is vacuous as the procedure now stands, and that is a defect in this amendment
> rather than in its implementation** (found 2026-10-21 by reading M349's code, which states it
> plainly in a comment instead of computing a meaningless number). Equivalence is probed **only on
> survivors** — survival is a precondition for attempting the replay at all — so
> `equivalence_unknown_kills` is structurally **0**, `kill_rate_lower_bound` always equals
> `kill_rate`, and `depends_on_failed_search` can never be true.
>
> **The bound was specified to catch one known case and is blind to exactly that case.** M319's
> mutant `D * l i j / (a i - a j)` is counted as a *kill* and is in fact a true law, because `Int`
> `ediv` is odd in its divisor. Nothing re-probes it, so the safeguard added for it cannot see it.
> A safeguard that cannot fire is the defect this spec's own G2 and G4 sections exist to find, and
> it reached `main` in the amendment that introduced them.
>
> **What would make it meaningful, and what it costs.** Probing every kill for equivalence doubles
> the replay attempts — one extra kernel run per killed mutant, so ~13 for M319's theorem — which
> is why it is not simply mandated here. The proportionate rule, and the one to implement: **probe
> a kill on demand**, when a reviewer disputes it or when its operator belongs to a class known to
> produce true laws (integer division and subtraction are the two established cases). Until a kill
> is probed, its label is `killed` and the bound reports equality honestly; a disputed kill that is
> then proved equivalent leaves the denominator like any other proved-equivalent mutant. **Open
> question 11 tracks it**, because the alternative — leaving a formula in the spec that always
> returns the same number as the thing it is meant to qualify — is worse than naming the gap.
>
> **Swept for others, and the scope of that negative matters more than the result.** Searching
> `src/` for the shape this one had — an input documented as structurally constant — found
> **exactly one** instance, this one (`verify/anti_triviality.py`). Two near-matches are not the
> same class: `publish/trusty.py`'s *"can never parse back as anything but the IRI it came from"*
> and `evidence/belief/elicit.py`'s *"can never exceed the uniform prior"* are **designed
> properties**, which is what a correct invariant reads like, not dead branches.
>
> **What the search cannot see is the point.** It finds a vacuous input only where someone *wrote
> down* that it is constant — which happened here because the implementer was honest about a zero
> they could not make non-zero. A vacuous safeguard that nobody noticed leaves no comment to grep
> for, so this negative covers *documented* cases only and says nothing about the rest. The
> general detector is the one this spec already mandates elsewhere: **run the arm and require it
> to kill**. A safeguard with no arm is unfalsifiable by construction, and `kill_rate_lower_bound`
> had none — it was specified, reviewed and landed without anything ever asking it to fire.

#### G3 — No literal-constant decision

The proof MUST NOT be closed by `decide`, `norm_num`, `native_decide` or `rfl` acting on a goal
containing only numeric literals and no universally quantified model symbol.

- `theorem law3_instability_criterion : law3_threshold_margin 70 19 > 0 := by decide` — goal is
  `70 - 19 > 0`, all literals. **Fail.** Where did 70 and 19 come from? Nothing says.
- `decide` closing a goal that quantifies over a model parameter is fine and MUST NOT be rejected.

#### G4 — Non-vacuity

- Hypotheses MUST be satisfiable **when the conclusion is something other than `False`**. If
  `hypotheses → False` is provable, that theorem is vacuous. **Fail.** For a theorem whose
  conclusion *is* `False`, see "Refutations" below.
- The conclusion MUST NOT be a syntactic identity after unfolding the definitions it names — i.e.
  `dsimp only [defs]` MUST NOT reduce the goal to `X = X` or `True`.
- `law2_balance p q = p` unfolds — explicitly, via `dsimp` or `unfold`; `omega` will not do it — to `p + q - q = p`, an `omega` identity over `Int` with no model
  content. **Fail.**

**Refutations, defined 2026-10-21.** The satisfiability bullet above, as it stood, rejected every
*refutation* by construction: a theorem whose content **is** that a set of constraints cannot all
hold concludes `False` from them, so the gate's vacuity probe and the theorem's own result are the
same proof. Vacuity is a defect of the hypotheses *relative to some other conclusion* — the
conclusion earns nothing because nothing satisfies the premises. Where the conclusion is the
unsatisfiability, there is no other conclusion left to be vacuous about.

This is not hypothetical. **M112** ("Lean incoherence certificates for elicited probability sets")
has as its acceptance *"a Farkas certificate from M106 replays in Lean as a proof of `False` using
its own multipliers"*, so under the old bullet M112 could never mint L2 — the same shape as the G2
defect above, where the gate's test coincided with the theorem's result.

The implementation did not protect against this; it only failed to notice, and which way it fell
depended on the number type rather than on the theorem. Measured on this host 2026-10-21 with
Lean 4.35.0, core only, on M106's own incoherent set (`P(A)=.7`, `P(B)=.6`, `P(A∧B)=.1` carrying the
Boole–Fréchet bound `P(A∧B) ≥ P(A)+P(B)-1` as a hypothesis). What was run is the probe's **tactic
on that goal shape**, hand-written — `example <binders> : False := by omega`, which is the source
`_g4` builds at `verify/anti_triviality.py` (read on main, not inferred) — and not `_g4` itself
end to end:

| statement of the same set | probe `omega` | old G4 verdict |
|---|---|---|
| over `Int`, scaled ×10 to clear denominators — what an integer Farkas certificate produces | **compiles** | **fail** — "hypotheses are unsatisfiable" |
| over `Rat`, unscaled | does not compile ("No usable constraints found") | pass |

So a correct refutation was rejected or admitted according to whether its multipliers had been
cleared of denominators. A gate whose verdict turns on that is reporting nothing about the
theorem.

**The gate therefore splits by mode, and the mode is read off the goal, never declared.** A
statement is a **refutation** iff `dsimp only [defs]` leaves `False` as the head of its conclusion
(`¬ P` is `P → False`, so a negated predicate qualifies once unfolded). An author-supplied `mode`
field MUST NOT be accepted: it would be an opt-out from vacuity checking of exactly the kind that
"this mutant looks equivalent" was from G2.

For a refutation, non-vacuity is **not** satisfiability — it is that the contradiction is *derived
from the model*. Three conditions:

1. **The contradiction MUST NOT be assumed.** No hypothesis may be `False` itself, and no two may
   be syntactically `h : P` and `h' : ¬ P`. **Fail.**
2. **It MUST depend on the model.** Delete every hypothesis mentioning a symbol in the statement's
   `symbol_map`; the proof MUST then fail. One that still compiles proves `False` from constants,
   which is G3's family arriving by another route. **Fail.**

   *Its scope is narrow and worth stating, so nobody reads it as the strong check.* Deleting
   **all** the hypotheses leaves `False` unprovable in a consistent logic, so this condition can
   only fail when a hypothesis that mentions **no** model symbol carries the contradiction by
   itself — a false numeric side condition, say. It is a real case and the overlap with G3 is
   deliberate, but condition 3 is where a refutation is actually tested. A refutation that passes
   2 and skips 3 has been barely checked.
3. **Every multiplier MUST be load-bearing**, and this is where the teeth are. The certificate
   names the hypotheses it uses with a nonzero multiplier; for each, deleting that one hypothesis
   MUST make the proof fail. A certificate that still closes without a hypothesis it claims to
   use has decorative multipliers — the refutation analogue of a theorem insensitive to its law.
   Record the per-hypothesis deletion outcomes on the verdict, as G2 records its mutants.

**When there is no multiplier record, condition 3 degrades to leave-one-out.** Not every
refutation comes from a Farkas certificate — a non-linear incoherence, or one closed by `linarith`
without an explicit witness, names no multipliers. The gate then deletes each hypothesis
mentioning a `symbol_map` symbol in turn and requires **at least one** deletion to break the proof.
That is strictly weaker than condition 3 (it establishes dependence on *something* in the model,
not that each claimed multiplier is used), and it costs one kernel run per such hypothesis plus
the original. A verdict reached this way MUST record `"minimality": "leave-one-out"` so a reader
is not told condition 3 ran when it did not.

**Non-minimality beyond condition 3 is a flag, not a failure**, consistent with rule 14's
treatment of unused hypotheses. An irrelevant extra constraint makes a refutation inelegant; the
smaller infeasible subset it contains is still a genuine incoherence. What is fatal is a
contradiction that does not need the elicited set at all, which is condition 2.

**G2 still applies to a refutation, and is a real gate there, not a formality.** Mutating the
elicited set should make it feasible, and a feasible set has no Farkas certificate, so the proof
must stop compiling. M112 is not being waved through: it exchanges a gate it could never pass for
one it must actually survive.

#### Gate output

```json
{
  "statement_ref": "law2_exact_cancellation",
  "verdict": "fail",
  "criteria": {
    "G1_symbol_grounding": {"pass": false, "detail": "binders [p,q] intersect symbol_map {} = empty"},
    "G2_mutation":         {"pass": false, "kill_rate": 0.0, "survivors": ["IDENTITY_COLLAPSE"]},
    "G3_literal_decide":   {"pass": true},
    "G4_non_vacuity":      {"pass": false, "detail": "goal reduces to Int identity p + q - q = p"}
  }
}
```

`G4_non_vacuity` on a **refutation** carries `"mode": "refutation"` — derived from the unfolded
goal, never from the statement's own declaration — plus `hypothesis_deletions`, one entry per
hypothesis the certificate uses with a nonzero multiplier, recording whether the proof still
compiled without it. A refutation verdict that reports no deletions has not run condition 3 and is
`indeterminate` under rule 5, not a pass.

### Mechanical statement checks (with step 3)

> **Added 2026-10-20.** These come from CausalSmith's mechanical audit layer (§5.3 and Table 4,
> as read in the report). That layer rejects any artifact containing `axiom`, `sorry`, `admit`,
> `opaque` or `unsafe` "or any library module it transitively depends on", and it runs an
> unused-hypothesis lint.

**What exists today.** We read `src/morphoswarm/verify/anti_triviality.py` on 2026-10-20. M17's
gate scans the source text of the **one module** under test for `sorry`, `admit`,
`native_decide` and `axiom` (`_FORBIDDEN_TACTS`, plus the `axiom` keyword). The modules the gate
generates for mutation set `linter.unusedVariables false`. So rule 7 is enforced over one file,
and nothing looks at hypotheses the proof never uses.

**Axioms over the dependency cone.** Run `#print axioms <theorem>` and allow only `propext`,
`Classical.choice` and `Quot.sound`. This check covers the whole dependency cone by construction.
The ADR-0017 spike showed that a `native_decide` proof appears in it as
`<thm>._native.native_decide.ax_*`. That `sorry` appears in it as `sorryAx` is standard Lean
behaviour; M217's test confirms it rather than assuming it.

**Keyword scan over project packages.** `#print axioms` does not report an `opaque` or `unsafe`
declaration, because neither one is an axiom. So the keyword scan covers `sorry`, `admit`,
`axiom`, `opaque` and `unsafe` over the theorem's module and every module in its import cone
that belongs to a project or third-party Lean package: our `lean/` packages, and Causalean at its
pin. It **excludes** the pinned toolchain's core library and the pinned Mathlib revision. Both
legitimately contain `opaque` and `unsafe` declarations, so a scan that included them would fire
on every theorem and be ignored. Both are still covered by `#print axioms`.

**Unused hypotheses.** A hypothesis that the proof never uses is **flagged, not failed**. It is
either decoration, which CausalSmith reads as "the statement says less than intended", or a
condition the source states that the formal argument happens not to need. The flag is cleared
only by a `departures` entry ([SPEC-041](SPEC-041-formalization-workbench.md)) or a reviewer note
that says which of the two it is. G2 cannot see this case. Its operators mutate `def` bodies,
and a hypothesis nothing uses survives every one of them. The check runs on the original module,
never on the gate's generated mutants, which have the linter switched off.

### Statement-audit drift benchmark (for step 5)

> **Added 2026-10-20, from the report's P2.** This plants known drift into correct
> (statement, Lean) pairs and measures what catches it. The kernel and G1–G4 answer whether the
> proof is valid and non-trivial. This benchmark measures the other question: *is it a proof of
> the right thing?*

**Corpus.** The corpus is a set of pairs, each a source statement with a locator plus its Lean
declaration, judged correct by a person before any mutation. Otherwise the false-alarm rate on
"unmutated" pairs has no meaning. The pairs come from three places:
- the gate's accepted theorems, Schnakenberg and the Gierer–Meinhardt steady state;
- MorphoLib's hand-built `MathOfBiology.lean` core (MIT, upstream `469bf3c`);
- the six Causalean definitions that [SPEC-050](SPEC-050-causal-factors-belief-graph.md)
  consumes, after M109's correspondence audit.

**Mutation operators.** These are taken from CausalSmith's Table 4 failure taxonomy and its
F4 and presentation-stage verdicts. They are *drift* operators applied to the statement side.
They are distinct from G2's law operators, which mutate the `def` body.

| Operator | Plants | CausalSmith's name |
|---|---|---|
| `DROP_HYP` | Remove a load-bearing hypothesis | over-narrow / wrong statement |
| `ADD_HYP` | Add a hypothesis the source does not state | over-assumption |
| `HARDCODE_CONST` | Replace a general binder by a constant | over-narrow ("hardcoded constant where general was intended") |
| `WEAKEN_CONCL` | Replace the conclusion by a consequence it implies | `derived` |
| `TRUE_CONCEPT` | Define a concept the statement uses as `True` | vacuity |
| `AXIOMATIZE` | Replace a proved step by an `axiom` | unproved step |
| `MISTAG_CITED` | Relabel a proved dependency as a cited external result | unproved step ("mis-tagged as cited") |
| `DILUTE` | Name a condition without its quantitative form | dilution ("present in NAME but absent in SUBSTANCE") |

**Only mutants that still kernel-check test an auditor.** A mutant the kernel rejects, or one
that the mechanical checks or G1–G4 catch, is recorded as caught *at that layer*. It is not
counted in an auditor's detection rate. Each mutant's record names the first layer that caught
it, so the result shows which defences carry the load. For example, `AXIOMATIZE` should die at
`#print axioms`, and `TRUE_CONCEPT` may die at G4.

**Auditors measured side by side** on the same surviving mutants:
- **(a) blind back-translation**, as open question 6 proposes (Sundial's design). It sees the
  Lean and the meanings in the symbol map, never the source.
- **(b) sighted equivalence review**, CausalSmith's design. It is given the source statement, the
  Lean, unfolded definitions and a notation table. It back-translates, then checks two-sided
  equivalence: "equivalent assumptions and equivalent conclusions, with neither stronger nor
  weaker".
- **(c) the cheap version** that open question 6(c) asks for: back-translate, embed both texts,
  and report the distance.

**Reported per auditor configuration.** A configuration is the model, its version, the prompt
hash and the blind/sighted setting. For each one the report gives:
- detections over surviving mutants, per operator;
- false alarms over unmutated pairs;
- the auditor's model family, and the formalizer's model family.

All are reported as **counts**. A corpus of tens of pairs, crossed with eight operators and with
kernel-caught mutants removed, leaves cells with single-digit or low double-digit counts.

**What the result licenses.** A configuration with measured counts may be used as a flag for
review (open question 6(a)), and its counts travel with every flag it raises. It never becomes a
verdict. A changed model or prompt is a new configuration and needs a new measurement.

## Rules

1. Every published claim MUST state which ladder levels it passed and MUST NOT imply others.
2. A level MUST NOT be asserted without a stored `VerificationResult` and a proof receipt.
3. **The compiler, not the agent, decides what is proved.** An agent's assertion that a proof
   succeeded MUST NOT be accepted; only kernel exit status and the checked artifact count.
4. L2 MUST NOT be granted unless the anti-triviality gate returns `pass` on all four criteria.
5. A gate verdict of `indeterminate` MUST be recorded as such and MUST NOT be treated as a pass.
6. Every formalised law MUST have a correspondence record, and the reviewer MUST NOT be the agent
   that produced the Lean. This is the only defence against a valid proof of a wrong translation.
7. `0 sorry` is necessary and not sufficient. `sorry`, `axiom` (other than Lean's own) and
   `native_decide` in a load-bearing proof MUST each fail the check.
8. The Lean toolchain and Mathlib revision MUST be pinned and recorded in every receipt. An
   unpinned proof is not reproducible and MUST NOT count.
8a. An L3 result **MUST** record its `instrument_family`
    ([ADR-0010](../docs/decisions/ADR-0010-l3-continuous-models.md)). Results from
    `discrete-model-checking` and `validated-reachability` **MUST NOT** be pooled without it,
    under the same rule that forbids mixing `independently-verified` with `source-only`. A
    simulation sweep is **not** an L3 instrument however many seeds it uses, because it claims
    nothing about the states it did not visit — that is L4.
8b. Where no instrument in either family applies to a model class, the ladder state is
    **`not-applicable`**, which is distinct from `not-attempted` and from `inconclusive` and
    **MUST NOT** reduce a MorphoEval score. Scoring a vertex model below a three-species CRN
    because the CRN's class happens to have a tool would make the ladder a measure of model
    class rather than of verification.
8c. Structural properties of continuous models — Turing instability, conservation, energy decay —
    route to **L2 here**, not to L3. That is a stronger claim than L3 can make, and the ladder
    must not read it as a lower rung.

9. L3 results MUST record the parameter regime they hold over; a temporal property verified in one
   regime MUST NOT be reported as holding generally.
10. L5 MUST use observations that were not used to fit the model (cross-ref SPEC-004 §discriminate,
    SPEC-006 held-out protocol). Fitting and validating on the same data MUST NOT be reported as L5.
11. Reports and UI MUST NOT aggregate levels into a single "verified" badge or score. Badges are
    per level (SPEC-013).
12. Mutation testing MUST run in a sandbox with a wall-clock cap; a timeout counts as a **survivor**,
    not a kill, because an unkilled mutant is unproven.
13. **Rule 7 MUST be checked over the dependency cone, not the one file.** L2 MUST NOT be granted
    unless two conditions hold. First, `#print axioms` for the theorem reports nothing beyond
    `propext`, `Classical.choice` and `Quot.sound`. Second, a scan of the theorem's module and of
    every project or third-party package module in its import cone finds no `sorry`, `admit`,
    `axiom`, `opaque` or `unsafe`. The pinned core library and the pinned Mathlib are excluded
    from the keyword scan, not from `#print axioms`. *(Added 2026-10-20.)*

    **The Mathlib exclusion extends to the packages that enter the cone only as its dependencies,
    and to nothing else.** *(Amended 2026-10-22, from M110.)* Two tokens in **Batteries** made
    M110's unmutated baseline red — `unsafe` at `Batteries.Tactic.Alias:166` and
    `private opaque spec` at `Batteries.Data.MLList.Basic:71` — neither in Causalean, neither an
    axiom, and both in modules the theorem does not use. Batteries arrives as a dependency of the
    pinned Mathlib/Causalean closure, so reading "the pinned Mathlib" as the package alone while
    scanning the package Mathlib itself is built on is incoherent: it excludes the library and
    flags its foundation. The excluded set is therefore **derived from the Lake manifest** — the
    pinned core library, the pinned Mathlib, and whatever enters the cone only because one of
    those pins it — and never a hand-maintained list, which would drift the moment a pin moved.

    **What stays scanned is the point of the rule**: our own modules, and any third-party package
    we pin *directly*. Causalean is ours by that test and is scanned, which is what ADR-0017
    requires it for — `#print axioms` catches an `axiom` and `native_decide` but **not** an
    `opaque` or `unsafe` declaration, so the keyword scan is the only check for those and must
    not be widened to cover a package we chose.

    **And the exclusion is reported, not silent.** The gate names the modules it skipped, because
    an exclusion nobody can see is indistinguishable from a scan that found nothing — the failure
    `AGENTS.md` §2b describes. `#print axioms` remains unexcluded over the whole cone, and on
    M110 it demonstrably bites: arm 4's `sorryAx` kill is what shows the first condition is live
    while the second was being argued about.

    *This settles a question M110 raised rather than created. It was reported as a normative
    conflict in the rule; it is not — the rule was under-specified about a package's closure, and
    `Batteries` is the first dependency to expose that.*

    **What this costs to implement, read from the code rather than guessed**: the mechanism
    exists and is one step short. `verify/statement_scan.py` already has
    `ModuleKind.EXCLUDED_PIN` and skips it beside `CORE` (line 1563), and `PackagePin(name, url,
    rev)` already carries a package's exact identity. What it does not have is plurality — line
    1465 compares `PackagePin(package.name, package.url, package.rev) == mathlib_pin`, a single
    pin by equality. So the amendment needs `mathlib_pin` to become the excluded **set**, derived
    from the manifest, and nothing else: no new module kind, no new scan, no change to
    `#print axioms`.

    *Not verified on this host, and the reason is recorded rather than worked around:* Mathlib is
    deliberately unbuilt here (§7), and `lean/morphoswarm-core/lake-manifest.json` pins **zero**
    packages, so the inherited-dependency markers this rule derives the set from cannot be read
    from this checkout. The implementer reads them from the real closure at Causalean's pin.
14. A hypothesis the proof does not use MUST be flagged on the `VerificationResult`. The flag is
    not a failure. It MUST be cleared only by a recorded `departures` entry or a reviewer note
    saying why the hypothesis is there. *(Added 2026-10-20.)*
15. **No statement auditor's output may be cited as evidence that a formal statement means its
    source until that auditor's configuration has measured counts on the drift benchmark.** This
    covers LLM back-translation, LLM equivalence review and embedding distance. A measured
    configuration contributes a flag for review, never a verdict, and it MUST NOT gate L2 on its
    own. The kernel and G1–G4 decide L2. The correspondence record (rule 6) decides what the
    proof is about. *(Added 2026-10-20. The basis is the report's P2, together with BadScientist's
    finding that LLM reviewers detected fabricated papers at near-chance rates for two of the
    three reviewers tested.)*
16. **The gate MUST NOT return `pass` for a theorem whose unmutated module, with its own proof,
    has not kernel-checked (exit 0, no errors) in the same run.** The gate report records that
    exit code. A failed or timed-out original check makes the verdict `fail` or `indeterminate`
    respectively, never `pass`. *(Added 2026-10-21, from the studio demo.)*

> **Notes on rule 16 (added 2026-10-21, from the studio demo).**
> - **Why G2 is not evidence the original compiles.** G2 proves each mutant under a fallback
>   script, `first | (<original>) | (dsimp [defs]; try simp; try omega; try decide; try rfl;
>   done)` (`_prove_script`). Killing every mutant therefore says nothing about whether the
>   original proof closes. Pipeline step 3 kernel-checks before step 4, but rule 3 ("the compiler,
>   not the agent, decides") has to hold inside the component that enforces it, not only in the
>   caller that happens to run it first.
> - **What was and was not observed.** The studio panel ran its own kernel stage on the exact
>   file and stopped a claim before the gate when that stage failed. While `formalise` emitted
>   `simp` that made no progress ([SPEC-034](SPEC-034-math-pipeline.md) §Scope note), no original
>   theorem compiled, and nothing in the gate's code path would have noticed. Nobody measured a
>   false `pass` from a non-compiling theorem; the rule rests on the code path. The fix is on
>   branch `feat/studio-2` and not on main as of 2026-10-21.
> - **A gate `pass` is not L2 until the correspondence is reviewed.** The studio showed L2 as
>   passed beside "correspondence NOT reviewed" because it read this spec as silent. It is not:
>   `VerificationResult.correspondence_ref` is required for L2, rule 6 requires a reviewed record
>   for every formalised law, and SPEC-034's **Correspondence enforced** row stops a statement
>   reaching `proven` without one. Until a reviewer distinct from the author signs the record, a
>   surface shows the gate verdict and no L2 badge. *(2026-10-22: the rule was written here and
>   still broken in two panels, `formal` and `causal`, each recording L2 `passed` with "not
>   reviewed" in its own note. Both now read one function, `studio.context.gate_l2_state`, which
>   returns `passed` only when every judged statement is at stage `proven`, and draw an
>   unreviewed gate pass as `indeterminate` with the gate receipt kept. The evidence panel's L2
>   is a kernel recomputation of belief arithmetic, not a translated law, and is out of this
>   rule's reach.)*

## Acceptance

| Check | Command / criterion |
|---|---|
| Toolchain | `scripts/install_lean.sh && lean --version` exits 0; version matches `lean-toolchain` |
| Kernel | `lake env lean <module>.lean` exits 0 with no `sorry`, no errors |
| `sorry` detector | A module containing `sorry` fails the check, not just warns |
| **Gate rejects real trivia** | Gate on `Loop_0393` `law2_exact_cancellation` returns `fail` citing G1, G2, G4; on `law3_instability_criterion` returns `fail` citing G3 |
| **Gate accepts real substance** | Gate on `Loop_002` `schnakenberg_equilibrium_zero_flux` returns `pass`, and on a Gierer–Meinhardt homogeneous steady state with symbolic binders returns `pass`. **Corrected 2026-10-20 — this row used to also demand `pass` on `turing_differential_diffusion_instability` and `gray_scott_homogeneous_equilibrium`, and it was wrong on both.** Honouring it would have required disabling the gate |

**Why those two were removed, since removing an acceptance row needs more justification than
adding one.** M17 implemented the gate, found both rows unsatisfiable without weakening G2 and
G3, and recorded them as defects instead of relaxing the criteria (AGENTS.md §1 rule 5). Checked
independently against the corpus theorems:

* `turing_differential_diffusion_instability` is
  `turing_fourier_det 4 (-6) 5 (-6) 1 1 0 = 6 ∧ …` — **four evaluations of a polynomial at
  hard-coded integers, closed by `decide`.** It states nothing general about a Turing
  instability; it is arithmetic on constants. That is precisely what G3 exists to reject, and
  what AGENTS.md §1 rule 4 names ("not reduce to `decide` on constants"). The gate is right.
* `gray_scott_homogeneous_equilibrium` proves `gray_scott_react_u F 1 0 = 0 ∧
  gray_scott_react_v F k 1 0 = 0`. Substituting `v = 0` annihilates every term —
  `-(1·0·0) + F(1−1) = 0` and `1·0·0 − (F+k)·0 = 0` — so the statement holds for **any** kinetics
  of that shape, whatever the law says. G2 measured a **kill rate of 0.21** against a 0.80
  threshold: four mutations in five leave the theorem provable, because the theorem does not
  depend on the law. The gate is right again.

Both are *true* theorems that *compile* with *zero `sorry`*, and both are vacuous with respect to
the model they are named after. They are better test cases than the row's author realised — as
**negative** ones. An acceptance criterion that would have forced the gate to accept them is the
most dangerous kind of defect this repository can carry, because satisfying it honestly is
impossible and satisfying it dishonestly looks like success.
| Mutation kill rate | ≥ 0.80 over applicable mutants for every L2-granted theorem; `IDENTITY_COLLAPSE` killed 100% |
| Correspondence | Every L2 result has a correspondence record with a non-empty `symbol_map` and a reviewer distinct from the author |
| L0 | pySHACL reports conformant for a valid ModelCard; a card missing `validation_status` is non-conformant |
| L1 | Pint rejects a deliberately unit-mismatched equation. It accepts the Gray–Scott system written in physical units (`tests/test_ladder_l0_l1.py::test_l1_accepts_length_aware_gray_scott_and_uses_srepr_not_latex`). On the scaled-form card it returns `fail` (`::test_l1_does_not_claim_the_scaled_spec_card_passes_physical_laplacian`) when the card declares `unit_regime: physical`; declared `nondimensionalised` it passes (`tests/test_nondimensionalisation.py::test_the_nondimensionalised_worked_example_passes`), and with no declaration it is `unverified`. *(Corrected 2026-10-23: this said "until SPEC-001 open question 0 (M85) gives a machine-readable scaling declaration". M85 is `passed` and the declaration is `ModelCard.unit_regime`, which SPEC-001 defines as of M326, §`UnitRegime`.)* Special-casing the example remains forbidden. **Corrected 2026-10-21, from the studio demo.** The row used to end "accepts the Gray–Scott system", which read as the scaled card. Over the 15 registry sidecars (`verify_l1` run on main `855f0ed`, 2026-10-21: 44 equations, 5 pass, 8 fail, 26 unverified, 5 not-applicable), L1 fails 8 equations: 6 are a laplacian on scaled coordinates (open question 0) and 2 are discrete-time updates (SPEC-001 open question 0b). Neither class is an error in the source paper. **Those figures predate M85 and no longer describe main.** Re-measured 2026-10-23 at `cf9354811` by loading every card in `data/registry/model_cards/` and calling `verify_l1`: **2,015 cards, every one `unit_regime: unknown`, every one `unverified`, 0 equations read** — M85 made an undeclared régime `unverified` before any equation is read, and no registry card declares one. Control: the same script reads 7 equations on the three `studio/specimens/capitulum/cards/` cards (`physical`, all `pass`) and 8 on the reconstruction card (`nondimensionalised`). So L1 currently checks nothing in the registry; the backfill is M2314 |
| Indeterminate | A theorem whose mutants time out yields `indeterminate`, never `pass` |
| Receipts | Every receipt validates and contains ontology commit, shape hash, toolchain, proof hash |
| No aggregation | No API or template emits a single boolean `verified` field |
| **Original compiles first (M262)** | `uv run pytest tests/test_gate_original_compiles.py -q`. The checks: a module whose theorem's own proof fails to close (for example `unfold; simp; omega` where `simp` makes no progress) gets no `pass`, even when every mutant is killed; the gate report carries the unmutated module's kernel exit code; a timeout on that check yields `indeterminate`; Schnakenberg still passes (rule 16) |
| **Dependency-cone checks (M217)** | `uv run pytest tests/test_statement_scan.py -q`. The checks: a theorem whose own file is clean but which imports a project module containing `sorry` or `axiom` fails; a `native_decide` proof fails through `#print axioms`; a `sorry` two imports away surfaces as `sorryAx`; an `opaque` declaration in a project module fails the scan while core and Mathlib `opaque`s do not; an unused hypothesis is flagged and the theorem is not failed |
| **Drift corpus (M218)** | `uv run pytest tests/test_drift_corpus.py -q`. The checks: every one of the eight drift operators produces at least one mutant; each mutant records whether it still kernel-checks and the first layer that caught it; unmutated pairs carry a person's correctness review |
| **Refutation mode (M495)** | `uv run pytest tests/test_anti_triviality.py -q`. The checks: a theorem whose unfolded goal is `False` is judged in refutation mode and is **not** failed for unsatisfiable hypotheses; an assumed contradiction (a hypothesis `False`, or `h : P` beside `h' : ¬ P`) fails; a refutation still compiling after every `symbol_map`-bearing hypothesis is deleted fails; a declared multiplier that is not load-bearing under its own deletion fails; an author-declared `mode` is ignored in favour of the unfolded goal; and a refutation verdict with no `hypothesis_deletions` is `indeterminate`, never `pass` |
| **Auditors measured (M219)** | `uv run pytest tests/test_statement_audit_results.py -q`. The checks: the results file has a count for every operator × configuration cell over surviving mutants, false alarms over unmutated pairs, and the model family of both auditor and formalizer, and it names no rate without its count |

## Open questions

8. **Extraction may be the better direction than translation, and there is a sound precedent.**
   This spec assumes the pipeline is *equation → Lean definition → theorem*: take the model we
   already have and formalise it. Coates (2020), *A Formalisation of Biochemical Process
   Languages in Lean* (`docs/prior-art/formalization-landscape.md` §6.1), runs the opposite
   direction — write the biology in a structured calculus (continuous π-calculus: species,
   prefixes, transitions), prove the **semantics sound**, and **extract the ODEs** from it
   (his §4.4.4), with worked Lean for an enzyme system, synthesis and degradation,
   phosphorylation, and a perfectly adapted response.

   If the equations are *derived* rather than *transcribed*, the derivation is the thing that
   carries the proof, and the wrong-translation failure mode this spec is built around
   **partly dissolves**: there is no informal source statement to mistranslate, because the
   formal object came first. That is a different and in some ways stronger position than
   back-translation (open question 6) or redundant formalization, both of which detect a bad
   translation rather than avoiding one.

   It does not dissolve entirely, and the residue is where the work is: *"is this calculus the
   right description of this biology"* replaces *"is this Lean the right translation of this
   sentence"*. The question moves from the formalization step to the modelling step, where it is
   more visible and more arguable — which is an improvement, not a solution.

   **Blockers to check before this becomes a plan.** Coates is **Lean 3**, and Lean 3 → Lean 4 is
   a rewrite, not a port; whether anyone has ported it is a five-minute check nobody has done.
   And cπ is a process algebra over species and reactions, which suits biochemistry and does not
   obviously suit the continuum mechanics and geometry that most of our corpus is written in. A
   calculus that covers reaction networks and not morphogen gradients would serve part of the
   registry and leave the rest where it is — which may still be worth it, but should be decided
   rather than discovered.

6. **We require the informal↔formal correspondence to be recorded; we do not check it.** This
   spec's central worry is that *a valid proof of a wrong translation* is undetectable by the
   kernel, and its answer is to make the correspondence an artifact that is reviewed and stored.
   Sundial's answer is a mechanism: a **blind audit agent** that *"sees only Lean"*, has no access
   to the source paper, **back-translates each statement into LaTeX**, and flags inconsistencies
   against the original `.tex` — described as *"an additional check on top of the Lean compiler"*
   (`docs/prior-art/formalization-landscape.md` §7).

   **The blindness is the whole mechanism.** An auditor that has read the source will read the
   Lean as meaning what the source meant; one that has not must recover the meaning from the
   formal statement alone, which is exactly the question being asked. A back-translation produced
   with the source in context tests nothing.

   Open issues before adopting it here. (a) It is an **LLM checking an LLM**, and Project Delphi's
   plan says plainly that *"an LLM judging its own answer is not an acceptance gate"* — so a
   disagreement between back-translation and source is a **flag for review**, never a verdict, and
   must not gate L2 on its own. (b) Biology makes it harder than mathematics: back-translating
   `turing_unstable D_u D_v` into prose a biologist would recognise requires the symbol map to
   carry meaning, not just names, which is SPEC-001 open question 4's territory (QUDT coverage;
   it was numbered 3 until that duplicate was resolved). (c) The cheap
   version is worth measuring first — back-translate, embed both, and report the distance — since
   a measured disagreement rate on the corpus would tell us whether the full mechanism earns its
   cost.

   **Update 2026-10-20: not resolved, but it now has a measurement plan** (from
   [research/science-agent-benchmarks.md](../docs/research/science-agent-benchmarks.md) §3–§4).
   CausalSmith's statement audit makes the opposite design choice. Its auditor is **sighted**:
   it gets the source statement, the Lean, unfolded definitions and a notation table, and is told
   to "Back-translate the paper statement into Lean-shaped natural language … then compare".
   CausalSmith does not discuss blindness; that contrast is the report's observation. Neither
   design has a measured error rate. CausalSmith's own words are "frontier models handled it
   well in our observations, but we do not estimate how often they err".

   BadScientist (arXiv:2510.18003, read by a sub-agent; its Table 4 was re-checked) is the
   evidence that an LLM reviewer's acceptance carries little information. Its fabrication
   detection reached 67.0% for o3, 46.0% for o4-mini and 50.0% for GPT-4.1, against a 50%
   baseline. Those are reviews of whole AI/ML papers, with OpenAI models on both sides.
   Comparing one declaration with one sentence is a narrower task and plausibly fares better.
   That is unmeasured.

   So the choice between (a) blind, (b) sighted and (c) embedding distance is made by
   measurement on the drift benchmark (M219), not by argument. The point above, that "the
   blindness is the whole mechanism", is a hypothesis that the benchmark tests.

7. **Our anti-triviality gate runs after the proof; Sundial attacks the statement before it.**
   Their adversary agent *"tries to break each statement and checks whether it survives trivial
   cases"* **before** any proving, and in their own preprint test it *"found a broken definition
   that earlier runs had missed"*. M17's gate mutates the law and re-runs the kernel, which
   requires a proof to exist first.

   These are complementary rather than alternatives, and the ordering is the point: a statement
   that cannot survive triviality screening should never have a proof attempted against it, and
   pre-filtering is strictly cheaper than discovering vacuity afterwards. The cost argument is
   concrete here — every Lean invocation is capped at 4 GB and Mathlib peaks at 2.49 GB RSS, so
   proof attempts are the expensive step. Pre-filter the statement, then gate the proof.

10. **Is leave-one-out strong enough for a refutation with no multiplier record?** *(added
    2026-10-21, with the G4 refutation split.)* It establishes that the contradiction needs some
    model hypothesis, which rules out a proof of `False` from constants. It does not rule out a
    refutation that leans on one hypothesis and carries the rest as scenery, and it cannot, because
    without multipliers there is nothing to compare the deletions against. Two candidates not
    chosen: require every model hypothesis to be load-bearing (too strong — a genuine incoherence
    in a subset would fail), or require the proof to be reported as an explicit witness in all
    cases (pushes a Lean-shaped obligation onto M106's elicitation). Needs a measurement: how often
    a refutation in our own corpus has a strictly smaller infeasible subset than it declares.

11. **When should a KILL be probed for equivalence?** *(added 2026-10-21, with the correction
    above.)* `kill_rate_lower_bound` is vacuous until some kills are probed, and probing all of
    them doubles the replay cost. M319 supplies the only measured instance of a kill that is
    really an equivalent mutant (`Int` `ediv` odd in its divisor), so the base rate is unknown and
    plausibly small. Candidates: probe on reviewer dispute; probe when the operator is `SWAP_OP`
    or `CONST_PERTURB` over `Int`, where the two known cases live; or probe a fixed sample and
    report the rate so the bound can be estimated rather than computed. **Needs a measurement
    before a rule**: how often a kill in our own corpus survives an equivalence replay. Until
    then the bound reports equality and says so.

1. **Kill-rate threshold.** 0.80 is a starting figure, not a measured one. It should be calibrated
   against the ~100 hand-built MorphoLib Lean modules once the gate runs over them — if substantive
   theorems routinely score below it, the operators are wrong, not the theorems.

   **PARTLY CLOSED 2026-10-21, and this question predicted its own answer.** A substantive theorem
   did score below it — M319's conservation law at 0.69 — and the operators *were* wrong, exactly
   as the last sentence anticipated: they counted four kernel-proved equivalent mutants as
   survivors. The fix is the applicability definition added to G2 above, not a lower bar; **0.80
   is unchanged**. What remains open is the original question, now narrower: the threshold is
   still uncalibrated against the corpus, and the ~100 hand-built modules have not been run
   through the gate.
2. `Int`-valued formalisations of real-valued dynamics (as all the MorphoLib loops use) sidestep
   analysis. Should the gate penalise an integer surrogate for a continuous law, or is that a
   legitimate, clearly-scoped abstraction that `scope_caveats` can carry?
3. G1 depends on `symbol_map`, which is author-supplied and therefore gameable. Can the mapping be
   independently checked against the ModelCard's declared parameters and the source equation text?
4. Mutation testing cost at corpus scale — 1,000 modules × ~6 operators × kernel time. Needs
   incremental caching keyed by proof hash.

   *Note, 2026-10-21, from the studio demo (measured by the studio, not re-run here).* Each
   mutant costs two kernel runs, a `sorry` probe and a proof. One core-Lean run took 0.5 s on an
   idle host and 0.8–1.3 s at load average 34. A 6-mutant claim took 21–24 s live at loads of
   34–80. Rule 12 asks for a wall-clock cap but gives no budget model, and a live surface needs
   one: the studio capped live runs at 10 mutants and refused claims above that. Rule 16 adds one
   more run per theorem.
5. Which L3 engine first? BIOCHAM covers reaction networks well. For vertex, continuum and PDE
   models — a large fraction of the corpus —
   [ADR-0010](../docs/decisions/ADR-0010-l3-continuous-models.md) resolves the shape of the
   answer: a second instrument family (`validated-reachability`), structural properties routed to
   **L2** here rather than to L3, and `not-applicable` as an honest ladder state. Which
   reachability engine remains open pending the M68 spike; no candidate is installed.
   *(Corrected 2026-10-26: the engine is no longer open. M68 passed and ADR-0013 was Accepted on
   2026-10-20: JuliaReach 0.33.0 decided a bounded invariant of the exact corpus Turing ring for
   t in [0,1], and returned `unknown` for [0,5]. Two things are still missing. The engine was
   installed under `/tmp` for the spike, not provisioned. And no recorded artifact carries an L3
   verdict. M2423 and M2424 own them.)*
6. Whether an `indeterminate` gate verdict should block publication entirely or publish with an
   explicit "unverified at L2" badge. Current lean: publish with the badge; silence is worse.
9. **Pre-proof drift screening** *(added 2026-10-20)*. CausalSmith runs a "presolve" before
   committing pipeline time: one call that attempts the result and attacks its own attempt. It
   also runs the D0-max "maximality" review before formalization. Open question 7 already asks
   for triviality screening before proof. Should the drift operators above also run before a
   proof is attempted? `WEAKEN_CONCL` and `ADD_HYP` mutants that are *easier* to prove than the
   original are exactly what a prover under pressure drifts towards. CausalSmith's first
   motivating failure was "the model altered a hypothesis, so the Lean 4 code proved a weaker
   statement than the paper claimed".

**Proposed from MorphoLib (2026-10-28).** In §Mechanical statement checks add (a) a static
formula-identifier lint, which requires the identifiers of a stated formula to appear in the paired
Lean `def`, and a classification of a quantified statement as `structural` or `ground_arithmetic`
according to whether its bound quantifier is referenced in the conclusion, both run before G1; (b) a
per-corpus template census, which reports how many files of a set are the placeholder trio; and (c)
an import path that admits upstream's Lean statements as `source-only` input and runs them through
G1 to G4, so that the result is a level and upstream's "0 sorry" is never shown as ours. Upstream's
own template gate and census are described in
[`docs/research/morpholib-spec-coverage.md`](../docs/research/morpholib-spec-coverage.md), §a.12 and
§f. This is P6 there. **Not normative.** No row is filed (none filed yet).

## References

- MorphoLib `morphoeval/lean/loops/Loop_0393_acanthometra_pellucida_clock_wavefront.lean` — the
  verbatim negative example (1,138 bytes, three trivial laws)
- MorphoLib `morphoeval/lean/loops/Loop_002_limit_cycle_turing.lean` — the verbatim positive
  example (8,050 bytes, Schnakenberg 1979 Eqs. 15–20, 24)
- MorphoLib `morphoeval/lean/MathOfBiology.lean`, `morphoeval/math_kg.py` — the 25-theorem
  hand-built core and its `MATH_LAWS_REGISTRY`
- `kganjam/scienceclaw-hackathon-ideas`
  `resources/research/catalogue-proof-receipts-grounding-2026-10-17.md` §2.2 — proof-receipt design
- `docs/prior-art/formalization-landscape.md` — Sundial, BIOCHAM 4, CRNT-Lean, the four-level table
- SPEC-008 (`verification` table), SPEC-013 (badges), SPEC-014 (delegates its Lean check here)
- [`docs/research/science-agent-benchmarks.md`](../docs/research/science-agent-benchmarks.md) §3–§4 and P2:
  CausalSmith's statement audit (arXiv:2607.22511 v4, `full-text`; repo `a7085d8`, Apache-2.0)
  and BadScientist (arXiv:2510.18003). These are the sources of the mechanical checks, the drift
  operators and rules 13–15
- [SPEC-041](SPEC-041-formalization-workbench.md) — the correspondence review that the drift
  benchmark measures, and the `ReviewRecord` carrying an auditor configuration
- Fisher & Henzinger, *Executable Cell Biology*, Nat. Biotechnol. 2007
