# Independent review: benchmark input and statement fidelity

Codex API, October 31, 2026; source `70845e6a68c18c4861d07021e5daf3de4e50e34d` on `work/rethink-critic`, frozen key SHA256 `747ddbae6a37dc00a4a9271b43075c752c203ae24a820d08d9fb0e9db37c4467`. This is a second-model-family review of semantics. I read the key, generator and preceding audit before writing it: **not blinded** and not an agent benchmark score. No key was changed. The director has paused v1 evaluation pending a disclosed v1.1.

## Blocking physical-model defect: pinned liquid bridges

The key uses the infinite-cylinder dispersion relation with `k=n*pi/L` for pinned ends, then declares instability as soon as `L>pi*r`. A pinned, fixed-volume bridge requires more than displacement zero at its ends.

Write its radial perturbation as `R(z)=r+epsilon*eta(z)`. To first order,

```
V(epsilon) = pi*r^2*L + 2*pi*r*epsilon*integral_0^L eta(z) dz + O(epsilon^2).
fixed volume => integral_0^L eta(z) dz = 0
eta_1(z)=sin(pi*z/L): integral_0^L eta_1(z) dz = 2L/pi != 0
```

Thus the n=1 sine mode used as the key's instability witness is inadmissible for that physical bridge. The n=2 sine mode has zero integral and becomes unstable at `L>2*pi*r`. More generally, a displacement with zero endpoints extends periodically; the zero-mean periodic Wirtinger inequality gives `integral eta'^2 >= (2*pi/L)^2 integral eta^2`. Combined with the fixed-volume cylinder's second-variation form proportional to `integral(r^2*eta'^2-eta^2)`, this yields the `2*pi*r` threshold, with equality at n=2. This derivation is an analytic audit, not a newly compiled Lean theorem.

The primary experimental/model paper [Martinez, Perales and Meseguer, “Non-linear response of a liquid bridge to a sinusoidal acceleration under microgravity,” introduction, p. 1](https://oa.upm.es/4915/1/Perales_36.pdf) explicitly describes contact lines pinned to equal coaxial disks, defines fixed liquid volume, and gives the weightless cylindrical limit `L>2*pi*R`. It corroborates the constraint issue; it does not justify substituting the unconstrained n=1 sine mode. If a reservoir/open-volume model is intended, declare it and derive its boundary/evolution equations; “pinned” alone does not establish it.

Affected v1 labels under the fixed-volume pinned-bridge interpretation: `rp-0008` through `rp-0015` (five out_of_scope and three underdetermined). The executable audit preserves their exact parameters and the nonzero integral. The other eight family items are not independently certified by this observation. Do not turn this into an undisclosed relabelling. Re-derive the family or replace/drop it in a versioned benchmark before agent evaluation.

## The four earlier disagreements

| Item | Independent review |
|---|---|
| gh-0005, gh-0013 | The uniform-column formula is outside its derivation's shape assumptions for a tapered column, even where its binary answer happens to agree. A scope verdict and an outcome-agreement verdict are different targets. Keep both fields or rewrite the question to choose one. I support excluding these from a single “clean scope accuracy” until the target is explicit. |
| gh-0008 | Density is missing, so the actual buckling outcome is underdetermined without a declared admissible density range. Independently, taper violates the uniform formula's condition. A condition-violation answer and a missing-outcome-input answer may both be valid. Do not pick an arbitrary plausible range to resolve the ambiguity. |
| wl-0009 | The key requires both continuum-near-onset and finite-mode agreement, while the question asks whether the formula predicts observed spacing. Those need not agree. Neither 10% tolerance nor the conjunction is stated in the request. The conflicting labels follow different targets; they do not establish a floating-point error. Declare “check both these licence conditions” or “predict fastest linear mode within tolerance,” then regenerate under a new hash. |

## Systematic input gaps, independently enumerated

- All 16 wavelength questions omit their hidden 10% criterion. Several say “observed spacing” despite specifying only a Jacobian, which fixes linear modes but not nonlinear observed patterns. State the operational target and tolerance in the common agent protocol or each request; verify agents actually receive them.
- Eight Kimura requests omit the 10% approximation tolerance that the key uses. “May I rely on” does not fix a loss tolerance. State the haploid one-copy initial state and transition law wherever those conventions are not explicit.
- Hamilton questions do not specify the pairing kernel and coefficient interpretation used to compute their key. The generator uses `P(partner=1|focal=1)=r+(1-r)p`, fixed payoff parameters, and synergy. The code calls `1-c*g+b*h+d*g*h` fitness, but ten items give a negative value for at least one pair. Negative game payoffs or Malthusian rates can be legitimate; negative absolute reproductive fitness is not. Declare a continuous-time/weak-selection model with a positive-fitness mapping. The marginal-fitness calculation I checked did not produce negative average carrier fitness; I am not claiming its sign answers are thereby numerically wrong.
- Five Allee requests provide compact support without sufficient amplitude/width to guarantee invasion. For every one, a compact patch bounded above by half the Allee threshold is consistent with the input and decays rather than launching the claimed front. The traveling-wave speed can be correct **conditional on invasion**; make that condition explicit, or ask for wave speed rather than the fate of the unspecified patch.
- Twelve Turing “applies” labels certify a growing linear mode, while requests sometimes assume stripes will form. A Jacobian alone does not specify global kinetics or prove a macroscopic stable pattern. Explicitly ask only for diffusion-driven linear instability and retain nonlinear outcome as a separate simulated question.
- “Applies” currently mixes satisfaction of source assumptions, agreement of a formula's output, and empirical pattern occurrence. Use one frozen target, with separate diagnosis/outcome fields. A condition can fail while an output agrees; an approximation can be useful without being an exact theorem.

Counts and IDs: `artifacts/integration/codex-api/benchmark-semantic-audit.json`. Reproduction: capped invocation of `audit_benchmark_semantics.py --output <path>` from repository root. It reads pinned git objects, uses independent Fraction arithmetic for the volume/fitness/Allee witnesses, and does not import the generator. No full benchmark accuracy is reported because these are overlapping review sets, not a new adjudicated key.

## Required v1.1 acceptance

Preserve v1 and explain changes; hash the final requests, key, generator and agent-visible operational definitions before agent runs. Independently review the physical equations and source correspondence, not only arithmetic implementations sharing the same assumptions. Specify whether each answer is about scope, prediction agreement or actual dynamics. Audit every label type and benign control. Give agents the stated tolerances/model conventions, while withholding keys and structured answers. Keep formal mathematics, floating-point numerical checks, simulated patterns and observed data distinct. Rerun targeted verification and review the changed items before releasing evaluation.

Catching this defect was an **independent human-directed agent audit**. Do not claim the deployed scope-checking service autonomously detected it or that it demonstrates measured collective superiority.
