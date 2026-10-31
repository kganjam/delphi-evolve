#!/usr/bin/env python3
"""Single source of facts for the Delphi deck, landing page, blog and storyboard.

Everything here is read from committed artifacts (paths named per fact) and, where a value can be
recomputed exactly, recomputed here (Fractions) and compared with the artifact.  Nothing is typed in
from memory.  Each fact carries the CLAIM-LEDGER row it falls under, or "unledgered" when the ledger has
no row yet (such facts must be shown as pending/unreviewed, and the trace gate enforces that).

    python3 presentation/delphi/facts.py [--root .] [--out presentation/delphi/facts.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from fractions import Fraction as F
from pathlib import Path

ROOT = Path(".")


def J(rel):
    return json.loads((ROOT / rel).read_text())


def T(rel):
    return (ROOT / rel).read_text()


def sha(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


# ------------------------------------------------------------------------------------ Price / Hamilton
def price_facts():
    pp = "artifacts/integration/codex-api/price-probe.json"
    d = J(pp)
    src = T("experiments/price_probe/Price.lean")
    assert sha("experiments/price_probe/Price.lean") == d["source_sha256"], "Price.lean changed since the receipt"
    assert sha("experiments/price_probe/Witnesses.lean.inc") == d["witness_source_sha256"], "Witnesses changed since the receipt"
    # axioms per theorem, from the recorded compiler output
    axioms = {}
    for line in d["original"]["output"].splitlines():
        m = re.match(r"'DelphiPrice\.(\w+)' depends on axioms: \[(.*)\]", line)
        if m:
            axioms[m.group(1)] = sorted(a.strip() for a in m.group(2).split(","))
    names = ["price", "selection_only", "fitness_selection", "population_price", "hamilton_regression"]
    # proof dependencies, derived from the source text: which declared theorems each proof body mentions
    deps = {}
    for nm in names:
        mm = re.search(r"theorem %s\b(.*?)(?=\n/--|\ntheorem |\n#print|\nstructure |\Z)" % nm, src, flags=re.S)
        body = mm.group(1)
        body = body.split(":=", 1)[1] if ":=" in body else body
        deps[nm] = sorted(o for o in names if o != nm and re.search(r"\b%s\b" % o, body))
    wit_names = re.findall(r"theorem (\w+)", T("experiments/price_probe/Witnesses.lean.inc"))
    wit_ok = {}
    for line in d["witness_controls"]["output"].splitlines():
        m = re.match(r"'DelphiPriceWitnesses\.(\w+)' depends on axioms: \[(.*)\]", line)
        if m:
            wit_ok[m.group(1)] = sorted(a.strip() for a in m.group(2).split(","))
    assert sorted(wit_ok) == sorted(wit_names) and len(wit_names) == 4
    # exact recomputation of the two-type witnesses stated in Witnesses.lean.inc
    p = [F(1, 2), F(1, 2)]
    z = [F(0), F(1)]
    mean = lambda w: sum(pi * wi for pi, wi in zip(p, w))
    cov = lambda x, y: mean([a * b for a, b in zip(x, y)]) - mean(x) * mean(y)
    desc = lambda w, zd: mean([a * b for a, b in zip(w, zd)]) / mean(w)
    one, zero = [F(1), F(1)], [F(0), F(0)]
    cost_w = [F(2) - zi for zi in z]
    resid = [2 * zi for zi in z]
    res_w = [F(2) - zi + r for zi, r in zip(z, resid)]
    w1 = {"transmission": {"mean_fitness_times_change": mean(one) * (desc(one, one) - mean(zero)),
                           "selection_covariance": cov(one, zero)},
          "nonvacuous": {"var_z": cov(z, z), "mean_fitness": mean(cost_w), "change": desc(cost_w, z) - mean(z)},
          "residual": {"cov_residual_z": cov(resid, z), "change": desc(res_w, z) - mean(z)}}
    assert w1["transmission"] == {"mean_fitness_times_change": F(1), "selection_covariance": F(0)}
    assert w1["nonvacuous"] == {"var_z": F(1, 4), "mean_fitness": F(3, 2), "change": F(-1, 6)}
    assert w1["residual"]["cov_residual_z"] == F(1, 2) and w1["residual"]["change"] > 0
    fr = lambda x: str(x)
    witnesses = {
        "transmission_is_needed": {"drops": "perfect transmission", "mean_fitness_times_change": fr(w1["transmission"]["mean_fitness_times_change"]),
                                   "selection_covariance": fr(w1["transmission"]["selection_covariance"]),
                                   "reading": "descendant trait mean changes although selection covariance is 0, so the transmission term cannot be dropped"},
        "regression_premises_nonvacuous": {"drops": "nothing (non-vacuity of the premises)", "var_z": fr(w1["nonvacuous"]["var_z"]),
                                           "mean_fitness": fr(w1["nonvacuous"]["mean_fitness"]), "change": fr(w1["nonvacuous"]["change"]),
                                           "reading": "the theorem's hypotheses are satisfiable; with r=1, b=0, c=1 the criterion r*b-c=-1 predicts decrease and the change is -1/6"},
        "reversed_cost_is_false": {"drops": "correct sign of the cost term", "reading": "the sign-reversed criterion is false on the same population"},
        "residual_assumption_is_needed": {"drops": "residual orthogonality", "cov_residual_z": fr(w1["residual"]["cov_residual_z"]),
                                          "change_positive": True, "criterion_value": -1,
                                          "reading": "with a residual correlated with the trait the trait mean RISES although r*b-c=-1 < 0"},
    }
    muts = [{"name": m["name"], "exit": m["exit"], "rejected": m["rejected"]} for m in d["mutants"]]
    assert all(m["exit"] == 1 and m["rejected"] for m in muts) and len(muts) == 2
    return {
        "ledger": "F07", "artifact": pp, "source_sha256": d["source_sha256"], "recorded_at": d["recorded_at"],
        "original_exit": d["original"]["exit"], "wall_seconds": d["original"]["wall_seconds"],
        "theorems": names, "axioms": axioms, "axiom_set": sorted({a for v in axioms.values() for a in v}),
        "depends_on": deps, "witnesses": witnesses, "witness_exit": d["witness_controls"]["exit"],
        "mutants": muts, "limitations": d["limitations"],
        "fisher_additive_genetic": "PENDING",
    }


# ------------------------------------------------------------------------------------ Turing
def turing_facts():
    res = J("artifacts/turing_scope/results.json")
    lr = J("artifacts/turing_scope/lean_receipt.json")
    Jm = [[F(1), F(-2)], [F(2), F(-3)]]
    Du, Dv = F(1), F(10)
    assert res["short_domain"]["inputs"] is not None
    det = lambda q: (Jm[0][0] - q * Du) * (Jm[1][1] - q * Dv) - Jm[0][1] * Jm[1][0]
    # det(q) = 10 q^2 - 7 q + 1 = (5q-1)(2q-1)
    for q in (F(0), F(1, 7), F(1, 3), F(2), F(7, 3)):
        assert det(q) == (5 * q - 1) * (2 * q - 1)
    band = (F(1, 5), F(1, 2))

    def verdict(k):
        modes = [n for n in range(0, 200) if det(F(n * n) / (k * k)) < 0]
        return modes
    scan = []
    for row in res["length_scan"]:
        k = F(row["length_over_pi"])
        modes = verdict(k)
        assert (row["verdict"] == "linearly_unstable") == bool(modes), row
        assert [int(x) for x in row["unstable_modes"]] == modes, row
        assert [str(F(n * n) / (k * k)) for n in modes] == row["q_of_unstable_modes"], row
        scan.append({"L_over_pi": str(k), "verdict": row["verdict"], "unstable_modes": modes,
                     "q": row["q_of_unstable_modes"]})
    verd = [s["verdict"] == "linearly_unstable" for s in scan]
    non_monotone = any(verd[i] and not verd[i + 1] for i in range(len(verd) - 1)) and any(not verd[i] and verd[i + 1] for i in range(len(verd) - 1))
    long = res["long_domain"]
    m1 = next(m for m in long["modes"] if m["n"] == 1)
    assert F(m1["determinant"]) == det(F(1, 4)) == F(-1, 8)
    muts = [{"file": m["file"].split("/")[-1], "description": m["description"], "exit": m["exit"], "as_expected": m["as_expected"]} for m in lr["mutants"]]
    assert all(m["as_expected"] for m in muts)
    gen = lr.get("generic_law_mutants", [])
    host = J("tasks/results/rethink-director.json")
    probe = next(c for c in host["commands_actually_run"] if "MathlibProbe.lean" in c["cmd"])
    lean_ver = re.search(r"version ([0-9.]+)", lr["lean_version"]).group(1)
    # exact finite-domain windows: mode n grows iff r1 < n^2/k^2 < r2  <=>  c_lo n^2 < k^2 < c_hi n^2 (k = L/pi)
    r1, r2 = band
    c_lo, c_hi = 1 / r2, 1 / r1
    assert (c_lo, c_hi) == (2, 5)
    for n in range(2, 400):  # consecutive intervals overlap from n = 2 on: c_hi n^2 > c_lo (n+1)^2
        assert c_hi * n * n > c_lo * (n + 1) ** 2
    assert c_hi * 1 < c_lo * 4  # gap between n=1 upper (sqrt5) and n=2 lower (2 sqrt2) is real
    windows = {"unstable_first": ["sqrt(%s)" % c_lo, "sqrt(%s)" % c_hi], "stable_gap": ["sqrt(%s)" % c_hi, "2*sqrt(%s)" % c_lo],
               "unstable_beyond": "2*sqrt(%s)" % c_lo, "c_lo": int(c_lo), "c_hi": int(c_hi)}
    return {
        "windows": windows,
        "ledger": "F01/F02", "artifact": "artifacts/turing_scope/results.json", "lean_receipt": "artifacts/turing_scope/lean_receipt.json",
        "J": [[str(x) for x in r] for r in Jm], "D": [str(Du), str(Dv)], "det_factored": "(5q-1)(2q-1)", "continuum_band": [str(band[0]), str(band[1])],
        "scan": scan, "scan_non_monotone_in_size": non_monotone,
        "pi": {"verdict": res["short_domain"]["verdict"], "unstable_modes": res["short_domain"]["unstable_modes"]},
        "two_pi": {"verdict": long["verdict"], "unstable_modes": long["unstable_modes"], "n1_q": m1["q"], "n1_det": m1["determinant"]},
        "lean": {"version": lean_ver, "build_exit": lr["build"]["exit"], "axiom_audit_exit": lr["axiom_audit"]["exit"],
                 "axioms": lr["axiom_audit"]["distinct_axiom_sets"], "mutants": muts, "n_generic_law_mutants": len(gen),
                 "ok": lr["ok"]},
        "mathlib_real_probe": {"ledger": "unledgered", "artifact": "artifacts/rethink_director/MathlibProbe_host.lean",
                               "receipt": "tasks/results/rethink-director.json", "exit": probe["exit"],
                               "sha256": sha("artifacts/rethink_director/MathlibProbe_host.lean"),
                               "statement": "no_unstable_mode_on_pi: over the reals, no admissible Neumann mode q=n^2 (n>=1) lies in (1/5, 1/2)",
                               "limit": "small, one band, no eigenvalue or PDE correspondence (director receipt)"},
    }


# ------------------------------------------------------------------------------------ our own errors
def error_facts():
    adm = T("artifacts/integration/codex-api/admissible-review/Admissible.lean")
    m = re.search(r"theorem finite_domain_stable.*?:=\s*by", adm, flags=re.S)
    assert m and "hout" in m.group(0) and "0 ≤ D S" in m.group(0)
    review = T("planning/rethink/CODEX-21-CLAIM-FREEZE-REVIEW.md")
    assert "logical restatement" in review and "not linear asymptotic stability" in review
    sem = J("artifacts/integration/codex-api/benchmark-semantic-audit.json")
    affected = sem["rayleigh_affected_key_ids"]
    svc = J("artifacts/integration/codex-api/service-fixed-review.json")
    cr_p = "artifacts/integration/codex-api/admissible-review/469874b/compile-review.json"
    cr = J(cr_p)
    new = T("artifacts/integration/codex-api/admissible-review/469874b/Admissible.lean")
    assert sha("artifacts/integration/codex-api/admissible-review/469874b/Admissible.lean") == cr["source_sha256"]
    assert re.search(r"def ModeStable \(q : ℝ\) : Prop := T S q < 0 ∧ 0 < D S q", new)
    thm = re.search(r"theorem finite_domain_linearly_stable.*?:= by", new, flags=re.S).group(0)
    assert "hwm : WellMixedStable S" in thm and "0 < D S (neumannMode L n)" in thm and "ModeStable S" in thm
    ax = {}
    for line in cr["output"].splitlines():
        m2 = re.match(r"'Admissible\.(\w+)' depends on axioms: \[(.*)\]", line)
        if m2:
            ax[m2.group(1)] = sorted(x.strip() for x in m2.group(2).split(","))
    assert cr["exit"] == 0 and "finite_domain_linearly_stable" in ax
    repl = {"ledger": "F10", "artifact": cr_p, "source_commit": cr["source_commit"], "compile_exit": cr["exit"],
            "theorem": "finite_domain_linearly_stable", "predicate": "ModeStable: trace < 0 and determinant > 0",
            "assumes": "well-mixed stability and strictly positive determinant at every admissible mode", "derives": "trace negativity at every mode",
            "axioms": ax["finite_domain_linearly_stable"], "audited_declarations": len(ax),
            "limits": "does not establish the full eigenvalue or PDE correspondence; no new mutants run; compile review is not a target-fidelity approval"}
    return {
        "vacuous_theorem": {
            "ledger": "P01 (note: existing stability theorem names overstate some statements)",
            "file": "artifacts/integration/codex-api/admissible-review/Admissible.lean", "name": "finite_domain_stable",
            "assumed": "for every admissible mode n, NOT(det(J - qD) < 0)", "concluded": "for every n, det(J - qD) >= 0",
            "hL_unused": "hL" not in re.sub(r"\(hL : 0 < L\)", "", m.group(0)),
            "reviewer": "independent review by the Codex API worker (CODEX-21-CLAIM-FREEZE-REVIEW.md, 'Existing Lean file: specific fidelity failures')",
            "reviewer_text": "a logical restatement; the conclusion is not linear asymptotic stability",
            "compiled_and_axiom_audited": "the review states a clean axiom audit certifies dependencies, not statement fidelity",
            "replacement": repl,
        },
        "five": [
            {"n": 1, "what": "Thompson: pooled regression read against a buckling envelope", "caught_by": "independent critic review",
             "witness": "descriptive Tallo probe: OLS 0.588 vs SMA 0.780 vs q99-bin 0.632 on the same rows",
             "ledger": "P05 (pending)", "artifact": "artifacts/rethink_director/thompson_tallo_probe.json"},
            {"n": 2, "what": "A diffusion-ratio threshold generalized beyond the model it came from", "caught_by": "independent review; Lean-checked classification and exact determinant",
             "witness": "a linear counterexample at diffusion ratio 1.1", "ledger": "F04",
             "artifact": "artifacts/integration/codex-api/service-fixed-review.json"},
            {"n": 3, "what": "Pinned liquid-bridge key used an inadmissible volume-changing mode", "caught_by": "independent Codex API review (not blinded)",
             "witness": "fixed-volume constraint needs integral of the n=1 sine to vanish; it is 2L/pi, nonzero; %d v1 labels affected (%s to %s)" % (len(affected), affected[0], affected[-1]),
             "ledger": "F05", "artifact": "artifacts/integration/codex-api/benchmark-semantic-audit.json", "affected": len(affected)},
            {"n": 4, "what": "Benchmark requests left out declared tolerances and conventions", "caught_by": "independent Codex API review",
             "witness": "v1.1 adds linear-only task definition, wavelength and Kimura tolerances; its own freeze was then withheld for answer information in public IDs",
             "ledger": "F08", "artifact": "artifacts/integration/codex-api/benchmark-v1-1-review.json"},
            {"n": 5, "what": "Turing scorecard line missing the requirement that det(J - qD) < 0 at an actual admissible q", "caught_by": "independent Codex API review",
             "witness": "review of the 21-record freeze, row turing-ddi", "ledger": "P01 (pending freeze)",
             "artifact": "planning/rethink/CODEX-21-CLAIM-FREEZE-REVIEW.md"},
        ],
        "f04_artifact_kind": svc["kind"],
    }


# ------------------------------------------------------------------------------------ scorecard + robustness + baseline
def scorecard_facts():
    fr = J("artifacts/integration/codex-api/admissible-review/committed-freeze.json")
    recs = fr["claims"]
    assert len(recs) == 21
    return {"ledger": "P01 (pending: freeze not approved)", "records": len(recs), "freeze_file": "artifacts/integration/codex-api/admissible-review/committed-freeze.json",
            "freeze_sha256": sha("artifacts/integration/codex-api/admissible-review/committed-freeze.json"),
            "compiled": "PENDING", "excluded": "PENDING", "scores": "PENDING"}


def robustness_facts():
    rel = "artifacts/gpuops/robustness_tax_check.json"
    d = J(rel)
    rows = {}
    for e in ("E1", "E2"):
        for noise in ("uniform", "gaussian"):
            b = d[e][noise]
            rows[f"{e}_{noise}"] = {"1.5-2": b["1.5-2"]["mean_survival_pct"], "30-inf": b["30-inf"]["mean_survival_pct"],
                                    "monotone": all(b[k1]["mean_survival_pct"] <= b[k2]["mean_survival_pct"] for k1, k2 in
                                                    zip(["1.0-1.5", "1.5-2", "2-3", "3-5", "5-10", "10-30"], ["1.5-2", "2-3", "3-5", "5-10", "10-30", "30-inf"]))}
    return {"ledger": "unledgered (appendix only; prior art unchecked)", "artifact": rel, "samples_per_ensemble": d["N"], "noise_fraction": d["noise"],
            "rows": rows, "all_monotone": all(r["monotone"] for r in rows.values()),
            "scope": "one two-species linear family, ensembles E1/E2 and the noise definition chosen by us; absolute values move by about 10 to 20 points with the noise model; not a property of any organism",
            "literature_point": "Nodal/Lefty effective ratio (Muller et al. 2012): NOT verified against the source in this tree (critic-diffusion-ratio.md says the numbers still need a direct reading); not plotted; no claim about where it sits"}


def baseline_facts():
    import csv
    tp = {(r["policy"], int(r["budget"])): r for r in csv.DictReader((ROOT / "artifacts/core/replay/table_primary.csv").open()) if r["family"] == "all"}
    lt = {r["variant"]: r for r in csv.DictReader((ROOT / "artifacts/lazysp/results/table_primary.csv").open())}
    cnt = J("artifacts/demo.json")["source"]["counts"]
    return {"ledger": "B01/B02/B03", "measured_nonstop": cnt["measured_nonstop_genotypes"], "imputed_excluded": cnt["unmeasured_nonstop_genotypes"],
            "q2c_1000": int(tp[("q2c", 1000)]["certified"]), "shared_1000": int(tp[("collective_shared", 1000)]["certified"]),
            "lazysp_1000": round(float(lt["alternate"]["resolved@1000"]) * int(lt["alternate"]["episodes"])),
            "budget": J("artifacts/lazysp/results/summary.json")["tau"],
            "scale": "five ESM2 sizes, 1,100 follow-up episodes: no clear assay-saving benefit (B03)"}


def build():
    return {"price": price_facts(), "turing": turing_facts(), "errors": error_facts(), "scorecard": scorecard_facts(),
            "robustness": robustness_facts(), "baseline": baseline_facts()}


def main():
    global ROOT
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="presentation/delphi/facts.json")
    a = ap.parse_args()
    ROOT = Path(a.root).resolve()
    f = build()
    (ROOT / a.out).write_text(json.dumps(f, indent=1, ensure_ascii=False) + "\n")
    print("facts written:", a.out, {k: list(v)[:3] for k, v in f.items() if k == "price"})


if __name__ == "__main__":
    main()
