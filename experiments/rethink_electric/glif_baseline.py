"""Released Allen Institute GLIF baseline for the same cells (closed form, no allensdk import, no NWB writes).

The released LIF / LIF-ASC `neuron_config.json` is downloaded as-is (zip from api.brain-map.org/neuronal_model/download).
Before the first spike the LIF and LIF-ASC (and the threshold-dynamics variants, whose threshold equals th_inf*coeff
until the first spike) reduce to
    C_eff dV/dt = I - G_eff V,   V(0)=0 (relative to rest),   threshold = coeffs['th_inf'] * th_inf
so a rectangular pulse of length T fires iff  I * (1 - exp(-G_eff T / C_eff)) / G_eff >= threshold. The rule is the
AllenSDK `dynamics_voltage_linear_forward_euler` update with G=1/R_input (source read from allensdk 2.16.2 wheel,
glif_neuron_methods.py), solved exactly instead of Euler-stepped (the SDK's dt is 5 us; difference is O(dt/tau)).

PROVENANCE CAVEAT (unresolved): the released config carries no list of the sweeps used for optimisation, and the
technical white paper that documents the optimisation was not retrieved by this worker. The GLIF numbers are therefore a
REFERENCE COMPARATOR that may have seen short-square or other held-out sweeps; they are not claimed as held-out.
"""
from __future__ import annotations

import hashlib, io, json, math, urllib.request, zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
Q = ("https://api.brain-map.org/api/v2/data/query.json?criteria=model::NeuronalModel,rma::criteria,"
     "specimen[id$in{ids}],rma::options[num_rows$eq2000]")
DL = "http://api.brain-map.org/neuronal_model/download/{}"


def get(url):
    with urllib.request.urlopen(url, timeout=120) as r:
        return r.read()


def main():
    feats = json.loads((HERE / "results" / "cell_features.json").read_text())["cells"]
    ids = [c["specimen__id"] for c in feats]
    q = Q.replace("{ids}", ",".join(map(str, ids)))
    resp = json.loads(get(q))
    assert resp["success"], resp["msg"]
    models = resp["msg"]
    by_spec = {}
    for m in models:
        by_spec.setdefault(m["specimen_id"], []).append(m)
    out = {}
    for sid in ids:
        ms = by_spec.get(sid, [])
        lif = [m for m in ms if m["name"].startswith("1 Leaky")]
        if not lif:
            out[str(sid)] = None
            continue
        m = lif[0]
        blob = get(DL.format(m["id"]))
        z = zipfile.ZipFile(io.BytesIO(blob))
        cfg_name = [n for n in z.namelist() if n.endswith("neuron_config.json")][0]
        cfg = json.loads(z.read(cfg_name))
        out[str(sid)] = {"model_id": m["id"], "zip_sha256": hashlib.sha256(blob).hexdigest(),
                         "R_input_ohm": cfg["R_input"], "C_F": cfg["C"], "th_inf_V": cfg["th_inf"],
                         "coeffs": {k: cfg["coeffs"][k] for k in ("C", "G", "th_inf")}, "El_reference_V": cfg["El_reference"],
                         "threshold_dynamics_method": cfg["threshold_dynamics_method"]}
    (HERE / "results" / "glif_lif_configs.json").write_text(json.dumps(
        {"source": "AllenSDK-era neuronal_model download; one LIF (template 395310469) model per cell", "models": out}, indent=1))
    print(sum(v is not None for v in out.values()), "of", len(out), "cells have a released LIF model")


def glif_short_threshold_pA(m: dict, T_s: float) -> float:
    G = (1.0 / m["R_input_ohm"]) * m["coeffs"]["G"]
    C = m["C_F"] * m["coeffs"]["C"]
    theta = m["th_inf_V"] * m["coeffs"]["th_inf"]
    return 1e12 * theta * G / (1.0 - math.exp(-G * T_s / C))


if __name__ == "__main__":
    main()
