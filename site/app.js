/* Darwin's Bridge — UI. Real TrpB measurements via data/landscape.js; integration data via
 * data/demo.json (core output, optional) and data/evidence.json (Delphi records + nanopub drafts).
 * Anything absent is displayed as unavailable; no result number is hardcoded here. */
(function () {
  "use strict";
  const L = window.TrpbLib;
  const $ = (s, r) => (r || document).querySelector(s);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const fmt = (x, d) => (x === null || x === undefined || Number.isNaN(x) ? "unknown" : Number(x).toFixed(d === undefined ? 4 : d));
  const POS = [183, 184, 227, 228];

  if (!window.TRPB_LANDSCAPE) {
    $("#ledger").innerHTML = '<li class="no"><span class="st">✕</span>landscape.js did not load — nothing to show</li>';
    return;
  }
  const D = L.decode(window.TRPB_LANDSCAPE);
  const state = {
    start: L.idxOf("VFVS"), target: L.idxOf("AIKG"), eps: 0, mode: "envelope", lens: "growth",
    sel: { node: L.idxOf("VFVS"), step: null }, baseRoute: null, decision: null, reach: null,
    demo: null, ev: null, tab: "decision", maxEps: null,
  };
  const presets = [
    ["VFVS", "AIKG", "parent → highest measured"],
    ["VFVS", "CLKG", "parent → CLKG"],
    ["VFVS", "VLKG", "parent → VLKG"],
  ];

  /* ---------------- colour ramps ---------------- */
  function ramp(stops) {
    const lut = new Uint8ClampedArray(256 * 3);
    for (let i = 0; i < 256; i++) {
      const t = i / 255 * (stops.length - 1), k = Math.min(Math.floor(t), stops.length - 2), f = t - k;
      for (let c = 0; c < 3; c++) lut[i * 3 + c] = stops[k][c] + (stops[k + 1][c] - stops[k][c]) * f;
    }
    return lut;
  }
  const hex = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
  const RAMPS = {
    growth: ramp(["#f3efe4", "#cfe5df", "#86bdb6", "#3a8a92", "#17566f", "#0a2a45"].map(hex)),
    disagree: ramp(["#f3efe4", "#f6dcb3", "#eba55a", "#c4621a", "#7d3410", "#3b1708"].map(hex)),
    reads: ramp(["#f3efe4", "#e1d7ee", "#b3a0d8", "#7b5fb8", "#4b2f8a", "#24114d"].map(hex)),
  };
  const LENS = {
    growth: { f: (i) => Math.pow(Math.max(0, Math.min(1, D.mean[i] / 0.36)), 0.55), label: "growth rate μ (bg-subtracted)", lo: "0", hi: "0.36" },
    disagree: { f: (i) => Math.pow(Math.min(1, (D.mx[i] - D.mn[i]) / 0.05), 0.6), label: "|replicate 1 − replicate 2|", lo: "0", hi: "≥0.05" },
    reads: { f: (i) => 1 - Math.log(1 + D.reads[i]) / Math.log(128), label: "fewer input reads (min of 2 replicates)", lo: "≥127", hi: "0" },
  };

  /* ---------------- map canvas ---------------- */
  const cv = $("#map"), ctx = cv.getContext("2d");
  const off = document.createElement("canvas"); off.width = off.height = 400;
  const octx = off.getContext("2d");
  const M = 26; // css px margin for axis letters
  let geo = { size: 600, scale: 1.5 };

  const cellXY = (i) => ({ x: (Math.floor(i / 20) % 20) * 20 + (i % 20), y: Math.floor(i / 8000) * 20 + (Math.floor(i / 400) % 20) });
  const xyCell = (x, y) => {
    const a1 = Math.floor(y / 20), a2 = y % 20, a3 = Math.floor(x / 20), a4 = x % 20;
    return a1 * 8000 + a2 * 400 + a3 * 20 + a4;
  };

  function paintOffscreen() {
    const img = octx.createImageData(400, 400), px = img.data;
    const lens = LENS[state.lens], lut = RAMPS[state.lens];
    const dim = $("#t-reach").checked && state.reach;
    for (let y = 0; y < 400; y++) for (let x = 0; x < 400; x++) {
      const i = xyCell(x, y), o = (y * 400 + x) * 4;
      let r, g, b;
      if (!D.measured[i]) { r = 255; g = 255; b = 255; }
      else { const k = Math.max(0, Math.min(255, Math.round(lens.f(i) * 255))) * 3; r = lut[k]; g = lut[k + 1]; b = lut[k + 2]; }
      if (dim && !state.reach[i] && D.measured[i]) { r = r * 0.38 + 243 * 0.62; g = g * 0.38 + 239 * 0.62; b = b * 0.38 + 228 * 0.62; }
      px[o] = r; px[o + 1] = g; px[o + 2] = b; px[o + 3] = 255;
    }
    octx.putImageData(img, 0, 0);
  }

  const css = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();

  function drawMap() {
    const rect = cv.parentElement.getBoundingClientRect();
    const cssW = Math.max(280, Math.floor(rect.width)), dpr = window.devicePixelRatio || 1;
    cv.style.height = cssW + "px";
    cv.width = Math.round(cssW * dpr); cv.height = Math.round(cssW * dpr);
    const s = (cssW - M) / 400;
    geo = { size: cssW, scale: s, dpr };
    const c = ctx; c.setTransform(dpr, 0, 0, dpr, 0, 0);
    c.clearRect(0, 0, cssW, cssW);
    c.imageSmoothingEnabled = false;
    c.drawImage(off, M, M, 400 * s, 400 * s);
    // tile grid
    c.strokeStyle = "rgba(21,32,43,.18)"; c.lineWidth = 0.5;
    c.beginPath();
    for (let t = 0; t <= 20; t++) { const p = M + t * 20 * s; c.moveTo(p, M); c.lineTo(p, M + 400 * s); c.moveTo(M, p); c.lineTo(M + 400 * s, p); }
    c.stroke();
    // axis letters
    c.fillStyle = css("--muted"); c.font = "600 10px " + css("--mono"); c.textAlign = "center"; c.textBaseline = "middle";
    for (let t = 0; t < 20; t++) {
      const p = M + (t * 20 + 10) * s;
      c.fillText(L.AA[t], p, M - 12); c.fillText(L.AA[t], M - 12, p);
    }
    c.font = "500 9px " + css("--sans");
    c.fillText("227 →", M + 400 * s / 2, 7); c.save(); c.translate(7, M + 400 * s / 2); c.rotate(-Math.PI / 2); c.fillText("183 →", 0, 0); c.restore();
    // unknown markers
    if ($("#t-unk").checked) {
      c.strokeStyle = css("--unknown"); c.lineWidth = 1; c.globalAlpha = 0.7;
      for (let i = 0; i < L.N; i++) if (!D.measured[i]) { const p = pt(i); c.beginPath(); c.arc(p.x, p.y, 2.2, 0, 6.2832); c.stroke(); }
      c.globalAlpha = 1;
    }
    drawRoutes(c);
    // selection
    if (state.sel.node !== null) {
      const p = pt(state.sel.node);
      c.strokeStyle = css("--ink"); c.lineWidth = 2; c.strokeRect(p.x - 5, p.y - 5, 10, 10);
    }
  }
  function pt(i) { const q = cellXY(i); return { x: M + (q.x + 0.5) * geo.scale, y: M + (q.y + 0.5) * geo.scale }; }

  function drawRoutes(c) {
    // core route overlay (from demo.json), if any
    const cr = coreRoute();
    if (cr) polyline(c, cr, css("--core"), false, true);
    const d = state.decision;
    if (state.baseRoute) {
      // The route chosen at eps=0 ("tempting route"); steps that fail at the current assumption are marked.
      const br = state.baseRoute;
      polyline(c, br, css("--route"), true, false);
    }
    if (d && d.route && (d.status === "open" || d.status === "undetermined")) polyline(c, d.route, css("--route"), false, false, true);
  }

  function polyline(c, nodes, color, ghostBase, dashed, current) {
    c.lineJoin = "round";
    for (let k = 0; k + 1 < nodes.length; k++) {
      const a = pt(nodes[k]), b = pt(nodes[k + 1]);
      const m = L.margin(D, nodes[k], nodes[k + 1], state.eps, state.mode);
      const fail = m !== null && m < 0;
      const unk = m === null;
      c.beginPath(); c.moveTo(a.x, a.y); c.lineTo(b.x, b.y);
      if (ghostBase) {
        c.strokeStyle = fail ? css("--break") : color; c.globalAlpha = fail ? 1 : 0.45; c.lineWidth = fail ? 2.5 : 1.5;
        c.setLineDash(fail ? [6, 4] : []);
      } else { c.strokeStyle = color; c.globalAlpha = 1; c.lineWidth = current ? 3 : 1.8; c.setLineDash(dashed || unk ? [4, 3] : []); }
      c.stroke(); c.setLineDash([]); c.globalAlpha = 1;
      if (ghostBase && fail) { // X marker at the midpoint of the failing step
        const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
        c.strokeStyle = css("--break"); c.lineWidth = 2.4; c.beginPath();
        c.moveTo(mx - 5, my - 5); c.lineTo(mx + 5, my + 5); c.moveTo(mx + 5, my - 5); c.lineTo(mx - 5, my + 5); c.stroke();
      }
    }
    if (ghostBase) return;
    nodes.forEach((n, k) => {
      const p = pt(n);
      c.beginPath(); c.arc(p.x, p.y, current ? 5.5 : 4, 0, 6.2832);
      c.fillStyle = D.measured[n] ? "#fff" : css("--unknown"); c.fill();
      c.strokeStyle = color; c.lineWidth = 2; c.stroke();
      if (current) { c.fillStyle = css("--ink"); c.font = "700 10px " + css("--mono"); c.textAlign = "left"; c.textBaseline = "bottom"; c.fillText(String(k), p.x + 7, p.y - 4); }
    });
  }

  function coreRoute() {
    const d = state.demo;
    if (!d || !Array.isArray(d.routes) || !d.routes.length || !Array.isArray(d.nodes)) return null;
    const byId = new Map(d.nodes.map((n) => [n.id, n.genotype]));
    const r = d.routes[state.coreRouteIdx || 0];
    const ids = (r.nodes || []).map((n) => L.idxOf(byId.get(n) || (typeof n === "string" ? n : "")));
    return ids.every((i) => i >= 0) && ids.length > 1 ? ids : null;
  }

  /* ---------------- tile inspector ---------------- */
  const tcv = $("#tilecv"), tctx = tcv.getContext("2d");
  function drawTile() {
    const n = state.sel.node ?? state.start;
    const a1 = Math.floor(n / 8000) % 20, a3 = Math.floor(n / 20) % 20;
    $("#tile-title").textContent = `V183 = ${L.AA[a1]}, 227 = ${L.AA[a3]}`.replace("V183", "183");
    const w = Math.min(520, Math.floor(tcv.parentElement.getBoundingClientRect().width)), dpr = window.devicePixelRatio || 1;
    tcv.style.height = w + "px"; tcv.width = Math.round(w * dpr); tcv.height = Math.round(w * dpr);
    const c = tctx, m = 20, cs = (w - m) / 20;
    c.setTransform(dpr, 0, 0, dpr, 0, 0); c.clearRect(0, 0, w, w);
    const lens = LENS[state.lens], lut = RAMPS[state.lens];
    c.font = "600 10px " + css("--mono"); c.textAlign = "center"; c.textBaseline = "middle";
    const route = new Set((state.decision && state.decision.route) || []);
    for (let a2 = 0; a2 < 20; a2++) for (let a4 = 0; a4 < 20; a4++) {
      const i = a1 * 8000 + a2 * 400 + a3 * 20 + a4, x = m + a4 * cs, y = m + a2 * cs;
      if (!D.measured[i]) { c.fillStyle = "#fff"; c.fillRect(x, y, cs - 1, cs - 1); c.strokeStyle = css("--unknown"); c.strokeRect(x + 1.5, y + 1.5, cs - 4, cs - 4); }
      else { const k = Math.max(0, Math.min(255, Math.round(lens.f(i) * 255))) * 3; c.fillStyle = `rgb(${lut[k]},${lut[k + 1]},${lut[k + 2]})`; c.fillRect(x, y, cs - 1, cs - 1); }
      if (route.has(i) || i === state.start || i === state.target) { c.strokeStyle = css("--route"); c.lineWidth = 2.5; c.strokeRect(x + 1, y + 1, cs - 3, cs - 3); c.lineWidth = 1; }
      if (i === state.sel.node) { c.strokeStyle = css("--ink"); c.lineWidth = 2; c.strokeRect(x, y, cs - 1, cs - 1); c.lineWidth = 1; }
      if (cs > 18 && D.measured[i]) { const lum = (lens.f(i)); c.fillStyle = lum > 0.5 ? "#fff" : "#26323d"; c.fillText(L.AA[a2] + L.AA[a4], x + cs / 2, y + cs / 2); }
    }
    c.fillStyle = css("--muted");
    for (let t = 0; t < 20; t++) { c.fillText(L.AA[t], m + t * cs + cs / 2, 9); c.fillText(L.AA[t], 9, m + t * cs + cs / 2); }
    tcv._geo = { m, cs, a1, a3 };
  }
  tcv.addEventListener("click", (e) => {
    const r = tcv.getBoundingClientRect(), g = tcv._geo; if (!g) return;
    const a4 = Math.floor((e.clientX - r.left - g.m) / g.cs), a2 = Math.floor((e.clientY - r.top - g.m) / g.cs);
    if (a2 >= 0 && a2 < 20 && a4 >= 0 && a4 < 20) selectNode(g.a1 * 8000 + a2 * 400 + g.a3 * 20 + a4);
  });

  /* ---------------- interaction on map ---------------- */
  function cellAt(e) {
    const r = cv.getBoundingClientRect(), x = Math.floor((e.clientX - r.left - M) / geo.scale), y = Math.floor((e.clientY - r.top - M) / geo.scale);
    return x >= 0 && x < 400 && y >= 0 && y < 400 ? xyCell(x, y) : -1;
  }
  const tip = $("#tip");
  cv.addEventListener("mousemove", (e) => {
    const i = cellAt(e);
    if (i < 0) { tip.hidden = true; return; }
    const r = cv.getBoundingClientRect();
    tip.hidden = false; tip.style.left = e.clientX - r.left + "px"; tip.style.top = e.clientY - r.top + "px";
    tip.textContent = D.measured[i] ? `${L.genoOf(i)}  μ ${fmt(D.mean[i], 3)}  (${fmt(D.mn[i], 3)}…${fmt(D.mx[i], 3)})` : `${L.genoOf(i)}  not measured`;
  });
  cv.addEventListener("mouseleave", () => { tip.hidden = true; });
  cv.addEventListener("click", (e) => { const i = cellAt(e); if (i >= 0) selectNode(i); });

  function selectNode(i) { state.sel = { node: i, step: null }; renderEvidence(); redraw(false); setTab("evidence"); }
  function selectStep(k) {
    const r = state.decision && state.decision.route; if (!r) return;
    state.sel = { node: r[k], step: k };
    renderEvidence(); renderDecisionSteps(); redraw(false); setTab("evidence");
  }

  /* ---------------- decision ---------------- */
  function compute() {
    const key = state.start + ":" + state.target + ":" + state.mode;
    if (state._baseKey !== key) {
      const b = L.decide(D, state.start, state.target, 0, state.mode);
      state.baseRoute = b.route || null; state._baseKey = key; state.maxEps = null; state._maxPending = true;
    }
    state.decision = L.decide(D, state.start, state.target, state.eps, state.mode);
    const r = L.search(D, state.start, -1, state.eps, state.mode, false);
    state.reach = new Uint8Array(L.N);
    for (let k = 0; k < r.reached; k++) state.reach[r.queueOrder[k]] = 1;
    state.reachCount = r.reached;
  }
  let maxTimer = null;
  function scheduleMaxEps() {
    clearTimeout(maxTimer);
    if (!state._maxPending) return;
    maxTimer = setTimeout(() => {
      state.maxEps = L.maxEps(D, state.start, state.target, state.mode); state._maxPending = false; renderDecision();
    }, 120);
  }

  function nodeLabel(i) { const g = L.genoOf(i); return g; }
  function mutLabel(a, b) {
    for (let p = 0; p < 4; p++) { const x = Math.floor(a / L.W[p]) % 20, y = Math.floor(b / L.W[p]) % 20; if (x !== y) return `${L.AA[x]}${POS[p]}${L.AA[y]}`; }
    return "";
  }

  function renderDecision(force) {
    const el = $("#p-decision"), d = state.decision;
    const eps = state.eps, tName = L.genoOf(state.target), sName = L.genoOf(state.start);
    const unmeasured = !D.measured[state.start] || !D.measured[state.target];
    let verdict = "";
    if (unmeasured) {
      verdict = `<div class="verdict undetermined"><span class="tag">Undetermined</span><h4>Start or target is not measured</h4><p>No genotype in the source table backs this endpoint. Pick a measured genotype, or this is an assay request for the endpoint itself.</p></div>`;
    } else if (d.status === "open") {
      verdict = `<div class="verdict open"><span class="tag">Open · measured subgraph</span><h4>${d.route.length - 1}-step route, every step admitted</h4>
        <p>Under the assumptions below, each step has a lower bound at or above the previous genotype’s upper bound, using only measured genotypes. This is a statement about this finite graph and these measurements — not about biology at large.</p></div>`;
    } else if (d.status === "undetermined") {
      verdict = `<div class="verdict undetermined"><span class="tag">Undetermined</span><h4>A route exists only through unmeasured genotypes</h4>
        <p>No measured-only route survives. If ${d.unknownNodes.map((n) => `<code>${L.genoOf(n)}</code>`).join(", ")} turned out to be good enough, a ${d.route.length - 1}-step route would exist. <strong>Assay request:</strong> measure ${d.unknownNodes.map((n) => L.genoOf(n)).join(", ")}.</p></div>`;
    } else {
      const nr = d.nearest;
      verdict = `<div class="verdict blocked"><span class="tag">Blocked · in this declared graph</span><h4>No admissible route — even if every unmeasured genotype were perfect</h4>
        <p>Everything reachable from ${esc(sName)} under these assumptions is a closed set of <strong>${d.closedSetSize.toLocaleString()}</strong> genotypes; all <strong>${d.boundaryEdges.toLocaleString()}</strong> single-substitution edges leaving it are rejected.${nr ? ` Nearest miss: <code>${L.genoOf(nr.from)} → ${L.genoOf(nr.to)}</code> misses by ${fmt(-nr.margin, 4)}.` : ""}</p>
        <p class="hint">This is a certificate about the measured four-residue graph at this assumed error bound. It does not show that no evolutionary path exists in the full protein sequence space.</p></div>`;
    }
    const brk = (state.maxEps === null && state._maxPending) ? "computing…"
      : state.maxEps === null ? "n/a" : state.maxEps === -Infinity ? "no measured-only route exists at any assumption" : `ε ≤ ${(Math.floor(state.maxEps * 1e4) / 1e4).toFixed(4)} (rounded down)`;
    const direct = L.directOrderings(D, state.start, state.target, eps, state.mode);
    const dAcc = direct.filter((x) => x.accepted).length;
    const cand = (d.status === "blocked" || d.status === "undetermined") && !unmeasured ? L.assayCandidates(D, state.start, state.target, eps, state.mode, 5) : null;

    const ctl = `
      <h3>Start → target</h3>
      <div class="row"><input id="in-s" type="text" maxlength="4" value="${sName}" aria-label="Start genotype"><span aria-hidden="true">→</span><input id="in-t" type="text" maxlength="4" value="${tName}" aria-label="Target genotype"><button class="btn" id="go">Set</button></div>
      <div class="presets">${presets.map((p, k) => `<button class="btn" data-pre="${k}" title="${esc(p[2])}">${p[0]}→${p[1]}</button>`).join("")}</div>
      <p class="hint">Residues: ${POS.join(" · ")}. Parent VFVS is the study’s starting enzyme; AIKG is the highest measured variant in the table.</p>
      <div class="slider-head"><label for="eps">Assumed error bound ε on every measurement <span class="chip unknown">assumed</span></label><output id="eps-out">${fmt(eps, 4)}</output></div>
      <input id="eps" type="range" min="0" max="0.03" step="0.0005" value="${eps}" aria-describedby="eps-hint">
      <p id="eps-hint" class="hint">Not an estimated confidence level. Each measurement is allowed to be wrong by ±ε beyond the range spanned by its two replicates. ε=0 uses only the replicate range.</p>
      <div class="row"><label><input type="radio" name="mode" value="envelope" ${state.mode === "envelope" ? "checked" : ""}> replicate range</label>
      <label><input type="radio" name="mode" value="point" ${state.mode === "point" ? "checked" : ""}> replicate mean (point values)</label></div>
      <div class="row"><button class="btn primary" id="challenge">Challenge the assumption ▶</button><button class="btn" id="reset">Reset ε</button></div>`;
    const dyn = `${verdict}
      <table class="kv"><tr><th>Breaks beyond</th><td>${brk}</td></tr>
        <tr><th>Reachable from start</th><td>${state.reachCount.toLocaleString()} measured genotypes</td></tr>
        <tr><th>Direct 4-substitution orderings admitted</th><td>${dAcc} of ${direct.length}</td></tr></table>
      <div id="steps-slot"></div>
      ${cand ? `<h3>Which assay next?</h3><p class="hint">${cand.total} unmeasured genotype(s) neighbour the reachable region${cand.total ? "; nearest the target first (a heuristic ordering, not a computed value of information)" : ". None, so no single new assay of an unmeasured genotype can reopen a route — the next question would concern the assumption itself, e.g. a higher-depth replicate of the nearest-miss step"}.</p>
        ${cand.top.length ? `<ul class="mini-list">${cand.top.map((c) => `<li><code>${L.genoOf(c.node)}</code> (neighbour of <code>${L.genoOf(c.via)}</code>, Hamming ${c.d} from target)</li>`).join("")}</ul>` : ""}` : ""}
      <details><summary>The ${direct.length} direct orderings (shortest possible routes)</summary>
        <table class="mini"><tr><th>Order of substitutions</th><th>worst margin</th><th></th></tr>
        ${direct.map((x) => `<tr><td>${x.nodes.slice(1).map((n, k) => mutLabel(x.nodes[k], n)).join(" ")}</td><td class="${x.accepted ? "" : "bad"}">${x.worst === null ? "unknown" : fmt(x.worst, 4)}</td><td>${x.accepted ? "admitted" : x.unknown ? "unknown" : "✕ rejected"}</td></tr>`).join("")}</table>
        <p class="hint">Margin = lower bound of the next genotype − upper bound of the current one. Negative means the route passes through a genotype measurably worse than where it came from.</p></details>`;
    if (!$("#dec-ctl") || force) { el.innerHTML = `<div id="dec-ctl">${ctl}</div><div id="dec-dyn"></div>`; bindDecision(); }
    $("#dec-dyn").innerHTML = dyn;
    $("#eps-out").textContent = fmt(eps, 4);
    if (document.activeElement !== $("#eps")) $("#eps").value = eps;
    renderDecisionSteps();
  }

  function renderDecisionSteps() {
    const slot = $("#steps-slot"); if (!slot) return;
    const d = state.decision; const route = d && d.route;
    if (!route) { slot.innerHTML = state.baseRoute ? `<h3>The route that worked at ε=0, now failing</h3>${stepsHtml(state.baseRoute, true)}` : ""; bindSteps(state.baseRoute); return; }
    slot.innerHTML = `<h3>Route</h3>${stepsHtml(route, false)}`; bindSteps(route);
  }
  function stepsHtml(route, ghost) {
    let weakest = -1, wv = Infinity;
    for (let k = 0; k + 1 < route.length; k++) { const m = L.margin(D, route[k], route[k + 1], state.eps, state.mode); if (m !== null && m < wv) { wv = m; weakest = k; } }
    let h = `<ol class="steps">`;
    h += `<li><button data-k="0" ${state.sel.step === null && state.sel.node === route[0] ? 'aria-current="true"' : ""}><span class="n">0</span><span class="g">${L.genoOf(route[0])}<small>start · μ ${fmt(D.mean[route[0]], 3)}</small></span><span class="m"></span></button></li>`;
    for (let k = 0; k + 1 < route.length; k++) {
      const m = L.margin(D, route[k], route[k + 1], state.eps, state.mode), cls = m === null ? "unk" : m < 0 ? "fail" : k === weakest ? "weak" : "";
      h += `<li class="${cls}"><button data-k="${k + 1}" ${state.sel.step === k + 1 ? 'aria-current="true"' : ""}><span class="n">${k + 1}</span><span class="g">${L.genoOf(route[k + 1])}<small>${mutLabel(route[k], route[k + 1])} · μ ${fmt(D.mean[route[k + 1]], 3)}</small></span><span class="m">${m === null ? "unmeasured" : "margin " + fmt(m, 4)}</span></button></li>`;
    }
    return h + "</ol>" + (ghost ? `<p class="hint">Steps marked ✕ no longer satisfy the dominance condition at the current ε.</p>` : "");
  }
  function bindSteps(route) {
    document.querySelectorAll("#steps-slot .steps button").forEach((b) => b.addEventListener("click", () => {
      const k = +b.dataset.k;
      if (state.decision && state.decision.route === route) selectStep(k);
      else { state.sel = { node: route[k], step: null }; renderEvidence(); redraw(false); setTab("evidence"); }
    }));
  }

  function bindDecision() {
    const epsEl = $("#eps");
    epsEl.addEventListener("input", () => { setEps(+epsEl.value); });
    $("#reset").addEventListener("click", () => setEps(0));
    $("#go").addEventListener("click", applyInputs);
    ["#in-s", "#in-t"].forEach((s) => $(s).addEventListener("keydown", (e) => { if (e.key === "Enter") applyInputs(); }));
    document.querySelectorAll("[data-pre]").forEach((b) => b.addEventListener("click", () => {
      const p = presets[+b.dataset.pre]; state.start = L.idxOf(p[0]); state.target = L.idxOf(p[1]); state.sel = { node: state.start, step: null }; recompute(true);
    }));
    document.querySelectorAll("input[name=mode]").forEach((r) => r.addEventListener("change", () => { state.mode = r.value; recompute(true); }));
    $("#challenge").addEventListener("click", challenge);
  }
  function applyInputs() {
    const s = L.idxOf($("#in-s").value.trim()), t = L.idxOf($("#in-t").value.trim());
    if (s < 0 || t < 0 || s === t) { $("#in-s").setAttribute("aria-invalid", s < 0); $("#in-t").setAttribute("aria-invalid", t < 0 || s === t); return; }
    state.start = s; state.target = t; state.sel = { node: s, step: null }; recompute(true);
  }
  function setEps(v) {
    state.eps = Math.round(v * 10000) / 10000;
    compute(); paintOffscreen(); drawMap(); drawTile(); renderDecision(); renderEvidence(); scheduleMaxEps();
  }
  let anim = null;
  function challenge() {
    cancelAnimationFrame(anim);
    const stop = Math.min(0.03, state.maxEps && isFinite(state.maxEps) ? state.maxEps * 1.6 + 0.002 : 0.012);
    state.eps = 0; let t0 = null;
    const step = (ts) => {
      if (t0 === null) t0 = ts; const f = Math.min(1, (ts - t0) / 4200);
      setEps(Math.round(stop * f / 0.0005) * 0.0005);
      if (f < 1) anim = requestAnimationFrame(step);
    };
    anim = requestAnimationFrame(step);
  }

  function recompute(full) {
    state._baseKey = null; compute(); paintOffscreen(); drawMap(); drawTile(); renderDecision(true); renderEvidence(); scheduleMaxEps();
  }
  function redraw(repaint) { if (repaint) paintOffscreen(); drawMap(); drawTile(); }

  /* ---------------- evidence ---------------- */
  function renderEvidence() {
    const el = $("#p-evidence"), meta = D.meta, src = meta.source, n = state.sel.node, st = state.sel.step, route = state.decision && state.decision.route;
    let h = "";
    if (st !== null && route && st > 0) {
      const a = route[st - 1], b = route[st], m = L.margin(D, a, b, state.eps, state.mode), base = L.baseGap(D, a, b, state.mode);
      h += `<h3>Step ${st}: ${L.genoOf(a)} → ${L.genoOf(b)} <span class="aside">${mutLabel(a, b)}</span></h3>
        <div class="card"><p><span class="chip observed">observed</span> Dominance test <code>L(next) ≥ U(current)</code></p>
        <table class="kv"><tr><th>Current ${L.genoOf(a)}</th><td>[${fmt(D.mn[a] - state.eps, 4)}, ${fmt(D.mx[a] + state.eps, 4)}]${state.mode === "point" ? " (point mean ±ε)" : ""}</td></tr>
        <tr><th>Next ${L.genoOf(b)}</th><td>[${fmt(D.mn[b] - state.eps, 4)}, ${fmt(D.mx[b] + state.eps, 4)}]</td></tr>
        <tr><th>Margin</th><td>${m === null ? "unknown (a genotype is unmeasured)" : fmt(m, 4) + (m >= 0 ? " ≥ 0 → admitted" : " < 0 → rejected")}</td></tr>
        <tr><th>Equals</th><td>${base === null ? "—" : fmt(base, 4)} − 2·ε (${fmt(2 * state.eps, 4)})</td></tr></table>
        <p class="hint">Values are the source table’s two replicate columns, shown at 1e-4 resolution. ε is assumed, not measured.</p></div>`;
    }
    h += `<h3>Genotype ${L.genoOf(n)}</h3>${genotypeCard(n)}`;
    const ab = state.start !== n ? `<button class="btn" id="set-s">Set as start</button> ` : "";
    const tb = state.target !== n ? `<button class="btn" id="set-t">Set as target</button>` : "";
    h += `<div class="row">${ab}${tb}</div>`;
    h += `<h3>Source</h3><table class="kv">
      <tr><th>Dataset</th><td class="t"><a href="https://doi.org/${esc(src.dataset_doi)}">${esc(src.dataset_doi)}</a> · ${esc(src.license)}</td></tr>
      <tr><th>Paper</th><td class="t"><a href="https://doi.org/${esc(src.paper_doi)}">${esc(src.paper_doi)}</a></td></tr>
      ${Object.entries(src.files).map(([f, v]) => `<tr><th>${esc(f)}</th><td>sha256 ${esc(v.sha256.slice(0, 16))}…</td></tr>`).join("")}
      <tr><th>Counts</th><td class="t">${meta.counts.measured_non_stop.toLocaleString()} measured · ${meta.counts.unmeasured_cells} unmeasured · ${meta.counts.measured_imputed_overlap} overlap with imputed file · ${meta.counts.stop_containing_rows_excluded.toLocaleString()} stop-containing rows excluded</td></tr>
      <tr><th>Score</th><td class="t">${esc(meta.score.definition)}</td></tr></table>
      <p class="hint">Landscape pack built ${esc(meta.built_seattle)} by <code>${esc(meta.builder)}</code>.</p>`;
    el.innerHTML = h;
    $("#set-s")?.addEventListener("click", () => { state.start = n; recompute(true); });
    $("#set-t")?.addEventListener("click", () => { state.target = n; recompute(true); });
  }
  function genotypeCard(n) {
    const g = L.genoOf(n);
    const resid = [0, 1, 2, 3].map((p) => `${g[p]}${POS[p]}`).join(" ");
    if (!D.measured[n]) {
      const imp = D.unknown[g];
      return `<div class="card"><p><span class="chip unknown">unknown</span> <code>${resid}</code> has no measurement in the source table.</p>
        <p>The source ships a KNN-imputed value${imp === null || imp === undefined ? "" : " (" + fmt(imp, 3) + ", on the source’s max-normalised scale)"}; it is an imputation, never an observation, and is not used for any edge decision here. Edges touching this genotype are <b>unknown</b>.</p></div>`;
    }
    const r1 = D.r1raw[n] / 1e4, r2 = D.r2raw[n] / 1e4, rd = D.reads[n];
    return `<div class="card"><p><span class="chip observed">observed</span> <code>${resid}</code></p>
      <table class="kv"><tr><th>Replicate 1 (μ₁−bg)</th><td>${fmt(r1)}</td></tr><tr><th>Replicate 2 (μ₂−bg)</th><td>${fmt(r2)}</td></tr>
      <tr><th>Mean</th><td>${fmt(D.mean[n])}</td></tr><tr><th>|difference|</th><td>${fmt(D.mx[n] - D.mn[n])}</td></tr>
      <tr><th>Input reads (min of 2)</th><td>${rd >= 127 ? "≥127" : rd}</td></tr><tr><th>Source “active” flag</th><td>${D.active[n] ? "true" : "false"} <span class="hint">(above stop-codon mean + 1.96 SD)</span></td></tr></table>
      ${rd < 20 ? `<p class="hint"><span class="chip unknown">uncertain</span> fewer than 20 input reads: replicate noise is largest in this bin (source-level audit, see docs).</p>` : ""}</div>`;
  }

  /* ---------------- claims / proof / replay ---------------- */
  function renderClaims() {
    const ev = state.ev, el = $("#p-claims");
    if (!ev) { el.innerHTML = `<div class="na">data/evidence.json is not available (static fetch blocked or file missing). Serve this folder over HTTP.</div>`; return; }
    let h = `<h3>Our operational hypothesis</h3><div class="card"><p><span class="chip observed">observed data</span><span class="chip sim">descriptive graph analysis</span></p>
      <p>On the finite measured four-site TrpB graph, is there a single-substitution route from the parent to a high-growth genotype in which every step is admitted under a stated assumed error bound?</p>
      <p class="hint">A narrow statement about a growth-selection proxy on a finite graph. Not about organisms, kcat/KM, or biological impossibility.</p></div>`;
    h += `<h3>Delphi records (motivation / context only)</h3><p class="hint">Queried live from <code>${esc(ev.delphi_endpoint)}</code> at ${esc(ev.delphi_run_utc)}. Local overview: ${ev.overview.local ? ev.overview.local.claims_total : "?"} claims; network: ${ev.overview.network ? ev.overview.network.claims_total : "?"}. The two sources differ; both are kept.</p>`;
    ev.claims.forEach((c) => {
      h += `<div class="card"><p><span class="chip motivation">${esc(c.role)}</span><code>${esc(c.id)}</code></p><p><b>${esc(c.label)}</b></p><p>${esc(c.statement)}</p>
        ${Object.entries(c.sources).map(([s, v]) => `<p class="hint">${esc(s)}: ${v.nanopubs.length ? v.nanopubs.map((x) => esc(x)).join(", ") : "no nanopub listed"}${v.assessments.length ? " · assessments (elicited LLM judgments, not probabilities): " + v.assessments.map((a) => `${esc(a.assessor.replace("delphisci-resolvability-assessor-", ""))} ${fmt(a.score, 3)} ${esc(a.verdict)}`).join("; ") : ""}</p>`).join("")}
        <p class="hint">${esc(c.relation_to_trpb_test)}</p></div>`;
    });
    h += `<h3>Text searches</h3><table class="mini">${ev.searches.map((s) => `<tr><td>“${esc(s.text)}”</td><td>${esc(s.source)}</td><td>${s.hits} hits</td></tr>`).join("")}</table>
      <p class="hint">${ev.limits.map(esc).join(" ")}</p>`;
    h += `<h3>Nanopublication drafts</h3><p class="hint">${esc(ev.nanopub_status)}.</p><ul class="mini-list">${ev.nanopub_drafts.map((d) => `<li><a href="${esc(d.file)}" download>${esc(d.file.split("/").pop())}</a> — ${d.triples} triples, rdflib parse ${d.valid_rdflib ? "ok" : "FAILED"}</li>`).join("")}</ul>`;
    if (state.demo && Array.isArray(state.demo.claims) && state.demo.claims.length) {
      h += `<h3>Claims in demo.json</h3>` + state.demo.claims.map((c) => `<div class="card"><p><code>${esc(c.id)}</code> <span class="chip motivation">${esc(c.status ?? "status unknown")}</span></p><p>${esc(c.statement)}</p><p class="hint">relation: ${esc(c.relation_to_test ?? "unknown")} · ${esc(c.source_uri ?? "")}</p></div>`).join("");
    }
    el.innerHTML = h;
  }

  function kvTable(o) {
    if (o === null || o === undefined) return "<span class='hint'>unknown</span>";
    if (typeof o !== "object") return esc(o);
    return `<table class="kv">${Object.entries(o).map(([k, v]) => `<tr><th>${esc(k)}</th><td>${typeof v === "object" && v !== null ? "<pre style='margin:0;white-space:pre-wrap'>" + esc(JSON.stringify(v, null, 1)) + "</pre>" : v === null ? "unknown" : esc(v)}</td></tr>`).join("")}</table>`;
  }
  function renderProof() {
    const el = $("#p-proof"), p = state.demo && state.demo.proof;
    if (!p) { el.innerHTML = `<div class="na"><b>No proof receipt loaded.</b><p>The site shows proof status only from a compiled receipt in <code>demo.json → proof</code> (theorem, command, kernel exit code, mutant exit code). None is present, so nothing is claimed — in particular, the in-browser route test on the Decision tab is <em>not</em> the Lean-checked certificate.</p></div>`; return; }
    const compiled = p.exit_code === 0 && typeof p.mutation_exit_code === "number" && p.mutation_exit_code !== 0;
    const partial = p.exit_code === 0 && !compiled;
    el.innerHTML = `<div class="verdict ${compiled ? "open" : "undetermined"}"><span class="tag">${compiled ? "Receipt: compiled, mutant rejected" : partial ? "Receipt incomplete" : "Not compiled / unverified"}</span>
      <h4>${esc(p.theorem ?? "theorem not named")}</h4><p>status field: <code>${esc(p.status ?? "unknown")}</code> · kernel exit <code>${esc(p.exit_code ?? "unknown")}</code> · mutant exit <code>${esc(p.mutation_exit_code ?? "unknown")}</code></p>
      <p class="hint">${compiled ? "Both exit codes are read from the receipt: the original compiled and the scientific-condition mutant was rejected." : "A green state needs original exit 0 and a non-zero mutant exit; the receipt does not show both."}</p></div>
      <h3>Receipt</h3>${kvTable(p)}
      <p class="hint">Correspondence between the Lean statement and the edge rule used here is documented by the proof worker; check it before relying on the receipt.</p>`;
  }
  function renderReplay() {
    const el = $("#p-replay"), d = state.demo;
    if (!d) { el.innerHTML = `<div class="na"><b>No replay results loaded.</b><p><code>data/demo.json</code> (core output) is not present, so no benchmark, abstention or false-certificate numbers are shown. The retrospective assay-budget replay is a planned/optional integration; nothing here is simulated by the site.</p></div>`; return; }
    const b = d.benchmark, c = d.compute;
    el.innerHTML = `<h3>Assay-budget replay <span class="chip sim">simulated selection replay</span></h3>${b ? kvTable({ status: b.status, protocol: b.protocol }) + (b.metrics ? `<h3>Metrics</h3>${kvTable(b.metrics)}` : "") + (b.limitations ? `<h3>Limitations</h3>${kvTable(b.limitations)}` : "") : "<div class='na'>benchmark absent in demo.json</div>"}
      <h3>GPU / foundation-model prior <span class="chip predicted">predicted</span></h3>${c ? kvTable(c) : "<div class='na'>compute absent in demo.json</div>"}
      <p class="hint">Predictions never discharge a missing measurement; they may only guide which assay is requested.</p>
      <h3>Limitations (demo.json)</h3>${Array.isArray(d.limitations) && d.limitations.length ? "<ul>" + d.limitations.map((x) => `<li>${esc(x)}</li>`).join("") + "</ul>" : "<span class='hint'>none listed</span>"}`;
  }

  /* ---------------- ledger ---------------- */
  function ledger() {
    const m = D.meta.counts, items = [
      [true, `Real data: ${m.measured_non_stop.toLocaleString()} measured · ${m.unmeasured_cells} unmeasured`],
      [!!state.ev, state.ev ? `Delphi MCP queried live ${state.ev.delphi_run_utc.slice(0, 16).replace("T", " ")} UTC` : "Delphi record: not loaded"],
      [!!(state.ev && state.ev.nanopub_drafts.every((x) => x.valid_rdflib)), state.ev ? `${state.ev.nanopub_drafts.length} nanopub drafts · rdflib-valid · unsigned` : "Nanopub drafts: not loaded"],
      [!!state.demo, state.demo ? `demo.json loaded (schema ${esc(state.demo.schema_version ?? "?")})` : "demo.json (core output): not present"],
      [!!(state.demo && state.demo.proof && state.demo.proof.exit_code === 0 && state.demo.proof.mutation_exit_code > 0), state.demo && state.demo.proof ? `Proof receipt: exit ${state.demo.proof.exit_code ?? "?"}, mutant exit ${state.demo.proof.mutation_exit_code ?? "?"}` : "Lean receipt: none"],
      [!!(state.demo && state.demo.benchmark && state.demo.benchmark.metrics), state.demo && state.demo.benchmark ? `Replay: ${esc(state.demo.benchmark.status ?? "status unknown")}` : "Replay benchmark: none"],
      [!!(state.demo && state.demo.compute && state.demo.compute.job_id), state.demo && state.demo.compute && state.demo.compute.job_id ? `GPU job ${esc(state.demo.compute.job_id)}` : "GPU run: none recorded"],
    ];
    $("#ledger").innerHTML = items.map(([ok, t]) => `<li class="${ok ? "ok" : "no"}"><span class="st">${ok ? "✓" : "○"}</span>${t}</li>`).join("");
  }

  /* ---------------- tabs / lens / boot ---------------- */
  function setTab(t) {
    state.tab = t;
    document.querySelectorAll(".tabs [role=tab]").forEach((b) => b.setAttribute("aria-selected", b.id === "tab-" + t));
    document.querySelectorAll(".pane").forEach((p) => { p.hidden = p.id !== "p-" + t; });
  }
  document.querySelectorAll(".tabs [role=tab]").forEach((b) => b.addEventListener("click", () => setTab(b.id.slice(4))));
  document.querySelectorAll(".lens button").forEach((b) => b.addEventListener("click", () => {
    state.lens = b.dataset.lens; document.querySelectorAll(".lens button").forEach((x) => x.setAttribute("aria-checked", x === b));
    paintOffscreen(); drawMap(); drawTile(); renderLegend();
  }));
  ["#t-reach", "#t-unk"].forEach((s) => $(s).addEventListener("change", () => { paintOffscreen(); drawMap(); }));
  function renderLegend() {
    const l = LENS[state.lens], lut = RAMPS[state.lens];
    const stops = [0, 64, 128, 192, 255].map((i) => `rgb(${lut[i * 3]},${lut[i * 3 + 1]},${lut[i * 3 + 2]})`).join(",");
    $("#legend").innerHTML = `<span>${l.lo}</span><span class="bar" style="background:linear-gradient(90deg,${stops})"></span><span>${l.hi}</span><span>${esc(l.label)}</span><span style="color:var(--unknown)">◯ unmeasured</span>`;
  }
  let rz; window.addEventListener("resize", () => { clearTimeout(rz); rz = setTimeout(() => { drawMap(); drawTile(); }, 100); });

  async function getJSON(u) { try { const r = await fetch(u, { cache: "no-store" }); if (!r.ok) return null; return await r.json(); } catch (e) { return null; } }

  (async function boot() {
    compute(); renderLegend(); paintOffscreen(); drawMap(); drawTile(); renderDecision(true); renderEvidence();
    [state.ev, state.demo] = await Promise.all([getJSON("data/evidence.json"), getJSON("data/demo.json")]);
    if (state.demo && Array.isArray(state.demo.routes) && state.demo.routes.length) state.coreRouteIdx = 0;
    ledger(); renderClaims(); renderProof(); renderReplay(); drawMap(); renderEvidence(); scheduleMaxEps();
    const q = new URLSearchParams(location.search);
    if (q.get("eps")) setEps(+q.get("eps"));
    if (q.get("tab")) setTab(q.get("tab"));
    window.__ready = true;
  })();
  window.__state = state;
})();
