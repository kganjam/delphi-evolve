#!/usr/bin/env python3
"""Trace every number on the Delphi deck to a committed artifact, independently of build_deck.py / facts.py.

    python3 presentation/delphi/trace.py [--root .] [--deck presentation/delphi/deck.html] [--out presentation/delphi/number_trace.json]

Same discipline as presentation/trace_numbers.py (which supplies the HTML parser): each claim's expected string is
re-derived here from the named committed files with exact arithmetic; the exact string must appear on its slide;
after removing all claims, NO number may remain (except page counters, declared list ordinals and ledger IDs, which
are checked against CLAIM-LEDGER.md instead); speaker-note numbers must be on the slide; every input hash recorded at
build time must equal the file now; the PDF's numbers must be on the HTML slide; every ledger ID shown on a slide must
be a row of planning/rethink/CLAIM-LEDGER.md; every slide-5 style metric must be marked pending, never a number.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from fractions import Fraction as F
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import trace_numbers as T  # noqa: E402

CLAIMS = []


def claim(slide, shown, files, thunk, kind="text"):
    CLAIMS.append((slide, kind, shown, thunk, tuple(files)))


def register():
    CLAIMS.clear()
    R = T.ROOT
    res = T.J("artifacts/turing_scope/results.json")
    lean = T.J("artifacts/turing_scope/lean_receipt.json")
    pj = T.J("artifacts/integration/codex-api/price-probe.json")
    RES, LEAN, PJ = "artifacts/turing_scope/results.json", "artifacts/turing_scope/lean_receipt.json", "artifacts/integration/codex-api/price-probe.json"

    # ---- exact model, from the artifact's own inputs
    inp = res["short_domain"]["inputs"]
    (a, b), (c, d) = [[F(x) for x in row] for row in inp["jacobian"]]
    Du, Dv = (F(x) for x in inp["diffusivities"])
    det = lambda q: (a - Du * q) * (d - Dv * q) - b * c
    A, B, C = Du * Dv, -(Dv * a + Du * d), a * d - b * c
    disc = B * B - 4 * A * C
    assert F(int(disc**0.5)) ** 2 == disc
    root = lambda s: (-B + s * F(int(disc**0.5))) / (2 * A)
    r1, r2 = sorted([root(-1), root(1)])
    assert det(r1) == 0 == det(r2)
    f1, f2 = (r1.denominator, r1.numerator), (r2.denominator, r2.numerator)
    assert f1[0] * f2[0] == A

    # ================= slide 1
    def reveal():
        assert not any(det(F(n * n)) < 0 for n in range(0, 300)) and [n for n in range(0, 300) if det(F(n * n) / 4) < 0] == [1]
        return "On a tissue of length π no admissible mode is in the band; at 2π one is."
    claim(1, "On a tissue of length π no admissible mode is in the band; at 2π one is.", [RES], reveal)
    claim(1, "J = [[1, -2], [2, -3]], diffusivities D = (1, 10)", [RES],
          lambda: f"J = [[{inp['jacobian'][0][0]}, {inp['jacobian'][0][1]}], [{inp['jacobian'][1][0]}, {inp['jacobian'][1][1]}]], diffusivities D = ({inp['diffusivities'][0]}, {inp['diffusivities'][1]})")
    claim(1, "1-D Neumann boundaries", [RES], lambda: f"{inp['domain']['dimension']}-D Neumann boundaries" if inp["domain"]["boundary"].startswith("neumann") else "MISMATCH")
    claim(1, "det(J − qD) = (5q-1)(2q-1), so the continuum band is 1/5 < q < 1/2", [RES],
          lambda: f"det(J − qD) = ({f1[0]}q-{f1[1]})({f2[0]}q-{f2[1]}), so the continuum band is {r1} < q < {r2}")

    def strip():
        hd, vd = [], []
        for row in res["length_scan"]:
            k = F(row["length_over_pi"])
            unstable = any(det(F(n * n) / (k * k)) < 0 for n in range(0, 300))
            assert unstable == (row["verdict"] == "linearly_unstable")
            hd.append(str(k)); vd.append("grows" if unstable else "stable")
        return "length L / π " + " ".join(hd) + " linear verdict " + " ".join(vd)
    claim(1, "length L / π 1/2 3/4 1 3/2 2 5/2 3 4 5 6 linear verdict stable stable stable grows grows stable grows grows grows grows", [RES], strip)

    def lean_txt():
        n1 = det(F(1) / 4)
        modes = [n for n in range(0, 300) if det(F(n * n) / 4) < 0]
        assert modes == [1] and not [n for n in range(0, 300) if det(F(n * n)) < 0]
        inst = (R / "turing_scope/lean/TuringScope/Instance.lean").read_text()
        assert sorted(set(re.findall(r"ModeStable exModel (\d) 1", inst))) == ["1", "2"]
        ver = re.search(r"version ([0-9.]+)", lean["lean_version"]).group(1)
        nm = sum(1 for m in lean["mutants"] if m["exit"] != 0 and m["as_expected"])
        return (f"Lean {ver}: L = π admits no unstable mode; L = 2π admits one (n = {modes[0]}, det = {n1}). Build exit {lean['build']['exit']}; {nm} mutants rejected. Only these two lengths are compiled.")
    claim(1, "Lean 4.35.0: L = π admits no unstable mode; L = 2π admits one (n = 1, det = -1/8). Build exit 0; 3 mutants rejected. Only these two lengths are compiled.",
          [LEAN, RES, "turing_scope/lean/TuringScope/Instance.lean"], lean_txt)

    def window():
        c_lo, c_hi = 1 / r2, 1 / r1
        assert (c_lo, c_hi) == (2, 5)
        for n in range(2, 500):
            assert c_hi * n * n > c_lo * (n + 1) ** 2
        assert c_hi * 1 < c_lo * 4
        for k2 in (F(5), F(6), F(15, 2), F(8)):
            assert not any(c_lo * n * n < k2 < c_hi * n * n for n in range(0, 300))
        for k2 in (F(2) + F(1, 100), F(9, 2), F(81, 8), F(8) + F(1, 100)):
            assert any(c_lo * n * n < k2 < c_hi * n * n for n in range(1, 300))
        return f"Mode n grows iff {c_lo}n² < (L/π)² < {c_hi}n²."
    claim(1, "Mode n grows iff 2n² < (L/π)² < 5n².", [RES], window)

    # ================= slide 2: repair
    RP, NCA, LVN = "artifacts/rethink_nca/repair.json", "planning/rethink/nca.md", "scopedesk/oracles/results/linear_vs_nonlinear.json"
    rp = T.J(RP)
    nca = (R / NCA).read_text()
    ctl = [x for x in rp["repairs"] if x["req"] >= 32 and x["knob"] == "diffusion_ratio"]
    assert len(ctl) == 16 and all(x["found"] for x in ctl)
    allok = sum(1 for x in ctl if all(e["ok"] for e in x["eval"]))
    mean = sum(x["success"] for x in ctl) / len(ctl)
    c0 = sum(rp["unrepaired_C0_success"][str(x["req"])] for x in ctl) / len(ctl)
    ratios = {}
    for x in ctl:
        ratios[x["found"]["d"]] = ratios.get(x["found"]["d"], 0) + 1
    top = max(ratios, key=ratios.get)
    seeds = {len(x["eval"]) for x in ctl}
    assert seeds == {3} and top == 9.0 and ratios[top] > len(ctl) / 2
    assert "Dv/Du=1" in nca and "refused by `turing-ddi`" in nca and "Schnakenberg" in nca and "0.10" in nca
    claim(2, "Target wavelength, equal diffusivities (Dv/Du = 1). 16 requests.", [RP, NCA], lambda: f"Target wavelength, equal diffusivities (Dv/Du = 1). {len(ctl)} requests.")
    claim(2, "No admissible unstable mode (turing-ddi). 16 of 16.", [RP, NCA], lambda: f"No admissible unstable mode (turing-ddi). {len(ctl)} of {len(ctl)}.")
    claim(2, "Raise Dv/Du to 9 (most requests); the exact check licenses it.", [RP], lambda: f"Raise Dv/Du to {int(top)} (most requests); the exact check licenses it.")
    claim(2, "Independent solver: pattern on 11 of 16 requests; mean success 0.708 (fraction of 3 noise seeds, averaged over requests).", [RP],
          lambda: f"Independent solver: pattern on {allok} of {len(ctl)} requests; mean success {mean:.3f} (fraction of {next(iter(seeds))} noise seeds, averaged over requests).")

    def by_construction():
        # equal diffusivities: J - q d I has eigenvalues (lambda - q d); a stable J stays stable. Checked exactly on the declared model's J over a grid of q and d.
        assert a + d < 0 and a * d - b * c > 0
        for dd in (F(1), F(3, 2), F(10)):
            for n_ in range(0, 60):
                q_ = F(n_, 7)
                assert (a - dd * q_) + (d - dd * q_) < 0 and (a - dd * q_) * (d - dd * q_) - b * c > 0
        return f"The plain formula's design without repair succeeded on {int(c0)} of {len(ctl)}, by construction: equal diffusivities admit no instability for any kinetics."
    claim(2, "The plain formula's design without repair succeeded on 0 of 16, by construction: equal diffusivities admit no instability for any kinetics.", [RP, RES], by_construction)
    lv = T.J(LVN)
    g = lv["gate_vs_C0_vs_pde"]

    def caveats():
        amp = max(e["amp"] for x in ctl if x["found"]["d"] == 9.0 for e in x["eval"])
        dl = [x for x in rp["repairs"] if x["req"] >= 32 and x["knob"] == "domain_length"]
        assert all(x["found"] is None for x in dl)
        tr = [x for x in rp["repairs"] if x["req"] < 32 and x["knob"] == "diffusion_ratio"]
        tr_ok = sum(1 for x in tr if all(e["ok"] for e in x["eval"]))
        return (f"One kinetics, 1-D Neumann, {seeds.pop()} noise seeds, no confidence interval; a model-only check, not an experiment. "
                f"Near-onset repaired patterns are marginal (amplitude up to {amp:.2f} against a 0.10 threshold). "
                f"The other {len(ctl) - allok} requests did not succeed on all seeds, and repairs for {len(tr)} further refusals worked on {tr_ok}. No domain-length repair was found. "
                f"Across {g['n_scored']} nonlinear configurations the gate agreed with the solver on {g['gate_equals_pde']} and the plain formula on {g['C0_equals_pde']}; "
                f"linear theory named the dominant wavelength in {lv['summary']['dominant_mode_equals_fastest_linear_mode']} patterned cases.")
    claim(2, "One kinetics, 1-D Neumann, 3 noise seeds, no confidence interval; a model-only check, not an experiment. Near-onset repaired patterns are marginal (amplitude up to 0.18 against a 0.10 threshold). The other 5 requests did not succeed on all seeds, and repairs for 2 further refusals worked on 0. No domain-length repair was found. Across 80 nonlinear configurations the gate agreed with the solver on 80 and the plain formula on 79; linear theory named the dominant wavelength in 43/61 patterned cases.",
          [RP, NCA, LVN], caveats)

    # ================= slide 3: compiled nodes + test set
    def receipt():
        ax = sorted({a_ for line in pj["original"]["output"].splitlines() for a_ in re.findall(r"\[(.*)\]", line)[0].split(", ")})
        assert ax == sorted(["propext", "Classical.choice", "Quot.sound"])
        nw = len(re.findall(r"DelphiPriceWitnesses\.\w+' depends", pj["witness_controls"]["output"]))
        nm = sum(1 for m in pj["mutants"] if m["exit"] != 0 and m["rejected"])
        assert pj["original"]["exit"] == 0 and pj["witness_controls"]["exit"] == 0
        return f"Lean exit {pj['original']['exit']}, standard axioms only, {nw} witness controls, {nm} changed-sign mutants rejected."
    claim(3, "Lean exit 0, standard axioms only, 4 witness controls, 2 changed-sign mutants rejected.", [PJ], receipt)

    def atlas3():
        t = (R / "lean_price/README.md").read_text()
        assert "duplicate of existing work" in t and "Selection.lean" in t and "'Queller' 0 hits" in t
        return "A critic's code search found no Hamilton form in ATLAS; not exhaustive."
    claim(3, "A critic's code search found no Hamilton form in ATLAS; not exhaustive.", ["lean_price/README.md"], atlas3)
    BD = "scopedesk/bench/v1_2"
    GD = "planning/rethink/CODEX-LEAN19-SLIDE-AND-FREEZE-DECISION.md"
    guide = (R / GD).read_text()
    cap = "A proof-search pilot on 19 frozen integer-arithmetic lemmas, with shared, private and sequential library controls; checker repair and result replay are under review."
    assert cap in guide

    def pilot():
        n_targets = len(re.findall(r"^\| ([TQHD]\d\d) \|", guide, flags=re.M))
        assert n_targets == 19
        return cap.replace("19", str(n_targets))
    pass
    ks = {ln.split()[1]: ln.split()[0] for ln in (R / BD / "KEY.sha256").read_text().splitlines() if len(ln.split()) == 2}
    pub = [json.loads(x) for x in (R / BD / "instances_public.jsonl").read_text().splitlines() if x.strip()]
    assert T.sha(f"{BD}/key.jsonl") == ks["key.jsonl"]
    status = (R / BD / "STATUS.md").read_text()
    claim(3, "Version 1.2: 127 requests, 8 families, key hash 28645a12….", [f"{BD}/key.jsonl", f"{BD}/KEY.sha256", f"{BD}/instances_public.jsonl"],
          lambda: f"Version {BD.split('/')[-1][1:].replace('_', '.')}: {len(pub)} requests, {len({r['family'] for r in pub})} families, key hash {ks['key.jsonl'][:8]}….")
    claim(3, "Turing, 2-D Turing and wavelength items.", ["artifacts/delphi_submit/at5_v1_2_frozen127.json"],
          lambda: "Turing, 2-D Turing and wavelength items." if sorted(k for k in T.J("artifacts/delphi_submit/at5_v1_2_frozen127.json")["table"] if k.lower() != "all") == ["turing_2d_rectangle", "turing_finite_domain", "wavelength_formula_licence"] else "MISMATCH")
    CM = "artifacts/integration/codex-api/bench-v1-2-frozen127-metadata.json"

    def gate():
        fz = (R / BD / "FROZEN.md").read_text()
        cod = T.J(CM)
        assert ks["key.jsonl"] in fz
        assert cod["all_ok"] is True and cod["n_items"] == len(pub) and len(cod["checks"]) == sum(1 for c in cod["checks"].values() if c["ok"])
        return f"Frozen. Codex's metadata and wording check passes ({len(cod['checks'])} of {len(cod['checks'])}); it does not audit the answers."
    claim(3, "Frozen. Codex's metadata and wording check passes (14 of 14); it does not audit the answers.", [f"{BD}/FROZEN.md", CM], gate)

    def methods():
        rd = (R / BD / "README.md").read_text()
        assert "exact unless noted" in rd and re.search(r"kimura_regime.*numerical", rd) and "hamilton_rule_form" in rd and "hawk_dove_ess" in rd and "greenhill_buckling" in rd and "fisher_kpp_speed" in rd
        return "Answers: exact rational arithmetic for Turing, Hamilton and Hawk–Dove items; numerical or closed-form for Kimura, Greenhill and Fisher–KPP; all under declared conventions."
    claim(3, "Answers: exact rational arithmetic for Turing, Hamilton and Hawk–Dove items; numerical or closed-form for Kimura, Greenhill and Fisher–KPP; all under declared conventions.", [f"{BD}/README.md"], methods)
    bl = T.J("scopedesk/audit_v12/blind_vs_key_v12.json")
    claim(3, "Audit trail: a blinded payload-only audit agreed on 132 of 135 items of an earlier candidate, by a model of the same family as the key's author.", ["scopedesk/audit_v12/blind_vs_key_v12.json"],
          lambda: (f"Audit trail: a blinded payload-only audit agreed on {bl['agree']} of {bl['n']} items of an earlier candidate, by a model of the same family as the key's author."
                   if "same model family as key author" in bl["limits"] else "MISMATCH"))
    AT5 = "artifacts/delphi_submit/at5_v1_2_frozen127.json"
    at5 = T.J(AT5)
    assert at5["bench_dir_files_sha256"]["key.jsonl"] == ks["key.jsonl"]
    _rerun_at5_matches(R, at5)

    def at5txt():
        tt = {"n": 0, "C0": 0, "full": 0, "co": 0, "rh": 0}
        for name, t in at5["table"].items():
            if name.lower() == "all":
                continue
            tt["n"] += t["n"]; tt["C0"] += t["C0"]["agree_with_key"]; tt["full"] += t["full"]["agree_with_key"]
            tt["co"] += t["continuum_only"]["agree_with_key"]; tt["rh"] += t["record_hash_changed"]["refused"]
        assert "not external validation" in " ".join(at5["notes"])
        return (f"Gate with the record {tt['full']} / {tt['n']} Plain textbook formula {tt['C0']} / {tt['n']} Continuum condition only {tt['co']} / {tt['n']} Record hash altered: refuses {tt['rh']} / {tt['n']}")
    claim(3, "Gate with the record 50 / 50 Plain textbook formula 29 / 50 Continuum condition only 34 / 50 Record hash altered: refuses 50 / 50", [AT5, f"{BD}/KEY.sha256"], at5txt)

    # ================= slide 4: ledger
    KL = "scopedesk/ledger/kill_ledger.json"
    kl = T.J(KL)
    rows = {r["id"]: r for r in kl["rows"]}
    claim(4, "Turing needs a diffusion ratio of at least 10", [KL], lambda: "Turing needs a diffusion ratio of at least 10" if "diffusion ratio >= 10" in rows["R03"]["claim"] else "MISMATCH")
    claim(4, "a Lean-checked linear model with diffusivity ratio 1.1 has a growing mode (determinant -21/25000)", [KL],
          lambda: "a Lean-checked linear model with diffusivity ratio 1.1 has a growing mode (determinant %s)" % re.search(r"Dv=1\.1.*?mode-1 det=(-?\d+/\d+)", rows["R03"]["witness"]).group(1))
    claim(4, "Pinned-end liquid bridge unstable beyond L > πr (our benchmark key)", [KL], lambda: "Pinned-end liquid bridge unstable beyond L > πr (our benchmark key)" if "l > pi*r" in rows["R11"]["claim"] else "MISMATCH")
    claim(4, "the n=1 mode violates the fixed-volume constraint; caught before any agent ran", [KL],
          lambda: "the n=1 mode violates the fixed-volume constraint; caught before any agent ran" if ("n=1 is inadmissible" in rows["R11"]["witness"] and "before any agent ran" in rows["R11"]["allowed"]) else "MISMATCH")
    claim(4, "ids encoded generator order: a tree on id suffixes alone scored 58/96 against 43/96 for the majority answer", [KL],
          lambda: "ids encoded generator order: a tree on id suffixes alone scored %s against %s for the majority answer" % re.search(r"(\d+/\d+) vs majority (\d+/\d+)", rows["R13"]["witness"]).groups())
    def r06():
        r = rows["R06"]
        assert "NOT vacuous" in r["kind"] and "advertised" in r["allowed"] and "holds for unstable systems" in r["allowed"]
        assert "nonlinear prompts scored against linear labels" in rows["R09"]["witness"] and "not a ceiling" in rows["R09"]["allowed"]
        return ("Also in the ledger: our theorem advertised as stability whose premise, determinant non-negativity, also holds for unstable systems (R06); a stronger statement now compiles (F10). "
                "Row R09, counted as measured, is a mismatched run (nonlinear prompts scored against linear labels), not a measured null.")
    claim(4, "Also in the ledger: our theorem advertised as stability whose premise, determinant non-negativity, also holds for unstable systems (R06); a stronger statement now compiles (F10). Row R09, counted as measured, is a mismatched run (nonlinear prompts scored against linear labels), not a measured null.", [KL], r06)
    claim(4, "21 ledger rows: 16 were caught by an independent reviewer or validator, 2 by the author with an independent hold, 3 only by the author's own measurement or rule.", [KL],
          lambda: _caught(kl))
    claim(4, "Kinds: prior art 7, counterexample 1, measured 4, mis-operationalised 3, convention defect 4, process defect 1, design defect 1.", [KL], lambda: _kinds(kl))

    # ================= slide 5: collective
    TP, LT = "artifacts/core/replay/table_primary.csv", "artifacts/lazysp/results/table_primary.csv"
    tp = {(r["policy"], int(r["budget"])): r for r in T.C(TP) if r["family"] == "all"}
    lt = {r["variant"]: r for r in T.C(LT)}
    cnt = T.J("artifacts/demo.json")["source"]["counts"]
    PH = T.J("artifacts/lazysp/results/exploratory_post_hoc.json")
    claim(5, "159,129 measured variants, 1,000 extra assays.", ["artifacts/demo.json", "artifacts/lazysp/results/summary.json"],
          lambda: f"{T.n(cnt['measured_nonstop_genotypes'])} measured variants, {T.n(T.J('artifacts/lazysp/results/summary.json')['tau'])} extra assays.")
    claim(5, "Single planner 78/100 Shared specialists 78/100 Plain lazy search 96/100", [TP, LT],
          lambda: (f"Single planner {tp[('q2c', 1000)]['certified']}/{tp[('q2c', 1000)]['episodes']} Shared specialists {tp[('collective_shared', 1000)]['certified']}/{tp[('collective_shared', 1000)]['episodes']} "
                   f"Plain lazy search {round(float(lt['alternate']['resolved@1000']) * int(lt['alternate']['episodes']))}/{lt['alternate']['episodes']}")
          if tp[("q2c", 1000)]["certified"] == tp[("collective_shared", 1000)]["certified"] else "MISMATCH")
    LR = "artifacts/scale/library_receipts.json"

    def usage():
        lr = T.J(LR)
        assert {j["state"] for j in lr["jobs"]} == {"COMPLETED"} and lr["total_owned_job_gpu_seconds"] == 9475
        rows_ = T.C("artifacts/scale/replay_summary.csv")
        pairs = [(float(r_["paired_seed_bootstrap_lo"]), float(r_["paired_seed_bootstrap_hi"])) for r_ in rows_ if r_["paired_seed_bootstrap_lo"] != ""]
        assert pairs and all(lo <= 0 <= hi for lo, hi in pairs)  # B03: no clear benefit
        st = [T.J(f"artifacts/services/nebius/trpb_{g}_openfold2_metrics.json") for g in ("VFVS", "AIKG")]
        assert all("PREDICTED" in x["epistemic_status"] and x["ranking_confidence"] < 50 for x in st)
        gl = T.J("artifacts/services/gemini/usage_ledger.json")
        assert gl["calls"] <= gl["caps"]["max_calls"] and (R / "artifacts/bench_headroom/U_gemini/SCORES.json").exists()
        orx = T.J("artifacts/gpu/orx/receipt.json")
        assert orx["backend"].startswith("local") and "NOT hosted compute" in orx["backend"]
        return (f"Infrastructure used, receipts only Nebius H100s with NVIDIA BioNeMo ESM2: {len(lr['models'])} sizes, {len(lr['jobs'])} jobs, {lr['total_owned_job_gpu_seconds']:,} recorded job-seconds, no clear benefit (B03) · "
                f"Nebius hosted OpenFold2: {len(st)} structure calls, predicted, low confidence · OpenResearch: local CPU analysis log · "
                f"Gemini: {gl['calls']} bounded review calls and the headroom run · receipts in")
    claim(6, "Infrastructure used, receipts only Nebius H100s with NVIDIA BioNeMo ESM2: 5 sizes, 10 jobs, 9,475 recorded job-seconds, no clear benefit (B03) · Nebius hosted OpenFold2: 2 structure calls, predicted, low confidence · OpenResearch: local CPU analysis log · Gemini: 4 bounded review calls and the headroom run · receipts in",
          [LR, "artifacts/scale/replay_summary.csv", "artifacts/services/gemini/usage_ledger.json", "artifacts/services/nebius/trpb_VFVS_openfold2_metrics.json",
           "artifacts/services/nebius/trpb_AIKG_openfold2_metrics.json", "artifacts/gpu/orx/receipt.json", "artifacts/bench_headroom/U_gemini/SCORES.json"], usage, kind="fn")
    LS2 = T.J("artifacts/lazysp/results/summary.json")

    def gain_note():
        rm = LS2["variants"]["alternate"]["paired"]["q2c"]["rmst_diff"]
        pp = PH["variants"]["alternate"]["per_problem"]
        top = max(pp.values(), key=lambda v: v["lazysp_resolved"] - v["comparator_resolved"])
        assert rm["lo95"] <= 0 <= rm["hi95"] and top["lazysp_resolved"] - top["comparator_resolved"] >= 15
        return (f"No collective advantage shown. One repeated panel, about {PH['problem_clusters']} distinct problems; the lazy search's gain sits mostly in one repeated pair and its assay-count interval includes zero.")
    claim(5, "No collective advantage shown. One repeated panel, about 24 distinct problems; the lazy search's gain sits mostly in one repeated pair and its assay-count interval includes zero.", ["artifacts/lazysp/results/exploratory_post_hoc.json", "artifacts/lazysp/results/summary.json"], gain_note)
    GJ = "tasks/results/guilds.json"
    gj = T.J(GJ)

    def headroom():
        hr = gj["bench_v12_headroom_check"]
        ks2 = {ln.split()[1]: ln.split()[0] for ln in (R / BD / "KEY.sha256").read_text().splitlines() if len(ln.split()) == 2}
        assert hr["key_sha256"] == ks2["key.jsonl"] and "checker tool" in hr["arm_not_run"] and "effective n is 8 families" in hr["interpretation"]
        res = {}
        for tag, art in (("c", "artifacts/bench_headroom/U_claude/SCORES.json"), ("g", "artifacts/bench_headroom/U_gemini/SCORES.json")):
            a_ = T.J(art)["all"]
            res[tag] = (a_["N"] - a_["errors_among_answered"], a_["N"], round(100 * (a_["N"] - a_["errors_among_answered"]) / a_["N"], 1))
        ge = hr["gemini_errors_by_family"]
        return (f"Unguarded models, no code tool: Claude Sonnet 5.5 {res['c'][0]}/{res['c'][1]} ({res['c'][2]}%), Gemini 3.8 flash {res['g'][0]}/{res['g'][1]} ({res['g'][2]}%). Checker-tool arm not run. "
                f"Effective n is {len(ge)} families. This measures judgement, not derivation, and is a coarse consistency check scored by the key's author; not a model ranking. "
                f"Gemini's misses sit in wavelength ({ge['wavelength_formula_licence']['errors']} of {ge['wavelength_formula_licence']['N']}) and Greenhill ({ge['greenhill_buckling']['errors']} of {ge['greenhill_buckling']['N']}). It mostly shows the test set is not hard for a frontier model without tools; nothing here says agents need the gate.")
    claim(5, "Unguarded models, no code tool: Claude Sonnet 5.5 121/127 (95.3%), Gemini 3.8 flash 110/127 (86.6%). Checker-tool arm not run. Effective n is 8 families. This measures judgement, not derivation, and is a coarse consistency check scored by the key's author; not a model ranking. Gemini's misses sit in wavelength (7 of 14) and Greenhill (6 of 13). It mostly shows the test set is not hard for a frontier model without tools; nothing here says agents need the gate.",
          [GJ, "artifacts/bench_headroom/U_claude/SCORES.json", "artifacts/bench_headroom/U_gemini/SCORES.json", f"{BD}/KEY.sha256"], headroom)

    def pilot():
        import statistics
        lp = gj["lean_verified_library_experiment"]
        cert = lp["primary_result"]["certified_per_run"]
        assert all(v == [19, 19, 19] for v in cert.values())
        mc = {k: statistics.median(v) for k, v in lp["calls_to_complete"].items()}
        mt = {k: round(statistics.median(v) / 1000) for k, v in lp["tokens"].items()}
        rs = lp["rescore_after_codex_finding"]
        m = re.search(r"deterministic tactics (\d+)/19", lp["primary_result"]["note"])
        assert "30 model calls per run" in lp["design"] and "3 replicates" in lp["design"] and "call-matched" in lp["design"]
        assert min(lp["reuse_proof_term_library_deps"]["Q"]) > 0 and max(lp["reuse_proof_term_library_deps"]["N"]) == 0
        assert "post-outcome" in (R / "lean_commons/PREREG.md").read_text()
        return (f"Same model, 3 replicates, 30 calls per run: every arm certified 19/19 in every run, a ceiling. Library reuse is real but saved nothing: median calls none {mc['N']:g}, private {mc['P']:g}, sequential {mc['Q']:g}, shared {mc['S']:g}; "
                f"median tokens {mt['N']}k, {mt['P']}k, {mt['Q']}k, {mt['S']}k. Deterministic tactics certified {m.group(1)}/19. All {rs['proofs']} recorded proofs re-certified after the checker was repaired, a repair made after the outcomes. Call-matched, not compute-matched; arithmetic surrogates, not biology.")
    claim(5, "Same model, 3 replicates, 30 calls per run: every arm certified 19/19 in every run, a ceiling. Library reuse is real but saved nothing: median calls none 21, private 22, sequential 20, shared 21; median tokens 72k, 80k, 78k, 80k. Deterministic tactics certified 4/19. All 228 recorded proofs re-certified after the checker was repaired, a repair made after the outcomes. Call-matched, not compute-matched; arithmetic surrogates, not biology.",
          [GJ, "lean_commons/PREREG.md"], pilot)
    claim(5, "proof-search pilot, 19 frozen integer-arithmetic lemmas", [GD], lambda: "proof-search pilot, %d frozen integer-arithmetic lemmas" % len(re.findall(r"^\| ([TQHD]\d\d) \|", guide, flags=re.M)))

    # ================= slide 6: close
    AC = "scopedesk/oracles/results/accept_receipt_fresh_clone.json"
    ac = T.J(AC)
    claim(6, "(exit 0, 56.6 s)", [AC], lambda: f"(exit 0, {ac['total_seconds']} s)" if ac["overall_pass"] else "MISMATCH")
    FR = "artifacts/integration/codex-api/admissible-review/committed-freeze.json"
    fr = T.J(FR)
    SCJ = "scopedesk/scorecard/scorecard.json"
    sc = T.J(SCJ)

    def scorecard():
        lab = {}
        for r in sc["rows"]:
            lab[r["status"]] = lab.get(r["status"], 0) + 1
        linked, lemma, emp, none = (lab.get(k, 0) for k in ("BENCHMARK-LINKED", "RELATED FORMAL LEMMA, TARGET NOT ESTABLISHED", "EMPIRICAL / FRAMEWORK", "NO CHECK IN THIS SCORECARD"))
        assert len(sc["rows"]) == 21 == len(fr["claims"]) and linked + lemma + emp + none == 21
        lim = " ".join(sc["global_limits"])
        md = (R / "scopedesk/scorecard/SCORECARD.md").read_text()
        assert "single-reader" in lim and "approves the CORRECTED descriptions" in lim and "not 12 open scientific problems" in md.replace("NOT 12", "not 12") or "backlog, not 12 open scientific problems" in md
        assert "NOT 6 false laws" in md
        return (f"Scorecard {len(sc['rows'])} records: {linked} linked to scope-check benchmark families, {lemma} related formal lemma (target unestablished), {emp} empirical/framework, {none} without a corresponding check. "
                f"Single-reader statuses, revised after a Codex review of version 0; the revision was not re-reviewed. The {none} are a backlog, not open problems, and the {linked} are not {linked} false laws.")
    claim(6, "Scorecard 21 records: 6 linked to scope-check benchmark families, 1 related formal lemma (target unestablished), 2 empirical/framework, 12 without a corresponding check. Single-reader statuses, revised after a Codex review of version 0; the revision was not re-reviewed. The 12 are a backlog, not open problems, and the 6 are not 6 false laws.", [SCJ, "scopedesk/scorecard/SCORECARD.md", FR], scorecard)
    AD = (R / "planning/rethink/CODEX-SCIENTIFIC-ADDENDUM.md").read_text()
    PA = (R / "planning/rethink/PRIOR-ART-VERDICT.md").read_text()
    SRC = "presentation/delphi/sources.md"
    claim(6, "Prove2Me (arXiv 2608.28433)", ["planning/rethink/CODEX-SCIENTIFIC-ADDENDUM.md"], lambda: "Prove2Me (arXiv %s)" % re.search(r"arxiv\.org/html/(\d{4}\.\d{5})", AD).group(1))
    claim(6, "Rashid et al. 2017", ["planning/rethink/PRIOR-ART-VERDICT.md"], lambda: "Rashid et al. %s" % re.search(r"Rashid et al\., PLOS ONE (\d{4})", PA).group(1))
    claim(6, "Ripple (arXiv 2607.13531)", ["planning/rethink/PRIOR-ART-VERDICT.md"], lambda: "Ripple (arXiv %s)" % re.search(r"arxiv\.org/html/(2607\.\d{5})v2\)", PA).group(1))

    def atlas6():
        t = (R / SRC).read_text()
        assert "MathlibExt/Biology" in t and "WantedExt" in t
        return "ATLAS (facebookresearch/atlas-lean)"
    claim(6, "ATLAS (facebookresearch/atlas-lean)", [SRC], atlas6)
    AF = "planning/rethink/ACTIVE-FRONTIER-PITCH-PROPOSAL.md"

    def frontier():
        t = (R / AF).read_text()
        assert "Delphi Frontier" in t and "Who's working on it" in t and "not a migration or a deployed platform" in t
        r21 = {r["id"]: r for r in T.J(KL)["rows"]}["R21"]
        assert "0 of 7 bounded" in r21["witness"] and "NOT Codex-reviewed" in r21["kind"] and "not re-run by the critic" in r21["witness"]
        return ("Delphi Frontier, a proposal, nothing deployed: one page per open problem showing what we know, what's next and who is working on it. "
                "Our own seed questions failed our own validator: 0 of 7 bounded (ledger R21, single-reader, not re-run by the critic).")
    claim(6, "Delphi Frontier, a proposal, nothing deployed: one page per open problem showing what we know, what's next and who is working on it. Our own seed questions failed our own validator: 0 of 7 bounded (ledger R21, single-reader, not re-run by the critic).", [AF, KL], frontier)


def _rerun_at5_matches(R, at5):
    """Re-run the committed checker on the committed key and require the same per-family totals (determinism and provenance)."""
    import os
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "at5.json"
        r = subprocess.run([sys.executable, "-m", "scopedesk.oracles.at5", str(R / "scopedesk/bench/v1_2"), str(out)], cwd=R, capture_output=True, text=True,
                           env={**os.environ, "OMP_NUM_THREADS": "2"})
        assert r.returncode == 0, r.stderr[-300:]
        new = json.loads(out.read_text())
    pick = lambda d: {k: (v["n"], v["full"]["agree_with_key"], v["C0"]["agree_with_key"], v["continuum_only"]["agree_with_key"], v["record_hash_changed"]["refused"]) for k, v in d["table"].items()}
    assert pick(new) == pick(at5), "re-running the checker gives different totals than the committed artifact"


def _caught(kl):
    rows = kl["rows"]
    cls = kl["summary"]["caught_by_class_rows"]  # explicit per-row classes (critic v2); substring matching on caught_by was wrong
    mixed = sorted(i for i, v in cls.items() if v == "mixed")
    author = sorted(i for i, v in cls.items() if v == "author")
    assert len(rows) == 21 and all(i in {r["id"] for r in rows} for i in cls)
    assert kl["summary"]["caught_by_class"] == {"independent": len(rows) - len(cls), "mixed": len(mixed), "author": len(author)}
    return (f"{len(rows)} ledger rows: {len(rows) - len(cls)} were caught by an independent reviewer or validator, {len(mixed)} by the author with an independent hold, "
            f"{len(author)} only by the author's own measurement or rule.")


def _kinds(kl):
    order = ["prior art", "counterexample", "measured", "mis-operationalised", "convention defect", "process defect", "design defect"]
    cnt = {k: sum(1 for r in kl["rows"] if r["kind"].startswith(k)) for k in order}
    assert sum(cnt.values()) == 21
    return "Kinds: " + ", ".join(f"{k} {cnt[k]}" for k in order) + "."


ORDINAL = re.compile(r"(?<![\w.])[1-5]\. (?=[A-Z])")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--deck", default="presentation/delphi/deck.html")
    ap.add_argument("--out", default="presentation/delphi/number_trace.json")
    a = ap.parse_args()
    root = Path(a.root).resolve()
    T.ROOT = root
    register()
    deck_p = Path(a.deck) if Path(a.deck).is_absolute() else root / a.deck
    slides = T.parse_deck(deck_p)
    errors, trace = [], []
    if len(slides) != 6:
        errors.append(f"expected 6 slides, found {len(slides)}")
    work = [dict(s) for s in slides]
    for slide, kind, shown, thunk, files in CLAIMS:
        try:
            exp = thunk()
        except Exception as e:  # noqa: BLE001
            errors.append(f"slide {slide}: cannot re-derive {shown!r}: {type(e).__name__}: {e}")
            continue
        if exp != shown:
            errors.append(f"slide {slide}: artifact gives {exp!r} but the slide claims {shown!r}")
            continue
        field = "fn" if kind == "fn" else ("svg" if kind == "svg" else "html")
        work[slide - 1][field], ok = T.consume(work[slide - 1][field], shown)
        if not ok:
            errors.append(f"slide {slide}: re-derived {shown!r} but it is NOT on the slide")
            continue
        trace.append({"slide": slide, "shown": shown, "where": field, "files": list(files), "sha256": {f: T.sha(f) for f in files}})

    prov = json.loads(deck_p.with_name("deck.provenance.json").read_text())
    head = prov["git"]["head"]
    if subprocess.run(["git", "-C", str(root), "cat-file", "-e", head + "^{commit}"], capture_output=True).returncode != 0:
        errors.append(f"provenance head {head} is not a commit in this repository")
    stale = [rel for rel, h in prov["sha256"].items() if not (root / rel).exists() or T.sha(rel) != h]
    errors += [f"STALE: {rel} changed since the deck was built; rerun presentation/delphi/rebuild.sh" for rel in stale]
    ledger_ids = set(re.findall(r"^\| ([A-Z]\d\d) \|", (root / "planning/rethink/CLAIM-LEDGER.md").read_text(), flags=re.M))
    ledger_ids |= {r["id"] for r in T.J("scopedesk/ledger/kill_ledger.json")["rows"]}  # kill-ledger row IDs (R01-R20)
    for i, s in enumerate(work, 1):
        s["fn"], ok = T.consume(s["fn"], f"artifacts @ {head[:8]}")
        if not ok:
            errors.append(f"slide {i}: footnote commit stamp missing or differs from provenance")
        s["html"], ok = T.consume(s["html"], f"{i} / 6")
        if not ok:
            errors.append(f"slide {i}: page counter missing")
        s["html"] = ORDINAL.sub(" ", s["html"])  # declared list ordinals on slide 4
        shown_ids = set(re.findall(r"\b([A-Z]\d\d)\b", slides[i - 1]["html"] + " " + slides[i - 1]["fn"]))
        missing = sorted(shown_ids - ledger_ids)
        if missing:
            errors.append(f"slide {i}: ledger IDs not in CLAIM-LEDGER.md: {missing}")
        # file paths cited in the footnote must exist in the repository, then are removed before the number scan
        for pth in sorted(set(re.findall(r"[\w./-]+\.(?:md|json|lean|csv|py|js|html)\b", s["fn"]))):
            if not (root / pth).exists() and "/" in pth:
                errors.append(f"slide {i}: cited path does not exist: {pth}")
            s["fn"] = s["fn"].replace(pth, " ")
        for pth in sorted(set(re.findall(r"(?:artifacts|experiments|planning)/[\w./-]+/", s["fn"]))):
            if not (root / pth).is_dir():
                errors.append(f"slide {i}: cited directory does not exist: {pth}")
            s["fn"] = s["fn"].replace(pth, " ")
        for field in ("html", "svg", "fn"):
            left = T.tokens(s[field])
            if left:
                errors.append(f"slide {i} {field}: numbers not traced to any artifact: {left}")
    for i, s in enumerate(slides, 1):
        pool = {tk.replace(",", "") for tk in T.tokens(" ".join([s["html"], s["svg"], s["fn"]]))}
        for tk in T.tokens(s["notes"]):
            if tk.replace(",", "") not in pool:
                errors.append(f"slide {i} notes: number {tk!r} is not on the slide itself")
    # every unmeasured item must read 'pending', never a number
    for i, label in ((3, "Second-reader review:"), (6, "receipt for the final commit is"),
                     (6, "Misprediction map over a large ensemble:")):
        m = re.search(re.escape(label) + r" (\S+)", slides[i - 1]["html"])
        if not m or m.group(1).lower() != "pending":
            errors.append(f"slide {i}: {label!r} must read 'pending', found {m.group(1) if m else None!r}")
    pdf = deck_p.with_suffix(".pdf")
    npdf = None
    if pdf.exists():
        pages = [p_ for p_ in subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True).stdout.split("\f") if p_.strip()]
        npdf = len(pages)
        if npdf != 6:
            errors.append(f"PDF has {npdf} pages, expected 6")
        for i, (pg, s) in enumerate(zip(pages, slides), 1):
            pool = {tk.replace(",", "") for tk in T.tokens(" ".join([s["html"], s["svg"], s["fn"]]))}
            extra = sorted({tk.replace(",", "") for tk in T.tokens(pg)} - pool)
            if extra:
                errors.append(f"PDF page {i}: numbers not on the HTML slide: {extra}")
    result = {"deck": a.deck, "claims_checked": len(trace), "inputs_hash_checked": len(prov["sha256"]), "pdf_pages_checked": npdf,
              "provenance_head": head, "ok": not errors, "errors": errors, "trace": trace}
    (root / a.out).write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n")
    print(f"claims traced: {len(trace)} / {len(CLAIMS)}; errors: {len(errors)}")
    for e in errors:
        print("  FAIL", e)
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
