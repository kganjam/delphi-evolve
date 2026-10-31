# Critic's final pitch and pick (deliverable as of 07:00 PDT Sat 31 Oct; no unfilled placeholders)

**Pick (critic's, final for this role; the director owns the actual selection):** market-mini — finite-domain reaction–diffusion applicability claims, authored with declared scope, settled by two sound checks (exact linear modes; converged nonlinear solve), bet on by agents that hold different tools, scored against matched-budget controls including a pooled-tools agent and a non-agent stacker. The gates in `critic-settled-science.md` §5 are kill criteria that the director can apply; they are not conditions on the pick being the strongest achievable.

## Three-minute script using only facts that exist now

**0:00–0:20.** "Take one chemistry. On a domain of length 2π it forms a pattern. Shorten the domain to π and the textbook Turing condition stays satisfied — but no pattern can exist. We calculated it exactly and checked it with the full nonlinear equations." *(Exact finite-domain result: `turing_scope/`, `docs/turing-scope.md`; nonlinear cost/shape illustration: `planning/rethink/wildcard/pde_cost_probe.json` — unrefined, so show it as an illustration until the refined run lands.)*

**0:20–0:50.** "Yesterday our agent swarm scored 78 out of 100 on enzyme route certification, exactly what a single agent scored, and a simpler published method scored 96. Copies of one policy are an echo chamber. We keep that result." *(`docs/lazysp.md`, `docs/novelty.md`.)*

**0:50–1:30.** "Science reuses models outside the regime they were stated for. We read the 92 math claims in the Delphi corpus: one reader's triage found 33 checkable as written, 29 that need someone to state a model, 30 that no calculation can decide. So the first job of an AI scientist is to say what a claim covers, and to refuse when it doesn't." *(`planning/rethink/wildcard/claim_decidability.json`; single reader.)*

**1:30–2:10.** "We built the checker the hard way: twelve mechanically edited versions of three tests. Seven change the answer, five don't. The most instructive failure was ours: a test that drops its scope condition only differs outside the scope, so a faithful test has to refuse there, and refusing has to count as an answer. A checker that can't see that will certify the wrong test." *(`fidelity_probe.json`, §7 of `critic-E-redteam.md`; harness check, not an LLM result.)*

**2:10–2:45.** "Now the experiment: agents with different tools bet on whether a pattern forms; two oracles settle every bet. We compare the market to one agent holding every tool, at equal token cost. Whatever the result is, it goes on this slide with its interval. If the pooled agent wins, we say so and measure what distributed information cost." *(Swap-in line, pre-written for both outcomes: "The market beat every single guild by [committed number] but not the pooled agent" or "The market matched the pooled agent at [committed number]"; use only the sentence the committed results support, and if no run finished: "The experiment is preregistered; here is its design and what the controls would show.")*

**2:45–3:00.** "We are offering one thing to other teams: give us your reaction–diffusion model and domain, and we return applies, refuses, or underdetermined, with receipts. Next step is a pilot asking a modelling team how many of their last K model reuses violated an assumption they had stated." No claims of firsts, wet-lab results or wins.

## What this pitch honestly claims and does not

- Claims: exact applicability result; a measured baseline null we disclose; a single-reader decidability triage; a 12-mutant harness showing refusal-as-verdict and baseline strength; a falsifiable pilot hypothesis.
- Does not claim: novelty over LLM forecasting crowds (Halawi 2024, Schoenegger 2024), over NL↔formal fidelity benchmarks (DriftBench, ShadowBench, FormalAlign), or over error-injection benchmarks (FLAWS, Benchmarking Agentic Review Systems); any collective advantage before the arms run; any wet-lab validation.
