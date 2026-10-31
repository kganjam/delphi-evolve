#!/usr/bin/env python3
"""Build the static Delphi landing page, appendix and blog from facts.py (committed artifacts).  No npm, no network.

    python3 presentation/delphi/build_site.py [--root .]

Owns: site/delphi/index.html, appendix.html, blog.html, style.css, assets/ (copies of the deck PDF/HTML/notes) and
presentation/delphi/blog.md.  Does NOT touch site/review/ (owned by the Codex API worker): it is linked only if
site/review/index.html already exists in this tree, and otherwise shown as pending.
"""
from __future__ import annotations

import argparse
import html
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import facts as FA  # noqa: E402

E = html.escape

CSS = """
:root{--bg:#f6f3ea;--card:#fdfcf8;--ink:#15202b;--ink2:#44505b;--rule:#d8d1bf;--accent:#d9480f;--ok:#2b6e3f;--blue:#1864ab;--violet:#5f3dc4;--warn:#8a5a00;--warnbg:#fbf3df;--s:#e3efe6;--u:#fbe0d3}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#14191f;--card:#1c232b;--ink:#eceae2;--ink2:#b9c0c7;--rule:#323c46;--accent:#ff8a54;--ok:#7bd193;--blue:#7db4ee;--violet:#b8a4f5;--warn:#f0c46b;--warnbg:#2a2415;--s:#1d3326;--u:#3d2418}}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:980px;margin:0 auto;padding:28px 16px 64px}
h1{font:500 clamp(30px,6vw,52px)/1.08 "Iowan Old Style",Palatino,Georgia,serif;letter-spacing:-.02em;margin:.2em 0 .3em}
h2{font:600 clamp(21px,3.4vw,27px)/1.2 "Iowan Old Style",Palatino,Georgia,serif;margin:2em 0 .5em}
h3{font:700 13px/1.2 system-ui,sans-serif;letter-spacing:.09em;text-transform:uppercase;color:var(--ink2);margin:0 0 6px}
p{margin:.5em 0}a{color:var(--blue)}.lede{font:italic 400 clamp(19px,2.6vw,23px)/1.4 "Iowan Old Style",Palatino,Georgia,serif;color:var(--ink2)}
.status{font:13px/1.4 ui-monospace,Menlo,monospace;color:var(--ink2);border:1px solid var(--rule);border-radius:6px;padding:6px 10px;background:var(--card)}
.grid3{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:12px;margin:12px 0}
.card{background:var(--card);border:1px solid var(--rule);border-radius:8px;padding:12px 14px}
.pf{display:inline-block;font:700 11.5px/1 system-ui;letter-spacing:.08em;text-transform:uppercase;border-radius:4px;padding:3px 7px;color:#fff;margin-right:6px}
.pf.pr{background:var(--ok)}.pf.ex{background:var(--blue)}.pf.si{background:var(--violet)}.pf.ob{background:#44505b}
.pend{display:inline-block;font:700 11.5px/1 system-ui;letter-spacing:.08em;text-transform:uppercase;color:var(--warn);border:1.5px dashed var(--warn);border-radius:4px;padding:2px 7px;background:var(--warnbg)}
.scope{border-left:4px solid var(--accent);padding:6px 12px;margin:12px 0;background:var(--card);border-radius:0 6px 6px 0}
table{border-collapse:collapse;width:100%;font-size:15px}th,td{border-bottom:1px solid var(--rule);padding:6px 8px;text-align:left;vertical-align:top}th{font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--ink2)}
.scroll{overflow-x:auto}td.s{background:var(--s);text-align:center;font-family:ui-monospace,monospace}td.u{background:var(--u);text-align:center;font:700 14px ui-monospace,monospace}
.mono{font:14px/1.4 ui-monospace,Menlo,monospace}.chain{display:flex;flex-direction:column;gap:2px;align-items:stretch;max-width:340px}
.node{border:2px solid var(--ink);border-radius:8px;background:var(--card);padding:6px 10px;font:600 15px ui-monospace,monospace;text-align:center}.node.pn{border-style:dashed;border-color:var(--warn);background:var(--warnbg);color:var(--warn)}
.arrow{text-align:center;color:var(--accent);font-weight:700}
details{border:1px solid var(--rule);border-radius:8px;background:var(--card);padding:8px 12px;margin:8px 0}summary{cursor:pointer;font-weight:600}
nav a{margin-right:14px}footer{margin-top:3em;font-size:14px;color:var(--ink2);border-top:1px solid var(--rule);padding-top:12px}
"""


