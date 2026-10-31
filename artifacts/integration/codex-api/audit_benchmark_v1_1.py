"""Read-only v1.1 review at an immutable critic commit; no generator imports.

Not blinded: reviewer read generators and keys before writing this program.
Numerical rechecks are separate implementations, not formal proof or agent scores.
Run under the repository's bounded systemd scope, with BLAS threads set to one.
"""
import hashlib
import json
import math
import re
import subprocess
from collections import Counter
from datetime import datetime
from fractions import Fraction as F
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import brentq
from scipy.stats import binom
from sklearn.dummy import DummyClassifier
from sklearn.tree import DecisionTreeClassifier

SOURCE = "e7760307f4cad2040715279949a94ead8437735d"
PREFIX = "scopedesk/bench/v1_1/"
OUTPUT = Path("artifacts/integration/codex-api/benchmark-v1-1-review.json")


def json_scalar(value):
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f"Unsupported JSON value: {type(value).__name__}")


def blob(name):
    return subprocess.check_output(["git", "show", f"{SOURCE}:{PREFIX}{name}"])


def records(name):
    return [json.loads(line) for line in blob(name).splitlines()]


def mode_check(x, boundary, dimensions=1):
    a, b, c, e = map(F, x["J"])
    d = F(x["Dv"])
    det = a * e - b * c
    if a + e >= 0 or det <= 0:
        return False, {"wellmixed_trace": str(a + e), "wellmixed_det": str(det)}
    # det(J-qD) = d*q^2 - B*q + C. For q >= max(B/d,0),
    # d*q^2-B*q >= 0 and C > 0; no unstable mode is omitted.
    bound = max((d * a + e) / d, F(0))
    mult = 2 if boundary == "periodic" else 1
    lengths = [F(x["r_over_pi"])] if dimensions == 1 else [F(x[k]) for k in ("a_over_pi", "b_over_pi")]
    axes = []
    for length in lengths:
        axis = []
        n = 0
        while (F(mult * n) / length) ** 2 < bound:
            axis.append((n, (F(mult * n) / length) ** 2))
            n += 1
        axes.append(axis)
    combinations = [((n,), q) for n, q in axes[0]] if dimensions == 1 else [
        ((m, n), qm + qn) for m, qm in axes[0] for n, qn in axes[1]]
    unstable = []
    for indices, q in combinations:
        if not any(indices):
            continue
        dq = d * q * q - (d * a + e) * q + det
        if dq < 0:
            unstable.append({"indices": indices, "q": str(q), "det": str(dq)})
    return bool(unstable), {"complete_search_q_upper": str(bound), "unstable": unstable}


def turing(x, dimensions):
    if x["bc"] is None:
        n, nw = mode_check(x, "neumann", dimensions)
        p, pw = mode_check(x, "periodic", dimensions)
        v = "underdetermined" if n != p else "applies" if n else "out_of_scope"
        return v, {"neumann": nw, "periodic": pw}
    unstable, witness = mode_check(x, x["bc"], dimensions)
    return "applies" if unstable else "out_of_scope", witness


def wavelength(x):
    J = np.array([float(F(v)) for v in x["J"]]).reshape(2, 2)
    d, length = float(F(x["Dv"])), F(x["r_over_pi"])
    _, modes = mode_check(x, "neumann")
    if not modes.get("unstable"):
        return "out_of_scope", {"no_growing_mode": True}
    values = []
    for mode in modes["unstable"]:
        q = float(F(mode["q"]))
        growth = float(np.max(np.linalg.eigvals(J - q * np.diag([1, d])).real))
        values.append((growth, mode["indices"][0]))
    growth, n = max(values)
    reference = 2 * math.pi / (float(np.linalg.det(J)) / d) ** 0.25
    actual = 2 * float(length) * math.pi / n
    error = abs(actual - reference) / reference
    return "applies" if error <= 0.1 else "out_of_scope", {
        "mode": n, "growth": growth, "lambda_reference": reference,
        "lambda_admissible": actual, "relative_error": error,
        "threshold_margin": abs(error - 0.1)}


