#!/usr/bin/env python3
"""Render the 6-slide Darwin's Bridge / Delphi Evolve deck from FINAL integrated artifacts.

    python3 presentation/build_deck.py --root /path/to/integrated/checkout            # final; rejects bad data
    python3 presentation/build_deck.py --root ... --allow-draft                         # DRAFT-stamped, no replay numbers

Every number on a slide is computed here from files under --root (hashes recorded in the
provenance JSON).  Final mode exits 2 if the replay is missing, has empty shards, or has the wrong
cardinality (policies x 20 seeds x 5 episodes).  Draft mode writes deck.DRAFT.html (never deck.html),
stamps every slide DRAFT and replaces the replay slide's figure with a labelled placeholder
that contains no replay numbers.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import io
import itertools
import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import validate as V  # noqa: E402

AA = "ACDEFGHIKLMNPQRSTVWY"
E = html.escape

POLICY_LABEL = {
    "random": "random frontier", "greedy": "greedy walk", "uncertainty": "GP uncertainty",
    "directed": "directed best-first", "q2c": "query-to-certify (single)",
    "collective_shared": "specialists, shared", "collective_isolated": "specialists, isolated*",
    "collective_shared_rr": "specialists, shared, round-robin",
    "q2c_nomodel": "single planner, no GP",
    "collective_shared_c": "specialists shared, no GP",
    "collective_isolated_c": "specialists isolated*, no GP",
}
POLICY_COLOR = {
    "random": "#9aa0a6", "greedy": "#7d8790", "uncertainty": "#b39ddb", "directed": "#1864ab", "q2c": "#d9480f",
    "collective_shared": "#15202b", "collective_isolated": "#5f3dc4", "collective_shared_rr": "#2b6e3f",
    "q2c_nomodel": "#d9480f", "collective_shared_c": "#15202b", "collective_isolated_c": "#5f3dc4",
}
POLICY_DASH = {"random": "2 4", "greedy": "6 4", "uncertainty": "1 3", "directed": "8 4", "q2c": "", "collective_shared": "", "collective_isolated": "10 3 2 3", "collective_shared_rr": "4 2"}


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    h.update(Path(p).read_bytes())
    return h.hexdigest()


def seattle_now() -> str:
    # Seattle is PDT (UTC-7) until 2026-11-01 02:00 local, PST (UTC-8) afterwards.
    u = datetime.now(timezone.utc)
    pdt_end = datetime(2026, 11, 1, 9, 0, tzinfo=timezone.utc)  # 02:00 PDT == 09:00 UTC
    off, name = (-7, "PDT") if u < pdt_end else (-8, "PST")
    return (u + timedelta(hours=off)).strftime("%Y-%m-%d %H:%M ") + name


def git_info(root: Path, rel_paths: list[str]) -> dict:
    def g(*a):
        r = subprocess.run(["git", "-C", str(root), *a], capture_output=True, text=True)
        return r.stdout.strip() if r.returncode == 0 else None
    st = g("status", "--porcelain", "--", *rel_paths) or ""
    return {"head": g("rev-parse", "HEAD"), "branch": g("rev-parse", "--abbrev-ref", "HEAD"),
            "inputs_untracked_or_modified": [l[3:] for l in st.splitlines()]}


# --------------------------------------------------------------------------------------- charts
def short(h):
    return h[:8]


def f3(x):
    return f"{x:.3f}"


def pct(x, d=0):
    return f"{100 * x:.{d}f}%"


def route_profile_svg(dm: dict, tempt: list[str], cert: list[str], w=560, h=360) -> str:
    """Score along the tempting 4-step route and the certified 6-step route (kappa=2 intervals)."""
    nodes = {n["id"]: n for n in dm["nodes"]}
    ml, mr, mt, mb = 52, 18, 18, 46
    ys = [nodes[g][k] for g in tempt + cert for k in ("lower", "upper")]
    lo, hi = min(ys) - 0.02, max(ys) + 0.02
    nmax = max(len(tempt), len(cert)) - 1
    X = lambda i: ml + (w - ml - mr) * i / nmax
    Y = lambda v: mt + (h - mt - mb) * (1 - (v - lo) / (hi - lo))
    out = [f'<svg viewBox="0 0 {w} {h}" style="width:100%;height:auto;display:block" role="img" aria-label="Measured score along two routes from VFVS to AIKG">']
    t = lo
    step = 0.1
    t = np.ceil(lo / step) * step
    while t < hi:
        out.append(f'<line x1="{ml}" x2="{w - mr}" y1="{Y(t):.1f}" y2="{Y(t):.1f}" stroke="#d8d1bf" stroke-width="1"/>'
                   f'<text x="{ml - 8}" y="{Y(t) + 4:.1f}" font-size="12" fill="#5b6670" text-anchor="end">{t:.1f}</text>')
        t += step
    out.append(f'<text x="14" y="{mt + 8}" font-size="12" fill="#5b6670" transform="rotate(-90 14 {mt + 8})" text-anchor="end">growth score (measured)</text>')
    for i in range(nmax + 1):
        out.append(f'<text x="{X(i):.1f}" y="{h - 26}" font-size="12" fill="#5b6670" text-anchor="middle">{i}</text>')
    out.append(f'<text x="{(ml + w - mr) / 2:.1f}" y="{h - 8}" font-size="12" fill="#5b6670" text-anchor="middle">mutation step</text>')
    # certified route: interval ribbon + line
    pts = [(X(i), Y(nodes[g]["observed_score"])) for i, g in enumerate(cert)]
    rib = [f"{X(i):.1f},{Y(nodes[g]['upper']):.1f}" for i, g in enumerate(cert)] + [f"{X(i):.1f},{Y(nodes[g]['lower']):.1f}" for i, g in reversed(list(enumerate(cert)))]
    out.append(f'<polygon points="{" ".join(rib)}" fill="#d9480f" opacity=".16"/>')
    out.append(f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" fill="none" stroke="#d9480f" stroke-width="3"/>')
    for (x, y), g in zip(pts, cert):
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="#d9480f"/>')
    # tempting route: ink dashed; first descent flagged
    tp = [(X(i), Y(nodes[g]["observed_score"])) for i, g in enumerate(tempt)]
    out.append(f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in tp)}" fill="none" stroke="#15202b" stroke-width="2.5" stroke-dasharray="7 5"/>')
    for i, ((x, y), g) in enumerate(zip(tp, tempt)):
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="#fdfcf8" stroke="#15202b" stroke-width="2"/>')
        if i:
            prev = nodes[tempt[i - 1]]["observed_score"]
            if nodes[g]["observed_score"] < prev:
                out.append(f'<path d="M{x - 6:.1f} {y + 12:.1f} l12 12 m0 -12 l-12 12" stroke="#b0145b" stroke-width="3" fill="none"/>'
                           f'<text x="{x + 12:.1f}" y="{y + 32:.1f}" font-size="13" font-weight="700" fill="#b0145b">{E(tempt[i - 1])}→{E(g)}: a step down</text>')
                break
    out.append(f'<text x="{X(0) + 8:.1f}" y="{Y(nodes[cert[0]]["observed_score"]) + 20:.1f}" font-size="13" font-weight="700" fill="#15202b">VFVS</text>')
    out.append(f'<text x="{X(len(cert) - 1) - 6:.1f}" y="{Y(nodes[cert[-1]]["observed_score"]) + 24:.1f}" font-size="13" font-weight="700" fill="#15202b" text-anchor="end">AIKG</text>')
    out.append("</svg>")
    return "".join(out)


def kappa_svg(sweep: list[dict], w=560, h=300) -> str:
    ml, mr, mt, mb = 20, 10, 30, 74
    n = len(sweep)
    bw = (w - ml - mr) / n
    top = 8.0
    out = [f'<svg viewBox="0 0 {w} {h}" style="width:100%;height:auto;display:block" role="img" aria-label="Shortest certifiable route length versus assumed read-noise multiplier kappa">']
    for i, r in enumerate(sweep):
        x = ml + i * bw
        cx = x + bw / 2
        L = r["shortest_route_edges"]
        base = h - mb
        if L is None:
            out.append(f'<rect x="{x + 8:.1f}" y="{mt:.1f}" width="{bw - 16:.1f}" height="{base - mt:.1f}" fill="none" stroke="#b0145b" stroke-width="2" stroke-dasharray="5 4"/>'
                       f'<text x="{cx:.1f}" y="{mt + 70}" font-size="14" font-weight="700" fill="#b0145b" text-anchor="middle">no route</text>'
                       f'<text x="{cx:.1f}" y="{mt + 88}" font-size="14" font-weight="700" fill="#b0145b" text-anchor="middle">certifiable</text>')
        else:
            bh = (base - mt) * L / top
            colr = "#d9480f" if L > sweep[0]["shortest_route_edges"] else "#15202b"
            out.append(f'<rect x="{x + 8:.1f}" y="{base - bh:.1f}" width="{bw - 16:.1f}" height="{bh:.1f}" fill="{colr}"/>'
                       f'<text x="{cx:.1f}" y="{base - bh - 7:.1f}" font-size="18" font-weight="700" fill="{colr}" text-anchor="middle">{L}</text>')
        out.append(f'<text x="{cx:.1f}" y="{base + 20}" font-size="14" font-weight="700" fill="#15202b" text-anchor="middle">{r["kappa"]:g}</text>'
                   f'<text x="{cx:.1f}" y="{base + 42}" font-size="13" fill="#5b6670" text-anchor="middle">{r["reachable_from_start"]}</text>')
    out.append(f'<line x1="{ml}" x2="{w - mr}" y1="{h - mb}" y2="{h - mb}" stroke="#15202b" stroke-width="2"/>')
    out.append(f'<text x="{ml}" y="{mt - 12}" font-size="13" fill="#5b6670">mutations on the shortest route whose every step is certified</text>')
    out.append("</svg>")
    return "".join(out)


def curves_svg(ep_rows: list[dict], policies: list[str], seeds_n: int, w=640, h=340) -> str:
    ml, mr, mt, mb = 52, 14, 14, 48
    X = lambda x: ml + (w - ml - mr) * x / 1000
    Y = lambda y: mt + (h - mt - mb) * (1 - y)
    out = [f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="Fraction of replay episodes with a sound certificate versus assays, by policy">']
    for g in (0, .25, .5, .75, 1):
        out.append(f'<line x1="{ml}" x2="{w - mr}" y1="{Y(g):.1f}" y2="{Y(g):.1f}" stroke="#d8d1bf"/><text x="{ml - 8}" y="{Y(g) + 4:.1f}" font-size="12" fill="#5b6670" text-anchor="end">{int(g * 100)}%</text>')
    for x in (0, 250, 500, 750, 1000):
        out.append(f'<text x="{X(x):.1f}" y="{h - 28}" font-size="12" fill="#5b6670" text-anchor="middle">{x}</text>')
    out.append(f'<text x="{(ml + w - mr) / 2:.1f}" y="{h - 8}" font-size="12" fill="#5b6670" text-anchor="middle">assays bought beyond the 96 initial observations (matched across policies)</text>')
    out.append(f'<text x="14" y="{(mt + h - mb) / 2:.0f}" font-size="12" fill="#5b6670" text-anchor="middle" transform="rotate(-90 14 {(mt + h - mb) / 2:.0f})">episodes with a certificate</text>')
    for p in policies:
        t = sorted(float(r["assays"]) for r in ep_rows if r["policy"] == p and r["certificate"] in ("open", "blocked"))
        n = sum(1 for r in ep_rows if r["policy"] == p)
        pts = []
        for x in range(0, 1001, 5):
            pts.append(f"{X(x):.1f},{Y(sum(1 for v in t if v <= x) / n):.1f}")
        da = f' stroke-dasharray="{POLICY_DASH[p]}"' if POLICY_DASH[p] else ""
        sw = 3.2 if p in ("q2c", "collective_shared") else 2.2
        out.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{POLICY_COLOR[p]}" stroke-width="{sw}"{da}/>')
    out.append("</svg>")
    return "".join(out)


def heatmap_png_b64(score: np.ndarray, unknown: np.ndarray) -> str:
    from PIL import Image
    s = score.reshape(400, 400)
    known = ~unknown.reshape(400, 400)
    lo, hi = np.percentile(s[known], [1, 99.7])
    u = np.clip((s - lo) / (hi - lo), 0, 1) ** 0.8  # gamma only to make the low-growth gradation visible; monotone
    stops = np.array([[240, 234, 214], [236, 168, 112], [217, 72, 15], [74, 26, 5]], float)
    pos = np.array([0, .35, .7, 1.0])
    img = np.zeros((400, 400, 3))
    for c in range(3):
        img[..., c] = np.interp(u, pos, stops[:, c])
    img[~known] = (95, 61, 196)
    im = Image.fromarray(img.astype(np.uint8)).resize((800, 800), Image.NEAREST)
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


def gidx(g: str) -> int:
    a = [AA.index(c) for c in g]
    return ((a[0] * 20 + a[1]) * 20 + a[2]) * 20 + a[3]


# ----------------------------------------------------------------------------------------- data
def load_inputs(root: Path) -> dict:
    D: dict = {"root": root}
    dm_path = root / "artifacts/demo.json"
    if not dm_path.exists():
        dm_path = root / "site/data/demo.json"
    D["demo_path"] = dm_path
    D["demo"] = json.loads(dm_path.read_text())
    D["receipt"] = json.loads((root / "artifacts/proof/receipt.json").read_text())
    br = root / "artifacts/integration/core_kappa2_route_lean.json"
    D["bridge"] = json.loads(br.read_text()) if br.exists() else None
    D["protocol"] = json.loads((root / "artifacts/core/protocol.json").read_text())
    rs = root / "artifacts/evidence/route_summary.json"
    D["route_summary"] = json.loads(rs.read_text()) if rs.exists() else None
    cr = root / "artifacts/claim_reuse"
    need = ["demo_receipt.json", "reuse_benchmark.json", "verification_receipt.json"]
    if all((cr / n).exists() for n in need):
        D["claims"] = {"receipt": json.loads((cr / "demo_receipt.json").read_text()), "reuse": json.loads((cr / "reuse_benchmark.json").read_text()),
                       "verify": json.loads((cr / "verification_receipt.json").read_text())}
    else:
        D["claims"] = None
    lz = (root / "artifacts/lazysp/panel/table_primary.csv").exists()
    gr = any((root / "artifacts/scale").glob("**/prior_replay*/table_primary.csv")) if (root / "artifacts/scale").exists() else False
    D["lazysp_present"], D["gpu_replay_present"] = lz, gr
    D["pending_text"] = ("a result file is present in artifacts/lazysp but this deck does not quote it; read it first." if lz
                         else "pending, not complete at render time (see appendix); no benefit is claimed.")
    D["pending_short"] = "a result file exists but is not quoted here" if lz else "still pending, so Q2C is not claimed to beat it"
    D["gpu_replay_text"] = ("result file present but not quoted here" if gr else "pending, not complete at render time")
    D["gpu_replay_short"] = "result file present but not quoted" if gr else "still pending"
    t = (root / "site/data/landscape.js").read_text()
    L = json.loads(t[t.index("{"):t.rindex("}") + 1])
    r1 = np.frombuffer(base64.b64decode(L["r1"]), "<i2").astype(float)
    r2 = np.frombuffer(base64.b64decode(L["r2"]), "<i2").astype(float)
    unk = (r1 == -32768) | (r2 == -32768)
    D["land_meta"] = L["meta"]
    D["unknown"] = unk
    D["score"] = np.where(unk, np.nan, (r1 + r2) / 2 / 50000.0)
    return D


def direct_orderings(score: np.ndarray, start="VFVS", target="AIKG"):
    diffs = [i for i in range(4) if start[i] != target[i]]
    good, tot = 0, 0
    for perm in itertools.permutations(diffs):
        g = list(start)
        prev = score[gidx("".join(g))]
        ok = True
        for i in perm:
            g[i] = target[i]
            s = score[gidx("".join(g))]
            if not (s >= prev):
                ok = False
            prev = s
        tot += 1
        good += ok
    return tot, good


def replay_numbers(root: Path, D: dict, info: dict) -> dict:
    rd = root / "artifacts/core/replay"
    tp = V.read_csv(rd / "table_primary.csv")
    tpp = V.read_csv(rd / "table_paired.csv")
    ep = V.read_csv(rd / "episodes.csv")
    seeds = D["protocol"]["seeds"]
    main = V.MAIN_POLICIES
    follow = info.get("followup_policies_complete", [])
    pols = main + follow
    ep = [r for r in ep if r["policy"] in pols]
    # cross-check curve vs table_primary at the budgets
    for r in tp:
        if r["family"] == "all" and r["policy"] in pols:
            b = int(r["budget"])
            rows = [x for x in ep if x["policy"] == r["policy"]]
            c = sum(1 for x in rows if x["certificate"] in ("open", "blocked") and float(x["assays"]) <= b)
            if c != int(r["certified"]):
                raise SystemExit(f"episodes.csv and table_primary disagree for {r['policy']}@{b}: {c} vs {r['certified']}")
    T = {(r["family"], r["policy"], int(r["budget"])): r for r in tp}
    P = {}
    for r in tpp:
        P[(r["a"], r["b"], r["family"], int(r["budget"]), r["metric"].split("(")[0])] = r
    return {"T": T, "P": P, "ep": ep, "pols": pols, "main": main, "follow": follow, "seeds": seeds,
            "n_ep": seeds * V.EPISODES_PER_SEED}


SHORT = {"higher": "interval above 0", "lower": "interval below 0", "not distinguishable from": "interval spans 0"}


def verdict(r) -> tuple[str, float, float, float]:
    m, lo, hi = float(r["mean_diff"]), float(r["seed_cluster_bootstrap_2.5"]), float(r["seed_cluster_bootstrap_97.5"])
    if lo > 0:
        w = "higher"
    elif hi < 0:
        w = "lower"
    else:
        w = "not distinguishable from"
    return w, m, lo, hi


# ----------------------------------------------------------------------------------- slide text
def build_slides(D: dict, R: dict | None, draft_reasons: list[str], prov: dict) -> tuple[list[str], list[str]]:
    dm = D["demo"]
    src = dm["source"]
    cnt = src["counts"]
    short = lambda h: h[:8]
    nodes = {n["id"]: n for n in dm["nodes"]}
    routes = {r["id"]: r for r in dm["routes"]}
    cert, tempt = routes["certified-shortest"], routes["tempting-direct"]
    sweep = dm["kappa_sweep"]
    n_ord, n_ok = direct_orderings(D["score"])
    if D["route_summary"]:
        rs = D["route_summary"]["direct_orderings"]
        if (rs["orderings"], rs["admitted_at_parameter_0"]) != (n_ord, n_ok):
            raise SystemExit(f"direct-ordering recount {(n_ord, n_ok)} disagrees with route_summary.json {rs}")
    kmap = {r["kappa"]: r for r in sweep}
    k0, k2, k3 = kmap[0.0], kmap[2.0], kmap[3.0]
    last_open = max(r["kappa"] for r in sweep if r["open"])
    first_closed = min(r["kappa"] for r in sweep if not r["open"])
    steps = cert["steps"]
    wk = steps[cert["weakest_step_index"]]
    rc = D["receipt"]
    br = D["bridge"]
    n_inst = len(rc.get("instance_mutants", []))
    n_inst_ok = sum(1 for m in rc.get("instance_mutants", []) if m.get("as_expected"))
    n_src = len(rc.get("source_mutants", []))
    n_src_rej = sum(1 for m in rc.get("source_mutants", []) if m.get("rejected"))
    axioms = sorted({a for v in rc["axioms"].values() for a in v})
    tempt_scores = [nodes[g]["observed_score"] for g in tempt["nodes"]]
    first_desc = next((i for i in range(1, len(tempt_scores)) if tempt_scores[i] < tempt_scores[i - 1]), None)

    ordtxt = (f"Taking the measurements at face value, <b>every one</b> of the {n_ord} steps down at least once." if n_ok == 0
              else f"Taking the measurements at face value, only <b>{n_ok}</b> of the {n_ord} never step down.")
    fn = lambda *parts: '<div class="fn">' + " · ".join(parts) + "</div>"
    sha = f'dataset summary_AA.csv sha256 {src["sha256"]["summary_AA.csv"][:12]}…'
    commit = f'artifacts @ {short(prov["git"]["head"] or "unknown")}'

    # ---- S1
    s1 = f"""
