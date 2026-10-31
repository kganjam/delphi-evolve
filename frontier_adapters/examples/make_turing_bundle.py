"""End to end: live Delphi claim `turing-ddi` + an exported OpenResearch run -> proposed Claim, Evidence, TriG drafts.

Run (bounded):  FRONTIER_PATH=<read-only checkout of kganjam/delphi-frontier> \
  systemd-run --user --scope -p MemoryMax=4G -p MemorySwapMax=0 -p TasksMax=128 -p RuntimeMaxSec=300 \
  python3 -I -m frontier_adapters.examples.make_turing_bundle
The replay step EXECUTES the exported run's command (code written by this session; trust_code=True is deliberate).
"""
import json
import os
import sys

from frontier_adapters import bundle, delphi_claim as dc, orx_evidence as oe, orx_replay
from frontier_adapters.delphi_mcp import Delphi

HERE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.join(HERE, "orx_run_turing")
OUT = os.path.join(HERE, "turing_bundle")
RUN_ID = "330735e8-d32e-47cd-99ee-fb54845367d7"

AUTHOR = {
    "method": ("Exact-rational scan. For each domain length L=(p/s)*pi in {pi, 3pi/2, 2pi, 5pi/2, 3pi, 4pi} form the Neumann mode "
               "numbers q_n=(n*s/p)^2, n=0..100, and compute trace=(a+d)-(Du+Dv)q and det=(Du*q-a)*(Dv*q-d)-b*c with Python Fractions. "
               "A mode is non-stable unless trace<0 and det>0. Executed as `python3 run_modes.py` on the OpenResearch local backend."),
    "context": ("Applicability witness for the Delphi claim turing-ddi. For J=[[1,-2],[2,-3]], Du=1, Dv=10 the continuum inequality "
                "Dv*fu+Du*gv > 2*sqrt(Du*Dv*detJ) holds (49 > 40), yet every admissible Neumann mode is stable on L=pi and L=5pi/2, while "
                "a non-stable mode exists on 3pi/2, 2pi, 3pi and 4pi. It shows the admissible-mode set decides the outcome; it does not "
                "support the claim's headline and carries no stance field because the Evidence schema has none."),
    "assumptions": [
        "Declared linearization J=[[1,-2],[2,-3]], Du=1, Dv=10: a worked instance, not fitted to any data.",
        "Two species, linear stability about a homogeneous steady state, 1-D interval, zero-flux boundaries.",
        "Neumann mode numbers are DEFINED as q_n=(n*pi/L)^2; they are not derived from the boundary-value problem in this run.",
        "A mode is stable iff trace<0 and det>0 (Routh-Hurwitz for a 2x2 matrix); modes n=0..100 are scanned."],
    "limitations": [
        "Evaluates the target claim's own linear criterion on one declared instance. It says nothing about nonlinear patterning, real morphogens or biology.",
        "Exact rational arithmetic removes numerical error, but the model and the mode set are declarations.",
        "Modes above n=100 are not scanned; their stability rests on an algebraic tail argument this run does not re-prove.",
        "Evidence kind is 'simulated', not 'formal': no proof checker was involved in this record.",
        "The author of the run also wrote this adapter; no independent party has re-executed it."],
    "uncertainty": ("Exact rational arithmetic: the sign tests carry no numerical uncertainty. Model-form uncertainty and relevance to any "
                    "real system are not quantified."),
    "source_dependence": {
        "shares_criterion_with_target": True,
        "note": "Evaluates the target claim's own stability criterion; it is not an independent confirmation of the criterion.",
        "producer": "corpus session (Claude Sonnet 5.5)",
        "independent_of_target_extractor": "unknown: the target was extracted by a Claude Opus 5.5 pipeline, same vendor family"},
}


def main():
    mcp = Delphi()
    snap, transient = dc.collect(mcp, "turing-ddi")
    claim_draft = dc.to_claim_draft(snap, verification=dc.verify_source(snap, transient))
    facts = oe.read_run(run_id=RUN_ID, export_dir=RUN, result_file="results.json")
    interps = {"python3.12": "/usr/bin/python3", "python3.13": "/home/ubuntu/miniconda3/bin/python"}
    normal = orx_replay.replay(RUN, command=facts["command"], result_file="results.json", recorded_sha256=facts["result_sha256"],
                               interpreters=interps, trust_code=True)
    control = orx_replay.replay(RUN, command=facts["command"], result_file="results.json", recorded_sha256=facts["result_sha256"],
                                interpreters={"python3.12": interps["python3.12"]}, trust_code=True,
                                mutation=("run_modes.py", "F(-3), F(1), F(10)", "F(-3), F(1), F(9)"))
    replay = dict(normal)
    replay["mutation_control"] = not any(v["matches_recorded"] for v in control["results"].values())  # control must NOT match
    replay["control_results"] = control["results"]
    manifest = bundle.assemble(
        claim_draft,
        lambda target: oe.to_evidence_draft(facts, target=target, author=AUTHOR, kind="simulated", replay=replay),
        out_dir=OUT, created_at=snap["retrieved_at"])
    json.dump(replay, open(os.path.join(OUT, "replay_report.json"), "w"), indent=2, sort_keys=True)
    print(json.dumps(manifest["records"], indent=1))
    print("evidence pinned to the exact claim version:", manifest["evidence_targets_exact_claim_version"])
    print("replay:", {k: v["matches_recorded"] for k, v in replay["results"].items()}, "| mutation control discriminates:", replay["mutation_control"])


if __name__ == "__main__":
    sys.exit(main())