def kimura(x):
    N, s = int(x["N"]), float(F(x["s"]))
    p = np.arange(N + 1) * (1 + s) / (N + np.arange(N + 1) * s)
    # Absorbing states are exact; avoid rounding the final p slightly above one.
    p[0], p[-1] = 0., 1.
    P = binom.pmf(np.arange(N + 1)[None, :], N, p[:, None])
    low = np.zeros(N + 1)
    low[-1] = 1
    high = np.ones(N + 1)
    high[0] = 0
    for iteration in range(100000):
        low, high = P @ low, P @ high
        if np.max(high - low) < 1e-12:
            break
    else:
        raise RuntimeError("Fixation iteration did not converge")
    exact = (low[1] + high[1]) / 2
    approximation = 1 / N if x["kind"] == "neutral" else math.expm1(-2*s) / math.expm1(-2*N*s)
    error = abs(approximation - exact) / exact
    return "applies" if error <= 0.1 else "out_of_scope", {
        "fixation_probability": exact, "iteration_gap": float(high[1]-low[1]),
        "iterations": iteration + 1, "row_sum_error": float(np.max(abs(P.sum(axis=1)-1))),
        "approximation": approximation, "relative_error": error,
        "threshold_margin": abs(error-0.1)}


def hawk_dove(x):
    if x["C"] is None:
        return "underdetermined", {"missing": "C"}
    V, C = F(x["V"]), F(x["C"])
    candidate = V/C
    # Payoff advantage Hawk-Dove is (V-C*p)/2; slope is -C/2.
    return "applies" if 0 < candidate < 1 and C > 0 else "out_of_scope", {
        "candidate_frequency": str(candidate), "payoff_difference_slope": str(-C/2)}


@lru_cache(None)
def greenhill_lambda(t, tolerance):
    # theta=y': -(f^4 theta')'=Lambda F theta. theta(0)=0, theta'(1)=0.
    # Shooting is independent of the generator's polynomial Rayleigh-Ritz basis.
    def solve(lam):
        def rhs(z, state):
            f = 1 - (1-t)*z
            weight = 1-z if t == 1 else (f**3-t**3)/(3*(1-t))
            return [state[1]/f**4, -lam*weight*state[0]]
        sol = solve_ivp(rhs, (0., 1.), (0., 1.), rtol=tolerance,
                        atol=tolerance/100, max_step=0.025, dense_output=True)
        if not sol.success:
            raise RuntimeError(sol.message)
        return sol
    lo = 0.
    for hi in np.arange(0.25, 256, 0.25):
        if solve(hi).y[1, -1] < 0:
            break
        lo = float(hi)
    else:
        raise RuntimeError("No first Greenhill root bracket")
    root = brentq(lambda lam: solve(lam).y[1, -1], lo, hi, xtol=tolerance)
    solution = solve(root)
    if np.min(solution.sol(np.linspace(0.001, 1, 1000))[0]) <= 0:
        raise RuntimeError("Shooting solution is not the node-free fundamental mode")
    return root


def greenhill(x):
    if x["E"] is None or x["rho"] is None:
        return "underdetermined", {"declared_missing_input_policy": True,
                                     "missing": [k for k in ("E", "rho") if x[k] is None]}
    t = float(x["t"])
    lam, refined = greenhill_lambda(t, 1e-8), greenhill_lambda(t, 1e-10)
    scale = float(x["E"]) * float(x["D"])**2 / (16*float(x["rho"])*9.81)
    actual = (scale*refined)**(1/3)
    exact_uniform = (scale*greenhill_lambda(1., 1e-10))**(1/3)
    printed_formula = 0.788*(float(x["E"])/(float(x["rho"])*9.81))**(1/3)*float(x["D"])**(2/3)
    H = float(x["H"])
    verdict = "applies" if (H > actual) == (H > printed_formula) else "out_of_scope"
    return verdict, {"lambda_shooting": refined, "refinement_delta": abs(lam-refined),
                     "critical_height": actual, "uniform_height_exact_constant": exact_uniform,
                     "uniform_height_printed_formula": printed_formula,
                     "both_uniform_constants_same_verdict": (H>exact_uniform) == (H>printed_formula),
                     "threshold_margin": min(abs(H/actual-1), abs(H/printed_formula-1))}