def page(title, body, head_extra=""):
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title><link rel="stylesheet" href="style.css">{head_extra}</head>
<body><main>{body}</main></body></html>
"""


PEND = '<span class="pend">pending</span>'


def landing(f, commit, review_exists):
    P, T, Bn, Rp, Kl, Ac, Sc, Bl = f["price"], f["turing"], f["bench"], f["repair"], f["kills"], f["accept"], f["scorecard"], f["baseline"]
    Hd, Lp, Us, Sw, Ci = f["headroom"], f["leanpilot"], f["usage"], f["sweep"], f["citations"]
    W, WIN = P["witnesses"], T["windows"]
    scan = T["scan"]
    head = "".join(f"<th>{E(s['L_over_pi'])}</th>" for s in scan)
    cells = "".join(f"<td class='{'u' if s['verdict'] == 'linearly_unstable' else 's'}'>{'grows' if s['verdict'] == 'linearly_unstable' else 'stable'}</td>" for s in scan)
    nmut = sum(1 for m in T["lean"]["mutants"] if m["exit"] != 0)
    rev = ('<a href="../review/index.html">interactive walkthrough with the length slider (exact-browser calculation versus compiled receipts)</a>'
           if review_exists else f"interactive walkthrough from the review worker: {PEND} (not yet committed in this tree)")
    g, A5 = Rp["nonlinear_grid"], Bn["at5"]["totals"]
    wit = "".join(f"<details><summary>Drop: {E(v['drops'])} <span class='mono'>({E(k)})</span></summary><p>{E(v['reading'])}</p></details>" for k, v in W.items() if k != "reversed_cost_is_false")
    wit += f"<details><summary>Drop: {E(W['reversed_cost_is_false']['drops'])} <span class='mono'>(reversed_cost_is_false; plus {len(P['mutants'])} changed-target mutants the compiler rejects)</span></summary><p>{E(W['reversed_cost_is_false']['reading'])}</p></details>"
    kc = Kl["kind_counts"]
    FX = f["frontier_example"]
    FX_TXT = (" One example of the claim, bounded test, result loop (a labelled example only, never evidence for the checker): one published claim about a cavefish gene re-tested against a later, different assembly was consistent with the claim (exact k-mer absence, positive controls present); the test was preregistered before the result (commits " + FX["prereg_commit"] + " then " + FX["result_commit"] + " in the separate delphi-frontier repository). It is single-reader, not independently reviewed; n=1 per population, haploid assemblies, nothing causal, and the other cavefish population was not tested."
              if FX.get("present") else "")
    FRONTIER = ('Delphi Frontier map (a proposal, nothing deployed; single-reader, not independently reviewed; it does not endorse our seed questions, which failed our own validator, 0 of 7 bounded, ledger R21): <a href="../review/frontier.html">the Frontier map from the review worker</a>.' + FX_TXT
                if (Path(FA.ROOT) / "site/review/frontier.html").exists() else f"Delphi Frontier map: {PEND}")
    lrows = "".join(f"<tr><td>{E(r['id'])}</td><td>{E(r['claim'])}</td><td>{E(r['kind'])}</td><td>{E(r['caught_by'])}</td><td>{E(r['allowed'])}</td><td class='mono'>{E(str(r['claim_stated_pdt']))}</td><td class='mono'>{E(str(r['kill_recorded_pdt']))}</td><td>{E(str(r['duration_min']))}</td></tr>" for r in Kl["all_rows"])
    V = f["errors"]["stability_mislabel"]
    bar = lambda v, label, color: f'<div style="display:flex;align-items:center;gap:10px;margin:6px 0"><div style="width:170px">{label}</div><div style="flex:1;background:var(--rule);border-radius:4px;height:22px"><div style="width:{v}%;height:22px;background:{color};border-radius:4px"></div></div><div class="mono" style="width:64px">{v}/100</div></div>'
    return f"""
<p class="status">Draft · built from commit {E(commit[:8])} · items marked pending are not results · owner-private review copy</p>
<h1>Delphi: from candidate laws to checked theorems</h1>
<div class="scope"><b>Review status.</b> The independent reviewer that covered earlier receipts is unavailable, so anything without a recorded independent review is labelled <b>single-reader, not Codex-reviewed</b>: the repair demo and nonlinear grid, the checker-versus-key recomputation, the kill ledger rows (Codex corrected only R06), the scorecard statuses, the headroom check and the proof-search pilot. A fresh read-only review of the final materials is planned after the final cut; nothing here has been marked accepted.</div>
<p class="lede">The textbook inequality is green. A program checks whether it applies to the model in front of you, returns a witness when it does not, and proposes a repair. Below: what runs, then what did not survive.</p>
<nav><a href="#reveal">Reveal</a><a href="#repair">Check and repair</a><a href="#nodes">Compiled nodes and test set</a><a href="#ledger">Ledger</a><a href="#collective">Collective</a><a href="#close">Close</a><a href="appendix.html">Appendix</a><a href="blog.html">Blog</a></nav>
<div class="grid3">
 <div class="card"><h3><span class="pf pr">Proved</span></h3>Compiled in Lean 4 under stated assumptions with rejected mutants: a finite Turing instance; a conditional Hamilton regression theorem.</div>
 <div class="card"><h3><span class="pf si">Simulated</span></h3>An independent solver on declared kinetics; a retrospective enzyme replay. The agent evaluation: {PEND}</div>
 <div class="card"><h3><span class="pf ob">Observed</span></h3><b>None.</b> No wet-lab experiment; simulations only.</div>
</div>

<h2 id="reveal">1. The reveal: length changes the answer</h2>
<p>Declared model: J = [[{T['J'][0][0]}, {T['J'][0][1]}], [{T['J'][1][0]}, {T['J'][1][1]}]], diffusivities D = ({T['D'][0]}, {T['D'][1]}), one-dimensional Neumann boundaries. det(J − qD) = {E(T['det_factored'])}, so the continuum band is {T['continuum_band'][0]} &lt; q &lt; {T['continuum_band'][1]}. Admissible modes are q = (nπ/L)².</p>
<div class="scroll"><table><tr><th>L / π</th>{head}</tr><tr><th>linear verdict</th>{cells}</tr></table></div>
<p>Exactly, mode n grows iff {WIN['c_lo']}n² &lt; (L/π)² &lt; {WIN['c_hi']}n². The model grows for L/π in (√{WIN['c_lo']}, √{WIN['c_hi']}) and for every L/π above 2√{WIN['c_lo']}, and is stable in the window √{WIN['c_hi']} ≤ L/π ≤ 2√{WIN['c_lo']} (recomputed exactly by the trace check).</p>
<div class="grid3">
 <div class="card"><h3><span class="pf pr">Proved</span> compiled instance</h3>Lean {E(T['lean']['version'])}, build exit {T['lean']['build_exit']}: L = π admits no unstable mode; L = 2π admits one (n = {T['two_pi']['unstable_modes'][0]}, det = {E(T['two_pi']['n1_det'])}). {nmut} mutants rejected. Only these two lengths are compiled.</div>
 <div class="card"><h3><span class="pf ex">Exact arithmetic</span></h3>The strip is rational arithmetic, not Lean. Over the reals with Mathlib, a host probe re-run by the director shows no admissible mode in the band at L = π (no ledger row yet).</div>
 <div class="card"><h3><span class="pf si">Simulated</span> / <span class="pf ob">Observed</span></h3>Nonlinear check of this model: {PEND}. Observed tissue pattern: <b>none</b>.</div>
