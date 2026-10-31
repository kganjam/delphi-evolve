"""Figure from results/strength_duration_results.json (observed thresholds, model-derived predictions). Palette: reference
dataviz slots 1 (blue) and 2 (orange), validated for 2 series on a light surface; marker shape + label also carry identity."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
r = json.loads((HERE / "results" / "strength_duration_results.json").read_text())
T = r["table"]
mid = np.array([np.sqrt(t["lo"] * t["hi"]) for t in T])
BLUE, ORANGE, INK, MUTED, SURF = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#fcfcfb"
fig, ax = plt.subplots(1, 2, figsize=(11, 4.6), facecolor=SURF, gridspec_kw={"width_ratios": [1.15, 1]})
a = ax[0]; a.set_facecolor(SURF)
p0 = np.array([t["P0_ratio_to_rheobase"] for t in T]); p1 = np.array([t["P1_lapicque_rheobase_tau"] for t in T])
a.scatter(mid, p0, s=22, marker="s", color=ORANGE, alpha=.8, edgecolor=SURF, linewidth=.8, label="ratio to rheobase (leave-one-out)")
a.scatter(mid, p1, s=26, marker="o", color=BLUE, alpha=.85, edgecolor=SURF, linewidth=.8, label="Lapicque from rheobase + tau (no fit)")
lim = [min(mid.min(), p0.min(), p1.min()) * .8, max(mid.max(), p0.max(), p1.max()) * 1.2]
a.plot(lim, lim, color=MUTED, lw=1); a.set_xscale("log"); a.set_yscale("log"); a.set_xlim(lim); a.set_ylim(lim)
a.set_xlabel("measured 3 ms short-square threshold (pA)", color=INK); a.set_ylabel("predicted from long-square data only (pA)", color=INK)
a.set_title("101 mouse cells, Allen Institute Cell Types data", loc="left", color=INK, fontsize=11)
a.legend(frameon=False, fontsize=8.5, loc="upper left"); a.grid(alpha=.15)
b = ax[1]; b.set_facecolor(SURF)
dec = r["robust_amplitude_decision_target_coverage_0.9"]
names = [("P0_ratio_to_rheobase(LOO)", "ratio to\nrheobase"), ("P1_lapicque_rheobase_tau(no fit)", "Lapicque\n(no fit)"),
         ("P3_LIF_from_Vth_Ri_tau(no fit)", "LIF from\nVth, Rin, tau"), ("P4_LOO_regression(log irh, log tau)", "regression\n(LOO)"),
         ("P5_released_GLIF_LIF(provenance unverified)", "released GLIF\nLIF (n=49)")]
vals = [dec[k]["median_energy_overshoot_x"] for k, _ in names]
cov = [dec[k]["coverage"] for k, _ in names]
bars = b.bar(range(len(vals)), vals, color=BLUE, width=.55)
bars[0].set_color(ORANGE)
for i, (v, c) in enumerate(zip(vals, cov)):
    b.text(i, v + .08, f"{v:.1f}x\ncov {c:.0%}", ha="center", va="bottom", fontsize=8.5, color=INK)
b.set_xticks(range(len(vals))); b.set_xticklabels([n for _, n in names], fontsize=8, color=INK); b.set_ylim(0, max(vals) * 1.3)
b.set_ylabel("median energy (I²·T) vs lowest observed firing amplitude", color=INK, fontsize=9)
b.set_title("Energy cost of a ~90%-coverage pulse amplitude", loc="left", color=INK, fontsize=11)
for s in ("top", "right"): b.spines[s].set_visible(False); a.spines[s].set_visible(False)
fig.text(.01, .005, "Observed: thresholds (Allen Institute NWB). Model-derived: all predictions. Intracellular current injection in slices; no electric-field or fabrication result. GLIF training sweeps unverified.", fontsize=7.5, color=MUTED)
fig.tight_layout(rect=(0, .03, 1, 1)); fig.savefig(HERE / "results" / "strength_duration.png", dpi=160, facecolor=SURF)
