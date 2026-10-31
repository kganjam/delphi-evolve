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
        "stability_mislabel": {
            "ledger": "P01 (note: existing stability theorem names overstate some statements); kill ledger R06",
            "file": "artifacts/integration/codex-api/admissible-review/Admissible.lean", "name": "finite_domain_stable",
            "premise": "determinant non-negativity at every admissible mode", "advertised_as": "finite-domain stability",
            "witness": "analytic, not Lean-compiled: J = diag(2, 2), Du = Dv = 1, L = pi has D(q) = (2 - q)^2 >= 0 at every q, yet mode n = 1 has two growth eigenvalues",
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
    sc = J("scopedesk/scorecard/scorecard.json")
    cnt = sc["counts"]
    assert sc["n_claims"] == len(sc["rows"]) == 21 and sum(cnt.values()) == 21
    lim = " ".join(sc["global_limits"])
    assert "single-reader" in lim and "Codex reviewed v0" in lim and "approves the CORRECTED descriptions" in lim
    md = T("scopedesk/scorecard/SCORECARD.md")
    assert "The 12 are a project backlog, not 12 open scientific problems" in md and "NOT 6 false laws" in md
    linked, lemma, emp, none = (cnt[k] for k in ("BENCHMARK-LINKED", "RELATED FORMAL LEMMA, TARGET NOT ESTABLISHED", "EMPIRICAL / FRAMEWORK", "NO CHECK IN THIS SCORECARD"))
    return {"ledger": "unledgered: critic's scorecard v0.1 (single reader; revised after a Codex review of v0; the revision was not re-reviewed)", "records": len(recs), "scorecard_artifact": "scopedesk/scorecard/scorecard.json",
            "linked": linked, "related_lemma": lemma, "empirical": emp, "no_check": none,
            "scorecard_limits": sc["global_limits"], "freeze_file": "artifacts/integration/codex-api/admissible-review/committed-freeze.json",
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
    clusters = J("artifacts/lazysp/results/exploratory_post_hoc.json")["problem_clusters"]
    return {"ledger": "B01/B02/B03", "clusters": clusters, "measured_nonstop": cnt["measured_nonstop_genotypes"], "imputed_excluded": cnt["unmeasured_nonstop_genotypes"],
            "q2c_1000": int(tp[("q2c", 1000)]["certified"]), "shared_1000": int(tp[("collective_shared", 1000)]["certified"]),
            "lazysp_1000": round(float(lt["alternate"]["resolved@1000"]) * int(lt["alternate"]["episodes"])),
            "budget": J("artifacts/lazysp/results/summary.json")["tau"],
            "scale": "five ESM2 sizes, 1,100 follow-up episodes: no clear assay-saving benefit (B03)"}


def bench_facts():
    d = "scopedesk/bench/v1_2"
    ks = {ln.split()[1]: ln.split()[0] for ln in T(f"{d}/KEY.sha256").splitlines() if len(ln.split()) == 2}
    assert sha(f"{d}/key.jsonl") == ks["key.jsonl"], "key.jsonl changed since KEY.sha256"
    pub = [json.loads(x) for x in T(f"{d}/instances_public.jsonl").splitlines() if x.strip()]
    key = [json.loads(x) for x in T(f"{d}/key.jsonl").splitlines() if x.strip()]
    assert len(pub) == len(key)
    fam = {}
    for r in pub:
        fam[r["family"]] = fam.get(r["family"], 0) + 1
    status = T(f"{d}/STATUS.md")
    frozen = T(f"{d}/FROZEN.md")
    assert ks["key.jsonl"] in frozen and len(pub) == 127
    cod = J("artifacts/integration/codex-api/bench-v1-2-frozen127-metadata.json")
    assert cod["all_ok"] is True and cod["n_items"] == 127 and len(cod["checks"]) == 14 and all(c["ok"] for c in cod["checks"].values())
    at5p = "artifacts/delphi_submit/at5_v1_2_frozen127.json"
    at5 = J(at5p)
    assert at5["bench_dir_files_sha256"]["key.jsonl"] == ks["key.jsonl"], "AT5 was computed on a different key than the committed one"
    al = at5["table"]
    tot = {"n": 0, "C0": 0, "full": 0, "continuum_only": 0, "record_hash_changed_refused": 0}
    for fam_name, t in al.items():
        if fam_name in ("ALL", "all"):
            continue
        tot["n"] += t["n"]; tot["C0"] += t["C0"]["agree_with_key"]; tot["full"] += t["full"]["agree_with_key"]
        tot["continuum_only"] += t["continuum_only"]["agree_with_key"]; tot["record_hash_changed_refused"] += t["record_hash_changed"]["refused"]
    assert tot == {"n": 50, "C0": 29, "full": 50, "continuum_only": 34, "record_hash_changed_refused": 50}, tot
    notes = " ".join(at5["notes"])
    assert "not external validation" in notes
    mc = J(f"{d}/metadata_check_receipt.json")
    bl = J("scopedesk/audit_v12/blind_vs_key_v12.json")
    sem = J("artifacts/integration/codex-api/benchmark-v1-1-review.json")
    return {"ledger": "P03 (the ledger row still describes the earlier 128-item candidate; Codex receipts cover the frozen 127)", "items": len(pub), "families": len(fam), "family_counts": fam, "key_sha256": ks["key.jsonl"],
            "key_file": f"{d}/key.jsonl", "status": "frozen (FROZEN.md); Codex metadata/text check 14 of 14 pass",
            "codex_metadata": {"artifact": "artifacts/integration/codex-api/bench-v1-2-frozen127-metadata.json", "checks": len(cod["checks"]), "all_ok": cod["all_ok"]}, "at5": {"artifact": at5p, "totals": tot, "caveat": "trap-enriched; shares its convention document with the checker; not external validation"},
            "metadata_check": {"artifact": f"{d}/metadata_check_receipt.json", "keys": sorted(mc.keys())[:6]},
            "blind_audit": {"artifact": "scopedesk/audit_v12/blind_vs_key_v12.json", "agree": bl["agree"], "n": bl["n"], "scope": "earlier 135-item candidate, one same-family model run"}}


def repair_facts():
    r = J("artifacts/rethink_nca/repair.json")
    ctl = [x for x in r["repairs"] if x["req"] >= 32 and x["knob"] == "diffusion_ratio"]
    assert len(ctl) == 16 and len({x["req"] for x in ctl}) == 16 and all(x["found"] for x in ctl)
    seeds = {len(x["eval"]) for x in ctl}
    assert seeds == {3}
    all_ok = sum(1 for x in ctl if all(e["ok"] for e in x["eval"]))
    mean = sum(x["success"] for x in ctl) / len(ctl)
    c0 = sum(r["unrepaired_C0_success"][str(x["req"])] for x in ctl) / len(ctl)
    assert (all_ok, round(mean, 3), c0) == (11, 0.708, 0.0)
    nine = [x for x in ctl if x["found"]["d"] == 9.0]
    amp_max = max(e["amp"] for x in nine for e in x["eval"])
    dl = [x for x in r["repairs"] if x["req"] >= 32 and x["knob"] == "domain_length"]
    assert all(x["found"] is None for x in dl) and len(dl) == 16
    tr = [x for x in r["repairs"] if x["req"] < 32 and x["knob"] == "diffusion_ratio"]
    tr_ok = sum(1 for x in tr if all(e["ok"] for e in x["eval"]))
    nca = T("planning/rethink/nca.md")
    assert "refused by `turing-ddi`" in nca and "Dv/Du=1" in nca
    lv = J("scopedesk/oracles/results/linear_vs_nonlinear.json")
    g = lv["gate_vs_C0_vs_pde"]
    assert (g["n_scored"], g["gate_equals_pde"], g["C0_equals_pde"]) == (80, 80, 79)
    dom = lv["summary"]["dominant_mode_equals_fastest_linear_mode"]
    return {"ledger": "unledgered (NCA worker artifact; model-only)", "artifact": "artifacts/rethink_nca/repair.json", "requests": len(ctl), "seeds": 3,
            "gate_refused": len(ctl), "plain_formula_success": c0, "repair_all_seeds": all_ok, "repair_mean": round(mean, 3), "repair_ratio": 9, "repair_ratio_count_at_9": len(nine),
            "amp_max_at_ratio_9": round(amp_max, 2), "amp_threshold": 0.10, "domain_length_repairs_found": 0, "other_refusals": len(tr), "other_refusals_repair_ok": tr_ok,
            "nonlinear_grid": {"artifact": "scopedesk/oracles/results/linear_vs_nonlinear.json", "n": g["n_scored"], "gate_agrees": g["gate_equals_pde"], "plain_agrees": g["C0_equals_pde"], "dominant_mode": dom},
            "scope": "one kinetics (Schnakenberg), 1-D Neumann, 3 noise seeds, no confidence interval; near-onset repaired patterns are marginal; not an experiment"}


def kill_facts():
    k = J("scopedesk/ledger/kill_ledger.json")
    rows = {r["id"]: r for r in k["rows"]}
    sm = k["summary"]
    assert sm["n_rows"] == len(k["rows"]) == 21 and sm["caught_by_class"] == {"independent": 16, "mixed": 2, "author": 3}
    cls_rows = sm["caught_by_class_rows"]
    assert sorted(cls_rows) == ["R09", "R15", "R17", "R18", "R20"] and sorted(v for v in cls_rows.values()) == ["author", "author", "author", "mixed", "mixed"]
    kinds = sm["kind_counts"]
    assert sum(kinds.values()) == 21 and kinds["design defect"] == 1
    r21 = rows["R21"]
    assert "0 of 7 bounded" in r21["witness"] and "NOT Codex-reviewed" in r21["kind"] and "Reported by the host, not re-run by the critic" in r21["witness"]
    assert "R06" in rows and "NOT vacuous" in rows["R06"]["kind"] and "Analytic witness J=diag(2,2)" in rows["R06"]["witness"]
    r03 = re.search(r"mode-1 det=(-?\d+/\d+)", rows["R03"]["witness"]).group(1)
    r13 = re.search(r"(\d+/\d+) vs majority (\d+/\d+)", rows["R13"]["witness"])
    show = [
        {"id": "R03", "claim": "Turing needs a diffusion ratio of at least 10", "kind": "counterexample", "witness": f"a Lean-checked linear model with diffusivity ratio 1.1 has a growing mode (determinant {r03})", "by": "independent reviewer"},
        {"id": "R11", "claim": "Pinned-end liquid bridge unstable beyond L > πr (our benchmark key)", "kind": "convention defect", "witness": "the n=1 mode violates the fixed-volume constraint; caught before any agent ran", "by": "independent reviewer, not the author's verifier"},
        {"id": "R08", "claim": "Thompson's scaling refuted by a pooled regression", "kind": "mis-operationalised", "witness": "a pooled OLS tests mean allometry, not the buckling limit", "by": "independent reviewer"},
        {"id": "R13", "claim": "Benchmark ids were label-neutral", "kind": "convention defect", "witness": f"ids encoded generator order: a tree on id suffixes alone scored {r13.group(1)} against {r13.group(2)} for the majority answer", "by": "independent reviewer"},
        {"id": "R16", "claim": "Our Price node as a novel formalization", "kind": "prior art", "witness": "atlas-lean already proves Price and Fisher; ours was a duplicate", "by": "independent scout, then the author"},
    ]
    for sh in show:
        assert sh["id"] in rows
    m = {x["id"]: x for x in k["measured_matched_control"]}
    assert "78/100" in m["M2"]["result"] and "96/100" in m["M1"]["result"]
    return {"artifact": "scopedesk/ledger/kill_ledger.json", "markdown": "scopedesk/ledger/KILL-LEDGER.md", "n_rows": 21, "independent": 16, "mixed": 2, "author_only": 3, "kind_counts": kinds,
            "r21": {"seeds_bounded": "0 of 7", "status": "single-reader, not Codex-reviewed; reported by the host and not re-run by the critic", "repo": "kganjam/delphi-frontier", "commit": "4e10ce0"},
            "n_with_both_times": sm["n_with_both_times"], "method": sm["method"], "shown": show, "all_rows": [{k2: r[k2] for k2 in ("id", "claim", "kind", "caught_by", "allowed", "claim_stated_pdt", "kill_recorded_pdt", "duration_min", "witness")} for r in k["rows"]],
            "r06_note": "R06 corrected by the critic per Codex: determinant non-negativity advertised as stability; the premise is not vacuous and holds for unstable systems", "median_shown": False}


def accept_facts():
    a = J("scopedesk/oracles/results/accept_receipt_fresh_clone.json")
    assert a["overall_pass"] is True and a["tracked_tree_clean_at_start"] is True
    return {"artifact": "scopedesk/oracles/results/accept_receipt_fresh_clone.json", "head_sha": a["head_sha"], "seconds": a["total_seconds"], "steps": len(a["steps"]),
            "scope": "fresh clone at an earlier commit; a receipt for the final SHA is pending"}


def headroom_facts():
    g = J("tasks/results/guilds.json")["bench_v12_headroom_check"]
    b = J("scopedesk/bench/v1_2/KEY.sha256".replace("KEY.sha256", "FROZEN.md").replace("FROZEN.md", "key_verification.json")) if False else None
    ks = {ln.split()[1]: ln.split()[0] for ln in T("scopedesk/bench/v1_2/KEY.sha256").splitlines() if len(ln.split()) == 2}
    assert g["key_sha256"] == ks["key.jsonl"] and g["payload_sha256"] == ks["model_payload.jsonl"]
    out = {}
    for tag, key, art in (("claude", "claude_sonnet_5_5", "artifacts/bench_headroom/U_claude/SCORES.json"), ("gemini", "gemini_3_8_flash", "artifacts/bench_headroom/U_gemini/SCORES.json")):
        s = J(art)["all"]
        assert s["N"] == g[key]["N"] == 127 and s["errors_among_answered"] == g[key]["errors_among_answered"] and s["coverage"] == 1.0
        right = s["N"] - s["errors_among_answered"]
        out[tag] = {"right": right, "n": s["N"], "pct": round(100 * right / s["N"], 1), "artifact": art}
    assert (out["claude"]["right"], out["gemini"]["right"]) == (121, 110) and (out["claude"]["pct"], out["gemini"]["pct"]) == (95.3, 86.6)
    ge = g["gemini_errors_by_family"]
    fams = len(ge)
    assert fams == 8 and ge["wavelength_formula_licence"] == {"errors": 7, "N": 14} and ge["greenhill_buckling"] == {"errors": 6, "N": 13}
    assert "checker tool" in g["arm_not_run"] and "effective n is 8 families" in g["interpretation"]
    return {"ledger": "unledgered (dx-guilds result, preregistered first; checker-tool arm not run)", "artifact": "tasks/results/guilds.json", "prereg": g["prereg"], **out,
            "families": fams, "gemini_wavelength": ge["wavelength_formula_licence"], "gemini_greenhill": ge["greenhill_buckling"],
            "scope": "models had no code tool: judgement, not derivation; coarse consistency check of the key scored by its author; not a model ranking"}


def lean_pilot_facts():
    import statistics
    g = J("tasks/results/guilds.json")["lean_verified_library_experiment"]
    cert = g["primary_result"]["certified_per_run"]
    assert all(v == [19, 19, 19] for v in cert.values()) and sorted(cert) == ["N", "P", "Q", "S"]
    med = lambda d: {k: statistics.median(v) for k, v in d.items()}
    calls, toks = med(g["calls_to_complete"]), med(g["tokens"])
    assert calls == {"N": 21, "P": 22, "Q": 20, "S": 21}
    tk = {k: round(v / 1000) for k, v in toks.items()}
    assert tk == {"N": 72, "P": 80, "Q": 78, "S": 80}
    reuse = {k: g["reuse_proof_term_library_deps"][k] for k in "NPQS"}
    assert [max(reuse["N"])] == [0] and min(reuse["Q"]) == 14
    rs = g["rescore_after_codex_finding"]
    assert rs["proofs"] == rs["strict"] == 228 and rs["mutants_accepted"] == 0
    m = re.search(r"deterministic tactics (\d+)/19", g["primary_result"]["note"])
    assert m and int(m.group(1)) == 4
    assert "30 model calls per run" in g["design"] and "call-matched" in g["design"]
    pre = T("lean_commons/PREREG.md")
    assert "Addendum D" in pre and "post-outcome" in pre
    return {"ledger": "unledgered (dx-guilds result; Codex fidelity review of the 19 statements is advisory only)", "artifact": "tasks/results/guilds.json", "prereg": "lean_commons/PREREG.md",
            "lemmas": 19, "replicates": 3, "calls_per_run": 30, "all_arms_19": True, "median_calls": calls, "median_tokens_k": tk, "reuse_deps": reuse,
            "recertified": rs["proofs"], "deterministic_solved": int(m.group(1)),
            "scope": "integer-arithmetic surrogates written by the experimenter; call-matched, not compute-matched; checker repaired after the outcomes (Addendum D); ceiling, so the primary outcome is uninformative"}


def usage_facts():
    """Real, committed usage of the sponsor tools (baseline TrpB work). No statement about scoring or points."""
    import csv
    lr = J("artifacts/scale/library_receipts.json")
    assert len(lr["models"]) == 5 and len(lr["jobs"]) == 10 and {j["state"] for j in lr["jobs"]} == {"COMPLETED"}
    assert lr["total_owned_job_gpu_seconds"] == 9475 and round(lr["total_owned_job_gpu_hours"], 2) == 2.63
    rows = list(csv.DictReader((ROOT / "artifacts/scale/replay_summary.csv").open()))
    pairs = [(float(r["paired_seed_bootstrap_lo"]), float(r["paired_seed_bootstrap_hi"])) for r in rows if r["paired_seed_bootstrap_lo"] != ""]
    assert pairs and all(lo <= 0 <= hi for lo, hi in pairs)
    gl = J("artifacts/services/gemini/usage_ledger.json")
    assert gl["calls"] == 4 and gl["calls"] <= gl["caps"]["max_calls"] and gl["input_tokens"] == 82481
    st = [J(f"artifacts/services/nebius/trpb_{g}_openfold2_metrics.json") for g in ("VFVS", "AIKG")]
    assert all("PREDICTED" in x["epistemic_status"] and 40 <= x["ranking_confidence"] < 50 for x in st)
    assert "INVALID_REQUEST" in T("artifacts/services/nebius/esmfold2fast_attempt_v0.json")
    gem_headroom = J("artifacts/bench_headroom/U_gemini/SCORES.json")["all"]["N"]
    orx = J("artifacts/gpu/orx/receipt.json")
    assert orx["backend"].startswith("local") and "NOT hosted compute" in orx["backend"] and orx["status"] == "done" and orx["exit_code"] == 0
    return {"ledger": "B03 (BioNeMo ESM2 on Nebius H100s), R02 (OpenResearch, local CPU analysis), R01 (H100 PDE pilot, worker-reported)", "esm2_sizes": len(lr["models"]), "variants_per_model": min(m["covered"] for m in lr["models"].values()), "jobs": len(lr["jobs"]), "job_seconds": lr["total_owned_job_gpu_seconds"],
            "h100_hours": round(lr["total_owned_job_gpu_hours"], 2), "comparisons_with_interval_including_zero": len(pairs),
            "gemini_review_calls": gl["calls"], "gemini_review_cap": gl["caps"]["max_calls"], "gemini_review_input_tokens": gl["input_tokens"], "gemini_review_output_tokens": gl["output_tokens"], "gemini_headroom_calls": gem_headroom,
            "nebius_structure_calls": len(st), "nebius_structure_ranking_confidence": round(st[0]["ranking_confidence"]),
            "artifacts": ["artifacts/scale/library_receipts.json", "artifacts/scale/replay_summary.csv", "artifacts/gpu/orx/receipt.json", "artifacts/services/gemini/usage_ledger.json", "artifacts/services/nebius/", "artifacts/bench_headroom/U_gemini/SCORES.json"],
            "openresearch": "a local CPU analysis was logged; not hosted compute"}


SWEEP_DIR = "scopedesk/oracles/results/nonlinear_sweep"


def sweep_facts():
    """The preregistered nonlinear sweep (NCA worker, single author). Every number is asserted against report.json, rows.jsonl and the orx receipt."""
    import hashlib
    rep = J(f"{SWEEP_DIR}/report.json")
    o = rep["overall"]
    rows_sha = hashlib.sha256((ROOT / f"{SWEEP_DIR}/rows.jsonl").read_bytes()).hexdigest()
    assert rows_sha == rep["rows_sha256"] and rows_sha.startswith("a32c2bf7")
    rs = rep["run_status"]
    assert rs["cells_total"] == rs["cells_done"] == o["cells"] == 2520 and rs["stopped_by"] == "completion" and rs["git_head"].startswith("cb27cf2")
    assert (o["linear_stable_cells"], o["linear_unstable_cells"]) == (1080, 1440)
    r1, r2, r3, un = (o[k] for k in ("R1_linear_stable_but_nonlinear_pattern", "R2_linear_unstable_but_no_pattern",
                                    "R3_linear_unstable_pattern_with_different_dominant_mode", "unresolved_mass"))
    assert (r1["k"], r1["n"], r2["k"], r2["n"], r3["k"], r3["n"], un["k"], un["n"]) == (30, 1080, 0, 1440, 461, 1440, 59, 2520)
    b = rep["strata"]["model"]
    assert b["brusselator"]["R1_linear_stable_but_nonlinear_pattern"]["k"] == 30 and b["schnakenberg"]["R1_linear_stable_but_nonlinear_pattern"]["k"] == 0
    r1e = rep["strata"]["eps"]
    assert sum(v["R1_linear_stable_but_nonlinear_pattern"]["k"] for k, v in r1e.items() if float(k) == 0.3) == 30
    pred = rep["predictions"]
    failed = [k for k, v in pred.items() if not v["holds"]]
    assert len(pred) == 5 and failed == ["P3_R2_concentrated_at_rho_1.03_or_x_2"]
    lower = pred["P4_R3_ge_0.2_and_mostly_lower"]["lower_share_of_mismatches"]
    rc = J(f"{SWEEP_DIR}/orx_receipt.json")
    assert rc["backend"].startswith("local") and "NOT hosted" in rc["backend"] and rc["status"] == "done" and rc["exit_code"] == 0
    assert "no GPU" in rc["backend"] or "no GPU" in T(f"{SWEEP_DIR}/REPORT.md")
    prereg = T("scopedesk/oracles/nonlinear_sweep/PREREG.md")
    assert prereg
    return {"cells": o["cells"], "stable": o["linear_stable_cells"], "unstable": o["linear_unstable_cells"],
            "r1_k": r1["k"], "r1_n": r1["n"], "r2_k": r2["k"], "r2_n": r2["n"], "r3_k": r3["k"], "r3_n": r3["n"], "r3_pct": round(100 * r3["k"] / r3["n"]),
            "lower_pct": round(100 * lower), "unresolved_k": un["k"], "unresolved_pct": round(100 * un["k"] / un["n"], 1), "wall_seconds": round(rs["wall_seconds_this_invocation"]),
            "prereg_commit": "cb27cf2", "rows_sha256": rows_sha, "failed_prediction": "P3", "predictions_holding": sum(v["holds"] for v in pred.values()),
            "report": f"{SWEEP_DIR}/REPORT.md", "report_json": f"{SWEEP_DIR}/report.json", "receipt": f"{SWEEP_DIR}/orx_receipt.json",
            "orx": "analysis logged as a LOCAL orx run; not hosted compute; no GPU or Nebius used for this sweep"}


ORX_LIT = "scopedesk/ledger/orx_literature_receipt.json"


def citation_facts():
    """The director's orx full-text citation check (single-reader). Asserted against the committed receipt; nothing is quoted from the papers here."""
    r = J(ORX_LIT)
    assert "exit 0 for all four" in r["tool"] and "orx paper" in r["tool"] and "--full" in r["tool"] and "single-reader" in r["by"]
    rows = {x["arxiv"]: x for x in r["rows"]}
    k, o = rows["1407.7114"], rows["2509.15829"]
    assert "FULL TEXT states the finite-domain caveat" in k["finding"] and "ABSTRACT does not mention it" in k["finding"]
    assert "FULL TEXT states" in o["finding"] and "ABSTRACT does not mention it" in o["finding"]
    return {"receipt": ORX_LIT, "kurics": {"arxiv": "1407.7114", "sha256_8": k["sha256"][:8]}, "ouchdiri": {"arxiv": "2509.15829", "sha256_8": o["sha256"][:8]},
            "texts_checked": len(r["rows"]), "tool": "OpenResearch orx paper --full (alphaXiv extracted full text)", "by": "the director, single-reader, not independently reviewed"}


FRONTIER_EXAMPLE = "planning/frontier/oca2-exon21-molino-RESULT.md"


def frontier_example_facts():
    """The oca2 exon-21 re-test, only if its result file is committed in THIS tree (director ruling). Otherwise nothing is shown.
    When present it must carry the two commit ids, the limits, and the single-reader label; the word 'solved' is never used."""
    p = ROOT / FRONTIER_EXAMPLE
    if not p.exists():
        return {"present": False, "expected_path": FRONTIER_EXAMPLE}
    t = p.read_text()
    prereg = re.search(r"\bf497073\b", t)
    result = re.search(r"\b9f237ae\b", t)
    assert prereg and result, "the result file must name the preregistration commit f497073 and the result commit 9f237ae"
    low = t.lower()
    for need in ("single-reader", "n=1", "haploid", "nothing causal", "pachon"):
        assert need in low, f"result file lacks the required limit: {need}"
    return {"present": True, "path": FRONTIER_EXAMPLE, "prereg_commit": "f497073", "result_commit": "9f237ae", "sha256": sha(FRONTIER_EXAMPLE),
            "label": "single-reader, not independently reviewed"}


def build():
    return {"citations": citation_facts(), "sweep": sweep_facts(), "frontier_example": frontier_example_facts(), "usage": usage_facts(), "headroom": headroom_facts(), "leanpilot": lean_pilot_facts(), "bench": bench_facts(), "repair": repair_facts(), "kills": kill_facts(), "accept": accept_facts(), "price": price_facts(), "turing": turing_facts(), "errors": error_facts(), "scorecard": scorecard_facts(),
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