def hamilton(x):
    b, c, r, d = [F(x[k]) for k in ("b", "c", "r", "d")]
    frequencies = [F(x["p"])] if x["p"] is not None else [F(1, 10), F(9, 10)]
    covariances, comparisons = [], []
    for p in frequencies:
        joint = []
        for g in (0, 1):
            partner = r*g + (1-r)*p
            for h in (0, 1):
                prob = (p if g else 1-p)*(partner if h else 1-partner)
                joint.append((prob, F(g), -c*g+b*h+d*g*h))
        mean_m = sum(prob*m for prob, g, m in joint)
        covariance = sum(prob*g*m for prob, g, m in joint)-p*mean_m
        covariances.append(str(covariance))
        comparisons.append((covariance > 0) == (r*b-c > 0))
    verdict = "underdetermined" if len(set(comparisons))>1 else "applies" if comparisons[0] else "out_of_scope"
    return verdict, {"frequencies": list(map(str, frequencies)), "covariances": covariances,
                     "predicted_sign_term": str(r*b-c), "sign_agreement": comparisons}


def kpp(x):
    kind = x["kind"]
    if kind == "unspecified":
        return "underdetermined", {"missing": "reaction"}
    par = F(x["par"]) if x["par"] is not None else None
    if kind == "logistic" or (kind == "cubic_pos" and par <= 2):
        return "applies", {"speed_squared_over_sD": "4", "selection_theorem_not_reproved": True}
    if kind == "allee":
        # U=1/(1+exp(kz)), k^2=1/2, c*k=1/2-m after scaling sD=1.
        k2, ck = F(1, 2), F(1, 2)-par
        residual = [k2-ck-par, -2*k2+1]
    else:
        # Same front profile: k^2=a/2, c*k=1+a/2.
        k2, ck = par/2, 1+par/2
        residual = [k2-ck+1, -2*k2+par]
    assert residual == [0, 0]
    speed_squared = ck**2/k2
    return "applies" if speed_squared == 4 else "out_of_scope", {
        "speed_squared_over_sD": str(speed_squared), "front_ODE_coefficient_residuals": list(map(str,residual)),
        "selection_theorem_not_reproved": True}


CHECKS = {"turing_finite_domain": lambda x:turing(x,1), "turing_2d_rectangle": lambda x:turing(x,2),
          "wavelength_formula_licence": wavelength, "kimura_regime": kimura,
          "hawk_dove_ess": hawk_dove, "greenhill_buckling": greenhill,
          "hamilton_rule_form": hamilton, "fisher_kpp_speed": kpp}


def exclusion_checks(excluded):
    output = []
    for row in excluded:
        x, f = row["params"], row["family"]
        if f == "wavelength_formula_licence":
            pairs = re.findall(r"Fraction\((-?\d+), (\d+)\)", x["J"])
            assert len(pairs) == 4
            _, w = wavelength({"J":[str(F(int(a),int(b))) for a,b in pairs], "Dv":x["d"], "r_over_pi":x["r"]})
            passes = w["threshold_margin"] < 0.02
        elif f == "kimura_regime":
            _, w = kimura(x)
            passes = w["threshold_margin"] < 0.02
        elif f == "greenhill_buckling":
            _, w = greenhill({k:float(v) for k,v in x.items()})
            passes = w["threshold_margin"] < 0.03
        elif f == "hamilton_rule_form":
            b,c,r,d = (F(x[k]) for k in ("b","c","r","d"))
            p = F(x["p"]) if x["p"] != "None" else F(1,10)
            terms = [r*b-c, r*b-c+d*(r+(1-r)*p)]
            passes = 0 in terms
            w = {"terms":list(map(str,terms))}
        elif f == "fisher_kpp_speed":
            a = F(x["par"])
            c2 = (2+a)**2/(2*a)
            passes = F(4) < c2 < 4*F(103,100)**2
            w = {"speed_squared":str(c2)}
        else:
            raise ValueError(f)
        output.append({**row,"reason_reproduced":passes,"check":w})
    return output