</div>
<div class="scope"><b>Limitation first.</b> Counting admissible modes in a band is a trivial algorithm, exact for rational L/π. This is classical mathematics and a linear-mode statement for a declared model: it does not say a pattern forms, and we are not saying Turing was wrong. Non-monotone dependence on size is textbook-derivable and not claimed as new. Finite-size effects on Turing patterns are discussed in Kurics et al. (arXiv 1407.7114) and Ouchdiri et al. (arXiv 2509.15829); {Ci['by']} checked the full texts with {Ci['tool']}, whose abstracts do not mention the point; mode quantisation itself is textbook and we claim no novelty. The offer is a certificate and packaging.</div>
<p>{rev}</p>

<h2 id="repair">2. The check and repair</h2>
<div class="grid3">
 <div class="card"><h3>Request</h3>Target wavelength with equal diffusivities (Dv/Du = 1): {Rp['requests']} requests.</div>
 <div class="card"><h3><span class="pf ex">Exact</span> refused</h3>No admissible unstable mode (turing-ddi), a witness attached: {Rp['gate_refused']} of {Rp['requests']}. The plain formula accepts them.</div>
 <div class="card"><h3><span class="pf ex">Exact</span> repair, then <span class="pf si">simulated</span></h3>Raise Dv/Du to {Rp['repair_ratio']} (most requests); an independent solver finds a pattern on {Rp['repair_all_seeds']} of {Rp['requests']} requests; mean success {Rp['repair_mean']} (fraction of {Rp['seeds']} noise seeds, averaged over requests). The plain formula's design without repair: {int(Rp['plain_formula_success'])} of {Rp['requests']}, by construction, since equal diffusivities admit no instability for any kinetics.</div>
</div>
<div class="scope"><b>Caveats, printed.</b> One kinetics (Schnakenberg), 1-D Neumann, {Rp['seeds']} noise seeds, no confidence interval: a model-only check, not an experiment. Near-onset repaired patterns are marginal (amplitude up to {Rp['amp_max_at_ratio_9']} against a {Rp['amp_threshold']:.2f} threshold). The other {Rp['requests'] - Rp['repair_all_seeds']} requests did not succeed on all seeds, and repairs for {Rp['other_refusals']} further refusals worked on {Rp['other_refusals_repair_ok']}. No domain-length repair was found. Across {g['n']} nonlinear configurations the gate agreed with the solver on {g['gate_agrees']} and the plain formula on {g['plain_agrees']}; linear theory named the dominant wavelength in {g['dominant_mode']} patterned cases. Source: artifacts/rethink_nca/repair.json (not in the claim ledger yet).</div>

<h2 id="nodes">3. Compiled nodes and the test set</h2>
<div class="grid3"><div class="chain"><div class="node" style="color:var(--ink2)">price · ATLAS has it; ours duplicates it</div><div class="arrow">↓ used by</div><div class="node">selection_only</div><div class="arrow">↓ used by</div><div class="node">hamilton_regression</div></div>
<div class="card" style="grid-column:span 2"><h3><span class="pf pr">Proved</span> receipt</h3>Lean exit {P['original_exit']}; axioms: propext, Classical.choice, Quot.sound only. {len(W)} witness controls exit {P['witness_exit']}. {len(P['mutants'])} changed-target mutants rejected (exit {P['mutants'][0]['exit']}). The dependencies are read from the Lean source. The Price identity is already formalized in the ATLAS biology library (facebookresearch/atlas-lean), so our version duplicates it; a critic's code search found no Hamilton form there, though that search is not exhaustive. A regression statement, not a causal cost–benefit rule. Statement review by a second reader: {PEND}</div></div>
<p>Each assumption has an exact compiled witness showing what breaks without it:</p>
{wit}
<div class="card"><h3>Test set, version 1.2</h3>{Bn['items']} requests in {Bn['families']} families whose answers come from stated methods under declared conventions (exact rational arithmetic for Turing, Hamilton and Hawk–Dove items; numerical or closed-form for Kimura, Greenhill and Fisher–KPP); key hash {E(Bn['key_sha256'][:16])}…. <b>Frozen.</b> Codex's metadata and wording check passes ({Bn['codex_metadata']['checks']} of {Bn['codex_metadata']['checks']}); it does not audit the answers. Audit trail: a blinded payload-only audit agreed on {Bn['blind_audit']['agree']} of {Bn['blind_audit']['n']} items of an earlier candidate (a model of the same family as the key's author, one run).</div>
<div class="card"><h3>Checker against the key (Turing, 2-D Turing and wavelength items)</h3><table><tr><th>method</th><th>agrees with the key</th></tr><tr><td>Gate with the record</td><td>{A5['full']} / {A5['n']}</td></tr><tr><td>Plain textbook formula</td><td>{A5['C0']} / {A5['n']}</td></tr><tr><td>Continuum condition only</td><td>{A5['continuum_only']} / {A5['n']}</td></tr><tr><td>Record hash altered (refuses)</td><td>{A5['record_hash_changed_refused']} / {A5['n']}</td></tr></table>
<p><b>Printed caveat:</b> the set is trap-enriched and shares its convention document with the checker; this is not external validation. The last row shows provenance dependence only.</p></div>