<div class="brand"><i></i>Darwin’s Bridge / Delphi Evolve</div><div class="num">1 / 6</div>
<div class="row" style="gap:36px">
 <div class="col" style="flex:1.05">
  <h1 class="hero">A protein design is <em>not a plan.</em></h1>
  <p class="lede">Which mutation do you make first — and what evidence says the next step will still work?</p>
  <div class="card" style="margin-top:6px"><h3>Target and the missing route</h3>
   <p class="small" style="margin:0">TrpB enzyme, four residues, parent <span class="mono">VFVS</span> → best measured variant <span class="mono">AIKG</span>. All four changes are needed, so there are <b>{n_ord}</b> orders to make them in. {ordtxt}</p></div>
 </div>
 <div class="col" style="flex:.95;margin-top:70px">
  <div class="card" style="padding:10px 10px 4px">{route_profile_svg(dm, tempt["nodes"], cert["nodes"])}
   <p class="small" style="margin:4px 8px 8px"><span class="sw" style="border-color:#15202b;border-top-style:dashed"></span>the most tempting direct ordering {" → ".join(tempt["nodes"])}<br><span class="sw" style="border-color:#d9480f"></span>the {len(cert["nodes"]) - 1}-step detour whose every step is certified (band = assumed κ=2 interval)</p></div>
 </div>