def main():
    full, public = records("instances_full.jsonl"), records("instances_public.jsonl")
    key = {x["id"]:x for x in records("key.jsonl")}
    conventions = json.loads(blob("conventions.json"))
    hashes = []
    for line in blob("KEY.sha256").decode().splitlines():
        expected, name = line.split()
        actual = hashlib.sha256(blob(name)).hexdigest()
        hashes.append({"file":name,"expected":expected,"actual":actual,"match":expected==actual})
    pub_by_id = {x["id"]:x for x in public}
    contracts, checked = [], []
    for row in full:
        public_copy = {k:v for k,v in row.items() if k != "hidden"}
        contracts.append({"id":row["id"], "public_full_identical":public_copy==pub_by_id[row["id"]],
                          "declared_conventions_visible":conventions["CONV"][row["family"]] in row["request_text"],
                          "common_verdict_definition_visible":conventions["COMMON"] in row["request_text"]})
        verdict, witness = CHECKS[row["family"]](row["hidden"]["structured"])
        checked.append({"id":row["id"],"family":row["family"],"key_verdict":key[row["id"]]["verdict"],
                        "recomputed_verdict":verdict,"match":verdict==key[row["id"]]["verdict"],"witness":witness})
    split = json.loads(blob("split.json"))
    dev = [r for r in full if r["family"] in split["dev_families"]]
    heldout = [r for r in full if r["family"] in split["heldout_families"]]
    X = lambda rows:[[int(r["id"].rsplit("-",1)[1])] for r in rows]
    Y = lambda rows:[key[r["id"]]["verdict"] for r in rows]
    leakage = []
    # Prespecified simple diagnostic; no text or science parameters enter X.
    for model in [DummyClassifier(strategy="most_frequent"),DecisionTreeClassifier(max_depth=3,random_state=0),DecisionTreeClassifier(random_state=0)]:
        model.fit(X(dev),Y(dev))
        pred = list(model.predict(X(heldout)))
        leakage.append({"classifier":type(model).__name__,"depth":getattr(model,"max_depth",None),
                        "features":["numeric item-ID suffix only"],"train_n":len(dev),"test_n":len(heldout),
                        "correct":sum(p==v for p,v in zip(pred,Y(heldout))),
                        "predictions":[{"id":r["id"],"prediction":p,"key":v} for r,p,v in zip(heldout,pred,Y(heldout))]})
    exclusions = exclusion_checks(json.loads(blob("excluded.json")))
    result = {
        "recorded_at":datetime.now(ZoneInfo("America/Los_Angeles")).isoformat(),
        "source_commit":SOURCE,"key_sha256":hashlib.sha256(blob("key.jsonl")).hexdigest(),
        "audit_script_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "review_type":"Nonblinded scientific/input review; not an agent benchmark run",
        "hash_checks":hashes,"contract_checks":contracts,"label_checks":checked,
        "exclusion_checks":exclusions,"public_id_leakage":leakage,
        "summary":{"n":len(full),"families":dict(Counter(r["family"] for r in full)),
                   "recomputed_labels_matching":sum(r["match"] for r in checked),
                   "exclusion_reasons_matching":sum(r["reason_reproduced"] for r in exclusions),
                   "exclusion_entries":len(exclusions)},
        "freeze_approved":False,
        "limitations":["Generators and key read before coding; not blinded and no independent NLP score.",
                       "Conditional numerical calculations are not machine-checked proofs or observed biology.",
                       "KPP front profiles checked algebraically; minimal-speed selection uses known theory and is not proved here.",
                       "Greenhill missing-input policy followed as declared; gravity assumed 9.81 as generator does.",
                       "Text contract checks verify visible definitions and byte agreement, not full semantic parsing.",
                       "ID leakage models are diagnostic checks, not preregistered performance claims.",
                       "No external Delphi source identity/version binding verified by this script."]}
    OUTPUT.write_text(json.dumps(result,indent=2,default=json_scalar)+"\n")
    print(json.dumps({"source_commit":SOURCE,**result["summary"],"hashes_match":all(x["match"] for x in hashes),
                      "contract_violations":[x for x in contracts if not all(v for k,v in x.items() if k != "id")],
                      "label_disagreements":[r for r in checked if not r["match"]],
                      "id_only_baselines":[{k:v for k,v in r.items() if k!="predictions"} for r in leakage]},indent=2,default=json_scalar))


if __name__ == "__main__":
    main()