<h2 id="ledger">4. The ledger: claims we held that did not survive</h2>
<div class="scope">{Kl['n_rows']} rows. {Kl['independent']} were caught by an independent reviewer or validator, {Kl['mixed']} by the author with an independent hold, {Kl['author_only']} only by the author's own measurement or rule. <b>There is no control arm: this compares independent audit with self-audit. It is not a measurement of collective intelligence.</b> Kinds are kept separate: prior art {kc['prior art']}, counterexample {kc['counterexample']}, measured {kc['measured']}, mis-operationalised {kc['mis-operationalised']}, convention defect {kc['convention defect']}, process defect {kc['process defect']}, design defect {kc['design defect']}. One team, one day: this is a hit rate for us, not a rate for the field.</div>
<div class="scroll"><table><tr><th>id</th><th>claim we held</th><th>kind</th><th>caught by</th><th>allowed wording now</th><th>claim stated (PDT)</th><th>kill recorded (PDT)</th><th>min</th></tr>{lrows}</table></div>
<p><b>R09 is not a measured null.</b> Its kind label reads "measured null (on a mismatched run)" in the critic's ledger, and it is counted among the measured rows, but the run asked a nonlinear question and was scored against linear-mode labels. It shows neither accuracy nor a ceiling, and the headroom check on the frozen key is the measurement that survives.</p>
<p><b>Timing caveats, printed.</b> Times are file modification times or git commit times, so durations are rough: a commit time is not the moment of an utterance, and rows differ in kind (lookups, audits, measurements). {Kl['n_with_both_times']} of {Kl['n_rows']} rows have both times derivable; the rest read "not derivable". No median is shown. R06 (our theorem <span class="mono">{E(V['name'])}</span>): its premise, determinant non-negativity at every admissible mode, was advertised as stability. The premise holds for unstable systems; the critic's analytic witness, not Lean-compiled, is J = diag(2, 2) with equal unit diffusivities on L = π, where D(q) = (2 − q)² is never negative yet mode n = 1 has two growth eigenvalues. A revised module compiles a stronger statement (ledger F10), with determinant positivity assumed and no new mutants.</p>
<p>Source: <span class="mono">scopedesk/ledger/KILL-LEDGER.md</span> and <span class="mono">kill_ledger.json</span> (critic).</p>

<h2 id="collective">5. What the collective measured</h2>
<div class="card"><h3><span class="pf si">Simulated</span> retrospective enzyme panel</h3><p>{Bl['measured_nonstop']:,} measured variants, {Bl['budget']:,} extra assays.</p>{bar(Bl['q2c_1000'], 'Single planner', '#d9480f')}{bar(Bl['shared_1000'], 'Shared specialists', 'var(--ink)')}{bar(Bl['lazysp_1000'], 'Plain lazy search', 'var(--ok)')}
<p>No collective advantage shown. One repeated panel, about {Bl['clusters']} distinct problems; the lazy search's gain sits mostly in one repeated pair and its assay-count interval includes zero.</p></div>
<div class="grid3">
<div class="card"><h3>Headroom check on the frozen test set</h3>Unguarded models, no code tool: Claude Sonnet 5.5 {Hd['claude']['right']}/{Hd['claude']['n']} ({Hd['claude']['pct']}%), Gemini 3.8 flash {Hd['gemini']['right']}/{Hd['gemini']['n']} ({Hd['gemini']['pct']}%). Checker-tool arm not run. Effective n is {Hd['families']} families. This measures judgement, not derivation, and is a coarse consistency check scored by the key's author; not a model ranking. Gemini's misses sit in wavelength ({Hd['gemini_wavelength']['errors']} of {Hd['gemini_wavelength']['N']}) and Greenhill ({Hd['gemini_greenhill']['errors']} of {Hd['gemini_greenhill']['N']}). It mostly shows the test set is not hard for a frontier model without tools. The "agents need the gate" claim is not supported by anything here.</div>
<div class="card" style="grid-column:span 2"><h3><span class="pf pr">Compiled</span> proof-search pilot, {Lp['lemmas']} frozen integer-arithmetic lemmas</h3>Same model, {Lp['replicates']} replicates, {Lp['calls_per_run']} calls per run: every arm certified {Lp['lemmas']}/{Lp['lemmas']} in every run, a ceiling. Library reuse is real but saved nothing: median calls none {Lp['median_calls']['N']:g}, private {Lp['median_calls']['P']:g}, sequential {Lp['median_calls']['Q']:g}, shared {Lp['median_calls']['S']:g}; median tokens {Lp['median_tokens_k']['N']}k, {Lp['median_tokens_k']['P']}k, {Lp['median_tokens_k']['Q']}k, {Lp['median_tokens_k']['S']}k. Deterministic tactics certified {Lp['deterministic_solved']}/{Lp['lemmas']}. All {Lp['recertified']} recorded proofs re-certified after the checker was repaired, a repair made after the outcomes (PREREG Addendum D). Call-matched, not compute-matched; the statements are arithmetic surrogates written by the experimenter, not biology, and Codex's fidelity review of them is advisory only.</div></div>

