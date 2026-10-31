"""Seeded generator of agent test questions with EXACT ground truth from falsify.engine (and Lean on a sample).
Question: 'two-species linearization J, diffusivities (Du,Dv), 1-D Neumann interval of length L=r*pi: does a growing linear mode exist?'
Classes (stratified): trap (textbook continuum band holds, NO admissible mode), positive (admissible unstable mode), no_band (no continuum band).
Systems whose well-mixed state is unstable, and exactly-marginal cases, are excluded so every key is unambiguous YES/NO. The answer key is a SEPARATE file.
Ground truth is for the precise proposition (strictly growing linear mode), not for nonlinear pattern formation."""
import json, os, random, sys
os.environ.setdefault("OMP_NUM_THREADS", "2")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fractions import Fraction as F
from falsify.engine import falsify_turing

SEED = 20261031
rng = random.Random(SEED)
want = {"trap": 60, "positive": 60, "no_band": 60}
have = {k: [] for k in want}
tries = 0
while any(len(have[k]) < want[k] for k in want) and tries < 400000:
    tries += 1
    a, b, c, d = (rng.randint(-6, 6) for _ in range(4))
    Du, Dv = rng.randint(1, 3), rng.randint(2, 60)
    r = F(rng.randint(1, 24), rng.randint(1, 4))
    req = {"jacobian": [[a, b], [c, d]], "diffusivities": [Du, Dv], "domain": {"dimension": 1, "boundary": "neumann", "length_over_pi": str(r)}, "crosscheck": False}
    o = falsify_turing(req)
    if o["verdict"] == "refused":
        cls = None                          # includes well-mixed-unstable systems: excluded (their uniform mode already grows; question would be trivial/ambiguous)
    elif o["verdict"] == "pattern_possible":
        cls = "positive"
    elif o["verdict"] == "domain_blocks_pattern":
        cls = "trap"
    elif o["verdict"] == "no_turing_instability":
        cls = "no_band"
    else:
        cls = None
    if cls and len(have[cls]) < want[cls]:
        have[cls].append((req, o))
items = [(k, req, o) for k, v in have.items() for req, o in v]
rng.shuffle(items)
qs, key = [], []
for i, (cls, req, o) in enumerate(items):
    (a, b), (c, d) = req["jacobian"]
    Du, Dv = req["diffusivities"]
    r = req["domain"]["length_over_pi"]
    text = (f"A two-species reaction-diffusion system u_t = f(u,v) + {Du} u_xx, v_t = g(u,v) + {Dv} v_xx has a homogeneous steady state at which the "
            f"Jacobian is [[{a}, {b}], [{c}, {d}]] (the well-mixed state without diffusion is stable: trace < 0, determinant > 0). The domain is the interval [0, L] with L = ({r}) * pi and zero-flux (Neumann) boundary conditions. "
            f"Question: does a spatial perturbation of this linearization grow (a strictly growing admissible Neumann mode exists)? "
            f"Answer one of: YES, NO.")
    qs.append({"id": f"q{i:03d}", "request": req, "text": text})
    ans = {"positive": "YES", "trap": "NO", "no_band": "NO"}[cls]
    key.append({"id": f"q{i:03d}", "class": cls, "answer": ans, "engine_verdict": o["verdict"],
                "unstable_modes": [m["index"] for m in o.get("modes", {}).get("unstable", [])]})
json.dump({"seed": SEED, "tries": tries, "counts": {k: len(v) for k, v in have.items()}, "questions": qs}, open("artifacts/scope_traps/questions.json", "w"), indent=1)
json.dump({"seed": SEED, "note": "ANSWER KEY - do not show to agents under test. Ground truth: exact-rational engine; Lean-checked sample in lean_sample.json", "key": key}, open("artifacts/scope_traps/answer_key.json", "w"), indent=1)
print({k: len(v) for k, v in have.items()}, "tries", tries)
