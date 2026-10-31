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
    P, T, Er, Sc, Bl = f["price"], f["turing"], f["errors"], f["scorecard"], f["baseline"]
    W = P["witnesses"]
    WIN = T["windows"]
    scan = T["scan"]
    head = "".join(f"<th>{E(s['L_over_pi'])}</th>" for s in scan)
    cells = "".join(f"<td class='{'u' if s['verdict'] == 'linearly_unstable' else 's'}'>{'grows' if s['verdict'] == 'linearly_unstable' else 'stable'}</td>" for s in scan)
    nmut = sum(1 for m in T["lean"]["mutants"] if m["exit"] != 0)
    rev = ('<a href="../review/index.html">audited walkthrough (Price and Hamilton, exact-browser versus compiled labels)</a>'
           if review_exists else f"audited walkthrough from the review worker: {PEND} (not yet committed in this tree)")
    errs = "".join(f"<tr><td>{e['n']}</td><td>{E(e['what'])}</td><td>{E(e['caught_by'])}</td><td>{E(e['witness'])}</td><td>{E(e['ledger'])}</td></tr>" for e in Er["five"])
    V = Er["vacuous_theorem"]
    wit = "".join(f"<details><summary>Drop: {E(v['drops'])} <span class='mono'>({E(k)})</span></summary><p>{E(v['reading'])}</p></details>" for k, v in W.items() if k != "reversed_cost_is_false")
    wit += f"<details><summary>Drop: {E(W['reversed_cost_is_false']['drops'])} <span class='mono'>(reversed_cost_is_false; plus {len(P['mutants'])} changed-target mutants the compiler rejects)</span></summary><p>{E(W['reversed_cost_is_false']['reading'])}</p></details>"
    return f"""
<p class="status">Draft of Oct 31 2026 · built from commit {E(commit[:8])} · numbers marked pending are not results · owner-private review copy</p>
<h1>Delphi: from candidate laws to checked theorems</h1>
<p class="lede">Experts know the conditions behind a law. An agent applying that law to a new setting does not reliably check them. This page shows an executable check, the compiled witnesses behind it, and our own failures.</p>
<nav><a href="#turing">Turing check</a><a href="#price">Price → Hamilton</a><a href="#errors">Our errors</a><a href="#scorecard">Scorecard</a><a href="#downloads">Deck and notes</a><a href="appendix.html">Appendix</a><a href="blog.html">Blog</a></nav>
<div class="grid3">
 <div class="card"><h3><span class="pf pr">Proved</span></h3>Compiled in Lean 4 under stated assumptions, each with rejected mutants: a finite Turing instance; the Price identity to a conditional Hamilton regression theorem.</div>
 <div class="card"><h3><span class="pf si">Simulated</span></h3>Nonlinear solver outcomes and the agent evaluation: {PEND}</div>
 <div class="card"><h3><span class="pf ob">Observed</span></h3><b>None.</b> We ran no experiment. The released enzyme baseline is appendix material.</div>
</div>
<div class="scope"><b>The caveats are not our discovery.</b> They are known to experts and appear in textbooks. What is new here is only that a program checks them before a law is applied, and that we show where we failed.</div>

<h2 id="turing">Check 1: a finite domain can admit no growing mode</h2>
<div class="scope"><b>Limitation first.</b> The algorithm is trivial: count the admissible modes that fall in the band. It is exact for rational L/π. What we offer is a certificate and packaging, not new mathematics. Non-monotone dependence on size is textbook-derivable, and we do not claim it as new. Finite-size effects on Turing patterns are in the literature; our citations for that are still being verified, so none is given here.</div>
<p>Declared model: J = [[{T['J'][0][0]}, {T['J'][0][1]}], [{T['J'][1][0]}, {T['J'][1][1]}]], diffusivities D = ({T['D'][0]}, {T['D'][1]}), one-dimensional Neumann boundaries. det(J − qD) = {E(T['det_factored'])}, so the continuum band is {T['continuum_band'][0]} &lt; q &lt; {T['continuum_band'][1]}. Admissible modes are q = (nπ/L)². The continuum condition holds; whether a mode lands in the band depends on the length.</p>
<div class="scroll"><table><tr><th>L / π</th>{head}</tr><tr><th>linear verdict</th>{cells}</tr></table></div>
<p>Stable at π, growing at 3π/2 and 2π, stable again at 5π/2. Exactly, mode n grows iff {WIN['c_lo']}n² &lt; (L/π)² &lt; {WIN['c_hi']}n². So the model grows for L/π in (√{WIN['c_lo']}, √{WIN['c_hi']}) and for every L/π above 2√{WIN['c_lo']}, and is stable in the window √{WIN['c_hi']} ≤ L/π ≤ 2√{WIN['c_lo']} (recomputed exactly by the trace check).</p>
<div class="grid3">
 <div class="card"><h3><span class="pf pr">Proved</span> compiled instance</h3>Lean {E(T['lean']['version'])}, build exit {T['lean']['build_exit']}: L = π admits no unstable mode; L = 2π admits one (n = {T['two_pi']['unstable_modes'][0]}, det = {E(T['two_pi']['n1_det'])}). {nmut} law and domain mutants rejected. Only these two lengths are compiled.</div>
 <div class="card"><h3><span class="pf ex">Exact arithmetic</span></h3>The strip above uses exact rational arithmetic, not Lean. Over the reals with Mathlib, a host probe re-run by the project director shows no admissible mode lies in the band at L = π (no ledger row yet).</div>
 <div class="card"><h3><span class="pf si">Simulated</span> / <span class="pf ob">Observed</span></h3>Nonlinear solver check: {PEND}. Observed tissue pattern: <b>none</b>.</div>
</div>
<div class="scope"><b>Scope.</b> A linear-mode statement for this declared model. It does not say whether a pattern forms, and we are not saying Turing was wrong: the continuum result is a large-domain statement. A supplied scope condition refers to the extracted record.</div>
<p>Interactive walkthrough: {rev}</p>

<h2 id="price">Check 2: Price identity → selection-only lemma → conditional Hamilton regression theorem</h2>
<div class="grid3"><div class="chain"><div class="node">price</div><div class="arrow">↓ used by</div><div class="node">selection_only</div><div class="arrow">↓ used by</div><div class="node">hamilton_regression</div><div class="node pn" style="margin-top:10px">Fisher additive-genetic theorem · PENDING</div></div>
<div class="card" style="grid-column:span 2"><h3><span class="pf pr">Proved</span> receipt</h3>Lean exit {P['original_exit']}; axioms: propext, Classical.choice, Quot.sound only. {len(W)} witness controls exit {P['witness_exit']}. {len(P['mutants'])} changed-target mutants rejected (exit {P['mutants'][0]['exit']}). The dependencies are read from the Lean source. Statement-fidelity review by a second reader: {PEND}</div></div>
<p>Each assumption has an exact compiled witness showing what breaks without it:</p>
{wit}
<div class="scope"><b>Established mathematics.</b> Price 1970; Frank 1997 links Price, Fisher and Hamilton. Whether the ATLAS biology library (facebookresearch/atlas-lean) already covers Price or Hamilton is unchecked. This is a statistical regression statement, not a causal cost–benefit rule. A fixed-fitness variance corollary also compiles; it is not Fisher's theorem.</div>

<h2 id="errors">Our own validity errors, caught</h2>
<div class="card"><h3>The near-vacuous theorem</h3><p><span class="mono">{E(V['name'])}</span> in our Admissible file assumed {E(V['assumed'])} and concluded {E(V['concluded'])}. A restatement: the length hypothesis is unused and it is not linear asymptotic stability. It compiled and passed the axiom audit. An independent reviewer caught it, not us. A revised module (Admissible {E(V['replacement']['source_commit'][:7])}) compiles a stronger statement, <span class="mono">{E(V['replacement']['theorem'])}</span>: every admissible mode has trace &lt; 0 and determinant &gt; 0. Trace negativity is derived; determinant positivity is assumed. Lean exit {V['replacement']['compile_exit']}, standard axioms. No new mutants have been run, and the full eigenvalue and PDE correspondence is not established (ledger F10). Mutants for it: {PEND}.</p></div>
<div class="scroll"><table><tr><th>#</th><th>error</th><th>caught by</th><th>exact witness</th><th>ledger</th></tr>{errs}</table></div>
<div class="scope">This is the check working, caught by independent review with exact witnesses. It is not a machine detecting its own errors autonomously.</div>

<h2 id="scorecard">Scorecard: {Sc['records']} candidate laws checked as theorems</h2>
<div class="card"><table><tr><td>records in the frozen list</td><td><b>{Sc['records']}</b></td></tr><tr><td>compiled with proof, axiom audit and a failing mutant</td><td>{PEND}</td></tr><tr><td>excluded, with reasons</td><td>{PEND}</td></tr><tr><td>source-correspondence review</td><td>{PEND}</td></tr><tr><td>agent evaluation: benchmark freeze, arms, coverage, false acceptance, false refusal</td><td>{PEND}</td></tr><tr><td>misprediction map: among parameter sets that pass the textbook Turing test, the fraction stable on a finite domain of length L, over a large ensemble</td><td>{PEND}</td></tr></table></div>
<p>The map has not been run on the GPUs, and earlier toy-ensemble figures are not shown. The pairing we are working toward is a certified finite-domain checker plus that map: the map would be the empirical contribution and the Lean statement the certificate.</p>
<p>The first freeze is not approved. To count in the agent evaluation: an always-refuse baseline, the same exact checker without a model, and the unguarded agent. A refusal is not a correct answer. A null will be shown. We do not claim that more agents beat fewer.</p>

<h2 id="downloads">Deck, script and sources</h2>
<ul><li><a href="assets/deck.pdf">Six-slide deck (PDF)</a> · <a href="assets/deck.html">HTML deck</a> · <a href="assets/speaker-notes.md">three-minute script</a> · <a href="blog.html">blog</a></li>
<li>Numbers are re-derived from committed artifacts by <span class="mono">presentation/delphi/trace.py</span>; the claim ledger is <span class="mono">planning/rethink/CLAIM-LEDGER.md</span>.</li></ul>

<h2>Credit and limits</h2>
<p>Collaborative formalization architecture: Prove2Me (arXiv 2608.28433). Prior formal biology: ATLAS (facebookresearch/atlas-lean, MathlibExt/Biology), Rashid et al. 2017 (HOL Light), lean-bio, crnt-lean, Ripple (arXiv 2607.13531). We aim to complement ATLAS, not compete with it; offering Turing statements to it is pending. We claim no experiment, no first library, no universal threshold, and not that any named law is wrong.</p>
<footer>Delphi draft · exact-browser means rational arithmetic in a program, compiled means a Lean receipt exit 0, simulated and observed are separate. Source commit {E(commit[:8])}.</footer>
"""


