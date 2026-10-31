# Turing scope: an existing Delphi claim becoming an executable applicability check

Recorded 2026-10-31 (Seattle, PDT). Worker model: Claude Sonnet 5.5 on the existing Max subscription (no metered API, no GPU, no subagents). This is a bounded second example of the claim-reuse idea in `tasks/claim-reuse-correction.md`; it does **not** change the TrpB benchmark and trains no NCA.

## What it is, in one paragraph
Take two existing Delphi claims, `turing-ddi` and `turing-wavelength`. A requester declares a two-species linearization (Jacobian J, diffusivities), a 1-D domain length `L = r·π`, and a **zero-flux (Neumann) boundary**. The adapter checks the source record against a pinned hash, checks the declared assumptions against what the record's context requires, then classifies the declared fixed point as `stable`, `linearly_unstable` or `refused` using exact rational arithmetic over the discrete modes `q_n = n²/r²`. The point: **the continuum Turing inequality does not guarantee that a discrete domain has an unstable mode, and the infinite-domain wavelength may be unavailable.** Same chemistry, only the length changes the answer.

## Evidence typing (nothing here is observed)
| Label | Content |
|---|---|
| observed | none. No measurement is used. |
| model-derived | every number in the outputs, derived from declared inputs |
| simulated | none (there is no time integration) |
| unknown / not established | nonlinear pattern formation, any real tissue or fabricated material, that the declared J and D describe anything real, growth/mechanics/other boundaries/higher dimensions |

This is established linear mathematics. Turing 1952 already states that on a finite ring the wavelengths must divide the circumference and that the "chemical wave-length" is only approximated; the finite-domain phenomenon is in the literature (PMC9884266, cited in `docs/research/inverse-design-synthesis.md`). No novelty, wet-lab, prospective or nanofabrication claim is made.

## The example (exact)
`J = [[1,-2],[2,-3]]`, `Du=1`, `Dv=10`; `tr J = -2`, `det J = 1`. For squared wavenumber `q`: `trace = -2 - 11q`, `det = 10q² - 7q + 1 = (5q-1)(2q-1)`; the continuum instability band is `1/5 < q < 1/2` (`S = Dv·a + Du·d = 7`, discriminant 9).

| Domain | Admissible q | Result |
|---|---|---|
| `L = π` | `0, 1, 4, 9, …` | **stable**: no admissible q in the band; for all `n≥1`, `q≥1` so `det ≥ 4`, `trace<0` |
| `L = 2π` | `0, 1/4, 1, 9/4, …` | **linearly unstable**: `n=1`, `q=1/4`, `trace=-19/4`, `det=-1/8<0`; one real positive eigenvalue ≈ 0.0262 |

The recorded length scan (`artifacts/turing_scope/results.json`) shows the answer is not monotone in `L`: stable at `π/2, 3π/4, π`; unstable at `3π/2, 2π`; stable again at `5π/2`; unstable at `3π, 4π (n=2)`, `5π (n=3)`, `6π (n=3,4)`.

## Source pinning and refusals
* Bundled offline snapshot `turing_scope/sources/`: raw Delphi MCP `delphi_get_claim` responses (`source=local`) for both claims, retrieved 2026-10-31 01:32:10 PDT from the keyless endpoint `https://delphisci-mcp.fly.dev/mcp`. `pins.json` holds the content hash (canonical JSON of label, description, source, context, notation, hypothesis type, matching the `claim_runtime` convention) and the raw-response hash. Claim IRIs are the ones Delphi returned; **no nanopub or claim IDs were invented**. The records are local *unsigned* nanopubs (`math-bio-theorems/nanopubs/unsigned/*.trig`), not confirmed network publications.
* Raw-byte note: the saved research artifact recorded `81d6…` as the raw hash of `turing-wavelength`; the bytes fetched now hash to `83ca…` with identical parsed content, and two repeat fetches reproduced `83ca…`. The content hash is the identity gate.
* Refusal codes (tested): `source_missing`, `source_withdrawn`/`source_unavailable`, `claim_changed` (names the changed fields), `assumption_text_missing` (even a re-pinned record is refused if its context no longer states the assumptions the adapter needs), `iri_mismatch`, `source_malformed`, `unsupported_boundary` (Dirichlet, periodic ring, Robin, undeclared), `unsupported_domain`, `assumption_not_declared`, `fixed_point_not_declared`, `invalid_input` (floats refused: use exact strings), `claim_precondition_failed` (well-mixed state unstable), `marginal_non_hyperbolic`, `resource_limit` (cutoff above 200000 modes is refused, never truncated).
* A withdrawn `turing-wavelength` leaves the stability verdict intact and refuses only the wavelength answer.
* The adapter's mathematics is hand-written. Nothing parses the claim's math string; the claim only supplies identity, the assumptions to require, and the hash the adapter was reviewed against. The review was by the authoring model, **not an independent human**.
* `claim_runtime` is not in this branch (it is on `work/claim-reuse`/`work/release`), so this module has its own small loader. A test checks hash compatibility with `claim_runtime.common` when importable; I ran it once against `common.py` read from `origin/work/release` and it passed (see receipt). No Delphisci code was copied.