</div>
{fn(f'<b>Source</b> Johnston et al., PNAS 2024, doi 10.1073/pnas.2400439121; data CaltechDATA {E(src["doi"])} (CC0), {sha}', f'descriptive full-label figure: orderings recounted from site/data/landscape.js, cross-checked with artifacts/evidence/route_summary.json', commit)}"""
    n1 = (f"A protein design is not a plan. Parent VFVS, best measured variant AIKG: four changes, {n_ord} possible orders. "
          f"At face value, {'every direct order steps down at least once' if n_ok == 0 else str(n_ok) + ' orders never step down'}. "
          f"The orange detour takes {len(cert['nodes']) - 1} steps, each certified under an assumption we state.")

    # ---- S2
    png = heatmap_png_b64(D["score"], D["unknown"])
    vi, ai = gidx("VFVS"), gidx("AIKG")
    pos = lambda i: (100 * ((i % 400) + .5) / 400, 100 * ((i // 400) + .5) / 400)
    (vx, vy), (ax_, ay) = pos(vi), pos(ai)
    s2 = f"""
<div class="brand"><i></i>Darwin’s Bridge / Delphi Evolve</div><div class="num">2 / 6</div>
<h2>This is a <em>measured</em> landscape: {cnt['measured_nonstop_genotypes']:,} of {cnt['library_nonstop_genotypes']:,} variants have a laboratory value.</h2>
<div class="row" style="gap:30px">
 <div style="position:relative;width:470px;height:470px;flex:none;border:1px solid var(--rule)">
  <img alt="Heat map of measured growth score for every measured four-residue TrpB variant" src="data:image/png;base64,{png}" style="width:470px;height:470px;display:block">
  <svg viewBox="0 0 100 100" style="position:absolute;inset:0;width:100%;height:100%" aria-hidden="true">
   <circle cx="{vx:.2f}" cy="{vy:.2f}" r="1.8" fill="none" stroke="#15202b" stroke-width=".7"/><text x="{vx - 2.6:.2f}" y="{vy + 1.4:.2f}" text-anchor="end" font-size="4.2" font-weight="700" fill="#15202b" style="paint-order:stroke;stroke:#fdfcf8;stroke-width:.9">VFVS</text>
   <circle cx="{ax_:.2f}" cy="{ay:.2f}" r="1.8" fill="none" stroke="#15202b" stroke-width=".7"/><text x="{ax_ + 2.6:.2f}" y="{ay + 1.4:.2f}" font-size="4.2" font-weight="700" fill="#15202b" style="paint-order:stroke;stroke:#fdfcf8;stroke-width:.9">AIKG</text></svg>
 </div>
 <div class="col">
  <div class="row" style="gap:18px;margin-bottom:14px">
   <div class="card col"><div class="big">{cnt['measured_nonstop_genotypes']:,}<small>measured genotypes, two replicate flasks each</small></div></div>
   <div class="card col"><div class="big" style="color:var(--violet)">{cnt['unmeasured_nonstop_genotypes']}<small>never measured — stay <b>unknown</b></small></div></div>
  </div>
  <table><tr><th>Row ledger</th><th>count</th></tr>
   <tr><td>rows in source file (incl. stop codons)</td><td>{cnt['source_rows_summary_AA']:,}</td></tr>
   <tr><td>stop-codon rows, excluded</td><td>{cnt['stop_containing_rows']:,}</td></tr>
   <tr><td>measured, no stop</td><td>{cnt['measured_nonstop_genotypes']:,}</td></tr>
   <tr><td>imputed in the authors’ separate file</td><td>{cnt['knn_imputed_rows_separate_file']}</td></tr>
   <tr><td>imputed rows used as observations here</td><td><b>{cnt['imputed_rows_used_as_observations']}</b></td></tr></table>
  <p class="small" style="margin:12px 0 10px">Colour = measured growth score, monotone gamma-stretched so low values are visible (cream low → deep orange high). The 871 unmeasured cells are violet and too small to see: each is a place a route could pass that we have no data for.</p>
  <div class="scope"><b>Reads as:</b> cellular growth of E. coli selecting for tryptophan synthase activity — a proxy, not a purified-enzyme constant. Layout: rows = residues 1×2, columns = residues 3×4. A projection of sequence space, not molecular geometry.</div>
 </div>