<h2 id="close">6. Close</h2>
<div class="grid3">
 <div class="card"><h3>Reusable now</h3>The checker, repair enumerator, test set and ledger are in this repository. A fresh-clone acceptance run passed (exit 0, {Ac['seconds']} s) at an earlier commit; a receipt for the final commit is {PEND} Outside use: none observed yet.</div>
 <div class="card"><h3>Next, a proposal</h3>A pilot on a modelling team's recent reuse decisions. Delphi Frontier, a proposal, nothing deployed: one page per open problem showing what we know, what's next and who is working on it. Our own seed questions failed our own validator: 0 of 7 bounded (ledger R21, single-reader, not re-run by the critic). Misprediction map over a large ensemble: {PEND}</div>
 <div class="card"><h3>Credit, and what we do not claim</h3>ATLAS (facebookresearch/atlas-lean), Prove2Me (arXiv 2608.28433), Rashid et al. 2017, lean-bio, crnt-lean, Ripple (arXiv 2607.13531). We aim to complement ATLAS, not compete with it; offering Turing statements to it is pending. No first library, no universal threshold, no claim that a named law is wrong.</div>
</div>
<div class="card"><h3>Scorecard</h3>{Sc['records']} records: {Sc['linked']} linked to scope-check benchmark families, {Sc['related_lemma']} related formal lemma (target unestablished), {Sc['empirical']} empirical/framework, {Sc['no_check']} without a corresponding check. Single-reader statuses, revised after a Codex review of version 0; the revision was not re-reviewed. The {Sc['no_check']} are a backlog, not open problems, and the {Sc['linked']} are not {Sc['linked']} false laws. The records' correspondence to their source papers is not reviewed, and the checks are of declared models only. Source: <span class="mono">scopedesk/scorecard/</span>.</div>
<p>{FRONTIER}</p>
<h2>Infrastructure used</h2>
<div class="card"><table>
<tr><th>tool</th><th>what ran</th><th>result</th><th>receipts</th></tr>
<tr><td>Nebius H100s, NVIDIA BioNeMo TransformerEngine ESM2</td><td>{Us['esm2_sizes']} model sizes scored all {Us['variants_per_model']:,} enzyme variants: {Us['jobs']} jobs, all completed, {Us['job_seconds']:,} recorded job-seconds ({Us['h100_hours']} H100-hours); released baseline</td><td>no clear assay-saving benefit (ledger B03)</td><td class="mono">artifacts/scale/</td></tr>
<tr><td>Nebius hosted scientific-model catalogue</td><td>{Us['nebius_structure_calls']} OpenFold2 structure calls on the enzyme parent and the best variant (single sequence, no templates); an ESMFold2 attempt was blocked by the server</td><td>predicted, low confidence (ranking confidence about {Us['nebius_structure_ranking_confidence']} of 100); not a measurement</td><td class="mono">artifacts/services/nebius/</td></tr>
<tr><td>OpenResearch</td><td>two local CPU analyses, logged through the tool (the enzyme data; the analysis of the nonlinear sweep, which itself ran outside the tool), and full-text retrieval of {Ci['texts_checked']} papers for citation verification</td><td>not hosted compute (ledger R02); no GPU or Nebius used for the sweep; the citation check is single-reader</td><td class="mono">artifacts/gpu/orx/, {Sw['receipt']}, {Ci['receipt']}</td></tr>
<tr><td>Gemini</td><td>{Us['gemini_review_calls']} bounded review calls (cap {Us['gemini_review_cap']}; {Us['gemini_review_input_tokens']:,} input and {Us['gemini_review_output_tokens']:,} output tokens), and {Us['gemini_headroom_calls']} calls as a subject of the headroom check</td><td>review opinions, not evidence; headroom result on slide 5</td><td class="mono">artifacts/services/gemini/, artifacts/bench_headroom/</td></tr>
</table>
<p>Only tools with committed receipts are listed. Claude Sonnet 5.5 workers ran on subscription capacity; no metered charge is claimed here. The Delphi checks themselves ran on CPU.</p></div>
<h2>Downloads</h2>
<ul><li><a href="assets/deck.pdf">Six-slide deck (PDF)</a> · <a href="assets/deck.html">HTML deck</a> · <a href="assets/speaker-notes.md">three-minute script</a> · <a href="blog.html">blog</a></li>
<li>Numbers are re-derived from committed artifacts by <span class="mono">presentation/delphi/trace.py</span>; the claim ledger is <span class="mono">planning/rethink/CLAIM-LEDGER.md</span>.</li></ul>
<footer>exact-browser means rational arithmetic in a program, compiled means a Lean receipt with exit 0, simulated and observed are separate. Source commit {E(commit[:8])}.</footer>
"""


def appendix(f, commit):
    R, Bl, Sw = f["robustness"], f["baseline"], f["sweep"]
    import json as _j
    rows = ""
    raw = _j.loads((Path(FA.ROOT) / R["artifact"]).read_text())
    bins = ["1.0-1.5", "1.5-2", "2-3", "3-5", "5-10", "10-30", "30-inf"]
    for e in ("E1", "E2"):
        for noise in ("uniform", "gaussian"):
            rows += f"<tr><td>{e}</td><td>{noise}</td>" + "".join(f"<td>{raw[e][noise][b]['mean_survival_pct']}</td>" for b in bins) + "</tr>"
    return f"""
