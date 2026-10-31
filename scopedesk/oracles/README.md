# Scope Desk oracle layer (rethink-nca)

Branch `work/rethink-nca`. Interfaces follow `scopedesk/SPEC.md` (director branch). Evidence kinds: `formal` (exact Fractions), `simulated`
(declared-model PDE), never `observed`. Run tests: `systemd-run --user --scope -p TasksMax=128 -p MemoryMax=4G -p MemorySwapMax=0 -p RuntimeMaxSec=600 env PYTHONPATH=. python3 -m pytest tests/test_scopedesk_oracles.py -q`.

| module | API | what it is |
|---|---|---|
| `linear.check(structured)` | `{verdict, scope_verdict, condition_ids, admissible_unstable_modes, witness, evidence}` | exact linear check, 1-D (Neumann/Dirichlet/periodic) and 2-D rectangle (Neumann/Dirichlet/periodic torus); `bc: null` -> evaluates Neumann and periodic, disagreement = `underdetermined`/`BC_UNSTATED`; refuses floats. `verdict` ∈ `linearly_unstable | stable | wellmixed_unstable | underdetermined | refused`; `scope_verdict` ∈ bench vocabulary `applies | out_of_scope | underdetermined | refused`. `linear.plain_formula` is the C0 baseline. |
| `pde.solve(structured, gamma=None)` | `{category, converged, settled, pattern, m_dom, amp, validity, ...}` | spectral nonlinear solve; categories `pattern | no_pattern | not_settled | nonconverged | diverged | refused | unchecked`. Needs `model` (`schnakenberg` or `brusselator`, `params`, `gamma`). Bare-Jacobian instances are refused (`no_nonlinear_model`). Only `pattern`/`no_pattern` are ever scored. |
| `repair.enumerate(structured, with_pde=False)` | `{repairs:[{knob,value,linear_verdict,pde?}]}` | knobs `domain_length` (scale of all sides), `reaction_scale` (gamma), `diffusion_ratio` (Dv); exact-checked, minimal relative change first. |
| `gate.decide(structured, records=None, pins=None, record_removed=False, record_hash_changed=False, continuum_only=False)` | `{decision, condition_ids, source_checks, baseline_C0, assumptions}` | Delphi-scoped decision with the three ablations. `baseline_C0` (plain textbook inequality) is returned in every mode. `gate.wavelength_licence` implements the bench's `wavelength_formula_licence` convention (10%). |

Structured input: `{J:[fu,fv,gu,gv] | model, params, gamma; Dv; Du(default 1); bc; r_over_pi | a_over_pi,b_over_pi}` (nested `domain` also accepted). Critic's audit runner convention (`verdict` in `linearly_unstable`/`stable` -> applies/out_of_scope) is honoured; all other verdicts are listed as `refused:<verdict>` by that runner, so note `wellmixed_unstable` (key: out_of_scope / `WELLMIXED_STABLE`) and `underdetermined` need mapping on the runner side — use `scope_verdict` directly.

## Explicit validity limits
* The nonlinear oracle is spectral Strang splitting (exact diffusion, RK4 reaction), **not** explicit-Euler finite differences. The critic showed Euler-FD flips the verdict at gamma >= 32 (Dv/Du = 10); the cause is a diffusion-only time-step bound that ignores the reaction time scale (`rd.euler_dt` now also caps dt; the scored NCA probe always passed dt explicitly, so it is unaffected). Euler results are never used by this layer.
* Convergence = identical patterned flag, dominant mode, amplitude within 10% for base, dt/2 and 2x grid **from the same band-limited initial function** (my earlier probe used per-grid white noise, which made "grid doubled" disagree for realisation reasons: agreement 0.82 vs 0.76 for new noise at the same resolution).
* Reaction CFL dt*||J_react||_1 <= 0.5 on the base run; >= 16 cells per smallest unstable wavelength; <= 256 cells (1-D) or 128x128 (2-D); horizon T = clip(30/sigma_max, 300, 3000), flagged `horizon_limited` otherwise.
* Small initial perturbations only (eps = 1e-2): finite-amplitude (subcritical) instability of a linearly stable state is not probed.
* Models are textbook equations with declared parameters; no real tissue is represented. Dirichlet/unstated boundaries are linear-only; the PDE layer supports Neumann and periodic.
* The Delphi records `turing-ddi` and `turing-wavelength` are checked by hash (turing_scope pins). The record text names no boundary condition, domain shape or wavelength tolerance; those are additions listed in `gate.decide(...)["assumptions"]`.
