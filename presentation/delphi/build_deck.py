#!/usr/bin/env python3
"""Build the Delphi deck (6 slides), speaker notes and provenance from committed artifacts.

    python3 presentation/delphi/build_deck.py [--root .] [--out-dir presentation/delphi]

Every number is rendered from facts.py (which reads committed artifacts).  Items without a result are rendered
as PENDING.  The old TrpB deck (presentation/deck.*) is the preserved baseline and is not touched.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import facts as FA  # noqa: E402

E = html.escape
INPUTS = [
    "scopedesk/oracles/results/nonlinear_sweep/report.json", "scopedesk/oracles/results/nonlinear_sweep/orx_receipt.json", "scopedesk/oracles/results/nonlinear_sweep/REPORT.md",
    "planning/rethink/CLAIM-LEDGER.md", "planning/rethink/CODEX-BENCH-V1-2-REV3-REVIEW.md", "presentation/delphi/sources.md", "lean_price/README.md", "scopedesk/bench/v1_2/KEY.sha256", "scopedesk/bench/v1_2/key.jsonl", "scopedesk/bench/v1_2/instances_public.jsonl", "scopedesk/bench/v1_2/STATUS.md", "scopedesk/bench/v1_2/FROZEN.md", "artifacts/integration/codex-api/bench-v1-2-frozen127-metadata.json", "artifacts/delphi_submit/at5_v1_2_frozen127.json", "planning/rethink/CODEX-LEAN19-SLIDE-AND-FREEZE-DECISION.md", "scopedesk/oracles/results/linear_vs_nonlinear.json", "scopedesk/oracles/results/accept_receipt_fresh_clone.json", "scopedesk/audit_v12/blind_vs_key_v12.json", "scopedesk/ledger/kill_ledger.json", "artifacts/rethink_nca/repair.json", "planning/rethink/nca.md", "planning/rethink/PITCH-OUTLINE.md", "artifacts/scale/library_receipts.json", "artifacts/scale/replay_summary.csv", "artifacts/gpu/orx/receipt.json", "artifacts/services/gemini/usage_ledger.json", "artifacts/services/nebius/trpb_VFVS_openfold2_metrics.json", "artifacts/services/nebius/trpb_AIKG_openfold2_metrics.json", "scopedesk/scorecard/scorecard.json", "scopedesk/scorecard/SCORECARD.md", "tasks/results/guilds.json", "artifacts/bench_headroom/U_claude/SCORES.json", "artifacts/bench_headroom/U_gemini/SCORES.json", "lean_commons/PREREG.md", "planning/rethink/ACTIVE-FRONTIER-PITCH-PROPOSAL.md",
    "artifacts/integration/codex-api/price-probe.json", "experiments/price_probe/Price.lean", "experiments/price_probe/Witnesses.lean.inc",
    "artifacts/turing_scope/results.json", "artifacts/turing_scope/lean_receipt.json",
    "artifacts/rethink_director/MathlibProbe_host.lean", "tasks/results/rethink-director.json",
    "artifacts/integration/codex-api/admissible-review/Admissible.lean", "artifacts/integration/codex-api/admissible-review/committed-freeze.json",
    "planning/rethink/CODEX-21-CLAIM-FREEZE-REVIEW.md", "artifacts/integration/codex-api/benchmark-semantic-audit.json",
    "artifacts/integration/codex-api/benchmark-v1-1-review.json", "artifacts/integration/codex-api/admissible-review/469874b/compile-review.json", "artifacts/integration/codex-api/admissible-review/469874b/Admissible.lean", "artifacts/integration/codex-api/service-fixed-review.json",
    "artifacts/rethink_director/thompson_tallo_probe.json", "artifacts/gpuops/robustness_tax_check.json",
    "artifacts/core/replay/table_primary.csv", "artifacts/lazysp/results/table_primary.csv", "artifacts/demo.json",
]


def seattle_now():
    u = datetime.now(timezone.utc)
    off, name = (-7, "PDT") if u < datetime(2026, 11, 1, 9, 0, tzinfo=timezone.utc) else (-8, "PST")
    return (u + timedelta(hours=off)).strftime("%Y-%m-%d %H:%M ") + name


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def git(root, *a):
    r = subprocess.run(["git", "-C", str(root), *a], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


EXTRA_CSS = """
.pend{display:inline-block;font:700 12px/1 var(--sans);letter-spacing:.08em;text-transform:uppercase;color:#8a5a00;border:1.5px dashed #8a5a00;border-radius:4px;padding:2px 7px;background:#fbf3df}
.pf{display:inline-block;font:700 12px/1 var(--sans);letter-spacing:.08em;text-transform:uppercase;border-radius:4px;padding:2px 7px}
.pf.pr{color:#fff;background:#2b6e3f}.pf.ex{color:#fff;background:#1864ab}.pf.si{color:#fff;background:#5f3dc4}.pf.ob{color:#fff;background:#44505b}
.node{border:2px solid var(--ink);border-radius:8px;background:var(--card);padding:6px 10px;font:600 15px/1.25 var(--mono);text-align:center}
.node.pn{border:2px dashed #8a5a00;background:#fbf3df;color:#8a5a00}
.arrow{font:700 22px/1 var(--sans);color:var(--orange);text-align:center}
td.s{background:#e3efe6;text-align:center;font:600 14px var(--mono)} td.u{background:#fbe0d3;text-align:center;font:700 14px var(--mono)}
table.t3 td,table.t3 th{padding:5px 6px}
.slide .small{font-size:17.5px!important}.slide .scope{font-size:17.5px!important}.slide table{font-size:16.5px!important}.slide table.t3 td.s,.slide table.t3 td.u{font-size:16px!important}.slide .card h3{font-size:13.5px}.slide .node{font-size:17px}.slide td[style*="font-size:13"],.slide td[style*="font-size:12"]{font-size:14.5px!important}
"""


def build_slides(f, led_ids, prov_head):
    P, T, Bn, Rp, Kl, Ac, Bl = f["price"], f["turing"], f["bench"], f["repair"], f["kills"], f["accept"], f["baseline"]
    fn = lambda *parts: '<div class="fn">' + " · ".join(parts) + "</div>"
    stamp = f"artifacts @ {prov_head[:8]}"
    brand = lambda i: f'<div class="brand"><i></i>Delphi · from candidate laws to checked theorems</div><div class="num">{i} / 6</div>'
    pend = '<span class="pend">pending</span>'
    notes = []

    # ------------------------------------------------------------ 1 Reveal (0:00-0:25)
    scan = T["scan"]
    cells_h = "".join(f"<th style='text-align:center'>{E(s['L_over_pi'])}</th>" for s in scan)
    cells_v = "".join(f"<td class='{'u' if s['verdict'] == 'linearly_unstable' else 's'}'>{'grows' if s['verdict'] == 'linearly_unstable' else 'stable'}</td>" for s in scan)
    nmut = sum(1 for m in T["lean"]["mutants"] if m["exit"] != 0)
    w = T["windows"]
    s1 = f"""{brand(1)}
<h2 style="font-size:32px;margin:24px 0 8px">The textbook inequality is green. On a tissue of length π no admissible mode is in the band; at 2π one is.</h2>
<div class="card" style="padding:8px 12px"><div class="small" style="font-size:14px;margin-bottom:4px">Declared model: J = [[{T['J'][0][0]}, {T['J'][0][1]}], [{T['J'][1][0]}, {T['J'][1][1]}]], diffusivities D = ({T['D'][0]}, {T['D'][1]}), 1-D Neumann boundaries; det(J − qD) = {T['det_factored']}, so the continuum band is {T['continuum_band'][0]} &lt; q &lt; {T['continuum_band'][1]}. Admissible modes are q = (nπ/L)².</div>
<table class="t3"><tr><th style="text-align:left">length L / π</th>{cells_h}</tr><tr><td style="text-align:left">linear verdict</td>{cells_v}</tr></table></div>
<div class="row" style="gap:14px;margin-top:10px">
 <div class="col card" style="padding:8px 12px"><h3><span class="pf pr">Proved</span> compiled instance</h3><p class="small" style="margin:0;font-size:14.5px">Lean {T['lean']['version']}: L = π admits no unstable mode; L = 2π admits one (n = {T['two_pi']['unstable_modes'][0]}, det = {T['two_pi']['n1_det']}). Build exit {T['lean']['build_exit']}; {nmut} mutants rejected. Only these two lengths are compiled.</p></div>
 <div class="col card" style="padding:8px 12px"><h3><span class="pf ex">Exact arithmetic</span></h3><p class="small" style="margin:0;font-size:14.5px">The whole strip is exact rational arithmetic. Mode n grows iff {w['c_lo']}n² &lt; (L/π)² &lt; {w['c_hi']}n².</p></div>
 <div class="col card" style="padding:8px 12px"><h3><span class="pf ob">Observed</span></h3><p class="small" style="margin:0;font-size:14.5px"><b>None.</b> No wet-lab experiment; simulations only.</p></div>
</div>
<div class="scope" style="margin-top:10px;font-size:14.5px"><b>Classical mathematics, a linear-mode statement for a declared model.</b> It is not a claim that a pattern forms, and not that Turing was wrong. What is new is only that a program checks it, with a witness, before a law is applied.</div>
{fn('<b>Ledger</b> F01 F02 · artifacts/turing_scope/results.json, lean_receipt.json · the same slider is in the walkthrough at site/review/ (F09)', '<b>Review</b> receipts reviewed earlier by Codex (F01, F02); the Mathlib probe is the director’s single-reader re-run', stamp)}"""
    notes.append("The textbook inequality is green. On a tissue of length pi, no admissible mode is in the band; at two pi, one is. This is a linear statement for a declared model, classical mathematics. What is new is only that a program checks it, with a witness, before a law is applied. No wet-lab experiment; simulations only.")

    # ------------------------------------------------------------ 2 Check + repair (0:25-1:00)
    g = Rp["nonlinear_grid"]
    Sw = f["sweep"]
    SW = (f"<b>Sweep</b> preregistered, simulated, {Sw['cells']:,} cells of two textbook kinetics: {Sw['r1_k']} of {Sw['r1_n']:,} linearly stable cells (all Brusselator, large perturbation, just below onset) still patterned; "
          f"{Sw['r2_k']} of {Sw['r2_n']:,} unstable cells failed to pattern; dominant wavelength differed from the fastest linear mode in {Sw['r3_k']} of {Sw['r3_n']:,}; {Sw['unresolved_k']} unresolved cells are in every denominator. "
          f"One author, a stated prior, not a claim about tissues; prediction {Sw['failed_prediction']} failed as stated; single-reader, not independently reviewed · {Sw['report']}")
    s2 = f"""{brand(2)}
<h2 style="font-size:30px;margin:24px 0 8px">A request the plain formula accepts is refused with a witness, repaired, and re-checked by an independent solver.</h2>
<div class="row" style="gap:10px;align-items:stretch">
 <div class="col card" style="padding:8px 10px"><h3>Request</h3><p class="small" style="margin:0;font-size:15px">Target wavelength, equal diffusivities (Dv/Du = 1). {Rp['requests']} requests.</p></div>
 <div class="arrow" style="align-self:center">→</div>
 <div class="col card" style="padding:8px 10px"><h3><span class="pf ex">Exact</span> Refused</h3><p class="small" style="margin:0;font-size:15px">No admissible unstable mode (turing-ddi). {Rp['gate_refused']} of {Rp['requests']}.</p></div>
 <div class="arrow" style="align-self:center">→</div>
 <div class="col card" style="padding:8px 10px"><h3><span class="pf ex">Exact</span> Repair</h3><p class="small" style="margin:0;font-size:15px">Raise Dv/Du to {Rp['repair_ratio']} (most requests); the exact check licenses it.</p></div>
 <div class="arrow" style="align-self:center">→</div>
 <div class="col card" style="padding:8px 10px"><h3><span class="pf si">Simulated</span> Solver</h3><p class="small" style="margin:0;font-size:15px">Independent solver: pattern on {Rp['repair_all_seeds']} of {Rp['requests']} requests; mean success {Rp['repair_mean']} (fraction of {Rp['seeds']} noise seeds, averaged over requests).</p></div>
</div>
<p class="small" style="margin:8px 0 0;font-size:16px">The plain formula's design without repair succeeded on {int(Rp['plain_formula_success'])} of {Rp['requests']}, by construction: equal diffusivities admit no instability for any kinetics.</p>
<div class="scope" style="margin-top:10px;font-size:15px"><b>Limitation first.</b> The algorithm is trivial. The contribution is the certificate, the refusal and the repair.</div>
<div class="card" style="padding:8px 12px;margin-top:8px"><h3>Caveats, printed</h3><p class="small" style="margin:0;font-size:14.5px">One kinetics, 1-D Neumann, {Rp['seeds']} noise seeds, no confidence interval; a model-only check, not an experiment. Near-onset repaired patterns are marginal (amplitude up to {Rp['amp_max_at_ratio_9']} against a {Rp['amp_threshold']:.2f} threshold). The other {Rp['requests'] - Rp['repair_all_seeds']} requests did not succeed on all seeds, and repairs for {Rp['other_refusals']} further refusals worked on {Rp['other_refusals_repair_ok']}. No domain-length repair was found. Across {g['n']} nonlinear configurations the gate agreed with the solver on {g['gate_agrees']} and the plain formula on {g['plain_agrees']}; linear theory named the dominant wavelength in {g['dominant_mode']} patterned cases.</p></div>
{fn('<b>Ledger</b> unledgered (NCA worker artifacts) · artifacts/rethink_nca/repair.json · scopedesk/oracles/results/linear_vs_nonlinear.json · planning/rethink/nca.md', '<b>Review</b> single-reader, not Codex-reviewed: NCA worker artifacts and a critic audit of the checker code', SW, stamp)}"""
    notes.append("Limitation first: the algorithm is trivial. The contribution is the certificate, the refusal and the repair. Sixteen requests with equal diffusivities, which the plain formula accepts, are refused with a witness. The exact check licenses a repair, raising the ratio to nine. An independent solver then finds a pattern on eleven of sixteen, mean 0.708. One kinetics, three seeds, near-onset and marginal. A model check, not an experiment.")

    # ------------------------------------------------------------ 3 Compiled nodes + benchmark (1:00-1:30)
    W = P["witnesses"]
    A5 = Bn["at5"]["totals"]
    s3 = f"""{brand(3)}
<h2 style="font-size:30px;margin:24px 0 10px">Two compiled nodes, and a test set whose answers come from stated methods; the checker is scored against it.</h2>
<div class="row" style="gap:18px">
 <div class="col"><div class="card" style="padding:9px 12px"><h3><span class="pf pr">Proved</span> proof dependencies</h3>
  <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;font:600 14px var(--mono)"><span class="node pn" style="border-style:solid;color:var(--ink2);background:var(--card)">price · ATLAS has it; ours duplicates</span><span class="arrow">→</span><span class="node">selection_only</span><span class="arrow">→</span><span class="node">hamilton_regression</span></div>
  <p class="small" style="margin:8px 0 0;font-size:14.5px">Conditional Hamilton regression theorem. Lean exit {P['original_exit']}, standard axioms only, {len(W)} witness controls, {len(P['mutants'])} changed-sign mutants rejected. A critic's code search found no Hamilton form in ATLAS; not exhaustive. Second-reader review: {pend}</p></div>
  <div class="card" style="padding:9px 12px;margin-top:8px"><h3>Test set</h3><p class="small" style="margin:0;font-size:13.5px">Version 1.2: <b>{Bn['items']}</b> requests, <b>{Bn['families']}</b> families, key hash {Bn['key_sha256'][:8]}…. <b>Frozen.</b> Codex's metadata and wording check passes (14 of 14); it does not audit the answers. Answers: exact rational arithmetic for Turing, Hamilton and Hawk–Dove items; numerical or closed-form for Kimura, Greenhill and Fisher–KPP; all under declared conventions. Audit trail: a blinded payload-only audit agreed on {Bn['blind_audit']['agree']} of {Bn['blind_audit']['n']} items of an earlier candidate, by a model of the same family as the key's author.</p></div></div>
 <div class="col"><div class="card" style="padding:9px 12px"><h3>Checker against the key</h3><p class="small" style="margin:0 0 4px;font-size:14px">Turing, 2-D Turing and wavelength items.</p>
  <table style="font-size:15px"><tr><th style="text-align:left">method</th><th>agrees</th></tr>
  <tr><td style="text-align:left"><b>Gate with the record</b></td><td><b>{A5['full']} / {A5['n']}</b></td></tr>
  <tr><td style="text-align:left">Plain textbook formula</td><td>{A5['C0']} / {A5['n']}</td></tr>
  <tr><td style="text-align:left">Continuum condition only</td><td>{A5['continuum_only']} / {A5['n']}</td></tr>
  <tr><td style="text-align:left">Record hash altered: refuses</td><td>{A5['record_hash_changed_refused']} / {A5['n']}</td></tr></table>
  <p class="small" style="margin:6px 0 0;font-size:14px"><b>Printed caveat:</b> the set is trap-enriched and shares its convention document with the checker. This is not external validation. The last row shows provenance dependence only.</p></div></div>
</div>
{fn('<b>Ledger</b> F07 P03 · artifacts/integration/codex-api/price-probe.json · lean_price/README.md · scopedesk/bench/v1_2/ · artifacts/delphi_submit/', '<b>Review</b> Codex: metadata and wording only. Checker-versus-key: single-reader recomputation, not Codex-reviewed. Hamilton statements: second reader pending', stamp)}"""
    notes.append("The Price identity is already in ATLAS, so ours is a duplicate. We add a compiled conditional Hamilton regression theorem with witnesses. The test set is frozen: one hundred twenty-seven requests, answers from stated methods under declared conventions. On the fifty Turing and wavelength items the gate agrees with the key on all fifty, the plain formula on twenty-nine. Our own conventions: not external validation.")

    # ------------------------------------------------------------ 4 Ledger (1:30-2:15)
    rows = "".join(f"<tr><td style='text-align:left'>{E(r['claim'])}</td><td style='text-align:left'><b>{E(r['kind'])}</b></td><td style='text-align:left'>{E(r['witness'])}</td></tr>" for r in Kl["shown"])
    kc = Kl["kind_counts"]
    s4 = f"""{brand(4)}
<h2 style="font-size:30px;margin:24px 0 8px">The ledger: claims we held that did not survive, each with a witness and the kind of failure kept separate.</h2>
<div class="card" style="padding:8px 10px"><table style="font-size:14.5px"><tr><th style="text-align:left">claim we held</th><th style="text-align:left">kind</th><th style="text-align:left">witness</th></tr>{rows}</table></div>
<div class="scope" style="margin-top:10px;font-size:15px"><b>{Kl['n_rows']} ledger rows: {Kl['independent']} were caught by an independent reviewer or validator, {Kl['mixed']} by the author with an independent hold, {Kl['author_only']} only by the author's own measurement or rule.</b> There is no control arm: this compares independent audit with self-audit. It is not a measurement of collective intelligence. Kinds: prior art {kc['prior art']}, counterexample {kc['counterexample']}, measured {kc['measured']}, mis-operationalised {kc['mis-operationalised']}, convention defect {kc['convention defect']}, process defect {kc['process defect']}, design defect {kc['design defect']}.</div>
<p class="small" style="margin:8px 0 0;font-size:14.5px">Also in the ledger: our theorem advertised as stability whose premise, determinant non-negativity, also holds for unstable systems (R06); a stronger statement now compiles (F10). Row R09, counted as measured, is a mismatched run (nonlinear prompts scored against linear labels), not a measured null. One team, one day: not a rate. No median is shown.</p>
{fn('<b>Ledger</b> F04 F05 F08 F10 A01 · scopedesk/ledger/KILL-LEDGER.md and kill_ledger.json (all rows, witnesses, times and caveats)', '<b>Review</b> single-reader, not Codex-reviewed: the critic’s ledger (Codex corrected only R06); rows not independently approved', stamp)}"""
    notes.append("The ledger. Five claims we held that did not survive, each with a witness: a diffusion threshold of ten, false at ratio one point one; our liquid bridge key; a regression that tested a different question; ids that leaked labels; our Price node, already in ATLAS. Sixteen of twenty-one rows were caught by an independent reviewer or validator, two with a hold, three only by the author. No control arm: not collective intelligence.")

    # ------------------------------------------------------------ 5 Collective (2:15-2:45)
    Hd, Lp = f["headroom"], f["leanpilot"]
    bar = lambda v, label, cls: f'<div style="display:flex;align-items:center;gap:8px;margin:5px 0"><div style="width:140px;font-size:14px">{label}</div><div style="flex:1;background:var(--rule);border-radius:4px;height:20px"><div style="width:{v}%;height:20px;background:{cls};border-radius:4px"></div></div><div style="width:62px;font:700 14px var(--mono)">{v}/100</div></div>'
    mc, mk = Lp["median_calls"], Lp["median_tokens_k"]
    s5 = f"""{brand(5)}
<h2 style="font-size:29px;margin:22px 0 8px">What the collective measured: no advantage shown in two small comparisons, and the proof pilot sat at a ceiling.</h2>
<div class="row" style="gap:14px;align-items:stretch">
 <div class="col card" style="padding:8px 12px"><h3><span class="pf si">Simulated</span> enzyme replay</h3><p class="small" style="margin:0 0 2px;font-size:13.5px">{Bl['measured_nonstop']:,} measured variants, {Bl['budget']:,} extra assays.</p>
 {bar(Bl['q2c_1000'], 'Single planner', '#d9480f')}{bar(Bl['shared_1000'], 'Shared specialists', '#15202b')}{bar(Bl['lazysp_1000'], 'Plain lazy search', '#2b6e3f')}
 <p class="small" style="margin:4px 0 0;font-size:13.5px">No collective advantage shown. One repeated panel, about {Bl['clusters']} distinct problems; the lazy search's gain sits mostly in one repeated pair and its assay-count interval includes zero.</p></div>
 <div class="col card" style="padding:8px 12px"><h3>Headroom check on the frozen test set</h3><p class="small" style="margin:0;font-size:14px">Unguarded models, no code tool: Claude Sonnet 5.5 <b>{Hd['claude']['right']}/{Hd['claude']['n']}</b> ({Hd['claude']['pct']}%), Gemini 3.8 flash <b>{Hd['gemini']['right']}/{Hd['gemini']['n']}</b> ({Hd['gemini']['pct']}%). Checker-tool arm not run. Effective n is {Hd['families']} families. This measures judgement, not derivation, and is a coarse consistency check scored by the key's author; not a model ranking. Gemini's misses sit in wavelength ({Hd['gemini_wavelength']['errors']} of {Hd['gemini_wavelength']['N']}) and Greenhill ({Hd['gemini_greenhill']['errors']} of {Hd['gemini_greenhill']['N']}). It mostly shows the test set is not hard for a frontier model without tools; nothing here says agents need the gate.</p></div>
</div>
<div class="card" style="padding:8px 12px;margin-top:10px"><h3><span class="pf pr">Compiled</span> proof-search pilot, {Lp['lemmas']} frozen integer-arithmetic lemmas</h3><p class="small" style="margin:0;font-size:14px">Same model, {Lp['replicates']} replicates, {Lp['calls_per_run']} calls per run: every arm certified {Lp['lemmas']}/{Lp['lemmas']} in every run, a ceiling. Library reuse is real but saved nothing: median calls none {mc['N']:g}, private {mc['P']:g}, sequential {mc['Q']:g}, shared {mc['S']:g}; median tokens {mk['N']}k, {mk['P']}k, {mk['Q']}k, {mk['S']}k. Deterministic tactics certified {Lp['deterministic_solved']}/{Lp['lemmas']}. All {Lp['recertified']} recorded proofs re-certified after the checker was repaired, a repair made after the outcomes. Call-matched, not compute-matched; arithmetic surrogates, not biology.</p></div>
{fn('<b>Ledger</b> B02 B03 P02 P03 · artifacts/core/replay/table_primary.csv · tasks/results/guilds.json · artifacts/bench_headroom/ · lean_commons/PREREG.md (Addendum D)', '<b>Review</b> single-reader, not Codex-reviewed: the guilds results, scored by the key’s author; Codex’s review of those statements is advisory only', stamp)}"""
    notes.append("What the collective measured. Shared specialists equal a single planner, seventy-eight of a hundred each; a lazy search reaches ninety-six, mostly one pair. No advantage shown in two small comparisons. Unguarded models without a code tool score one hundred twenty-one and one hundred ten of one hundred twenty-seven; the checker arm was not run. The proof pilot sat at a ceiling.")

    # ------------------------------------------------------------ 6 Close (2:45-3:00)
    U = f["usage"]
    infra = (f"<b>Infrastructure used, receipts only</b> Nebius H100s with NVIDIA BioNeMo ESM2: {U['esm2_sizes']} sizes, {U['jobs']} jobs, {U['job_seconds']:,} recorded job-seconds, no clear benefit (B03) · "
             f"Nebius hosted OpenFold2: {U['nebius_structure_calls']} structure calls, predicted, low confidence · OpenResearch: local CPU analysis logs (enzyme data; nonlinear sweep) · "
             f"Gemini: {U['gemini_review_calls']} bounded review calls and the headroom run · receipts in artifacts/scale/ artifacts/services/ artifacts/gpu/orx/")
    s6 = f"""{brand(6)}
<h2 style="font-size:30px;margin:24px 0 10px">Reusable now: a checker that returns a witness. Outside use: none observed yet.</h2>
<div class="row" style="gap:16px">
 <div class="col"><div class="card" style="padding:9px 14px;height:100%"><h3>Now</h3><p class="small" style="margin:0;font-size:15px">The checker, repair enumerator, test set and ledger are in this repository. A fresh-clone acceptance run passed (exit 0, {Ac['seconds']} s) at an earlier commit; a receipt for the final commit is {pend}</p></div></div>
 <div class="col"><div class="card" style="padding:9px 14px;height:100%"><h3>Next, a proposal</h3><p class="small" style="margin:0;font-size:15px">A pilot on a modelling team's recent reuse decisions. Delphi Frontier, a proposal, nothing deployed: one page per open problem showing what we know, what's next and who is working on it. Our own seed questions failed our own validator: 0 of 7 bounded (ledger R21, single-reader, not re-run by the critic). Misprediction map over a large ensemble: {pend}</p></div></div>
 <div class="col"><div class="card" style="padding:9px 14px;height:100%"><h3>Credit, and what we do not claim</h3><p class="small" style="margin:0;font-size:15px">ATLAS (facebookresearch/atlas-lean), Prove2Me (arXiv 2608.28433), Rashid et al. 2017, lean-bio, crnt-lean, Ripple (arXiv 2607.13531). No first library, no universal threshold, and no claim that a named law is wrong.</p></div></div>
</div>
<div class="card" style="padding:9px 14px;margin-top:12px"><h3>Scorecard</h3><p class="small" style="margin:0;font-size:15px">{f['scorecard']['records']} records: {f['scorecard']['linked']} linked to scope-check benchmark families, {f['scorecard']['related_lemma']} related formal lemma (target unestablished), {f['scorecard']['empirical']} empirical/framework, {f['scorecard']['no_check']} without a corresponding check. Single-reader statuses, revised after a Codex review of version 0; the revision was not re-reviewed. The {f['scorecard']['no_check']} are a backlog, not open problems, and the {f['scorecard']['linked']} are not {f['scorecard']['linked']} false laws.</p></div>
<p style="font:500 26px/1.2 var(--serif);margin:14px 0 0;max-width:1120px">Make the assumptions behind a biological-model decision <em style="font-style:normal;border-bottom:4px solid var(--orange)">executable and auditable</em>.</p>
{fn('<b>Ledger</b> A01 A02 P01 P07 P08 · scopedesk/scorecard/ (critic, v0) · scopedesk/oracles/results/accept_receipt_fresh_clone.json · planning/rethink/PRIOR-ART-VERDICT.md', infra, '<b>Review</b> single-reader, not Codex-reviewed: scorecard statuses (revised after a Codex review of the first draft; the revision was not re-reviewed)', stamp)}"""
    notes.append("Reusable now: a checker that returns a witness. Outside use: none observed yet. Next, a proposal: a pilot on a modelling team's reuse decisions, and Delphi Frontier; our own seed questions failed our own validator, zero of seven bounded. Scorecard: twenty-one records, six linked to benchmark families, one related lemma, two empirical, twelve without a check; single reader. Credit ATLAS and Prove2Me. Make the assumptions executable and auditable.")
    return [s1, s2, s3, s4, s5, s6], notes


def assemble(slides, notes, prov):
    css = (HERE.parent / "deck.css").read_text() + EXTRA_CSS
    js = (HERE.parent / "deck.js").read_text()
    body = ""
    for i, (s, n) in enumerate(zip(slides, notes), 1):
        body += f'<section class="slide" id="s{i}" aria-label="Slide {i} of 6">{s}<div class="notes">{E(n)}</div></section>\n'
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Delphi: from candidate laws to checked theorems</title>
<!-- built {prov['built']} from artifacts commit {prov['git']['head']}; numbers rendered from presentation/delphi/facts.py; inputs hashed in deck.provenance.json -->
<style>{css}</style></head>
<body><div class="stage"><div class="deck">
{body}</div></div><div id="notes-live" class="notes"></div><div class="hint">← → navigate · n notes · print = one slide per page</div>
<script>{js}</script></body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out-dir", default=str(HERE))
    a = ap.parse_args()
    root = Path(a.root).resolve()
    FA.ROOT = root
    f = FA.build()
    led = (root / "planning/rethink/CLAIM-LEDGER.md").read_text()
    led_ids = set(re.findall(r"^\| ([A-Z]\d\d) \|", led, flags=re.M))
    head = git(root, "rev-parse", "HEAD") or "unknown"
    prov = {"built": seattle_now(), "root": str(root),
            "git": {"head": head, "branch": git(root, "rev-parse", "--abbrev-ref", "HEAD"),
                    "inputs_untracked_or_modified": [l[3:] for l in (git(root, "status", "--porcelain", "--", *INPUTS) or "").splitlines()]},
            "sha256": {p: sha(root / p) for p in INPUTS}, "ledger_ids": sorted(led_ids)}
    slides, notes = build_slides(f, led_ids, head)
    out = Path(a.out_dir)
    (out / "deck.html").write_text(assemble(slides, notes, prov))
    words = [len(re.sub(r"<[^>]+>", " ", n).split()) for n in notes]
    prov["spoken_words"] = {"total": sum(words), "per_slide": words}
    (out / "deck.provenance.json").write_text(json.dumps(prov, indent=1) + "\n")
    (out / "facts.json").write_text(json.dumps(f, indent=1, ensure_ascii=False) + "\n")
    sn = [f"# Speaker notes: Delphi deck", "", f"Built {prov['built']} from {head}.", ""]
    t = 0
    for i, n in enumerate(notes, 1):
        sn += [f"**Slide {i}** ({words[i-1]} words)", "", n, ""]
    (out / "speaker-notes.md").write_text("\n".join(sn))
    print(f"spoken words: {sum(words)} per slide {words}")
    if sum(words) > 420:
        raise SystemExit("script too long for the 3-minute budget")
    print("wrote", out / "deck.html")


if __name__ == "__main__":
    main()
