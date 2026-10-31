"""Optional bridge to the repository's audited TrpB loader (needs the `evolve` package and the Caltech CSVs).

The portable parts of claim_runtime do not import this module.
"""
from __future__ import annotations

import os
from pathlib import Path


def raw_dir() -> Path:
    for c in (os.environ.get("EVOLVE_RAW"), Path(__file__).resolve().parent.parent / "data" / "raw",
              "/data/artifacts/v2-scout/data/caltech"):
        if c and (Path(c) / "summary_AA.csv").exists():
            return Path(c)
    raise FileNotFoundError("TrpB raw CSVs not found; run scripts/fetch_data.py or set EVOLVE_RAW")


def load_landscape(kappa: float = 2.0):
    from evolve import data
    land = data.load(raw_dir(), kappa=kappa)      # verifies SHA-256 against data/manifest.json
    return land, land.sha["summary_AA.csv"]