## Wavelength gate
`turing-wavelength` is licensed only if **both** hold: near onset, and domain large compared with `λc`. The record gives no numbers, so the requester must declare `near_onset_max_excess` and `min_domain_over_wavelength`; these are labelled requester-declared operationalizations. With declared tolerance 1/2 and multiple 5, the example is near onset (excess 0.225) but the domain is only ≈0.28 (L=π) / 0.56 (L=2π) wavelengths long, so the gate returns `not_licensed` on both. On `L=2π` the realized unstable mode has wavelength `2L/n = 4π`; the infinite-domain `λc ≈ 11.17` is not what the domain offers.

## Lean (`turing_scope/lean`, Lean 4.35.0, core only, no Mathlib)

Coordinator integration also mutates the actual parameterized determinant law and the Neumann mode spectrum in fresh project copies. Both must fail in `TuringScope/Basic.lean`, beyond the three constant-witness rejection tests. The audit rejects unexpected axioms, rather than only printing them. The general Lean model has integer coefficients; the Python adapter accepts exact rational coefficients. The displayed integer-coefficient example is instantiated in Lean; arbitrary adapter requests do not produce a new kernel certificate.
Integer arithmetic with `q = N/M`, `N = n²s²`, `M = p²`, `L = (p/s)π`, mode matrix scaled by `M`. Proved (axioms printed: `propext, Classical.choice, Quot.sound` only; no `sorry`, `admit`, `native_decide`):
* `modeTr_eq`, `modeDet_eq`: dispersion identities for **any** integer `a b c d Du Dv N M`.
* `neumann_tail_hurwitz`: for any J with `tr J<0`, `det J>0`, any `Du, Dv>0`, any domain `p,s>0` and any `n0` with `S·p² ≤ Du·Dv·n0²·s²`, **every** `n ≥ n0` is stable. This is the unbounded-in-`n` tail rule the Python adapter uses.
* `mode_zero_stable`, `charpoly_sign_change` (sign change `p(0)<0<p(Λ)` for `D<0`).
* Instance: `ex_modeDet_factor` (`(5N−M)(2N−M)`), `ex_det_neg_iff` (band `⇔ 1/5<N/M<1/2`), `short_all_modes_stable` (`L=π`, all `n`), `long_unstable_iff` (`L=2π`: unstable **iff** `n=1`), `domain_changes_answer` (band non-empty ∧ all modes stable on `π` ∧ some mode unstable on `2π`).

**Boundary of the formalization.** "Stable" is *defined* in Lean by the Routh–Hurwitz sign test (`trace<0 ∧ det>0`); the textbook equivalence with eigenvalue real parts is not proved. Real eigenvalues, the intermediate value theorem, the PDE and any nonlinear or biological statement are not formalized. Eigenvalues are checked numerically in Python (`numpy.linalg.eigvals`, a floating-point check, not Lean). The instance uses `decide` only for arithmetic on the fixed numerals; the scientific content is in the parameterized lemmas they instantiate.

Mutants (`lean/mutants/`, compiled by `python -m turing_scope lean-check`): the unmutated control compiles (exit 0); a reaction-law mutation (`d: −3→−2`), a diffusion mutation (`Dv: 10→1`) and a domain mutation (`L=π`) each state the unstable-mode claim and all fail (exit 1, "`decide` proved that the proposition … is false"). The same two law mutations make the Python adapter return `stable` on both domains.

## Reproduce (bounded)
```bash
B="systemd-run --user --scope -p TasksMax=128 -p MemoryMax=4G -p MemorySwapMax=0 -p RuntimeMaxSec=600"
export OMP_NUM_THREADS=2
$B python3 -m turing_scope check turing_scope/examples/long_L_2pi.json --crosscheck
$B python3 -m turing_scope check turing_scope/examples/long_L_2pi.json --source turing-ddi=turing_scope/sources/turing-ddi.local.mcp.json   # explicit local snapshot file
$B python3 -m turing_scope sources
$B python3 -m turing_scope lean-check        # lake build + audit + mutants -> artifacts/turing_scope/lean_receipt.json
$B python3 -m turing_scope demo              # -> artifacts/turing_scope/results.json, turing_scope/site/data.js
$B python3 -m pytest tests/test_turing_scope.py -q
```
Offline by default. A real snapshot from a local file is an explicit input (`--source CLAIM=FILE` or `--source-dir`); it must still match the pins. If live retrieval is needed use the keyless Delphi MCP (`delphi_get_claim {id, source:"local"}`), save the raw response bytes, and re-run `python -m turing_scope pin` as a deliberate reviewer step.

## Static demonstration and integration
`turing_scope/site/index.html` + `data.js`: pure HTML/SVG/JS, no dependencies, no imagery of cells. It displays recorded outputs of the Python run (not computed in the browser): two domain lengths (plus the scan), the unstable `q` band against the discrete modes, source claim → applicability → result, and the typed evidence banner. **To integrate** into the main site: copy `turing_scope/site/{index.html,data.js}` to `site/turing/` (files are self-contained; no path dependencies). Regenerate `data.js` after any adapter change with `python -m turing_scope demo`. I did not touch `site/` or add deployment metadata.

## Limits
Linear spectral statement for a declared Jacobian; one boundary condition; one dimension; rational lengths; two species. The chosen J is a hand-picked illustration, not fitted to a system. A matching Python/Lean result would not make a real pattern appear or fail to appear. Existing Delphi claim statuses are unchanged by this work.
