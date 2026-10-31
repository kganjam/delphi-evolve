import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "experiments", "rethink_wildcard"))
import numpy as np
import binder_views_check as b
import claim_decidability_labels as c

ROOT = os.path.join(os.path.dirname(__file__), "..")

def test_claim_label_counts_match_committed_raw():
    raw = os.path.join(ROOT, "planning/rethink/wildcard/delphi_math_claims_raw.json")
    t = json.loads(json.load(open(raw))["search"]["result"]["content"][0]["text"])
    assert len(t) == 92 and set(c.LABELS) == set(range(92))
    assert sum(1 for v in c.LABELS.values() if v == "D1") == 33

def test_sequence_clusters_group_near_duplicates_only():
    g = b.sequence_clusters(["ACDEFGHIKLMNPQRSTVWY" * 2, "ACDEFGHIKLMNPQRSTVWY" * 2 + "A", "WWWWWYYYYYFFFFFHHHHH"])
    assert g[0] == g[1] and g[0] != g[2]

def test_seq_features_charge_sign():
    assert b.seq_features("KKKK")["net_charge_per_res"] == 1.0
    assert b.seq_features("DDDD")["net_charge_per_res"] == -1.0

def test_group_folds_hold_out_whole_groups():
    import pandas as pd
    df = pd.DataFrame({"username": list("aabbccddee") * 4, "y": ([0, 1] * 20)})
    for col in ["pae_interaction", "iptm", "plddt", "esm_pll_per_res", "similarity_check", "num_residues",
                "gravy", "net_charge_per_res", "frac_aromatic", "frac_gly_pro", "frac_cys"]:
        df[col] = np.random.default_rng(0).standard_normal(len(df))
    oof = b.cv_scores(df)
    assert all(not np.isnan(v).any() for v in oof.values())