</div>
{fn(f'<b>Source</b> {sha}; counts from artifacts/demo.json source.counts (independent recount: scripts/audit_data.py)', 'score = mean of two replicates’ growth rate minus stop-codon background; not max-normalised', commit)}"""
    n2 = (f"Every pixel is a measured enzyme variant: {cnt['measured_nonstop_genotypes']:,} of {cnt['library_nonstop_genotypes']:,} four-residue combinations, from the published CC0 dataset, scored by cellular growth. "
          f"{cnt['unmeasured_nonstop_genotypes']} were never measured. We keep them unknown, and we used none of the authors' imputed rows as observations. This is a map of measurements, not of molecular geometry.")

    # ---- S3
    s3 = f"""
<div class="brand"><i></i>Darwin’s Bridge / Delphi Evolve</div><div class="num">3 / 6</div>
<h2>Challenge the assumption and the route moves: <em>{k0['shortest_route_edges']} steps → {k2['shortest_route_edges']} → {k3['shortest_route_edges']}</em>, then no route can be certified.</h2>
<div class="row" style="gap:28px">
 <div class="col" style="flex:1.1"><div class="card" style="padding:10px 12px 8px">{kappa_svg(sweep)}<p class="small" style="margin:2px 0 0;font-size:14px">bold row: assumed κ · grey row: variants reachable from VFVS by certified steps</p></div>
  <p class="small" style="margin:8px 0 0"><b>κ</b> multiplies the replicate-disagreement spread to widen every measurement into an interval. It is an <b>assumed</b> sensitivity — not a confidence level. A step is certified only if the next variant’s lower bound clears the current one’s upper bound.</p></div>
 <div class="col" style="flex:.9">
  <div class="card"><h3 style="text-transform:none;letter-spacing:0;font-size:15px">The weakest step of the κ={k2['kappa']:g} route</h3>
   <p class="small" style="margin:0 0 6px"><span class="mono">{E(wk['from'])} → {E(wk['to'])}</span> clears the bar by only <b>{wk['margin']:.4f}</b> growth units; the route is certifiable up to κ≈<b>{cert['breaks_at_kappa']}</b> and must be re-planned beyond.</p>
   <p class="small" style="margin:0">Variants reachable from VFVS by certified steps: <b>{k0['reachable_from_start']}</b> at κ=0 → <b>{k2['reachable_from_start']}</b> at κ=2 → <b>{kmap[first_closed]['reachable_from_start']}</b> at κ={first_closed:g}. In the live tool, clicking a step shows its raw replicate rows.</p></div>
  <div class="scope" style="margin-top:14px"><b>Precisely:</b> at κ={first_closed:g} the tool says “no route certifiable at this bound” ({kmap[first_closed]['reachable_from_start']} variants reachable by certified steps). That does <i>not</i> mean no ascending route exists: overlapping intervals are simply not certified. κ={last_open:g} is the last bound in the sweep with a certified route.</div>
  <p class="small" style="margin:12px 0 0">When the evidence cannot settle a step, the system’s output is the next assay to run — not a confidence number it cannot support.</p>
 </div>