def appendix(f, commit):
    R, Bl = f["robustness"], f["baseline"]
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
<h2>Released enzyme baseline (preserved, with its nulls)</h2>
<p>{Bl['measured_nonstop']:,} measured non-stop TrpB variants from the authors' CC0 table; {Bl['imputed_excluded']} imputed-only variants excluded. On the retrospective panel, shared specialists {Bl['shared_1000']}/100 equal the single planner {Bl['q2c_1000']}/100 at {Bl['budget']:,} extra assays; a plain lazy search reaches {Bl['lazysp_1000']}/100. Five protein-model sizes did not establish assay savings. No general superiority claim. Full release: the earlier deck and site in this repository.</p>
<p><a href="index.html">Back to the Delphi page</a></p>
"""


def blog_parts(f):
    P, T, Er, Sc = f["price"], f["turing"], f["errors"], f["scorecard"]
    V = Er["vacuous_theorem"]
    return [
        ("h1", "Delphi: from candidate laws to checked theorems"),
        ("p", "Experts know the conditions that bound a law. An agent that reads a textbook inequality and applies it to a new system usually does not check them. This post describes a small executable check, what is compiled behind it, what is still pending, and the mistakes we made on the way."),
        ("h2", "What we are not claiming"),
        ("p", "The caveats we check are known to experts. We do not present them as discoveries, we ran no experiment, and we do not say that any named law is wrong: a scope condition we supply refers to the extracted record of the claim, not to the law's author. We did not set out to build the first library of formal biology. ATLAS (facebookresearch/atlas-lean, MathlibExt/Biology) already holds a large body of exact biology statements with cited sources and non-vacuity witnesses, and Prove2Me (arXiv 2608.28433), Rashid et al. 2017, lean-bio, crnt-lean and Ripple (arXiv 2607.13531) came before at their own scope. We aim to complement ATLAS, not compete with it."),
        ("h2", "Check one: a finite domain with no growing mode"),
        ("p", f"Take a declared two-species linear model, J = [[{T['J'][0][0]}, {T['J'][0][1]}], [{T['J'][1][0]}, {T['J'][1][1]}]] with diffusivities ({T['D'][0]}, {T['D'][1]}) and Neumann boundaries. The continuum Turing condition holds: det(J − qD) = {T['det_factored']} is negative for {T['continuum_band'][0]} < q < {T['continuum_band'][1]}. On a finite domain only q = (nπ/L)² exist. At L = π none lies in the band; at 3π/2 and 2π one does; at 5π/2 none does again. Lean {T['lean']['version']} compiles the L = π and L = 2π cases and rejects {sum(1 for m in T['lean']['mutants'] if m['exit'] != 0)} mutants. The other lengths are exact rational arithmetic, not Lean. The algorithm is trivial, counting admissible modes in a band, so what we offer is a certificate and packaging, not new mathematics; non-monotone dependence on size is textbook-derivable and not claimed as new. This is a linear-mode statement; whether a pattern forms is a nonlinear question we have not simulated yet (pending)."),
        ("h2", "Check two: Price to Hamilton, with the assumptions attached"),
        ("p", f"We compiled the finite Price identity, a selection-only lemma that depends on it, and a conditional Hamilton regression theorem that depends on that lemma. Lean exits {P['original_exit']}, the axioms are propext, Classical.choice and Quot.sound only, {len(P['witnesses'])} witness controls exit {P['witness_exit']}, and {len(P['mutants'])} changed-target mutants are rejected. Each assumption (perfect transmission, residual orthogonality, the sign of the cost term) has an exact witness showing what fails without it. This is established mathematics; Price and Frank did the science, and whether ATLAS already covers it is unchecked. It is a regression statement, not a causal cost-benefit rule. Fisher's additive-genetic theorem is not proved (pending), and a second reader has not yet reviewed the statements (pending)."),
        ("h2", "Our own near-vacuous theorem"),
        ("p", f"One of our theorems, {V['name']}, assumed that no admissible mode has negative determinant and concluded that every mode has non-negative determinant. That is a restatement. It compiled and passed the axiom audit, which certifies proof dependencies and not what a statement says. An independent reviewer caught it, not us. A revised module now compiles trace negative and determinant positive at every admissible mode; the determinant is assumed, no new mutants have run, and the eigenvalue and PDE correspondence is not established (ledger F10). We list five more validity errors from this team in the page, each caught by independent review with an exact witness. We read this as the check working, with humans and agents reviewing independently. It is not a machine detecting its own errors."),
        ("h2", "What is pending"),
        ("p", f"The scorecard of {Sc['records']} candidate laws checked as theorems has no compiled count yet, and the misprediction map (what fraction of parameter sets passing the textbook Turing test are stable on a finite domain, over a large ensemble) has not been run. The agent evaluation needs a corrected benchmark freeze, an always-refuse baseline, the same checker without a model, and the unguarded agent. A refusal is not a correct answer, and a null will be shown. We do not claim that more agents beat fewer."),
        ("h2", "Appendix material"),
        ("p", "A robustness sweep (simulated, one linear family, noise-model dependent, not ledger-reviewed) and the earlier enzyme baseline with its nulls are in the appendix."),
    ]


def render_blog_html(parts):
    return "".join(f"<{t}>{E(x)}</{t}>" for t, x in parts) + '<p><a href="index.html">Back to the Delphi page</a></p>'


def render_blog_md(parts):
    return "\n\n".join(("# " if t == "h1" else "## " if t == "h2" else "") + x for t, x in parts) + "\n"


def storyboard(f, timing):
    ps = {r["slide"]: r for r in timing["per_slide"]}
    mm = lambda t: f"{int(t // 60)}:{int(t % 60):02d}"
    T, P = f["turing"], f["price"]
    shots = [
        (1, "Title and the three columns: Proved, Simulated, Observed", "Hold on the three cards. Cursor rests on 'Observed: None'.",
         "Caption: 'We ran no experiment. Pending means not yet measured.'", "deck slide 1"),
        (2, "Turing strip: stable at pi, grows at 3pi/2 and 2pi, stable at 5pi/2", "Highlight the stable cell at pi, then the two growing cells, then 5pi/2.",
         "Caption: 'Linear-mode statement for one declared model. Only pi and 2pi are Lean-compiled.'", "deck slide 2; then site/review walkthrough, Neumann pi to 2pi control (record after final integration)"),
        (3, "Price, selection-only lemma, Hamilton regression: the dependency chain", "Trace the two arrows, then open one witness (residual orthogonality dropped).",
         "Caption: 'Established mathematics. Statement review by a second reader: pending.'", "deck slide 3; site/delphi#price"),
        (4, "Our own near-vacuous theorem and the five errors", "Zoom on 'Assumed / Concluded', then the replacement line, then the table.",
         "Caption: 'Caught by independent review with exact witnesses, not by a machine on its own.'", "deck slide 4; site/delphi#errors"),
        (5, "Scorecard: every result pending", "Slow pan over the pending tags; no numbers other than the record count.",
         "Caption: 'No scores shown. A null will be shown.'", "deck slide 5; site/delphi#scorecard"),
        (6, "Credit, what we do not claim, what is pending", "Hold on the credit card, then the closing line.",
         "Caption: 'Make the assumptions behind a biological-model decision executable and auditable.'", "deck slide 6"),
    ]
    out = ["# Video storyboard: Delphi, three-minute walkthrough", "",
           f"Timings are the measured per-slide start times of a synthetic-voice read-through (`timing.json`, total {timing['total_mm_ss']}); a human presenter will differ. No narration audio has been recorded and no video has been produced; this is a shot list.", "",
           "| Start | Slide | Shot | Action | Caption | Source |", "|---|---|---|---|---|---|"]
    for n, shot, act, cap, src in shots:
        out.append(f"| {mm(ps[n]['starts_at_s'])} | {n} | {shot} | {act} | {cap} | {src} |")
    out += ["", "Rules for the recording: show the pending tags; never show a benchmark number; do not display any claim not in `planning/rethink/CLAIM-LEDGER.md`; no first-ever, universal-threshold or solved-biology language, and no statement that a named law is wrong.",
            "Interactive segment (optional, only if time allows): the audited walkthrough at `site/review/` (ledger F09). Recording it is pending until the integration commit is final.", ""]
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
    for src, dst in (("deck.pdf", "deck.pdf"), ("deck.html", "deck.html"), ("speaker-notes.md", "speaker-notes.md")):
        shutil.copyfile(HERE / src, out / "assets" / dst)
    print("site written:", sorted(p.name for p in out.iterdir()), "review linked" if review else "review pending")


if __name__ == "__main__":
    main()
