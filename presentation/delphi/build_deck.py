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
    "planning/rethink/CLAIM-LEDGER.md",
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
    P, T, Er, Sc, Rb, Bl = f["price"], f["turing"], f["errors"], f["scorecard"], f["robustness"], f["baseline"]
    fn = lambda *parts: '<div class="fn">' + " · ".join(parts) + "</div>"
    stamp = f"artifacts @ {prov_head[:8]}"
    brand = lambda i: f'<div class="brand"><i></i>Delphi · from candidate laws to checked theorems</div><div class="num">{i} / 6</div>'
    pend = '<span class="pend">pending</span>'
    notes = []

    # ---------------------------------------------------------------- slide 1
    scan = T["scan"]
    s1 = f"""{brand(1)}
<h1 class="hero" style="font-size:58px;margin-top:70px">Delphi: from candidate laws to <em>checked theorems</em></h1>
<p class="lede" style="font-size:26px;max-width:1040px">Experts know the conditions behind a law. An agent applying that law to a new setting does not reliably check them. We make the check executable, and keep proved, simulated and observed apart.</p>
<div class="row" style="gap:18px;margin-top:8px">
 <div class="col card"><h3><span class="pf pr">Proved</span> compiled in Lean 4</h3><p class="small" style="margin:0;font-size:16px">A finite Turing instance, and Price identity to a conditional Hamilton regression theorem, each under stated assumptions with rejected mutants.</p></div>
 <div class="col card"><h3><span class="pf si">Simulated</span></h3><p class="small" style="margin:0;font-size:16px">Nonlinear solver outcomes and the agent evaluation: {pend}</p></div>
 <div class="col card"><h3><span class="pf ob">Observed</span></h3><p class="small" style="margin:0;font-size:16px"><b>None.</b> We ran no experiment. The released enzyme baseline is appendix only.</p></div>
</div>
<div class="scope" style="margin-top:14px;font-size:15.5px"><b>The caveats are not our discovery.</b> What is new here is only that they are checked by a program before a law is applied, and that we show our own failures.</div>
{fn('<b>Ledger</b> F01 F07 F05 P01 P02 P03 · planning/rethink/CLAIM-LEDGER.md', stamp)}"""
    notes.append("Delphi turns candidate laws into checked theorems. The conditions behind these laws are known to experts, so we do not present them as discoveries. The problem is an agent that applies a law outside its scope without checking. We make that check executable, and we sort everything three ways: proved, simulated, observed. We ran no experiment. Anything unmeasured is marked pending.")

    # ---------------------------------------------------------------- slide 2
    cells_h = "".join(f"<th style='text-align:center'>{E(s['L_over_pi'])}</th>" for s in scan)
    cells_v = "".join(f"<td class='{'u' if s['verdict'] == 'linearly_unstable' else 's'}'>{'grows' if s['verdict'] == 'linearly_unstable' else 'stable'}</td>" for s in scan)
    nmut = sum(1 for m in T["lean"]["mutants"] if m["exit"] != 0)
    s2 = f"""{brand(2)}
<h2 style="font-size:31px;margin:24px 0 8px">The continuum Turing conditions hold, yet a finite domain can admit <em>no growing mode</em>, and not monotonically in size.</h2>
<div class="card" style="padding:8px 12px"><div class="small" style="font-size:14px;margin-bottom:4px">Declared model: J = [[{T['J'][0][0]}, {T['J'][0][1]}], [{T['J'][1][0]}, {T['J'][1][1]}]], diffusivities D = ({T['D'][0]}, {T['D'][1]}), 1-D Neumann boundaries; det(J − qD) = {T['det_factored']}, so the continuum band is {T['continuum_band'][0]} &lt; q &lt; {T['continuum_band'][1]}. Admissible modes are q = (nπ/L)².</div>
<table class="t3"><tr><th style="text-align:left">length L / π</th>{cells_h}</tr><tr><td style="text-align:left">linear verdict</td>{cells_v}</tr></table></div>
<div class="row" style="gap:14px;margin-top:10px">
 <div class="col card" style="padding:8px 12px"><h3><span class="pf pr">Proved</span> compiled instance</h3><p class="small" style="margin:0;font-size:14.5px">Lean {T['lean']['version']}: L = π admits no unstable mode; L = 2π admits one (n = {T['two_pi']['unstable_modes'][0]}, det = {T['two_pi']['n1_det']}). Build exit {T['lean']['build_exit']}; {nmut} law and domain mutants rejected. Only these two lengths are compiled.</p></div>
 <div class="col card" style="padding:8px 12px"><h3><span class="pf ex">Exact arithmetic</span></h3><p class="small" style="margin:0;font-size:14.5px">The whole strip above is exact rational arithmetic, not Lean-compiled. Over the reals with Mathlib, a host probe re-run by the director shows no admissible mode lies in the band at L = π.</p></div>
 <div class="col card" style="padding:8px 12px"><h3><span class="pf si">Simulated</span> / <span class="pf ob">Observed</span></h3><p class="small" style="margin:0;font-size:14.5px">Nonlinear solver check: {pend}. Observed tissue pattern: <b>none</b>.</p></div>
</div>
<div class="scope" style="margin-top:10px;font-size:14.5px"><b>Scope.</b> This is a linear-mode statement for this declared model, not a claim about whether a pattern forms. The continuum condition is a large-domain result; we are not saying Turing was wrong.</div>
{fn('<b>Ledger</b> F01 F02 (Mathlib probe: no ledger row yet, director receipt) · artifacts/turing_scope/results.json, lean_receipt.json · artifacts/rethink_director/MathlibProbe_host.lean', stamp)}"""
    notes.append("First check. Take a declared two-species model where the textbook continuum condition holds. On a finite domain only certain wavenumbers exist. At length pi none falls in the unstable band, so it is stable. At three halves pi and two pi a mode grows; at five halves pi it is stable again. Only pi and two pi are compiled in Lean. This is a linear statement; nonlinear simulation is pending.")

    # ---------------------------------------------------------------- slide 3
    W = P["witnesses"]
    dep = P["depends_on"]
    s3 = f"""{brand(3)}
<h2 style="font-size:30px;margin:24px 0 10px">Price identity, then a selection-only lemma, then a <em>conditional</em> Hamilton regression theorem: a real proof dependency.</h2>
<div class="row" style="gap:20px">
 <div class="col" style="flex:.9">
  <div class="node">price</div><div class="arrow">↓ used by</div>
  <div class="node">selection_only</div><div class="arrow">↓ used by</div>
  <div class="node">hamilton_regression</div>
  <div class="node pn" style="margin-top:12px">Fisher additive-genetic theorem · PENDING</div>
  <p class="small" style="font-size:13.5px;margin:8px 0 0">The dependencies are read from the Lean source. A fixed-fitness variance corollary also compiles; it is <b>not</b> Fisher's theorem.</p>
 </div>
 <div class="col" style="flex:1.5">
  <div class="card" style="padding:8px 12px"><h3>Drop an assumption: the exact compiled witness</h3>
  <table style="font-size:14px"><tr><th style="text-align:left">assumption dropped</th><th style="text-align:left">what the witness shows</th></tr>
  <tr><td style="text-align:left">perfect transmission</td><td style="text-align:left">mean fitness × trait change = {W['transmission_is_needed']['mean_fitness_times_change']} while selection covariance = {W['transmission_is_needed']['selection_covariance']}</td></tr>
  <tr><td style="text-align:left">residual orthogonality</td><td style="text-align:left">trait mean rises although r·b − c = {W['residual_assumption_is_needed']['criterion_value']}</td></tr>
  <tr><td style="text-align:left">correct sign of the cost term</td><td style="text-align:left">the sign-reversed criterion is false on the same population</td></tr>
  <tr><td style="text-align:left">premises satisfiable?</td><td style="text-align:left">yes: change = {W['regression_premises_nonvacuous']['change']}, variance {W['regression_premises_nonvacuous']['var_z']}</td></tr></table></div>
  <div class="card" style="padding:8px 12px;margin-top:8px"><h3><span class="pf pr">Proved</span> receipt</h3><p class="small" style="margin:0;font-size:14.5px">Lean exit {P['original_exit']}; axioms: propext, Classical.choice, Quot.sound only. {len(W)} witness controls exit {P['witness_exit']}. {len(P['mutants'])} changed-target mutants rejected (exit {P['mutants'][0]['exit']}). Statement-fidelity review by a second reader: {pend}</p></div>
 </div>
</div>
<div class="scope" style="margin-top:10px;font-size:14.5px"><b>Established mathematics.</b> Price 1970; the Price–Fisher–Hamilton link is in Frank 1997. In a bounded search we did not find a prior machine-checked Price formalization. This is a statistical regression statement, not a causal cost–benefit rule.</div>
{fn('<b>Ledger</b> F07 · artifacts/integration/codex-api/price-probe.json (source sha ' + P['source_sha256'][:8] + '…) · experiments/price_probe/ · interactive walkthrough: site/review/ (F09)', stamp)}"""
    notes.append("Second check. The Price identity, a selection-only lemma, and a conditional Hamilton regression theorem depend on each other in the Lean source. Each assumption has an exact compiled witness showing what breaks without it, and two changed-sign versions are rejected by the compiler. Fisher's additive genetic theorem is not proved; it is pending. This is established mathematics, a regression statement, not a causal rule.")

    # ---------------------------------------------------------------- slide 4
    V = Er["vacuous_theorem"]
    rows = "".join(
        f"<tr><td style='text-align:left'>{e['n']}. {E(e['what'])}</td><td style='text-align:left;font-size:13px'>{E(e['caught_by'])}</td><td style='text-align:left;font-size:12.5px'>{E(e['ledger'])}</td></tr>"
        for e in Er["five"])
    s4 = f"""{brand(4)}
<h2 style="font-size:30px;margin:24px 0 8px">Our own near-vacuous theorem compiled, passed the axiom audit, and was caught by an <em>independent reviewer</em>.</h2>
<div class="row" style="gap:18px">
 <div class="col" style="flex:1">
  <div class="card" style="padding:9px 14px"><h3>{E(V['name'])}, in our Admissible file</h3>
  <p class="small" style="margin:0 0 5px;font-size:15px"><b>Assumed:</b> {E(V['assumed'])}.<br><b>Concluded:</b> {E(V['concluded'])}.<br>A restatement. The length hypothesis is unused. It is <b>not</b> linear asymptotic stability.</p>
  <p class="small" style="margin:0;font-size:14.5px">A clean axiom audit certifies proof dependencies, not whether the statement says what its name claims. The reviewer's check did.</p>
  <p class="small" style="margin:6px 0 0;font-size:14.5px"><b>Replacement:</b> a revised module compiles <i>every admissible mode has trace &lt; 0 and det &gt; 0</i> (exit {V['replacement']['compile_exit']}, standard axioms). Trace is derived; determinant positivity is assumed. No new mutants yet; eigenvalue and PDE correspondence not established.</p></div>
  <div class="scope" style="margin-top:8px;font-size:14px"><b>This is the system working.</b> Caught by independent review with exact witnesses, not by a machine detecting autonomously.</div>
 </div>
 <div class="col" style="flex:1.1"><div class="card" style="padding:8px 10px"><h3>Five more validity errors this team made</h3>
  <table style="font-size:13.5px"><tr><th style="text-align:left">error</th><th style="text-align:left">caught by</th><th style="text-align:left">ledger</th></tr>{rows}</table></div></div>
</div>
{fn('<b>Ledger</b> P01 F04 F05 F08 F10 P05 · artifacts/integration/codex-api/admissible-review/Admissible.lean · artifacts/integration/codex-api/admissible-review/469874b/compile-review.json · planning/rethink/CODEX-21-CLAIM-FREEZE-REVIEW.md', stamp)}"""
    notes.append("Our own failure. We wrote a theorem assuming no mode has negative determinant and concluding every mode has non-negative determinant. A tautology. It compiled and passed the axiom audit. An independent reviewer caught it, not us. A revised version now compiles, with the determinant assumed and no mutants yet. Five more errors from this team were each caught by independent review. That is the check working, not a machine detecting alone.")

    # ---------------------------------------------------------------- slide 5
    s5 = f"""{brand(5)}
<h2 style="font-size:30px;margin:24px 0 10px">The scorecard of {Sc['records']} candidate laws checked as theorems: every result is <em>pending</em>.</h2>
<div class="row" style="gap:18px">
 <div class="col"><div class="card" style="padding:10px 14px"><h3>Scorecard</h3>
  <table style="font-size:15px"><tr><td style="text-align:left">records in the frozen list</td><td><b>{Sc['records']}</b></td></tr>
  <tr><td style="text-align:left">compiled with proof, axiom audit and a failing mutant</td><td>{pend}</td></tr>
  <tr><td style="text-align:left">excluded, with reasons</td><td>{pend}</td></tr>
  <tr><td style="text-align:left">source-correspondence review</td><td>{pend}</td></tr></table>
  <p class="small" style="margin:8px 0 0;font-size:14px">The first freeze is not approved; a revised freeze with full formal statements is required before any count is reported.</p></div></div>
 <div class="col"><div class="card" style="padding:10px 14px"><h3>Do agents need the gate?</h3>
  <table style="font-size:15px"><tr><td style="text-align:left">benchmark freeze</td><td>{pend}</td></tr><tr><td style="text-align:left">agent arms and matched budgets</td><td>{pend}</td></tr><tr><td style="text-align:left">coverage, false acceptance, false refusal</td><td>{pend}</td></tr></table>
  <p class="small" style="margin:8px 0 0;font-size:14px">To count: an always-refuse baseline, the same exact checker without a model, and the unguarded agent. A refusal is not a correct answer. A null will be shown.</p></div></div>
</div>
<div class="scope" style="margin-top:12px;font-size:15px"><b>No scores are shown.</b> An earlier benchmark version was retired for input errors. Its successor's numerical verdicts reproduced, but its freeze was withheld because answer information leaks through public IDs. We do not claim that more agents beat fewer.</div>
{fn('<b>Ledger</b> P01 P02 P03 F08 · artifacts/integration/codex-api/admissible-review/committed-freeze.json (sha ' + Sc['freeze_sha256'][:8] + '…) · planning/rethink/CODEX-BENCH-V1-1-REVIEW.md', stamp)}"""
    notes.append("The headline we are after is a scorecard of twenty-one candidate laws checked as theorems. Every result is pending: the first freeze was not approved, so no compiled count exists. The agent evaluation likewise needs a corrected freeze, an always-refuse baseline, the checker without a model, and the unguarded agent. A refusal is not a correct answer, and a null will be shown.")

    # ---------------------------------------------------------------- slide 6
    s6 = f"""{brand(6)}
<h2 style="font-size:30px;margin:24px 0 10px">What this is, what it is not, and whose work it stands on.</h2>
<div class="row" style="gap:18px">
 <div class="col"><div class="card" style="padding:9px 14px;height:100%"><h3>Credit</h3><p class="small" style="margin:0;font-size:14.5px">
  Collaborative formalization architecture: <b>Prove2Me</b> (arXiv 2608.28433). Prior formal biology: <b>Rashid et al. 2017</b> (HOL Light), <b>lean-bio</b>, <b>crnt-lean</b>, <b>Ripple</b> (arXiv 2607.13531). Price–Fisher–Hamilton: Price, Frank. Turing: Turing, Murray.</p></div></div>
 <div class="col"><div class="card" style="padding:9px 14px;height:100%"><h3>We do not claim</h3><p class="small" style="margin:0;font-size:14.5px">
  Any experiment, a first library, a universal threshold, that any named law is wrong (a scope condition refers to the extracted record), or that agents beat a plain check.</p></div></div>
 <div class="col"><div class="card" style="padding:9px 14px;height:100%"><h3>Still pending</h3><p class="small" style="margin:0;font-size:14.5px">
  The 21-record scorecard · the agent evaluation · Fisher additive-genetic · second-reader review of the Price statements · mutants for the replacement theorem · public use of the tool.</p></div></div>
</div>
<div class="scope" style="margin-top:12px;font-size:15px"><b>Preserved baseline.</b> The earlier enzyme work stays in the appendix with its nulls: {Bl['measured_nonstop']:,} measured variants; specialists {Bl['shared_1000']}/100 equal the single planner {Bl['q2c_1000']}/100; a plain lazy search reaches {Bl['lazysp_1000']}/100.</div>
<p style="font:500 26px/1.2 var(--serif);margin:16px 0 0;max-width:1120px">Make the assumptions behind a biological-model decision <em style="font-style:normal;border-bottom:4px solid var(--orange)">executable and auditable</em>.</p>
{fn('<b>Ledger</b> A01 A02 B01 B02 B03 P07 P08 · planning/rethink/PRIOR-ART-VERDICT.md · artifacts/core/replay/table_primary.csv', stamp)}"""
    notes.append("The collaborative formalization architecture comes from Prove2Me. Prior formal biology includes Rashid 2017, lean-bio, crnt-lean and Ripple. We claim no experiment, no first library, no universal threshold, and not that any named law is wrong. Pending: the scorecard, the agent evaluation, Fisher, a second-reader review, and mutants for the replacement theorem. The enzyme baseline stays in the appendix. Make the assumptions behind a biological model decision executable and auditable.")
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
