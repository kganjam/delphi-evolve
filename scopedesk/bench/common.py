"""Shared helpers for Scope Desk bench (critic). Exact arithmetic with Fractions wherever stated."""
import math
from fractions import Fraction as F

EXCLUDED = []   # (family, reason, params) for ambiguous / near-threshold items dropped by generators

def exclude(family, reason, params):
    EXCLUDED.append({"family": family, "reason": reason, "params": {k: str(v) for k, v in params.items()}})

def ftxt(x):
    x = F(x)
    return str(x.numerator) if x.denominator == 1 else f"{x.numerator}/{x.denominator}"

def signed(x):
    x = F(x)
    return ("- " if x < 0 else "+ ") + ftxt(abs(x))

def pi_len(r):                       # domain length r*pi in two spellings (caller picks)
    return ftxt(r)

CONDITION_IDS = ["BC_NEUMANN", "BC_PERIODIC", "BC_DIRICHLET", "BC_UNSTATED", "DOMAIN_ADMISSIBLE_MODE", "NEAR_ONSET",
                 "LARGE_DOMAIN", "WELLMIXED_STABLE", "DIFFUSION_RATIO", "LINEARIZATION_ONLY",
                 "ESTIMATOR_MEAN_VS_ENVELOPE", "MECH_INPUTS_MISSING",
                 # added by critic 2026-10-31 (dated note per SPEC.md):
                 "BC_PINNED_ENDS", "DRIFT_DOMINATED", "PAYOFF_REGIME", "UNIFORM_COLUMN", "HAMILTON_NONADDITIVE",
                 "KPP_NONLINEARITY", "SMALL_SELECTION_LIMIT"]

def item(fid, family, stratum, text, structured, key_verdict, cond, witness, repairs=None, tset="A", target=None):
    pub = {"id": fid, "family": family, "stratum": stratum, "request_text": text,
           "tools_allowed": ["exact_modes", "pde_solve", "source_lookup", "python"]}
    full = dict(pub); full["hidden"] = {"structured": structured, "benign": key_verdict == "applies",
                                         "template_set": tset, "target": target}
    key = {"id": fid, "verdict": key_verdict, "condition_ids": cond, "witness": witness,
           "expected_repairs": repairs or {}}
    return pub, full, key
