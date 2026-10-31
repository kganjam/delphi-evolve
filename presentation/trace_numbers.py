#!/usr/bin/env python3
"""Trace every number on the deck to a committed artifact, independently of build_deck.py.

    python3 presentation/trace_numbers.py [--root .] [--deck presentation/deck.html] [--out presentation/number_trace.json]

What it does
1. Parses the six slides of the built deck (visible text, SVG text, footnote, speaker notes).
2. For each registered claim, re-derives the expected string from the committed artifacts with
   small readers that do NOT import build_deck.py, then requires that exact string to appear on
   the slide.  Claims name their source files.
3. Removes every claimed phrase from the slide text and requires that NO numeric token is left
   over, except page counters and explicitly-declared axis scales.  An unaccounted-for number
   fails the run (exit 1).  Speaker-note numbers must also appear in the slide's own text.
4. Writes presentation/number_trace.json: slide, shown text, artifact files, SHA-256 of each file.

A passing run means: every number on the slides was re-derived from a committed file.  It does not
mean the numbers are scientifically right, only that they are not stale or hand-typed.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(".")
NUM = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?")


# ----------------------------------------------------------------------------- artifact readers
def J(rel):
    return json.loads((ROOT / rel).read_text())


def C(rel):
    with (ROOT / rel).open() as f:
        return list(csv.DictReader(f))


def jsvar(rel):
    t = (ROOT / rel).read_text()
    return json.loads(t[t.index("{"):t.rindex("}") + 1])


def sha(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def n(x):  # 159129 -> "159,129"
    return f"{int(x):,}"


def pct0(x):
    return f"{100 * float(x):.0f}%"


def gfmt(x):
    return f"{x:g}"


# ----------------------------------------------------------------------------- claim registry
CLAIMS = []  # (slide, kind, shown, expected_thunk, files)


def claim(slide, shown, files, expected, kind="text"):
    """`shown`: the exact string on the slide.  `expected`: thunk returning the string re-derived from artifacts."""
    CLAIMS.append((slide, kind, shown, expected, tuple(files)))


def register():
    CLAIMS.clear()
    dm = J("artifacts/demo.json")
    cnt = dm["source"]["counts"]
    routes = {r["id"]: r for r in dm["routes"]}
    cert, tempt = routes["certified-shortest"], routes["tempting-direct"]
    nodes = {x["id"]: x for x in dm["nodes"]}
    sweep = dm["kappa_sweep"]
    rs = J("artifacts/evidence/route_summary.json")["direct_orderings"]
    DEMO, RS = "artifacts/demo.json", "artifacts/evidence/route_summary.json"

    # ---- slide 1
    claim(1, "so there are 24 orders", [RS], lambda: f"so there are {rs['orderings']} orders")
    claim(1, "every one of the 24 steps down at least once", [RS],
          lambda: f"every one of the {rs['orderings']} steps down at least once" if rs["admitted_at_parameter_0"] == 0 else "MISMATCH")
    claim(1, "the 6-step detour", [DEMO], lambda: f"the {len(cert['nodes']) - 1}-step detour")
    claim(1, "assumed κ=2 interval", [DEMO], lambda: f"assumed κ={gfmt(dm['interval_model']['kappa'])} interval")

    def first_descent():
        sc = [nodes[g]["observed_score"] for g in tempt["nodes"]]
        i = next(i for i in range(1, len(sc)) if sc[i] < sc[i - 1])
        return f"{tempt['nodes'][i - 1]}→{tempt['nodes'][i]}: a step down"
    claim(1, "VIVS→VIVG: a step down", [DEMO], first_descent, kind="svg")

    # ---- slide 2
    claim(2, "159,129 of 160,000 variants", [DEMO],
          lambda: f"{n(cnt['measured_nonstop_genotypes'])} of {n(cnt['library_nonstop_genotypes'])} variants")
    claim(2, "159,129 measured genotypes", [DEMO], lambda: f"{n(cnt['measured_nonstop_genotypes'])} measured genotypes")
    claim(2, "871 never measured", [DEMO], lambda: f"{cnt['unmeasured_nonstop_genotypes']} never measured")
    claim(2, "(incl. stop codons) 193,170", [DEMO], lambda: f"(incl. stop codons) {n(cnt['source_rows_summary_AA'])}")
    claim(2, "stop-codon rows, excluded 34,041", [DEMO], lambda: f"stop-codon rows, excluded {n(cnt['stop_containing_rows'])}")
    claim(2, "measured, no stop 159,129", [DEMO],
          lambda: f"measured, no stop {n(cnt['source_rows_summary_AA'] - cnt['stop_containing_rows'])}" if cnt["source_rows_summary_AA"] - cnt["stop_containing_rows"] == cnt["measured_nonstop_genotypes"] else "MISMATCH")
    claim(2, "imputed in the authors’ separate file 871", [DEMO],
          lambda: f"imputed in the authors’ separate file {cnt['knn_imputed_rows_separate_file']}"
          if cnt["knn_imputed_rows_separate_file"] == cnt["unmeasured_nonstop_genotypes"] and cnt["knn_imputed_equals_unmeasured_set"] else "MISMATCH")
    claim(2, "imputed rows used as observations here 0", [DEMO], lambda: f"imputed rows used as observations here {cnt['imputed_rows_used_as_observations']}")
    claim(2, "The 871 unmeasured cells", [DEMO], lambda: f"The {cnt['unmeasured_nonstop_genotypes']} unmeasured cells")
    claim(2, "rows = residues 1×2, columns = residues 3×4", [DEMO],
          lambda: "rows = residues 1×2, columns = residues 3×4" if len(dm["source"]["positions"]) == 4 else "MISMATCH")
    claim(2, "a631d8cf6c5b", [DEMO], lambda: dm["source"]["sha256"]["summary_AA.csv"][:12], kind="fn")
    claim(1, "a631d8cf6c5b", [DEMO], lambda: dm["source"]["sha256"]["summary_AA.csv"][:12], kind="fn")
    claim(1, "10.22002/h5rah-5z170", [DEMO], lambda: dm["source"]["doi"], kind="fn")
    claim(1, "10.1073/pnas.2400439121", [DEMO], lambda: dm["source"]["paper_doi"], kind="fn")
    # Bibliographic year of the cited paper: cannot be derived from a committed artifact; recorded as such.
    claim(1, "Johnston et al., PNAS 2024", [DEMO], lambda: "Johnston et al., PNAS 2024", kind="fn_biblio")

    # ---- slide 3
    open_sw = [r for r in sweep if r["open"]]
    first_closed = min(r["kappa"] for r in sweep if not r["open"])
    last_open = max(r["kappa"] for r in open_sw)
    lens = sorted({r["shortest_route_edges"] for r in open_sw})
    km = {r["kappa"]: r for r in sweep}
    claim(3, "5 steps → 6 → 7 , then no route can be certified", [DEMO],
          lambda: " → ".join([f"{lens[0]} steps"] + [str(x) for x in lens[1:]]) + " , then no route can be certified")
    claim(3, "5 0 577 5 0.5 381 5 1 278 5 1.5 230 6 2 137 7 3 77 7 4 56 no route certifiable 6 25", [DEMO],
          lambda: " ".join(f"{r['shortest_route_edges']} {gfmt(r['kappa'])} {r['reachable_from_start']}" if r["open"]
                           else f"no route certifiable {gfmt(r['kappa'])} {r['reachable_from_start']}" for r in sweep), kind="svg")
    wk = cert["steps"][cert["weakest_step_index"]]
    claim(3, "clears the bar by only 0.0013 growth units", [DEMO], lambda: f"clears the bar by only {wk['margin']:.4f} growth units")
    claim(3, "κ≈ 2.45", [DEMO], lambda: f"κ≈ {cert['breaks_at_kappa']}")
    claim(3, "577 at κ=0 → 137 at κ=2 → 25 at κ=6", [DEMO],
          lambda: f"{km[0.0]['reachable_from_start']} at κ=0 → {km[2.0]['reachable_from_start']} at κ=2 → {km[first_closed]['reachable_from_start']} at κ={gfmt(first_closed)}")
    claim(3, "at κ=6 the tool says", [DEMO], lambda: f"at κ={gfmt(first_closed)} the tool says")
    claim(3, "(25 variants reachable by certified steps)", [DEMO], lambda: f"({km[first_closed]['reachable_from_start']} variants reachable by certified steps)")
    claim(3, "κ=4 is the last bound in the sweep with a certified route", [DEMO],
          lambda: f"κ={gfmt(last_open)} is the last bound in the sweep with a certified route")
    claim(3, "The weakest step of the κ=2 route", [DEMO], lambda: f"The weakest step of the κ={gfmt(dm['interval_model']['kappa'])} route")
    claim(3, "all 8 κ", [DEMO], lambda: f"all {len(sweep)} κ", kind="fn")
    claim(3, "measured 4-site subgraph", [DEMO], lambda: f"measured {len(dm['source']['positions'])}-site subgraph", kind="fn")
    claim(3, "871 unmeasured genotypes outside", [DEMO], lambda: f"{cnt['unmeasured_nonstop_genotypes']} unmeasured genotypes outside", kind="fn")

    # ---- slide 4
    LS = "artifacts/lazysp/results/summary.json"
    PH = "artifacts/lazysp/results/exploratory_post_hoc.json"
    TP = "artifacts/core/replay/table_primary.csv"
    EO = "artifacts/lazysp/results/episodes_with_original.csv"
    AU = "artifacts/lazysp/results/audit.json"
    ls = J(LS)
    alt = ls["variants"]["alternate"]
    pair = alt["paired"]["q2c"]
    ph = J(PH)
    pha = ph["variants"]["alternate"]
    tp = {(r["policy"], int(r["budget"])): r for r in C(TP) if r["family"] == "all"}
    pol_count = lambda p, b=1000: int(tp[(p, b)]["certified"])
    sgn = lambda v, d=0: f"{v:+.{d}f}"
    pp = lambda v: sgn(round(100 * v))
    claim(4, "established search certifies 96/100; our model-assisted planner 78/100", [LS, TP],
          lambda: f"established search certifies {round(alt['resolved_at']['1000'] * alt['episodes_present'])}/{alt['episodes_present']}; our model-assisted planner {pol_count('q2c')}/{tp[('q2c', 1000)]['episodes']}")
    claim(4, "50% 96% 477", [LS], lambda: f"{pct0(alt['resolved_at']['250'])} {pct0(alt['resolved_at']['1000'])} {alt['rmst_assays']:.0f}", kind="html")
    for pol, lab in (("q2c", "43% 78% 483"), ("collective_shared", "47% 78% 467"), ("q2c_nomodel", "16% 96% 378")):
        claim(4, lab, [TP], (lambda p: lambda: f"{pct0(tp[(p, 250)]['cert_rate'])} {pct0(tp[(p, 1000)]['cert_rate'])} {float(tp[(p, 1000)]['rmst_assays']):.0f}")(pol))
    rd, rm = pair["resolved_diff_1000"], pair["rmst_diff"]
    phd = pha["problem_cluster_bootstrap_resolved_at_1000_diff"]
    claim(4, "+18 [+14, +22]", [LS], lambda: f"{pp(rd['diff'])} [{pp(rd['lo95'])}, {pp(rd['hi95'])}]")
    claim(4, "+18 [+0, +51]", [PH], lambda: f"{pp(phd['diff'])} [{pp(phd['lo95'])}, {pp(phd['hi95'])}]")
    claim(4, "same, post hoc, 24 problem clusters", [PH], lambda: f"same, post hoc, {ph['problem_clusters']} problem clusters")
    claim(4, "-6.5 [-53, +49]", [LS], lambda: f"{sgn(rm['diff'], 1)} [{sgn(rm['lo95'])}, {sgn(rm['hi95'])}]")
    claim(4, "@250 @1000 assays†", [LS], lambda: f"@{250} @{ls['tau']} assays†" if str(250) in alt["resolved_at"] else "MISMATCH")
    claim(4, "certified @1000, preregistered seed bootstrap", [LS], lambda: f"certified @{ls['tau']}, preregistered seed bootstrap")
    claim(4, "the assay-count interval includes 0", [LS],
          lambda: "the assay-count interval includes 0" if rm["lo95"] <= 0 <= rm["hi95"] else "MISMATCH")
    claim(4, "(percentage points; 95% interval; descriptive)", [LS], lambda: "(percentage points; 95% interval; descriptive)"
          if ls["bootstrap"]["draws"] and "lo95" in rd else "MISMATCH")

    def only_by_pair():
        rows = C(EO)
        key = lambda r: (r["family"], r["seed"], r["start"], r["target"])
        ok = lambda r: r["certificate"] in ("open", "blocked") and float(r["assays"]) <= 1000
        lz = {key(r): ok(r) for r in rows if r["policy"] == "lazysp_alternate"}
        qc = {key(r): ok(r) for r in rows if r["policy"] == "q2c"}
        only = [k for k in lz if lz[k] and not qc.get(k, False)]
        only_q = [k for k in qc if qc[k] and not lz.get(k, False)]
        by = {}
        for k in only:
            by[f"{k[2]}→{k[3]}"] = by.get(f"{k[2]}→{k[3]}", 0) + 1
        top, tn = max(by.items(), key=lambda kv: kv[1])
        return len(only), len(only_q), top, tn
    claim(4, "18 / 0 , 17 of 18 at VFVS→ALKG", [EO, LS],
          lambda: (lambda o: f"{o[0]} / {o[1]} , {o[3]} of {o[0]} at {o[2]}" if (o[0], o[1]) == (pair["resolved_only_by_lazysp"], pair["resolved_only_by_comparator"]) else "MISMATCH")(only_by_pair()))
    claim(4, "About 24 distinct problems, not 100 independent targets", [PH, LS],
          lambda: f"About {ph['problem_clusters']} distinct problems, not {alt['episodes_present']} independent targets")

    def checks():
        pols = {p for p, _ in tp}
        cert_core = sum(pol_count(p) for p in pols)
        false_core = sum(int(tp[(p, 1000)]["false_certificates"]) for p in pols)
        lt = C("artifacts/lazysp/results/table_primary.csv")
        cert_lz = sum(round(float(r["resolved@1000"]) * int(r["episodes"])) for r in lt)
        false_lz = sum(int(r["false_certificates"]) for r in lt)
        return f"{false_core + false_lz} false certificates among {cert_core + cert_lz} issued checks"
    claim(4, "0 false certificates among 883 issued checks", [TP, "artifacts/lazysp/results/table_primary.csv"], checks)
    claim(4, "3 variants × 100 episodes; 300 shards audited, 0 errors", [LS, AU],
          lambda: f"{len(ls['variants'])} variants × {alt['episodes_expected']} episodes; {sum(v['shards_audited'] for v in J(AU).values())} shards audited, {sum(len(v['errors']) for v in J(AU).values())} errors", kind="fn")
    protocol = J("artifacts/core/protocol.json")
    claim(4, "20 seeds × 5 pairs × 11 arms", ["artifacts/core/protocol.json", TP],
          lambda: f"{protocol['seeds']} seeds × 5 pairs × {len({p for p, _ in tp})} arms", kind="fn")

    # ---- slide 5
    VR, DR, RB = ("artifacts/claim_reuse/verification_receipt.json", "artifacts/claim_reuse/demo_receipt.json",
                  "artifacts/claim_reuse/reuse_benchmark.json")
    vr, rb = J(VR), J(RB)
    ad = vr["adapters"]["kimura-fixation-probability/diploid-genic-diffusion"]
    claim(5, "content sha bbfd686b…", [VR], lambda: f"content sha {ad['claim_content_sha256'][:8]}…")
    claim(5, "src sha f371ae67…", [VR], lambda: f"src sha {ad['adapter_source_sha256'][:8]}…")
    claim(5, "v1.0.0", [VR], lambda: f"v{ad['adapter_version']}")
    tr = J("artifacts/turing_scope/results.json")
    m1 = next(m for m in tr["long_domain"]["modes"] if m["n"] == 1)
    claim(5, "no admissible unstable mode at L=π but one (n=1, determinant -1/8) at L=2π", ["artifacts/turing_scope/results.json"],
          lambda: f"no admissible unstable mode at L=π but one (n={m1['n']}, determinant {m1['determinant']}) at L=2π"
          if tr["short_domain"]["verdict"] == "stable" and not tr["short_domain"]["unstable_modes"] and tr["long_domain"]["unstable_modes"] == [1] else "MISMATCH")
    pooled = rb["baseline"]["pooled"]
    reqs = sum(v["requests"] for v in pooled["by_policy"].values())
    claim(5, "Of 488,601 recorded paid requests, 95.3% repeat an earlier one", [RB],
          lambda: f"Of {n(reqs)} recorded paid requests, {100 * pooled['avoided_fraction']:.1f}% repeat an earlier one")
    claim(5, "avoid exactly the same 465,564", [RB],
          lambda: f"avoid exactly the same {n(pooled['cache_avoided'])}" if pooled["cache_avoided"] == pooled["claim_avoided"] else "MISMATCH")
    fi = rb["fault_injection"]["pooled"]
    claim(5, "(4 injected fault types)", [RB], lambda: f"({len(fi['cache']['events_by_attack'])} injected fault types)")
    claim(5, "reused 2,564 invalid facts; typed reuse 0", [RB],
          lambda: f"reused {n(fi['cache']['distinct_invalid_facts_reused'])} invalid facts; typed reuse {fi['typed_claim_reuse']['invalid_reuse_events']}")
    claim(5, "87 passed, 4 skipped in 2.27s", [VR], lambda: vr["tests"]["tail"])
    mut = vr["mutation"]
    claim(5, "guard mutants 9/9, source mutants 7/7 killed", [VR],
          lambda: f"guard mutants {mut['guard_mutants_killed']}/{mut['guard_mutants_total']}, source mutants {mut['source_mutants_killed']}/{mut['source_mutants_total']} killed")

    # ---- slide 6
    RC, BR = "artifacts/proof/receipt.json", "artifacts/integration/core_kappa2_route_lean.json"
    rc, br = J(RC), J(BR)
    ver = re.search(r"version ([0-9.]+)", rc["lean_version"]).group(1)
    claim(6, "Lean 4.35.0 compiled", [RC], lambda: f"Lean {ver} compiled")
    claim(6, "one 7-node VFVS → AIKG route recomputed exactly from raw CSV intervals (7/7); swapped-route mutant rejected (exit 1)", [BR],
          lambda: f"one {br['nodes']}-node VFVS → AIKG route recomputed exactly from raw CSV intervals ({br['recompute_exact_matches']}/{br['nodes']}); swapped-route mutant rejected (exit {br['lean_mutant_swap_build_exit']})")
    core_eps = len(C("artifacts/core/replay/episodes.csv"))
    lz_eps = len(C("artifacts/lazysp/results/episodes.csv"))
    claim(6, "The 1,400 core and LazySP replay decisions", ["artifacts/core/replay/episodes.csv", "artifacts/lazysp/results/episodes.csv"],
          lambda: f"The {n(core_eps + lz_eps)} core and LazySP replay decisions")
    LR = "artifacts/scale/library_receipts.json"
    lr = J(LR)

    def sizes():
        ps = []
        for m in lr["models"].values():
            mm = re.search(r"_(\d+)([MB])_", m["repo"])
            ps.append(int(mm.group(1)) * (1e6 if mm.group(2) == "M" else 1e9))
        lo, hi = min(ps), max(ps)
        f = lambda v: f"{int(v / 1e6)}M" if v < 1e9 else f"{int(v / 1e9)}B"
        return f"{f(lo)}–{f(hi)}"
    claim(6, "Five BioNeMo ESM2 sizes, 8M–3B", [LR], lambda: f"{['Zero','One','Two','Three','Four','Five'][len(lr['models'])]} BioNeMo ESM2 sizes, {sizes()}")
    claim(6, "each scored all 160,000 variants", [LR],
          lambda: f"each scored all {n(next(iter(lr['models'].values()))['covered'])} variants" if all(m["covered"] == 160000 for m in lr["models"].values()) else "MISMATCH")
    sc_rows = C("artifacts/scale/replay_summary.csv")
    sc_n = sum(int(r["episodes"]) for r in sc_rows)

    def zero_incl():
        ok = all(float(r["paired_seed_bootstrap_lo"]) <= 0 <= float(r["paired_seed_bootstrap_hi"]) for r in sc_rows if r["paired_seed_bootstrap_lo"] != "")
        return ok
    claim(6, "1,100 follow-up episodes: no clear assay-saving benefit; all descriptive RMST intervals include zero",
          ["artifacts/scale/replay_summary.csv"],
          lambda: f"{n(sc_n)} follow-up episodes: no clear assay-saving benefit; all descriptive RMST intervals include zero" if zero_incl() else "MISMATCH")
    doc = (ROOT / "docs/company-hypothesis.md").read_text()
    day_re = re.compile(r"## (\d+)-day milestones")
    claim(6, "(120 days)", ["docs/company-hypothesis.md"], lambda: f"({day_re.search(doc).group(1)} days)")



# ----------------------------------------------------------------------------- deck parsing
def parse_deck(path):
    t = re.sub(r"<!--.*?-->", "", Path(path).read_text(encoding="utf-8"), flags=re.S)
    out = []
    for sec in re.findall(r"<section[^>]*>(.*?)</section>", t, flags=re.S):
        sec = re.sub(r"<script.*?</script>|<style.*?</style>", "", sec, flags=re.S)
        notes = re.findall(r'<div class="notes">(.*?)</div>', sec, flags=re.S)
        sec = re.sub(r'<div class="notes">.*?</div>', "", sec, flags=re.S)
        fn = re.findall(r'<div class="fn">(.*?)</div>', sec, flags=re.S)
        sec = re.sub(r'<div class="fn">.*?</div>', "", sec, flags=re.S)
        svgs = re.findall(r"<svg.*?</svg>", sec, flags=re.S)
        sec = re.sub(r"<svg.*?</svg>", " ", sec, flags=re.S)
        clean = lambda x: re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", x))).strip()
        svg_text = " ".join(clean(x) for svg in svgs for x in re.findall(r"<text[^>]*>(.*?)</text>", svg, flags=re.S))
        out.append({"html": clean(sec), "svg": svg_text, "fn": clean(" ".join(fn)), "notes": clean(" ".join(notes))})
    return out


# Axis scales: tick labels that are coordinates, not data.  Declared explicitly per slide.
AXIS = {
    1: ["0.2", "0.3", "0", "1", "2", "3", "4", "5", "6"],  # growth-score ticks and mutation-step ticks 0..6
    4: ["0", "25", "50", "75", "100", "0", "250", "500", "750", "1000"],  # certified-fraction ticks and assay-budget ticks
}


def tokens(s):
    return [m.group(0).rstrip(",.") for m in NUM.finditer(s)]


def consume(text, phrase):
    i = text.find(phrase)
    if i < 0:
        return text, False
    return text[:i] + " " * len(phrase) + text[i + len(phrase):], True


def main():
    global ROOT
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--deck", default="presentation/deck.html")
    ap.add_argument("--out", default="presentation/number_trace.json")
    a = ap.parse_args()
    ROOT = Path(a.root).resolve()
    register()
    slides = parse_deck(ROOT / a.deck)
    errors, trace = [], []
    if len(slides) != 6:
        errors.append(f"expected 6 slides, found {len(slides)}")
    work = [dict(s) for s in slides]
    for slide, kind, shown, expected, files in CLAIMS:
        try:
            exp = expected()
        except Exception as e:  # noqa: BLE001
            errors.append(f"slide {slide}: cannot re-derive {shown!r}: {type(e).__name__}: {e}")
            continue
        if exp != shown:
            errors.append(f"slide {slide}: artifact gives {exp!r} but trace expects {shown!r}")
            continue
        field = {"text": "html", "html": "html", "svg": "svg", "fn": "fn", "fn_biblio": "fn"}[kind]
        s = work[slide - 1]
        # html-kind claims may also be matched in html field only; svg claims in svg only
        s[field], ok = consume(s[field], shown)
        if not ok:
            errors.append(f"slide {slide}: re-derived {shown!r} but it is NOT on the slide ({field})")
            continue
        trace.append({"slide": slide, "shown": shown, "where": field, "files": list(files),
                      "sha256": {f: sha(f) for f in files},
                      **({"note": "bibliographic year of a cited paper; not derivable from a committed artifact"} if kind == "fn_biblio" else {})})
    # footnote commit stamp "artifacts @ <head7>" must equal the provenance head, and that commit must exist in this repo
    deck_p = (ROOT / a.deck) if not Path(a.deck).is_absolute() else Path(a.deck)
    prov = json.loads(deck_p.with_name("deck.provenance.json").read_text())
    head = prov["git"]["head"]
    if subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e", head + "^{commit}"], capture_output=True).returncode != 0:
        errors.append(f"provenance head {head} is not a commit in this repository")
    for i, s in enumerate(work, 1):
        s["fn"], ok = consume(s["fn"], f"artifacts @ {head[:8]}")
        if not ok:
            errors.append(f"slide {i}: footnote commit stamp 'artifacts @ {head[:8]}' missing or differs from deck.provenance.json")
    # Staleness: every input hash recorded when the deck was built must equal the file as committed NOW.
    stale = [rel for rel, h in prov.get("sha256", {}).items() if not (ROOT / rel).exists() or sha(rel) != h]
    for rel in stale:
        errors.append(f"STALE: {rel} changed (or vanished) since the deck was built; rerun bash presentation/rebuild.sh")
    if not prov.get("sha256"):
        errors.append("deck.provenance.json records no input hashes")
    # page counters
    for i, s in enumerate(work, 1):
        s["html"], ok = consume(s["html"], f"{i} / 6")
        if not ok:
            errors.append(f"slide {i}: page counter '{i} / 6' missing")
    # leftover numbers
    leftovers = {}
    for i, s in enumerate(work, 1):
        for field in ("html", "svg", "fn"):
            left = tokens(s[field])
            if field == "svg":
                allow = list(AXIS.get(i, []))
                rest = []
                for tk in left:
                    if tk in allow:
                        allow.remove(tk)
                    else:
                        rest.append(tk)
                left = rest
            elif field == "html" and i in AXIS:
                # axis-title tick labels may be rendered outside SVG in some builds; none expected
                pass
            if left:
                leftovers[f"slide {i} {field}"] = left
                errors.append(f"slide {i} {field}: numbers not traced to any artifact: {left}")
    # speaker notes: every number must appear in that slide's own text (visible + svg + footnote)
    for i, s in enumerate(slides, 1):
        pool = {tk.replace(",", "") for tk in tokens(" ".join([s["html"], s["svg"], s["fn"]]))}
        for tk in tokens(s["notes"]):
            if tk.replace(",", "") not in pool:
                errors.append(f"slide {i} notes: number {tk!r} is not on the slide itself")
    # The PDF is what gets uploaded: every number rendered on each PDF page must be a number the HTML slide carries.
    pdf = deck_p.with_suffix(".pdf")
    pdf_pages = None
    if pdf.exists():
        txt = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True).stdout
        pages = txt.split("\f")
        pages = [p for p in pages if p.strip()]
        pdf_pages = len(pages)
        if pdf_pages != 6:
            errors.append(f"PDF has {pdf_pages} pages, expected 6")
        for i, (pg, s) in enumerate(zip(pages, slides), 1):
            pool = {tk.replace(",", "") for tk in tokens(" ".join([s["html"], s["svg"], s["fn"]]))}
            extra = sorted({tk.replace(",", "") for tk in tokens(pg)} - pool)
            if extra:
                errors.append(f"PDF page {i}: numbers not on the HTML slide: {extra}")
    result = {"deck": a.deck, "inputs_hash_checked": len(prov.get("sha256", {})), "pdf_pages_checked": pdf_pages, "claims_checked": len(trace), "errors": errors, "ok": not errors,
              "provenance_head": head, "trace": trace}
    Path(ROOT / a.out).write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n")
    print(f"claims traced: {len(trace)} / {len(CLAIMS)}; errors: {len(errors)}")
    for e in errors:
        print("  FAIL", e)
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