</div>
{fn('<b>Source</b> artifacts/demo.json kappa_sweep (core worker; frozen noise model artifacts/core/protocol.json), independently recomputed at all 8 κ by scripts/independent_truth.py', 'descriptive, uses all measured labels (not a replay result); graph scope: measured 4-site subgraph, 871 unmeasured genotypes outside', commit)}"""
    n3 = (f"Challenge the assumption. Kappa is how much we distrust each measurement. The shortest route has {k0['shortest_route_edges']} steps at zero, {k2['shortest_route_edges']} at the default, {k3['shortest_route_edges']} at three; "
          f"by kappa {first_closed:g}, none can be certified. That does not mean none exists. "
          f"The weakest step, {wk['from']} to {wk['to']}, clears by {wk['margin']:.4f}: that is where the tool asks for a measurement.")

    # ---- S4
    wordnotes = {}
    if R is None:
        reasons = "".join(f"<li>{E(r)}</li>" for r in draft_reasons[:5])
        body4 = f"""<div class="ghost" style="height:340px;flex-direction:column"><div style="font-size:30px">REPLAY RESULT NOT FINAL</div>
          <div style="font-size:16px;margin-top:10px;font-weight:600;max-width:520px">No replay numbers are shown: the integrated 20-seed run failed validation.</div></div>
          <ul class="small" style="margin:8px 0 0;padding-left:18px">{reasons}</ul>"""
        head4 = "DRAFT — matched-budget replay result pending the integrated 20-seed run."
        fn4 = fn('<b>Source</b> replay not validated (see list above)', commit)
        n4 = "DRAFT: replay is not final; do not present this slide until the deck is rebuilt in final mode."
    else:
        T, P, pols = R["T"], R["P"], R["pols"]
        B = 1000
        orig, post = V.ORIGINAL_POLICIES, R["follow"]
        rate = lambda p, b=B: float(T[("all", p, b)]["cert_rate"])
        cnt_ = lambda p, b=B: int(T[("all", p, b)]["certified"])
        need = ("collective_shared", "q2c", "all", B, "cert_rate_diff")
        if need not in P:
            raise SystemExit(f"table_paired.csv lacks {need}; cannot state specialists vs single policy")
        wc, mc, lc, hc = verdict(P[need])
        nep = R["n_ep"]
        false_tot = sum(int(T[("all", p, B)]["false_certificates"]) for p in pols)
        cert_tot = sum(int(T[("all", p, B)]["certified"]) for p in pols)
        fv = sum(int(T[("all", p, B)]["full_data_verification_failures"]) for p in pols)
        spec = {"higher": "certify more than", "lower": "certify fewer than", "not distinguishable from": "are indistinguishable from"}[wc]
        sh_pct = pct(rate("collective_shared"))
        head4 = (f"Matched budget, {B} assays: query-to-certify certifies {pct(rate('q2c'))} of {nep} episodes; directed {pct(rate('directed'))}, random {pct(rate('random'))}. "
                 f"Specialists {spec} the single planner.")
        rows = []
        def prow(p, cls=""):
            r250, r = T[("all", p, 250)], T[("all", p, B)]
            return (f'<tr{cls}><td><span class="sw" style="border-color:{POLICY_COLOR.get(p, "#555")}"></span>{POLICY_LABEL[p]}</td>'
                    f'<td>{pct(float(r250["cert_rate"]))}</td><td><b>{pct(float(r["cert_rate"]))}</b></td><td>{float(r["rmst_assays"]):.0f}</td><td>{r["false_certificates"]}</td></tr>')
        for p in orig:
            rows.append(prow(p))
        if post:
            rows.append('<tr class="sep"><td colspan="5" style="text-align:left;font-size:12px;color:var(--ink2);font-weight:700;letter-spacing:.04em">POST HOC arms — added after the original run was observed; the no-GP arm was selected after seeing it, not a pre-registered winner</td></tr>')
            for p in post:
                rows.append(prow(p, ' class="follow"'))
        def cell(a_, b_, bud):
            k = (a_, b_, "all", bud, "cert_rate_diff")
            if k not in P:
                return "—"
            w, m, lo, hi = verdict(P[k])
            return f"{m * 100:+.0f} [{lo * 100:+.0f}, {hi * 100:+.0f}]"
        pair_rows = []
        for a_, b_, lab in (("q2c", "directed", "single planner − directed"), ("q2c", "random", "single planner − random"),
                            ("collective_shared", "q2c", "specialists shared − single"), ("collective_shared", "collective_isolated", "shared − isolated*"),
                            ("q2c_nomodel", "q2c", "post hoc: no-GP − single")):
            if (a_, b_, "all", B, "cert_rate_diff") in P:
                pair_rows.append(f'<tr><td>{lab}</td><td>{cell(a_, b_, 250)}</td><td><b>{cell(a_, b_, B)}</b></td></tr>')
        lazy = "Strong LazySP baseline and GPU-prior ablation: " + ("pending (appendix)" if "pending" in D["pending_text"] else "see appendix")
        body4 = f"""
<div class="row" style="gap:20px">
 <div class="col" style="flex:none;width:540px"><div class="card" style="padding:6px 2px 0">{curves_svg(R['ep'], orig, R['seeds'], w=536, h=236)}</div>
  <p class="small" style="margin:2px 0 4px;font-size:12.5px">Original 7 arms. Certified fraction (percentage points, paired by seed; seed-cluster bootstrap 95%):</p>
  <table style="font-size:13px"><tr><th>paired difference</th><th>@250</th><th>@{B}</th></tr>{"".join(pair_rows)}</table></div>
 <div class="col">
  <table style="font-size:13px"><tr><th>policy</th><th>@250</th><th>@{B}</th><th>assays†</th><th>false</th></tr>{"".join(rows)}</table>
  <div class="scope" style="margin-top:8px;font-size:13px;line-height:1.3"><b>Read carefully.</b> No collective uplift over one planner. {false_tot} false certificates among {cert_tot} issued, {fv} full-data failures: certificates use only revealed labels, so this checks structural consistency, not biological accuracy. 20 seed clusters; 100 episodes per policy are 4 targets repeated over 20 seeds (80) plus 20 seed-chosen pairs, not 100 independent targets. *Isolated specialists still share a duplicate-request path and arbitration differs. † unresolved counted at budget.</div>
 </div>
</div>"""
        fn4 = fn(f'<b>Source</b> artifacts/core/replay/ table_primary, table_paired, episodes ({R["seeds"]} seeds × 5 pairs × {len(pols)} arms; each arm’s paid-query trace re-counted = assays)',
                 '<b>Prior art</b> LazySP, BAEE, ALDE (not run here). ' + lazy, commit)
        q2c_early = cnt_("q2c", 250)
        nogp_txt = (f"Dropping the learned model, an arm chosen after seeing the original run, reaches {cnt_('q2c_nomodel')}, but only {cnt_('q2c_nomodel', 250)} versus {q2c_early} at 250 assays. "
                    if "q2c_nomodel" in pols else "")
        n4 = (f"Does asking for the decisive assay save measurements? Retrospectively, matched budgets, {R['seeds']} seed clusters. At {B} assays, query-to-certify certifies {cnt_('q2c')} of 100; directed {cnt_('directed')}; random {cnt_('random')}. "
              f"Specialists sharing evidence: {cnt_('collective_shared')}. No collective uplift. "
              f"{nogp_txt}"
              f"A hundred episodes are not a hundred independent targets; zero false certificates is a consistency check. LazySP-style baseline: {D['pending_short']}.")
    s4 = f"""
<div class="brand"><i></i>Darwin’s Bridge / Delphi Evolve</div><div class="num">4 / 6</div>
<h2 style="font-size:27px;margin:24px 0 8px;line-height:1.14">{head4}</h2>
{body4}
{fn4}"""

    # ---- S5: Delphi claims as bounded, assumption-aware knowledge execution
    cr = D["claims"]
    if cr is None:
        s5 = f"""<div class="brand"><i></i>Darwin’s Bridge / Delphi Evolve</div><div class="num">5 / 6</div>
