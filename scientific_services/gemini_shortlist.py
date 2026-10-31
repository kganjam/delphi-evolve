"""OPTIONAL, UNVALIDATED: ask Gemini to choose the next assay from a pre-built SHORTLIST, using only publicly revealed
labels (start, target, the seed-0 Family-B initial 96 observations) and their assumed intervals. No hidden label enters
the prompt or the shortlist construction (label-free rule: the 4 one-step moves toward the target + 4 seeded-random
neighbours of the start). After the response, the candidates' true admissibility is looked up for an ANECDOTAL check.
This is one sample; it is not compared with core's policies on the same assay budget and is NOT evidence of improved agency."""
import json, hashlib
from pathlib import Path
import numpy as np
from .gemini_client import Gemini
from .verify_review import load, intervals, neighbours, enc, dec, AA

START, TARGET, SEED = "VFVS", "AIKG", 0

def build():
    meas, s1, s2, s, cm, sha = load("/data/artifacts/v2-scout/data/caltech/summary_AA.csv")
    ids = np.flatnonzero(meas)
    init = [int(x) for x in np.random.default_rng(20261031 + 10_000 + SEED).choice(ids, 96, replace=False)]
    init_sha = hashlib.sha256(json.dumps(sorted(init)).encode()).hexdigest()
    Lo, Hi = intervals(s, cm)
    revealed = [enc(START), enc(TARGET)] + [v for v in init if v not in (enc(START), enc(TARGET))]
    rows = [{"genotype": dec(v), "score_micro": int(s[v]), "lower": int(Lo[v]), "upper": int(Hi[v])} if meas[v] else {"genotype": dec(v), "outside_measured_library": True} for v in revealed]
    st = enc(START); nb = [int(x) for x in neighbours(np.array([st]))[0]]
    toward = [enc("AFVS"), enc("VIVS"), enc("VFKS"), enc("VFVG")]
    rest = [v for v in nb if v not in toward and v not in revealed]
    rng = np.random.default_rng(7); rnd = [int(x) for x in rng.choice(rest, 4, replace=False)]
    short = toward + rnd; order = np.random.default_rng(11).permutation(len(short)); short = [short[i] for i in order]
    truth = {dec(v): {"measured": bool(meas[v]), "admissible_from_VFVS": bool(meas[v] and Lo[v] >= Hi[st])} for v in short}
    return rows, short, truth, init_sha, sha

def main():
    rows, short, truth, init_sha, sha = build()
    prompt = f"""You are advising an enzyme-engineering team. Landscape: four mutable sites (183,184,227,228) of tryptophan synthase beta (TrpB); genotypes are 4-letter strings. Each measured genotype has a growth-assay score in integer micro-units and an ASSUMED interval [lower, upper] (kappa=2 sensitivity band from two replicates; NOT a confidence interval). An edge u->v between genotypes differing at one site is "admissible" only if lower[v] >= upper[u].
Goal: decide whether a chain of admissible single-substitution steps exists from start {START} to target {TARGET}; choose ONE next assay (a single genotype to measure) from the SHORTLIST that best helps settle that decision. You may only use the labels below. Unmeasured genotypes have unknown scores.
REVEALED LABELS ({len(rows)} genotypes; the first two are the start and target):
{json.dumps(rows)}
SHORTLIST (unlabeled, each is a single substitution away from {START}): {json.dumps([dec(v) for v in short])}
Return strict JSON: {{"choice": "<genotype from shortlist>", "ranking": ["<all shortlist genotypes best-first>"], "rationale": "<<=120 words, cite only the revealed labels>", "what_would_change_my_mind": "<<=40 words>", "confidence": "low|medium|high"}}"""
    g = Gemini()
    rec = g.generate("gemini-3.8-flash", prompt, system="Be calibrated; say when the revealed labels are insufficient.", max_output_tokens=2500,
                     temperature=0.2, label="shortlist_choice_flash", thinking_level="low", response_mime_type="application/json")
    try:
        ans = json.loads(rec["response_text"])
    except Exception:
        ans = {"parse_error": True}
    out = {"epistemic_status": "UNVALIDATED model suggestion; one sample; not an agency/performance result",
           "episode": f"Family B seed {SEED} {START}->{TARGET}", "initial_observations_sha256": init_sha,
           "protocol_expected_initial_sha256": "32592d5ffd18a6ff1f7b16ea303dc6a89ec8297c421a6a3c0cf647c7f3e6e862",
           "shortlist_rule": "label-free: 4 one-step moves toward target + 4 seeded-random neighbours (rng seed 7), shuffled (seed 11)",
           "shortlist": [dec(v) for v in short], "gemini_answer": ans,
           "after_the_fact_lookup_not_shown_to_model": truth,
           "known_full_data_route_for_context": ["VFVS", "VFMS", "SFMS", "SIMS", "SIMG", "SIKG", "AIKG"],
           "model_version_returned": rec["model_version_returned"], "usage": rec["usage_metadata"], "t_seattle": rec["t_seattle"]}
    Path("artifacts/services/gemini/shortlist_result.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("initial_observations_sha256", "shortlist", "gemini_answer", "after_the_fact_lookup_not_shown_to_model")}, indent=1)[:3500])

if __name__ == "__main__":
    main()
