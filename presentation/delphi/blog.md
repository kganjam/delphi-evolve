# Delphi: from candidate laws to checked theorems

Experts know the conditions that bound a law. An agent that reads a textbook inequality and applies it to a new system usually does not check them. This post describes a small executable check, what is compiled behind it, what is still pending, and the mistakes we made on the way.

## What we are not claiming

The caveats we check are known to experts. We do not present them as discoveries, we ran no experiment, and we do not say that any named law is wrong: a scope condition we supply refers to the extracted record of the claim, not to the law's author. We did not set out to build the first library of formal biology. ATLAS (facebookresearch/atlas-lean, MathlibExt/Biology) already holds a large body of exact biology statements with cited sources and non-vacuity witnesses, and Prove2Me (arXiv 2608.28433), Rashid et al. 2017, lean-bio, crnt-lean and Ripple (arXiv 2607.13531) came before at their own scope. We aim to complement ATLAS, not compete with it.

## Check one: a finite domain with no growing mode

Take a declared two-species linear model, J = [[1, -2], [2, -3]] with diffusivities (1, 10) and Neumann boundaries. The continuum Turing condition holds: det(J − qD) = (5q-1)(2q-1) is negative for 1/5 < q < 1/2. On a finite domain only q = (nπ/L)² exist. At L = π none lies in the band; at 3π/2 and 2π one does; at 5π/2 none does again. Lean 4.35.0 compiles the L = π and L = 2π cases and rejects 3 mutants. The other lengths are exact rational arithmetic, not Lean. The algorithm is trivial, counting admissible modes in a band, so what we offer is a certificate and packaging, not new mathematics; non-monotone dependence on size is textbook-derivable and not claimed as new. This is a linear-mode statement; whether a pattern forms is a nonlinear question we have not simulated yet (pending).

## Check two: Price to Hamilton, with the assumptions attached

We compiled the finite Price identity, a selection-only lemma that depends on it, and a conditional Hamilton regression theorem that depends on that lemma. Lean exits 0, the axioms are propext, Classical.choice and Quot.sound only, 4 witness controls exit 0, and 2 changed-target mutants are rejected. Each assumption (perfect transmission, residual orthogonality, the sign of the cost term) has an exact witness showing what fails without it. This is established mathematics; Price and Frank did the science, and ATLAS already formalizes the Price identity, so our version of that part is a duplicate. It is a regression statement, not a causal cost-benefit rule. Fisher's additive-genetic theorem is not proved (pending), and a second reader has not yet reviewed the statements (pending).

## Our own near-vacuous theorem

One of our theorems, finite_domain_stable, assumed that no admissible mode has negative determinant and concluded that every mode has non-negative determinant. That is a restatement. It compiled and passed the axiom audit, which certifies proof dependencies and not what a statement says. An independent reviewer caught it, not us. A revised module now compiles trace negative and determinant positive at every admissible mode; the determinant is assumed, no new mutants have run, and the eigenvalue and PDE correspondence is not established (ledger F10). We list five more validity errors from this team in the page, each caught by independent review with an exact witness. We read this as the check working, with humans and agents reviewing independently. It is not a machine detecting its own errors.

## What is pending

The scorecard of 21 candidate laws checked as theorems has no compiled count yet, and the misprediction map (what fraction of parameter sets passing the textbook Turing test are stable on a finite domain, over a large ensemble) has not been run. The agent evaluation needs a corrected benchmark freeze, an always-refuse baseline, the same checker without a model, and the unguarded agent. A refusal is not a correct answer, and a null will be shown. We do not claim that more agents beat fewer.

## Appendix material

A robustness sweep (simulated, one linear family, noise-model dependent, not ledger-reviewed) and the earlier enzyme baseline with its nulls are in the appendix.
