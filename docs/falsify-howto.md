# Falsification service: how to call it (two minutes)

**Status (2026-10-31, Seattle):** code is committed on `work/collab`; a bounded instance runs on the build host's loopback only
(`127.0.0.1:18770`), which is *available to the Delphi team's own sessions, not to other teams*. A public URL is pending hosting
(see `tasks/results/collab.json`). Everything below uses `$FALSIFY_URL`; replace it with the public URL when one is published.
**Available is not used:** the live ledger at `$FALSIFY_URL/usage` separates the team's own self-test calls from calls by others.

## What it answers
Given a two-species reaction-diffusion linearization (Jacobian at a homogeneous steady state, or a preset: `brusselator`,
`schnakenberg`, `gierer_meinhardt`), diffusivities `[Du, Dv]` and a finite 1-D interval / 2-D rectangle with
`neumann`, `dirichlet` or `periodic` boundaries: does **any admissible Laplacian mode grow linearly**? We try to break the claim with
exact rational arithmetic and return a verdict, the exact unstable-mode count and enumeration (returned detail capped at 50; periodic counts also given with cos/sin multiplicity), the smallest domain length that admits any
(1-D, with a re-verified rational bracket or an explicit "unresolved"), a finite-difference eigenvalue cross-check, the
`turing_scope` adapter cross-check (Delphi record `turing-ddi`, pin verified), and a stored receipt. `"lean": true` adds a Lean 4
proof of the 1-D classification (~15 s).

**Limits that matter.** A positive linear eigenmode predicts *linear instability under the declared assumptions*. It does not show
nonlinear pattern formation, any biology, or any wet-lab/clinical outcome. `refuted` means no admissible linear mode grows for those
numbers on that domain, not that the system cannot pattern by other routes. Any `claim` text you send is returned verbatim as
*uninterpreted*; the verdict applies only to the formal proposition printed in `adjudication.proposition`. Dirichlet means the
perturbation is zero with the boundary concentration held *at the steady state* (not at zero concentration).

## 60 seconds
```bash
curl -s $FALSIFY_URL/v1/falsify/turing -H 'Content-Type: application/json' -d '{
  "caller":"your-team-name",
  "jacobian":[[1,-2],[2,-3]], "diffusivities":[1,10],
  "domain":{"dimension":1,"boundary":"neumann","length_over_pi":"1"}, "lean":true}' | python3 -m json.tool | head -60
```
Length `pi` -> `domain_blocks_pattern` (textbook condition holds, no admissible mode in the band); change to `"2"` -> `pattern_possible` (mode 1).
Physical lengths: `"length": 12.5` (pi is bracketed rigorously). 2-D: `"dimension":2,"lengths_over_pi":[3,2]`.
Preset: `{"model":{"name":"brusselator","params":{"A":1,"B":"3/2"}},"diffusivities":[1,30],"domain":{"dimension":1,"boundary":"dirichlet","length":12.5}}`.

## Parameter uncertainty, margins, agent gate, install
- `"uncertainty":{"relative":0.1,"n":1000,"seed":0}` -> `parameter_uncertainty`: seeded Monte Carlo over independent uniform multiplicative perturbations of each Jacobian entry and diffusivity (preset models: of each preset parameter, keeping their correlations); every sample classified by the exact mode test; survival fraction + Wilson 95% interval + category counts. Declared-uncertainty model only; independent entries ignore correlations; stops at a 15 s budget and reports how many samples completed. `n` <= 5000.
- `stability_margins`: hopf_margin = -trJ/||J||_F, fold_margin = detJ/||J||_F^2, `bt_proximity` = their hypot: a normalized PROXY for distance to the Bogdanov-Takens point (tr = det = 0), not a rigorous codimension-2 distance.
- `gate`: for agents. `linear_onset_on_this_domain` is true / false / null (null = do not answer), plus `may_assert` and `must_not_assert` (nonlinear/biological pattern formation; other parameters or domains; the continuum inequality alone settling a finite domain).
- Install: `pip install .` from a repository checkout gives `turing-scope-check check request.json`; Lean receipts need the checkout's built `turing_scope/lean` (otherwise reported unavailable).
- Agent test set with exact ground truth: `artifacts/scope_traps/` (180 questions: 60 scope traps, 60 positives, 60 no-band; separate answer key; keys re-derived with numpy, 0 mismatches; Lean on a stratified sample of 6).

## Calculator note: `diffusion_requirement`
For your Jacobian, the exact bracket of D_inhibitor/D_activator the textbook band needs (9 for the example), or "no ratio suffices". It is a property of the kinetics, not a universal threshold (always above |delta|/alpha > 1; ratio 1.1 suffices for J=[[1,-1],[1011/1000,-101/100]], Lean-checked, `test_no_universal_threshold_codex_counterexample`). Well-known background, already measured in vivo (per the director's scout, not independently checked here: Mueller et al. 2012 Science 336:721; Kuhn et al. 2022 Nat Commun). **Not a finding and not part of the pitch.** The earlier protein-mass comparison was removed.

## MCP
Remote: `$FALSIFY_URL/mcp` (streamable HTTP), tool `falsify_turing_pattern`. Stdio proxy:
`claude mcp add falsify -- python3 -m falsify mcp-stdio --endpoint $FALSIFY_URL --caller your-team-name` (run from a checkout of this repo).

## Verify a receipt yourself
`curl $FALSIFY_URL/v1/receipts/<receipt_id> > receipt.json && python3 -m falsify verify-receipt receipt.json --lean`

Rate limits: 30 requests/min, 10 Lean receipts/hour per caller. Requests and results are logged publicly (salted network hash only); send nothing confidential.
