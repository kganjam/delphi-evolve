/* Darwin's Bridge — Results section. Renders ONLY numbers found in data/results.json
 * (copied by scripts/build_results_json.py from artifacts/core/replay/table_primary.csv and table_paired.csv). */
(function () {
  const root = document.getElementById("results-body");
  if (!root) return;
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const pct = (x) => (100 * x).toFixed(0) + "%";
  const sgn = (x) => (x >= 0 ? "+" : "−") + Math.abs(x).toFixed(2);
  fetch("data/results.json").then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); }).then(render).catch((e) => {
    root.innerHTML = `<div class="na"><b>No replay results loaded</b> (data/results.json: ${esc(e.message || e)}). Nothing is shown rather than a placeholder.</div>`;
  });
  const followup = document.getElementById("lazysp-result");
  if (followup) fetch("data/lazysp.json").then(r => {
    if (!r.ok) throw new Error(r.status);
    return r.json();
  }).then(d => {
    if (d.status !== "completed") throw new Error("incomplete follow-up");
    followup.innerHTML = `<h3>The stronger baseline changed the conclusion</h3>
      <p>Established lazy path search resolves <strong>${d.primary.certified}/${d.primary.episodes}</strong> cases with the primary alternating selector. Our original model-assisted planner is not demonstrated to beat it.</p>
      <div class="tablewrap"><table class="mini"><tr><th>LazySP selector</th><th>Basis</th><th>Certified at 1,000 assays</th><th>Restricted-mean assays</th></tr>
      ${d.variants.map(v => `<tr><td>${esc(v.variant)}</td><td>${esc(v.basis)}</td><td>${v.certified}/${v.episodes}</td><td>${v.rmst_assays.toFixed(1)}</td></tr>`).join("")}</table></div>
      <p class="hint">${esc(d.scope)}</p><p><a href="https://github.com/kganjam/delphi-evolve/blob/main/docs/lazysp.md">Read the protocol, source-checked query traces and comparison ↗</a></p>`;
  }).catch(() => { followup.textContent = "No completed stronger-baseline result loaded."; });

  function render(R) {
    const state = { budget: 1000, fam: "all" };
    const FAM = { all: "all 100 episodes", A: "family A (20 seeded pairs)", B: "family B (80 episodes: VFVS → 4 published targets × 20 seeds)" };
    root.innerHTML = `
      <div class="res-controls" role="group" aria-label="Chart controls">
        <div class="seg" role="radiogroup" aria-label="Assay budget">${[250, 500, 1000].map((b) => `<button type="button" role="radio" data-budget="${b}" aria-checked="${b === state.budget}">${b} assays</button>`).join("")}</div>
        <div class="seg" role="radiogroup" aria-label="Episode family">${Object.keys(FAM).map((f) => `<button type="button" role="radio" data-fam="${f}" aria-checked="${f === state.fam}">${f === "all" ? "All" : "Family " + f}</button>`).join("")}</div>
      </div>
      <h3 id="res-h3" class="res-sub"></h3>
      <div id="res-bars" class="res-bars" role="list"></div>
      <div class="res-legend"><span><i class="sw solid"></i> frozen in the protocol before the main run</span><span><i class="sw hatch"></i> added post hoc (exploratory)</span></div>
      <div id="res-tip" class="tip" hidden></div>
      <details class="res-table"><summary>Show the same numbers as a table</summary><div class="tablewrap"><table class="mini" id="res-tab"></table></div></details>
      <p>One enzyme assay; retrospective decisions under assumed error bounds. The shared collective did not beat the single planner. The top no-model arms were added after the initial results and are exploratory.</p>
      <details class="res-table"><summary>Paired comparisons, uncertainty and full interpretation limits</summary>
      <h3 class="res-sub">Paired contrasts (certified fraction, a − b, all 100 episodes)</h3>
      <div class="tablewrap"><table class="mini" id="res-pairs"></table></div>
      <p class="hint">${esc(R.uncertainty_procedure)}. The interval is a descriptive resampling summary over ${R.seeds} seeds, not a coverage claim.</p>
      <h3 class="res-sub">Read this before quoting</h3>
      <ul class="res-cav">${R.caveats.map((c) => `<li>${esc(c)}</li>`).join("")}</ul>
      <p class="hint">${esc(R.kind)}. Source tables: ${R.source_tables.map((s) => `<code>${esc(s)}</code>`).join(", ")}.</p></details>`;
    const tip = root.querySelector("#res-tip");
    function draw() {
      const rows = R.policies.map((p) => ({ p, v: p.by_family[state.fam][state.budget] }));
      rows.sort((a, b) => b.v.cert_rate - a.v.cert_rate || a.v.rmst_assays - b.v.rmst_assays);
      root.querySelector("#res-h3").textContent = `Episodes with a sound certificate by ${state.budget} assays beyond the initial observations — ${FAM[state.fam]}`;
      root.querySelector("#res-bars").innerHTML = rows.map(({ p, v }) => {
        const sentence = `${p.label}: ${v.certified} of ${v.episodes} episodes certified (${pct(v.cert_rate)}); ${v.unresolved_censored} unresolved and kept in the denominator; ${v.false_certificates} false certificates; restricted-mean assays ${v.rmst_assays.toFixed(0)}${p.frozen_in_protocol ? "" : "; added post hoc"}.`;
        return `<div class="bar-row" role="listitem" tabindex="0" aria-label="${esc(sentence)}" data-tip="${esc(sentence)}">
          <span class="bar-label">${esc(p.label)}${p.frozen_in_protocol ? "" : ' <em class="ph">post hoc</em>'}</span>
          <span class="bar-track"><span class="bar ${p.frozen_in_protocol ? "solid" : "hatch"}" style="width:${(100 * v.cert_rate).toFixed(1)}%"></span></span>
          <span class="bar-val">${pct(v.cert_rate)} <small>${v.certified}/${v.episodes}</small></span></div>`;
      }).join("");
      const tb = root.querySelector("#res-tab");
      tb.innerHTML = `<tr><th>policy</th><th>basis</th><th>certified</th><th>unresolved (censored)</th><th>false certificates</th><th>restricted-mean assays</th></tr>` +
        rows.map(({ p, v }) => `<tr><td>${esc(p.label)}</td><td>${p.frozen_in_protocol ? "frozen" : "post hoc"}</td><td>${v.certified}/${v.episodes} (${pct(v.cert_rate)})</td><td>${v.unresolved_censored}</td><td>${v.false_certificates}</td><td>${v.rmst_assays.toFixed(1)}</td></tr>`).join("");
      root.querySelectorAll(".bar-row").forEach((el) => {
        const show = (ev) => { tip.textContent = el.dataset.tip; tip.hidden = false; const r = el.getBoundingClientRect(), h = root.getBoundingClientRect(); tip.style.left = Math.max(0, Math.min(r.left - h.left + 12, h.width - 260)) + "px"; tip.style.top = (r.bottom - h.top + 6) + "px"; };
        el.addEventListener("mouseenter", show); el.addEventListener("focus", show);
        el.addEventListener("mouseleave", () => (tip.hidden = true)); el.addEventListener("blur", () => (tip.hidden = true));
      });
    }
    root.querySelector("#res-pairs").innerHTML = `<tr><th>a</th><th>b</th><th>assays</th><th>difference</th><th>95% seed-cluster bootstrap</th><th>a better / b better / tied</th></tr>` +
      R.paired_contrasts.map((c) => `<tr><td>${esc(c.a_label)}${c.a_posthoc ? " <em class='ph'>post hoc</em>" : ""}</td><td>${esc(c.b_label)}${c.b_posthoc ? " <em class='ph'>post hoc</em>" : ""}</td><td>${c.budget}</td><td><b>${sgn(c.mean_diff)}</b></td><td>[${sgn(c.ci_low)}, ${sgn(c.ci_high)}]</td><td>${c.a_better} / ${c.b_better} / ${c.tied}</td></tr>`).join("");
    root.querySelectorAll("[data-budget]").forEach((b) => b.addEventListener("click", () => { state.budget = +b.dataset.budget; root.querySelectorAll("[data-budget]").forEach((x) => x.setAttribute("aria-checked", x === b)); draw(); }));
    root.querySelectorAll("[data-fam]").forEach((b) => b.addEventListener("click", () => { state.fam = b.dataset.fam; root.querySelectorAll("[data-fam]").forEach((x) => x.setAttribute("aria-checked", x === b)); draw(); }));
    draw();
  }
})();
