#!/usr/bin/env python3
"""Fixed run command for the orx experiment: ESM2 prior vs measured TrpB assay (descriptive).

Reads config.json (committed code/config is the ONLY thing that varies between nodes).
Inputs live outside the repo (large; hashes are recomputed by analyze_prior and printed).
"""
import json
import sys
from pathlib import Path

here = Path(__file__).resolve().parent
sys.path.insert(0, str(here))
import analyze_prior  # noqa: E402

cfg = json.loads((here / "config.json").read_text())
out = here / "results"
out.mkdir(exist_ok=True)
sys.argv = ["analyze_prior", "--summary", cfg["summary"], "--imputed", cfg["imputed"], "--zeroshot", cfg["zeroshot"],
            "--embed-sites", cfg["embed_sites"], "--out", str(out / "analysis.json"),
            "--seeds", str(cfg["seeds"]), "--boot", str(cfg["boot"])]
analyze_prior.main()
print("ORX_RESULT_JSON " + json.dumps(json.loads((out / "analysis.json").read_text())))