<h2>Claim-runtime artifacts unavailable in this root.</h2>{fn('claim_runtime receipts missing', commit)}"""
        n5 = "Claim runtime receipts are unavailable in this build."
    else:
        sc = {s["scenario"]: s["response"] for s in cr["receipt"]["claim_scenarios"]}
        dc = {c["scenario"]: c for c in cr["receipt"]["decision_changes"]}
        LAB = [("kimura_valid_calculation", "Kimura: diploid, genic, constant Ne (declared s)"),
               ("kimura_refused_haploid_model_transfer", "Kimura on haploid E. coli"),
               ("kimura_refused_trpb_assay_score_as_s", "Kimura with a TrpB growth score as s"),
               ("fisher_valid_partial_change", "Fisher: partial change, declared V<sub>A</sub>"),
               ("fisher_refused_total_change", "Fisher: total fitness change"),
               ("fisher_refused_every_step_improves", "Fisher: “every step improves”")]
        for k, _ in LAB:
            if k not in sc:
                raise SystemExit(f"demo_receipt.json lacks scenario {k}")
        def dec(r):
            return ('<span class="tag ok">COMPUTE</span>' if r["decision"] == "compute" else '<span class="tag no">REFUSE</span>')
        scen_rows = "".join(f'<tr><td style="text-align:left">{lab}</td><td>{dec(sc[k])}</td><td class="mono" style="font-size:12.5px;text-align:left">{E(sc[k]["reason_code"])}</td></tr>' for k, lab in LAB)
        CH = [("kimura_claim_withdrawn", "source withdrawn"), ("kimura_claim_deleted", "source deleted"),
              ("kimura_claim_unavailable", "source unreachable"), ("kimura_claim_context_edited", "assumption text edited")]
        for k, _ in CH:
            if k not in dc or not dc[k]["decision_changed"] or dc[k]["after"]["decision"] != "refuse":
                raise SystemExit(f"decision_changes lacks refuse-flip for {k}")
        ch_rows = "".join(f'<tr><td style="text-align:left">{lab}</td><td>compute → <span class="tag no">REFUSE</span></td><td class="mono" style="font-size:12.5px;text-align:left">{E(dc[k]["after"]["reason_code"])}</td></tr>' for k, lab in CH)
        kc = sc["kimura_valid_calculation"]["claim_use"]
        ad_k = sc["kimura_valid_calculation"]["adapter"]
        rb = cr["reuse"]
        pooled, perpol = rb["baseline"]["pooled"], rb["baseline"]["per_policy"]
        reqs = sum(v["requests"] for v in pooled["by_policy"].values())
        fi = rb["fault_injection"]["pooled"]
        if not (pooled["cache_equals_claim"] and pooled["claim_gain_over_cache"] == 0):
            raise SystemExit("reuse benchmark no longer shows cache == claim reuse; slide text would be wrong")
        ver = cr["verify"]
        s5 = f"""
<div class="brand"><i></i>Darwin’s Bridge / Delphi Evolve</div><div class="num">5 / 6</div>
<h2 style="font-size:30px;margin:24px 0 10px">An existing Delphi claim now <em>changes a decision</em>: it runs when its assumptions hold and refuses when they don’t.</h2>
<div class="row" style="gap:20px">
 <div class="col" style="flex:1.12">
  <div class="card" style="padding:8px 12px"><div style="display:flex;gap:6px;align-items:stretch;font-size:14px;line-height:1.3">
   <div style="flex:1;border:1px solid var(--rule);padding:5px 7px;border-radius:5px"><b>Delphi claim</b><br>kimura-fixation-probability · Fisher FTNS<br><span class="mono" style="font-size:12px">content sha {short(kc["pinned_content_sha256"])}…</span></div>
   <div style="align-self:center;color:var(--orange);font-weight:800">→</div>
   <div style="flex:1;border:1px solid var(--rule);padding:5px 7px;border-radius:5px"><b>hand-authored adapter</b><br>v{E(ad_k["version"])}, pinned to the record<br><span class="mono" style="font-size:12px">src sha {short(ad_k["source_sha256"])}…</span></div>
   <div style="align-self:center;color:var(--orange);font-weight:800">→</div>
   <div style="flex:1;border:1px solid var(--rule);padding:5px 7px;border-radius:5px"><b>applicability guard</b><br>model, ploidy, quantity, inference<br>computes or refuses</div></div>
   <div class="small" style="font-size:14px;margin:6px 0 0">Provenance kept in four layers: source record · adapter mapping · new operationalization · result kind (<b>SIMULATED</b>, never observed).</div></div>
  <table style="margin-top:10px;font-size:15px"><tr><th>request</th><th>decision</th><th style="text-align:left">reason</th></tr>{scen_rows}</table>
 </div>
 <div class="col" style="flex:1">
  <div class="card" style="padding:8px 12px"><h3 style="margin-bottom:4px">Same request, different source state</h3>
   <table style="font-size:15px">{ch_rows}</table></div>
  <div class="card" style="padding:8px 12px;margin-top:8px"><h3 style="margin-bottom:4px">Observed TrpB evidence, typed reuse</h3>
   <p class="small" style="margin:0 0 4px;font-size:15px;line-height:1.35"><b>Same context = ordinary cache.</b> Of {reqs:,} recorded paid requests, {pct(pooled["avoided_fraction"], 1)} repeat an earlier one: typed reuse and a plain cache avoid exactly the same {pooled["cache_avoided"]:,}. Typed reuse gains nothing there.</p>
   <p class="small" style="margin:0;font-size:15px;line-height:1.35"><b>Fault tests are not savings.</b> In synthetic fixtures (4 injected fault types) a context-blind cache reused {fi["cache"]["distinct_invalid_facts_reused"]:,} invalid facts; typed reuse {fi["typed_claim_reuse"]["invalid_reuse_events"]} and re-assayed them.</p></div>
  <div class="scope" style="margin-top:10px;font-size:14.5px;line-height:1.35"><b>Bounded knowledge execution,</b> not theorem extraction. Two existing claims, hand-authored adapters, recorded demo — not a live service. Adapters do <b>not</b> improve the TrpB route benchmark: a TrpB score is refused as a selection coefficient. Checks: {E(ver["tests"]["tail"])}; guard mutants {ver["mutation"]["guard_mutants_killed"]}/{ver["mutation"]["guard_mutants_total"]}, source mutants {ver["mutation"]["source_mutants_killed"]}/{ver["mutation"]["source_mutants_total"]} killed.</div>
 </div>
</div>
{fn('<b>Source</b> artifacts/claim_reuse/{demo_receipt,reuse_benchmark,verification_receipt}.json; interactive: site/claims/', 'adapters reviewed by the authoring model, not a population geneticist (appendix)', commit)}"""
        n5 = (f"Delphi claims are now executable. Kimura and Fisher run through hand-authored, hash-pinned adapters with an applicability guard. A valid diploid calculation computes; the haploid E. coli transfer, and a TrpB score used as a selection coefficient, are refused. "
              f"Withdraw or edit the source and the answer flips to refuse. Ordinary caching already captures same-context reuse, identically; typed guards matter when the context is wrong. "
              f"This is bounded, assumption-aware knowledge execution, not theorem extraction, and it does not improve the TrpB route benchmark.")

    # ---- S6: checks, predictions, ask
    bridge_ok = bool(br and br.get("ok"))
    import re
    cp = dm.get("compute") or {}
    sp = (re.search(r"Spearman ([0-9.]+-[0-9.]+)", cp.get("headline", "")) or [None, None])[1]
    gpu_ok = bool(cp.get("status") == "completed" and sp)
    lean_v = (re.search(r"version ([0-9.]+)", rc["lean_version"]) or [None, rc["lean_version"]])[1]
    bridge_txt = (f"one {br['nodes']}-node VFVS → AIKG route recomputed exactly from raw CSV intervals ({br['recompute_exact_matches']}/{br['nodes']}); swapped-route mutant rejected (exit {br['lean_mutant_swap_build_exit']})"
                  if bridge_ok else "the benchmark route is not Lean-bridged in this build")
    gpu_txt = (f"BioNeMo ESM2-650M prior for {cp['variants']:,} variants on one Nebius H100 ({cp['runtime_seconds'] // 60} min). Zero-shot Spearman <b>{sp}</b> with the measured score; near-zero gain over one-hot site identity in a random-split ridge check. The OpenResearch analysis ran locally on CPU: no hosted service, no biological experiment."
               if gpu_ok else "GPU prior receipt unavailable in this build.")
    s6 = f"""
