# Outreach packet for the falsification service: DRAFT, NOT SENT

> **Status: prepared only.** Nothing here has been sent to anyone. Sending any of it to another team requires the user's explicit
> instruction (director sign-off alone is not enough). No team has used the service as of this writing; the usage ledger, not this
> document, is the record of use. **Do not describe any collaboration or adoption until `/usage` shows external calls.**
> Blocked on: a publicly reachable URL (hosting request open with dx-gpuops). Placeholders: `<URL>`.

## One-paragraph pitch (for a message or a slide)
"If your project uses a reaction-diffusion or Turing-type pattern model, we can check whether your parameters can actually produce a
linear instability *on your domain and boundary conditions*. Send a Jacobian (or Brusselator / Schnakenberg / Gierer-Meinhardt
parameters), diffusivities and a domain; you get back an exact-arithmetic verdict, the full list of unstable modes, the minimum
domain length, two independent cross-checks and, optionally, a Lean 4 machine-checked proof, plus a receipt you can re-run. Textbook
Turing conditions can pass while no admissible mode fits the domain; this catches that case. It is a linear-stability check only:
no nonlinear, biological or wet-lab claim."

## Why it helps a team (honest version)
- Catches the "textbook condition holds, but the domain is too small / the boundary is wrong" failure before a simulation or slide relies on it.
- Gives a number they can quote: the smallest domain length (multiples of pi) that admits any unstable mode.
- Runs in seconds; no install for HTTP; MCP tool for agent workflows.
- Does **not** replace simulation, does not validate biology, covers only 2 species, linearization at a homogeneous state, isotropic constant diffusion, 1-D/2-D rectangles.

## 60-second call
```bash
curl -s <URL>/v1/falsify/turing -H 'Content-Type: application/json' -d '{"caller":"<their team name>",
 "jacobian":[[1,-2],[2,-3]],"diffusivities":[1,10],"domain":{"dimension":1,"boundary":"neumann","length_over_pi":"1"},"lean":true}'
```
One page: `<URL>/howto`. MCP: `<URL>/mcp` or `claude mcp add falsify -- python3 -m falsify mcp-stdio --endpoint <URL> --caller <team>`.

## Short message (≤ 80 words)
"Hi, we run a free checker for Turing/reaction-diffusion claims: send your Jacobian (or model parameters), diffusivities and domain, and it tells you with exact arithmetic whether any pattern mode can grow there, with a re-runnable receipt (Lean proof optional). Linear stability only, no biology claims. 60-second curl and MCP tool at <URL>/howto. Calls are logged publicly at <URL>/usage under the name you give. Happy to run your model for you."

## What we will record, and what we will not claim
- Record: the public ledger (caller label as self-declared, salted network hash, request, verdict, receipt id). Export it unmodified into `tasks/results/collab.json` at handoff.
- Count as **used** only: calls with origin `external-unverified` in the ledger. The Delphi team's own tests are `self-test`.
- Do not claim: a collaboration, an adoption, or a scientific result for another team, unless that team independently confirms it.
