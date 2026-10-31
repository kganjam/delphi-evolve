"""AMENDMENT_001 (critic, 2026-10-31): adjudicate the 4 ids disputed by the AT3 audit WITHOUT changing the frozen key (sha 747ddbae...).
Produces scopedesk/bench/AMENDMENT_001.json with the critic's decision per id and baseline scores on all 136 vs the 132-item clean set."""
import json, os, sys
from scipy.stats import beta
B = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, B)
import baselines
pub = [json.loads(l) for l in open(f"{B}/instances_public.jsonl")]; key = {json.loads(l)["id"]: json.loads(l) for l in open(f"{B}/key.jsonl")}
DISPUTED = {
 "gh-0005": {"audit": "out_of_scope", "decision": "disputed_excluded_from_clean_score",
   "rationale": "Tapered column (t=0.5). Key semantics (used uniformly in Rayleigh-Plateau, Hamilton, KPP, Kimura): 'applies' = the cited formula gives the same conclusion as the exact model for the request posed. Formula H_u=141.1 m and exact tapered H_t=162.9 m both exceed H=112.9 m, so 'no buckling' is robust -> key 'applies'. The auditor used a condition-based reading (uniform-column scope condition violated => out_of_scope). Both readings are defensible for a 3-way label, so the item cannot be a clean ground truth. Ideal answer: 'formula is for uniform columns; for this taper the conclusion (no buckling) still holds, with H_t in place of H_u'."},
 "gh-0013": {"audit": "out_of_scope", "decision": "disputed_excluded_from_clean_score",
   "rationale": "Same dispute as gh-0005 (t=0.4): H=58.1 m exceeds both H_u=36.3 m and H_t=43.6 m, so 'will buckle' is robust. Key 'applies' (outcome-based); audit out_of_scope (condition-based)."},
 "gh-0008": {"audit": "out_of_scope", "decision": "disputed_excluded_from_clean_score",
   "rationale": "Density is missing (E given, tapered t=0.5). Key rule: any missing mechanical input => underdetermined (MECH_INPUTS_MISSING) - NOT robustness-checked, unlike BC-unstated items (this is an inconsistency in the key). Critic recomputation: outcome-based verdict is 'applies' for rho=400,600,800,1000,1200 kg/m^3 and flips to out_of_scope only at 1500; so neither the key's 'underdetermined' (arbitrary plausible range) nor the auditor's 'out_of_scope' (tapered, condition-based) is a clean label. Excluded."},
 "wl-0009": {"audit": "applies", "decision": "disputed_excluded_from_clean_score",
   "rationale": "Key out_of_scope(NEAR_ONSET) because the continuum fastest-growing wavelength deviates 13.3% from lambda_c, even though the wavelength actually selected on the finite domain (admissible mode n=7) deviates 7.8% (<10%). Under the outcome-based semantics used elsewhere (does the formula predict the observed spacing within tolerance?) this is 'applies', matching the auditor. Critic judgment: the key's wavelength rule mixed a condition-based criterion (continuum onset) with outcome-based ones; wl-0009 is the only wavelength out_of_scope item with deviation of the selected mode <=10% (checked: 1 of 10). If the director wants a corrected key, relabel wl-0009 applies under a new hash (v1.1); v1 is unchanged."}}
def cp(k, n): return [round(0.0 if k == 0 else float(beta.ppf(.025, k, n - k + 1)), 4), round(1.0 if k == n else float(beta.ppf(.975, k + 1, n - k)), 4)]
def score(fn, ids):
    ok = sum(fn(p) == key[p["id"]]["verdict"] for p in pub if p["id"] in ids); return {"correct": ok, "n": len(ids), "acc": round(ok / len(ids), 4), "cp95": cp(ok, len(ids))}
allids = {p["id"] for p in pub}; clean = allids - set(DISPUTED)
out = {"amendment": "AMENDMENT_001", "frozen_key_sha256": "747ddbae6a37dc00a4a9271b43075c752c203ae24a820d08d9fb0e9db37c4467", "key_changed": False,
       "audit_source": "scopedesk/bench/audit/independent_audit_AT3_director_subagent.json (director commit d8768fd): 132/136 agree; same model family; semantics partly shared (see its independence_limits)",
       "decisions": DISPUTED, "clean_set_n": len(clean),
       "audit_agreement": {"all_136": {"agree": 132, "n": 136, "cp95": cp(132, 136)}, "clean_132": {"agree": 132, "n": 132, "cp95": cp(132, 132)}},
       "baselines_all_136": {"B0": score(baselines.predict_B0, allids), "R_always_applies": score(baselines.predict_R, allids)},
       "baselines_clean_132": {"B0": score(baselines.predict_B0, clean), "R_always_applies": score(baselines.predict_R, clean)},
       "reporting_rule": "Headline agent scores on the 132-item clean set, family-clustered; report the 136-item score as secondary; list the 4 ids. Do not tune prompts on these items.",
       "key_lessons": ["Greenhill family mixes condition-based and outcome-based semantics: tapered-but-robust items are inherently ambiguous for a 3-way label.",
                       "'Missing input => underdetermined' was not robustness-checked for Greenhill (it was for BC-unstated).",
                       "wl-0009 shows the wavelength rule is partly condition-based."]}
json.dump(out, open(f"{B}/AMENDMENT_001.json", "w"), indent=1)
print(json.dumps({k: out[k] for k in ("audit_agreement", "baselines_all_136", "baselines_clean_132")}, indent=0))