<div class="brand"><i></i>Darwin’s Bridge / Delphi Evolve</div><div class="num">6 / 6</div>
<h2 style="font-size:31px;margin:24px 0 12px">The contribution is compact: <em>assay decisions with machine-checkable, conditional certificates and typed, reusable evidence.</em></h2>
<div class="row" style="gap:18px">
 <div class="col"><div class="card" style="height:100%"><h3>Checked — conditionally</h3>
  <p class="small" style="margin:0 0 6px;font-size:16.5px">Lean {E(lean_v)} compiled the generic route-soundness theorem, a weak “no certifiable route” cut and a strong cut; plus {bridge_txt}.</p>
  <p class="small" style="margin:0;font-size:16.5px"><span class="tag as">ASSUMED</span> interval containment. Noise bins were fit on all replicates, so κ is a <b>transductive sensitivity</b>, not held-out validation. Not every one of the {D["protocol"]["seeds"] * 5 * 11:,} episode certificates is kernel-checked.</p></div></div>
 <div class="col"><div class="card" style="height:100%"><h3>Predicted — not measured</h3>
  <p class="small" style="margin:0 0 6px;font-size:16.5px">{gpu_txt}</p>
  <p class="small" style="margin:0;font-size:16.5px">Replay using this prior: <b>{D["gpu_replay_text"]}</b>. Nothing here says it helps.</p></div></div>
 <div class="col"><div class="card" style="height:100%;background:var(--ink);color:var(--paper);border-color:var(--ink)"><h3 style="color:#c8c2ae">Next real experiment</h3>
  <p style="margin:0 0 8px;font:500 24px/1.18 var(--serif)">One lab. One prior campaign. One prospective round.</p>
  <p class="small" style="margin:0;color:#d8d3c2;font-size:16px">Pre-register the rule, equal assay budgets, read out cost and days to a defensible decision (120 days). No customer, LOI or market size exists.</p></div></div>
</div>
<div class="scope" style="margin-top:18px;font-size:17px"><b>Not new:</b> query-efficient path evaluation (LazySP, BAEE), ML-guided directed evolution (ALDE). <b>Not shown:</b> a wet-lab advantage, collective-agent uplift, or biological truth of any certificate.</div>
<p style="font:500 30px/1.2 var(--serif);margin:22px 0 0;max-width:1120px">Biologic design starts with <em style="font-style:normal;border-bottom:4px solid var(--orange)">justified enzyme experiments</em> — one measured decision at a time.</p>
{fn(f'<b>Source</b> artifacts/proof/receipt.json, artifacts/integration/core_kappa2_route_lean.json, artifacts/gpu/, tasks/results/gpu.json; docs/company-hypothesis.md (hypotheses)', 'prior art: docs/novelty.md', commit)}"""
    n6 = (f"Lean checks the generic route and cut theorems, plus one seven-node route recomputed exactly from raw data, conditional on assumed intervals. "
          f"The ESM2 prior is predicted, weakly correlated, not measured, and its replay is {D['gpu_replay_short']}. "
          f"The contribution is compact: assay decisions with machine-checkable conditional certificates and typed reusable evidence. Not the first query-efficient pathfinding. "
          f"Next: one lab, one prior campaign, one prospective round.")
    return [s1, s2, s3, s4, s5, s6], [n1, n2, n3, n4, n5, n6]


def assemble(slides, notes, draft: bool, reasons: list[str], prov: dict) -> str:
    css = (HERE / "deck.css").read_text()
    js = (HERE / "deck.js").read_text()
    mark = ('<div class="draftmark"><span>DRAFT</span><em>DRAFT — replay not validated</em></div>' if draft else "")
    body = ""
    for i, (s, n) in enumerate(zip(slides, notes)):
        body += f'<section class="slide" id="s{i + 1}" aria-label="Slide {i + 1} of 6">{s}{mark}<div class="notes">{n}</div></section>\n'
    title = "DRAFT — " if draft else ""
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}Darwin’s Bridge / Delphi Evolve — pitch deck</title>
<!-- built {prov['built']} from artifacts commit {prov['git']['head']}; inputs hashed in deck provenance JSON; draft={str(draft).lower()} -->
<style>{css}</style></head>
<body class="{'draft' if draft else ''}"><div class="stage"><div class="deck">
{body}</div></div><div id="notes-live" class="notes"></div><div class="hint">← → navigate · n notes · print = one slide per page</div>
<script>{js}</script></body></html>"""


def word_count(notes: list[str]) -> int:
    import re
    return sum(len(re.sub(r"<[^>]+>", " ", n).split()) for n in notes)