<p class="status">Appendix · not part of the three-minute pitch · built from commit {E(commit[:8])}</p>
<h1>Appendix</h1>
<h2>Robustness sweep {PEND} <span class="pend">no ledger row</span></h2>
<p>Simulated, in one two-species linear family. Share of stable systems that keep a Turing instability under {R['noise_fraction']:.0%} parameter noise, by required diffusion ratio, in two sampling ensembles (E1, E2) and two noise definitions. {R['samples_per_ensemble']:,} samples per ensemble.</p>
<div class="scroll"><table><tr><th>ensemble</th><th>noise</th>{''.join(f'<th>{b}</th>' for b in bins)}</tr>{rows}</table></div>
<p>All four rows rise monotonically with the required ratio. The absolute values move by about 10 to 20 points with the noise definition and sampling box, so no single figure is the answer.</p>
<div class="scope"><b>Scope.</b> {E(R['scope'])}. This is not a universal robustness cliff and not a property of any organism. It has not been through the claim ledger and its prior art is unchecked. A literature ratio for Nodal and Lefty is <b>not plotted</b>: the source numbers have not been read directly in this tree, and a literature point could only be descriptive context. A diffusion-ratio threshold of 10 as a universal rule is false: a linear counterexample uses 1.1.</div>
<h2>Where exact linear theory mispredicts the nonlinear outcome (preregistered sweep) <span class="pend">single-reader, not independently reviewed</span></h2>
<p>Simulated, in two textbook kinetics (Schnakenberg and Brusselator), 1-D Neumann boundaries, CPU only. The design was committed as <span class="mono">{Sw['prereg_commit']}</span> before any scored row; all {Sw['cells']:,} cells ran to completion ({Sw['wall_seconds']:,} s).</p>
<div class="scroll"><table><tr><th>quantity</th><th>cells</th></tr>
<tr><td>Linearly stable, yet a finite-amplitude pattern (all Brusselator, large perturbation, just below onset)</td><td>{Sw['r1_k']} of {Sw['r1_n']:,}</td></tr>
<tr><td>Linearly unstable, yet no pattern by the horizon</td><td>{Sw['r2_k']} of {Sw['r2_n']:,}</td></tr>
<tr><td>Linearly unstable and patterned, with a dominant wavelength different from the fastest linear mode (mostly longer, {Sw['lower_pct']}% of mismatches)</td><td>{Sw['r3_k']} of {Sw['r3_n']:,} ({Sw['r3_pct']}%)</td></tr>
<tr><td>Unresolved (the two solvers disagree, or not settled); counted in every denominator</td><td>{Sw['unresolved_k']} of {Sw['cells']:,} ({Sw['unresolved_pct']}%)</td></tr></table></div>
<div class="scope"><b>Limits.</b> A stated prior, two solvers by one author that share the equations, one family of initial perturbations: a sweep, not a claim about real tissues. Cells share parameter draws and seeds, so the exact intervals in the report treat cells as independent and are too narrow; they are not repeated here. {Sw['predictions_holding']} of 5 preregistered predictions held; {Sw['failed_prediction']} failed as stated because no linearly unstable cell failed to pattern. Not Codex-reviewed. Analysis logged as a local OpenResearch run, not hosted compute; no GPU or Nebius used. Files: <span class="mono">{Sw['report']}</span>, raw rows sha256 <span class="mono">{Sw['rows_sha256'][:8]}…</span>.</div>
<h2>Released enzyme baseline (preserved, with its nulls)</h2>
<p>{Bl['measured_nonstop']:,} measured non-stop TrpB variants from the authors' CC0 table; {Bl['imputed_excluded']} imputed-only variants excluded. On the retrospective panel, shared specialists {Bl['shared_1000']}/100 equal the single planner {Bl['q2c_1000']}/100 at {Bl['budget']:,} extra assays; a plain lazy search reaches {Bl['lazysp_1000']}/100. Five protein-model sizes did not establish assay savings. No general superiority claim. Full release: the earlier deck and site in this repository.</p>
<p><a href="index.html">Back to the Delphi page</a></p>
"""


def blog_fx(f):
    fx = f["frontier_example"]
    if not fx.get("present"):
        return ""
    return ("A labelled example of the claim, bounded test, result loop, which is not evidence for the checker: one published claim about a cavefish gene was re-tested against a later, different assembly and was consistent with the claim (exact k-mer absence, positive controls present). The test was preregistered before the result (commits " + fx["prereg_commit"] + " then " + fx["result_commit"]
            + " in the separate delphi-frontier repository); it is single-reader and not independently reviewed, with one sample per population, haploid assemblies, nothing causal, and the other population not tested. ")


def blog_parts(f):
    P, T, Bn, Rp, Kl, Sc, Bl = f["price"], f["turing"], f["bench"], f["repair"], f["kills"], f["scorecard"], f["baseline"]
    Hd, Lp, Us = f["headroom"], f["leanpilot"], f["usage"]
    V = f["errors"]["stability_mislabel"]
    kc = Kl["kind_counts"]
    A5 = Bn["at5"]["totals"]
    return [
        ("h1", "Delphi: from candidate laws to checked theorems"),
        ("p", "The textbook inequality is green. This post describes a small executable check that asks whether it applies to the model in front of you, what it returns when it does not, what is compiled behind it, what is still pending, and the claims we held that did not survive."),
        ("h2", "What we are not claiming"),
        ("p", "The conditions we check are known to experts, and we do not present them as discoveries. We ran no wet-lab experiment; the simulations are declared-model only. We do not say that any named law is wrong: a scope condition we supply refers to the extracted record of the claim. We did not build the first library of formal biology. ATLAS (facebookresearch/atlas-lean, MathlibExt/Biology) already holds a large body of exact biology statements with cited sources and non-vacuity witnesses, and Prove2Me (arXiv 2608.28433), Rashid et al. 2017, lean-bio, crnt-lean and Ripple (arXiv 2607.13531) came before at their own scope. We aim to complement ATLAS, not compete with it."),
        ("h2", "The reveal"),
        ("p", f"Take a declared two-species linear model, J = [[{T['J'][0][0]}, {T['J'][0][1]}], [{T['J'][1][0]}, {T['J'][1][1]}]] with diffusivities ({T['D'][0]}, {T['D'][1]}) and Neumann boundaries. The continuum Turing condition holds: det(J − qD) = {T['det_factored']} is negative for {T['continuum_band'][0]} < q < {T['continuum_band'][1]}. On a finite domain only q = (nπ/L)² exist. At L = π none lies in the band; at 3π/2 and 2π one does; at 5π/2 none does again. Lean {T['lean']['version']} compiles the L = π and L = 2π cases and rejects {sum(1 for m in T['lean']['mutants'] if m['exit'] != 0)} mutants; the other lengths are exact rational arithmetic. The algorithm is trivial, counting admissible modes in a band, so what we offer is a certificate and packaging, not new mathematics. Non-monotone dependence on size is textbook-derivable and not new. This is a linear-mode statement; whether a pattern forms is a nonlinear question we have not settled (pending)."),
        ("h2", "The check and the repair"),
        ("p", f"We gave the checker {Rp['requests']} requests for a target wavelength with equal diffusivities, which the plain formula accepts. It refused all {Rp['gate_refused']} with a witness. The exact check then licensed a repair, raising the diffusivity ratio to {Rp['repair_ratio']} for most requests, and an independent solver found a pattern on {Rp['repair_all_seeds']} of {Rp['requests']} requests, mean success {Rp['repair_mean']} (fraction of {Rp['seeds']} noise seeds, averaged over requests). The plain formula's design without repair succeeded on {int(Rp['plain_formula_success'])}, which is true by construction for equal diffusivities. The caveats matter: one kinetics, one-dimensional Neumann boundaries, {Rp['seeds']} noise seeds, no confidence interval, near-onset repaired patterns that are marginal, five requests that did not succeed on all seeds, and no domain-length repair found. It is a model-only check, not an experiment."),
        ("h2", "Compiled nodes and a test set"),
        ("p", f"We compiled a conditional Hamilton regression theorem that depends on a selection-only lemma, with exact witnesses for each assumption and {len(P['mutants'])} rejected changed-sign mutants (Lean exit {P['original_exit']}, standard axioms only). The Price identity underneath it is already formalized in ATLAS, so our version of that part is a duplicate; a critic's code search found no Hamilton form there, though the search is not exhaustive. A second reader has not yet reviewed the statements (pending). The test set has {Bn['items']} requests in {Bn['families']} families whose answers come from stated methods under declared conventions (exact rational arithmetic for Turing, Hamilton and Hawk–Dove items; numerical or closed-form for Kimura, Greenhill and Fisher–KPP); it is frozen and Codex's metadata and wording check passes, which does not audit the answers. On the {A5['n']} Turing, 2-D Turing and wavelength items the gate agrees with the key on {A5['full']}, the plain formula on {A5['C0']} and the continuum condition alone on {A5['continuum_only']}. The set is trap-enriched and shares its convention document with the checker, so this is not external validation."),
        ("h2", "The ledger"),
        ("p", f"We kept a ledger of claims we held that did not survive: {Kl['n_rows']} rows, each with a witness and a kind. {Kl['independent']} were caught by an independent reviewer or validator, {Kl['mixed']} by the author with an independent hold, and {Kl['author_only']} only by the author's own measurement or rule. Kinds are kept separate: prior art {kc['prior art']}, counterexample {kc['counterexample']}, measured {kc['measured']}, mis-operationalised {kc['mis-operationalised']}, convention defect {kc['convention defect']}, process defect {kc['process defect']}, design defect {kc['design defect']}. There is no control arm, so this compares independent audit with self-audit; it is not a measurement of collective intelligence, and one team's day is not a rate for the field. One row is our own theorem, {V['name']}, whose premise (determinant non-negativity) was advertised as stability; the premise also holds for unstable systems. A revised module now compiles a stronger statement, with the determinant assumed and no new mutants yet."),
        ("h2", "What the collective measured"),
        ("p", f"On the controlled enzyme replay, shared specialists matched a single planner ({Bl['shared_1000']} of 100 each) and a plain lazy search reached {Bl['lazysp_1000']}, mostly in one repeated pair, with an assay-count interval that includes zero. In a proof-search pilot on {Lp['lemmas']} frozen integer-arithmetic lemmas every arm certified all {Lp['lemmas']} in every run, a ceiling; library reuse was real but saved no calls or tokens (median calls {Lp['median_calls']['N']:g}, {Lp['median_calls']['P']:g}, {Lp['median_calls']['Q']:g}, {Lp['median_calls']['S']:g}). The statements are arithmetic surrogates, the arms are call-matched and not compute-matched, and the checker was repaired after the outcomes were seen. On the frozen test set, unguarded models without a code tool scored {Hd['claude']['right']} and {Hd['gemini']['right']} of {Hd['claude']['n']}; the checker-tool arm was not run, the effective n is {Hd['families']} families, and the check measures judgement rather than derivation. Two small comparisons showed no advantage for a shared-evidence collective, one of them at a ceiling that could not discriminate; nothing here says that agents need the gate, and the headroom result mostly shows the test set is not hard for a frontier model without tools."),
        ("h2", "Infrastructure used"),
        ("p", f"Receipts only. Five BioNeMo ESM2 sizes scored all {Us['variants_per_model']:,} enzyme variants on Nebius H100s ({Us['jobs']} jobs, all completed, {Us['job_seconds']:,} recorded job-seconds) in the released baseline, with no clear assay-saving benefit. Two OpenFold2 structure calls went to the Nebius hosted catalogue and came back predicted and low confidence. OpenResearch logged two local CPU analyses, one of the same data and one of the nonlinear sweep, neither hosted compute, and retrieved full text for a citation check; no GPU or Nebius was used for the sweep. Gemini made {Us['gemini_review_calls']} bounded review calls and was a subject of the headroom check. The Delphi checks themselves ran on CPU."),
        ("h2", "Reusable now, and next"),
        ("p", f"{blog_fx(f)}The checker, repair enumerator, test set and ledger are in the repository; outside use is none observed yet. Next, as a proposal and not a deployed system: a pilot on a modelling team's recent reuse decisions, and Delphi Frontier, one page per open problem showing what we know, what is next and who is working on it; our own seed questions failed our own validator, 0 of 7 bounded (ledger R21, single-reader, not re-run by the critic). A first scorecard of the {Sc['records']} extracted records has {Sc['linked']} linked to scope-check benchmark families, {Sc['related_lemma']} related formal lemma whose target is unestablished, {Sc['empirical']} empirical or framework, and {Sc['no_check']} without a corresponding check; the statuses are one reader's, revised after a Codex review of version 0, and the revision was not re-reviewed. A misprediction map over a large parameter ensemble is pending."),
    ]


def render_blog_html(parts):
    return "".join(f"<{t}>{E(x)}</{t}>" for t, x in parts) + '<p><a href="index.html">Back to the Delphi page</a></p>'


def render_blog_md(parts):
    return "\n\n".join(("# " if t == "h1" else "## " if t == "h2" else "") + x for t, x in parts) + "\n"


CAPS = {}


def storyboard(f, timing):
    ps = {r["slide"]: r for r in timing["per_slide"]}
    mm = lambda t: f"{int(t // 60)}:{int(t % 60):02d}"
    shots = [
        (1, "Reveal: the length strip flips from stable at π to growing at 2π", "Slider on the declared model (walkthrough, site/review) or the strip on slide 1; highlight π, then 2π.",
         "'Classical mathematics. A program checks it, with a witness.'", "deck slide 1; site/review walkthrough"),
        (2, "Request, refusal with witness, repair, independent solver", "Step the four boxes left to right; hold on the printed caveats.",
         "'Limitation first: the algorithm is trivial. The offer is the certificate, the refusal and the repair.'", "deck slide 2; site/delphi#repair"),
        (3, "Compiled nodes and the test set", "Trace price, selection_only, hamilton_regression; point at the ATLAS note; then the four-row table and its caveat.",
         "'Frozen test set. Agreement with our own key is not external validation.'", "deck slide 3; site/delphi#nodes"),
        (4, "The ledger", "Five rows with witnesses, then the 17 and 3 line and the no-control-arm sentence.",
         "'Audit versus self-audit, not collective intelligence. One team, one day.'", "deck slide 4; site/delphi#ledger"),
        (5, "What the collective measured", "Three bars; then the headroom card (checker-tool arm not run) and the proof-pilot ceiling.",
         "'No advantage shown in two small comparisons. A ceiling and a missing arm, stated as such.'", "deck slide 5; site/delphi#collective"),
        (6, "Close: reusable now, next as a proposal, credit", "Hold on the three cards, then the closing line.",
         "'Outside use: none observed yet. Nothing deployed.'", "deck slide 6; site/delphi#close"),
    ]
    CAPS.clear()
    CAPS.update({n: cap.strip("'") for n, shot, act, cap, src in shots})
    out = ["# Video storyboard: Delphi, three-minute walkthrough", "",
           f"Built to `planning/rethink/PITCH-OUTLINE.md`. Start times are the measured per-slide starts of a synthetic-voice read-through (`timing.json`, total {timing['total_mm_ss']}); a human presenter will differ. No narration audio and no video has been recorded; this is a shot list. Backup if the live demo fails: a captioned recording made from the same artifacts.", "",
           "| Start | Slide | Shot | Action | Caption | Source |", "|---|---|---|---|---|---|"]
    for n, shot, act, cap, src in shots:
        out.append(f"| {mm(ps[n]['starts_at_s'])} | {n} | {shot} | {act} | {cap} | {src} |")
    out += ["", "Rules for the recording: show the pending tags; never show an agent-evaluation number; show the printed caveats on slides 2, 3 and 4; do not show a median or a '10 of 10' count; no first-ever, universal-threshold, pattern-forms or solved-biology language, and no statement that a named law is wrong.",
            "Opening alternative if the scorecard is thin: start on the ledger's diffusion-ratio-1.1 counterexample, then the reveal.", ""]
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    a = ap.parse_args()
    root = Path(a.root).resolve()
    FA.ROOT = root
    f = FA.build()
    prov = json.loads((HERE / "deck.provenance.json").read_text())
    commit = prov["git"]["head"]
    out = root / "site/delphi"
    (out / "assets").mkdir(parents=True, exist_ok=True)
    (out / "style.css").write_text(CSS)
    review = (root / "site/review/index.html").exists()
    (out / "index.html").write_text(page("Delphi: from candidate laws to checked theorems", landing(f, commit, review)))
    (out / "appendix.html").write_text(page("Delphi appendix", appendix(f, commit)))
    parts = blog_parts(f)
    (out / "blog.html").write_text(page("Delphi blog", render_blog_html(parts)))
    (HERE / "blog.md").write_text(render_blog_md(parts))
    if (HERE / "timing.json").exists():
        (HERE / "storyboard.md").write_text(storyboard(f, json.loads((HERE / "timing.json").read_text())))
    if CAPS:
        (HERE / "video").mkdir(exist_ok=True)
        (HERE / "video" / "captions.json").write_text(json.dumps({"deck_slide_captions": {str(k): v for k, v in sorted(CAPS.items())},
            "site_ledger_caption": "The ledger on the landing page: every row with its witness, kind, and printed timing caveats.",
            "persistent_tag": "Draft. Declared-model statements only. No wet-lab experiment; simulations only. Pending items are not results."}, indent=1) + "\n")
    for src, dst in (("deck.pdf", "deck.pdf"), ("deck.html", "deck.html"), ("speaker-notes.md", "speaker-notes.md")):
        shutil.copyfile(HERE / src, out / "assets" / dst)
    print("site written:", sorted(p.name for p in out.iterdir()), "review linked" if review else "review pending")


if __name__ == "__main__":
    main()