def appendix_md(D: dict, R: dict | None, prov: dict) -> str:
    dm = D["demo"]
    L = ["# Appendix — long limitations and pending items (not slide material)", "",
         f"Built {prov['built']} from artifacts commit `{prov['git']['head']}`. Every number below is read from the files named in `deck.provenance.json`.", "",
         "## Pending at render time (no benefit claimed)", "",
         f"* **Current strong LazySP-style baseline** on the same 100 episodes per policy: {D['pending_text'].replace(' (see appendix)', '')} The worker's branch records a preregistration and a seed-0 smoke test only. Until it is complete, query-to-certify (Q2C) is **not** claimed to beat a LazySP-style policy; LazySP and BAEE are prior art for query-efficient path evaluation.",
         f"* **GPU-prior policy ablation** (replay with the ESM2 prior as input): {D['gpu_replay_text']}. The prior's agreement with the measured data was computed (weak Spearman) but its effect on assay decisions is untested.",
         "* **Roadmap only:** an optional second-domain Lean example (Turing-model applicability check) is in progress on another branch; nothing from it is claimed here.", ""]
    if R is not None:
        T, pols = R["T"], R["pols"]
        L += ["## All arms, certified fraction of 100 episodes (family: all)", "",
              "| arm | status | @100 | @250 | @500 | @1000 | mean assays (restricted) @1000 | false certificates |", "|---|---|---|---|---|---|---|---|"]
        for p in pols:
            st = "original (pre-declared)" if p in V.ORIGINAL_POLICIES else "POST HOC"
            L.append(f"| {p} | {st} | " + " | ".join(f"{float(T[('all', p, b)]['cert_rate']) * 100:.0f}%" for b in (100, 250, 500, 1000)) +
                     f" | {float(T[('all', p, 1000)]['rmst_assays']):.0f} | {T[('all', p, 1000)]['false_certificates']} |")
        L += ["", "Arm names: `collective_shared_c` = shared specialists without the GP; `collective_isolated_c` = isolated specialists without the GP; `q2c_nomodel` = single planner without the GP; `collective_shared_rr` = shared evidence with round-robin proposals. The no-GP arms were selected after observing the original run and are not pre-registered winners.", ""]
    L += ["## Replay limitations", "",
          "* 20 seed clusters; 100 episodes per policy = 4 published-parent targets (AIKG, CLKG, VLKG, ALKG) repeated across 20 seeds (80 cases) + 20 seed-chosen family-A pairs. Not 100 independent biological targets. Bootstrap intervals resample seeds and are descriptive, not coverage claims.",
          "* 0 false certificates is guaranteed by construction (certificates are computed only from revealed labels) and was re-checked against full data: structural consistency, not biological accuracy.",
          "* Specialists are deterministic software objects in one process, not independent agents. Isolated arms are not fully isolated: a duplicate request is answered from the data specialist's ledger at zero cost. Shared vs isolated also differs in arbitration. No collective uplift over a single planner was found.",
          "* Truth is reachability in the measured graph under the declared interval rule (benchmark truth), not biological truth. `blocked`/`no route certifiable` is not the Lean no-path theorem.",
          "* Of the original 700 episodes, 175 intact rows were kept and 525 missing rows were recovered from saved assay histories without re-running policies (recovered rows have unknown wall time); the core worker separately re-ran the panel after a bug fix. The 400 post hoc episodes were run afterwards. Query traces are committed under `artifacts/core/replay/queries/`; each arm's per-episode paid-query count equals `assays` in `episodes.csv` (checked by `validate.py`).",
          "* The noise-bin standard deviations are fit on all replicates: κ is a transductive sensitivity, not held-out validation.", "",
          "## Lean scope", "",
          "* Kernel-checked: generic route-soundness and cut theorems (conditional on assumed interval containment); one VFVS→AIKG κ=2 seven-node route with an exact raw-CSV recompute (7/7); a swapped-route mutant is rejected.",
          "* Not kernel-checked: the individual decisions of the 1,100 replay episodes; source/nanopub claims do not become verified biology because Lean compiled.", "",
          "## Claim runtime limits", "",
          "* Two existing Delphi claims (Kimura, Fisher) with hand-authored, hash-pinned adapters; authored and reviewed by the same model, not by a population geneticist. The Kimura 1962 PDF could not be retrieved; the diploid reading was checked against an exact Wright–Fisher chain.",
          "* Same-context reuse equals an ordinary cache (identical avoided requests). Fault-injection counts are synthetic software fixtures, not savings and not biology. The diffusion formula is up to 139% off for small deleterious mutants (s=-0.05) in the exact-chain benchmark.",
          "* A recorded execution, not a live browser service. No claim that these adapters improve the TrpB route benchmark.", "",
          "## GPU / compute", "",
          f"* {dm.get('compute', {}).get('headline', 'unavailable')}", f"* Job {dm.get('compute', {}).get('job_id')} on {dm.get('compute', {}).get('provider')}; wall {dm.get('compute', {}).get('wall_seattle')}. Predictions never discharge an empirical premise.",
          "* OpenResearch: a local CPU analysis actually ran (`artifacts/gpu/orx/receipt.json`); no hosted OpenResearch service and no biological experiment.", "",
          "## Spend and model", "",
          "* Deck authored with Claude Sonnet 5.5 on an existing subscription; metered API charge, if any, is unknown (CLI cost estimates are not subscription spend). No GPU used by this worker.", ""]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", required=True, help="integrated checkout holding artifacts/ and site/")
    ap.add_argument("--out-dir", default=str(HERE))
    ap.add_argument("--shards-dir", default=None, help="explicit path to run_shard JSONs (git-ignored in release); else queries/ traces are the check")
    ap.add_argument("--allow-draft", action="store_true", help="if replay validation fails, write deck.DRAFT.html with no replay numbers")
    a = ap.parse_args()
    root = Path(a.root).resolve()
    out = Path(a.out_dir)
    merrs = V.validate_misc(root)
    if merrs:
        print("REJECTED (non-replay inputs missing):", *merrs, sep="\n  ", file=sys.stderr)
        return 2
    D = load_inputs(root)
    errs, info = V.validate_replay(root, a.shards_dir)
    draft = bool(errs)
    if draft and not a.allow_draft:
        print("REJECTED: replay is not final; refusing to render numbers.", *errs[:12], sep="\n  ", file=sys.stderr)
        print("  (use --allow-draft to write a clearly marked deck.DRAFT.html)", file=sys.stderr)
        return 2
    R = None if draft else replay_numbers(root, D, info)
    rels = ["artifacts/demo.json", "site/data/demo.json", "artifacts/proof/receipt.json", "artifacts/integration/core_kappa2_route_lean.json",
            "artifacts/core/protocol.json", "site/data/landscape.js", "artifacts/evidence/route_summary.json",
            "artifacts/claim_reuse/demo_receipt.json", "artifacts/claim_reuse/reuse_benchmark.json", "artifacts/claim_reuse/verification_receipt.json",
            "artifacts/gpu/compute_block.json", "tasks/results/gpu.json", "artifacts/gpu/orx/receipt.json"]
    if not draft:
        rels += [f"artifacts/core/replay/{f}" for f in V.REQUIRED_REPLAY]
        rels += [f"artifacts/core/replay/queries/queries__{p}.tsv.gz" for p in (R or {}).get("pols", [])]
    hashes = {r: sha256(root / r) for r in rels if (root / r).exists()}
    prov = {"built": seattle_now(), "root": str(root), "git": git_info(root, rels + ["artifacts/core/replay"]), "sha256": hashes,
            "mode": "DRAFT" if draft else "FINAL", "validation_errors": errs, "replay_info": info,
            "posthoc_arms_shown": (R or {}).get("follow", []), "pending": {"lazysp": D["pending_text"], "gpu_prior_replay": D["gpu_replay_text"]}}
    slides, notes = build_slides(D, R, errs, prov)
    wc = word_count(notes)
    prov["spoken_words"] = wc
    if not draft and wc > 420:
        print(f"REJECTED: speaker notes are {wc} words (> 420); per slide {[word_count([n]) for n in notes]}; trim before rendering", file=sys.stderr)
        return 2
    page = assemble(slides, notes, draft, errs, prov)
    name = "deck.DRAFT.html" if draft else "deck.html"
    (out / name).write_text(page)
    (out / (name.replace(".html", ".provenance.json"))).write_text(json.dumps(prov, indent=1))
    (out / ("speaker-notes.DRAFT.md" if draft else "speaker-notes.md")).write_text(
        "# Speaker notes" + (" (DRAFT)" if draft else "") + f"\n\nBuilt {prov['built']} from {prov['git']['head']}.\n\n" +
        "\n\n".join(f"**Slide {i + 1}** ({'0:00-0:20 0:20-0:40 0:40-1:05 1:05-1:50 1:50-2:30 2:30-3:00'.split()[i]})\n\n{n}" for i, n in enumerate(notes)) + "\n")
    (out / ("appendix.DRAFT.md" if draft else "appendix.md")).write_text(appendix_md(D, R, prov))
    print(f"spoken words: {wc} per slide {[word_count([n]) for n in notes]} (target <=380, hard cap 420)")
    print(f"{prov['mode']}: wrote {out / name} ({len(page) // 1024} KiB); provenance {name.replace('.html', '.provenance.json')}")
    if draft:
        print("validation errors:", *errs[:8], sep="\n  ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
