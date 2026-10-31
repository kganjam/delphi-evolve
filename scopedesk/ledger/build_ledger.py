"""Kill ledger builder (critic, 2026-10-31). Times are COMPUTED, never typed: file mtime (message files; mtime = LAST modification, so a claim time may be too late
and a kill time too late if the file was edited afterwards) or git commit time (%cI, commit not first utterance). A time that cannot be derived is the string
'not derivable'. Duration = kill_recorded - claim_stated, only when both are derivable AND claim <= kill. Summary prints n and method; no rate is implied.
Usage: python3 -I build_ledger.py OUT_DIR"""
import json, os, subprocess, sys, statistics, datetime as dt
from zoneinfo import ZoneInfo
PDT = ZoneInfo("America/Los_Angeles")
MSG = "/data/artifacts/delphi-evolve-rethink/messages/"
WT = "/data/worktrees/delphi-evolve/"
def t_file(name):
    p = MSG + name
    return dt.datetime.fromtimestamp(os.stat(p).st_mtime, PDT) if os.path.exists(p) else None
def t_commit(sha, wt="rethink-critic"):
    try:
        out = subprocess.check_output(["git", "-C", WT + wt, "show", "-s", "--format=%cI", sha], stderr=subprocess.DEVNULL).decode().strip()
        return dt.datetime.fromisoformat(out).astimezone(PDT)
    except Exception: return None
def t_first_add(path, wt="rethink-critic"):
    try:
        out = subprocess.check_output(["git", "-C", WT + wt, "log", "--diff-filter=A", "--format=%cI", "--", path], stderr=subprocess.DEVNULL).decode().split()
        return dt.datetime.fromisoformat(out[-1]).astimezone(PDT) if out else None
    except Exception: return None
def tm(spec):
    k, *a = spec
    return {"file": t_file, "commit": t_commit, "first_add": t_first_add}[k](*a) if spec else None
F, C, A = "file", "commit", "first_add"
rows = [
 # ---------- the ten from THE-REFRAME (messages/2026-10-31-THE-REFRAME-zero-for-ten.md)
 dict(id="R01", claim="First machine-checked formal biology library / no such library exists", stated_by="host (primary session)", kind="prior art",
      claim_ref=(F, "2026-10-31-REFINEMENT-verified-commons.md"), kill_ref=(F, "primary-prior-art-verdict.md"),
      witness="messages/primary-prior-art-verdict.md; messages/2026-10-31-ATLAS-and-the-surviving-claim.md (Rashid et al. 2017 HOL Light; lean-bio; crnt-lean; facebookresearch/atlas-lean MathlibExt/Biology)", caught_by="independent reviewer (primary + scouts)",
      allowed="Machine-checked biology libraries already exist; ours is a complement (Turing/finite-domain statements), not a first."),
 dict(id="R02", claim="A shared verified lemma commons is our mechanism / novelty", stated_by="host", kind="prior art + negative replication",
      claim_ref=(F, "2026-10-31-REFINEMENT-verified-commons.md"), kill_ref=(F, "primary-prior-art-verdict.md"),
      witness="messages/2026-10-31-POST-AUDIT-what-survives.md (LEGO-Prover, LeanAgent, Prove Together; Berlot-Attwell arXiv 2504.03048: no direct reuse, no compute-adjusted advantage)", caught_by="independent reviewer (primary)",
      allowed="Shared-library reuse is published (Prove2Me etc.); our four-arm measurement tests it at matched budget and a null is a result."),
 dict(id="R03", claim="Turing needs a diffusion ratio >= 10", stated_by="host", kind="counterexample",
      claim_ref=(F, "2026-10-31-CONVERGENCE-final-spec.md"), kill_ref=(F, "2026-10-31-DIFFUSION-GAP-KILLED.md"),
      witness="messages/2026-10-31-DIFFUSION-GAP-KILLED.md: Lean-checked J=[[1,-1],[1011/1000,-101/100]], Du=1, Dv=1.1, L=5pi Neumann, mode-1 det=-21/25000 (codex-api); closed form r*=(sqrt(det J)+sqrt(-bc))^2/a^2 is classical (Murray)", caught_by="independent reviewer (codex-api)",
      allowed="There is no universal diffusion-ratio threshold; the required ratio depends on the kinetics (two-species floor r*>1)."),
 dict(id="R04", claim="Real proteins cannot reach the required diffusion ratio", stated_by="host", kind="prior art",
      claim_ref=(F, "2026-10-31-CONVERGENCE-final-spec.md"), kill_ref=(F, "2026-10-31-DELPHI-FRAMING-AND-DIFFUSION-VERDICT.md"),
      witness="messages/2026-10-31-DELPHI-FRAMING-AND-DIFFUSION-VERDICT.md; critic note planning/rethink/critic-diffusion-ratio.md (Mueller 2012 Science 336:721 measured Nodal/Lefty effective ratio; Kuhn 2022 Nat Commun: binding/retention, not size)", caught_by="independent reviewer (critic + scout)",
      allowed="Effective ratios in tissue are set by binding and retention (Mueller 2012; Kuhn 2022); a bare Stokes-Einstein ratio is not the relevant quantity."),
 dict(id="R05", claim="Physics knows where its equations stop; biology does not (as a novelty claim)", stated_by="host", kind="prior art",
      claim_ref=(F, "2026-10-31-THE-LARGER-FRAME.md"), kill_ref=(F, "2026-10-31-THE-PIVOT-gate-is-for-agents.md"),
      witness="messages/2026-10-31-THE-PIVOT-gate-is-for-agents.md (independent Gemini review: the scope conflicts are in textbooks and Wikipedia); messages/2026-10-31-THE-REFRAME-zero-for-ten.md", caught_by="independent reviewer (external model review)",
      allowed="The finite-domain scope caveats are textbook; what we built is a checkable, versioned statement of them."),
 dict(id="R06", claim="`finite_domain_stable` Lean theorem advertised as finite-domain STABILITY (its premise was determinant non-negativity)", stated_by="host (lean worker)", kind="mis-operationalised (determinant nonnegativity advertised as stability; NOT vacuous premises)",
      claim_ref=None, kill_ref=(C, "b4e60db", "codex-api"),
      witness="Codex commit b4e60db: planning/rethink/CODEX-21-CLAIM-FREEZE-REVIEW.md (original theorem paragraph) and the exact source snapshot artifacts/integration/codex-api/admissible-review/Admissible.lean (sha256 c51b98a8c4218c5e272223c5d710de0d765804d78beace544850f9749cf07236); messages/codex-price-probe-progress.md states the finding. Analytic witness J=diag(2,2), Du=Dv=1, L=pi: D(q)=(2-q)^2>=0 for all q satisfies the premise, yet mode n=1 (q=1) has both growth eigenvalues +1 (no new Lean compile of this witness is claimed). A stronger theorem `finite_domain_linearly_stable` was added later (commit 469874b; compiled by Codex at 7f9035a), so the historical defect was partly repaired. Earlier ledger text describing it as 'not_lt / saying nothing' came from THE-REFRAME and is NOT the accurate description.", caught_by="independent reviewer (Codex)",
      allowed="A theorem whose premise is determinant non-negativity was advertised as stability; the premise holds for unstable systems. It compiled and passed an axiom audit, which shows those checks do not establish that a statement means what its name says."),
 dict(id="R07", claim="Operationalization-fidelity benchmark is a new contribution", stated_by="host", kind="prior art",
      claim_ref=(F, "2026-10-31-PITCH-v2-operationalization-gap.md"), kill_ref=(F, "primary-prior-art-details.md"),
      witness="messages/primary-prior-art-details.md (DriftBench arXiv 2606.16541; ShadowBench 2608.29270; Benchmarking Agentic Review Systems 2606.19749); planning/rethink/critic-E-redteam.md", caught_by="independent reviewer (primary; critic search-level)",
      allowed="Mutation/witness-based fidelity checking is published; our narrow gap is executable scientific-test repair with checked witnesses tied to a stated scope."),
 dict(id="R08", claim="Thompson d~h^(3/2) refuted by a pooled Tallo regression", stated_by="director probe / team agent", kind="mis-operationalised",
      claim_ref=(C, "3975262", "rethink-director"), kill_ref=(F, "primary-selection-review.md"),
      witness="messages/primary-selection-review.md (Thompson pp.19-20 is a self-weight buckling envelope; Tallo 2022 already compared the exponent with 2/3); scopedesk/bench/descriptive/thompson_repair.json (commit 895f0a2) keeps four operationalisations separate", caught_by="independent reviewer (primary)",
      allowed="A pooled OLS tests mean allometry, not Thompson's buckling limit; no slope here confirms or refutes the claim."),
 dict(id="R09", claim="LLM agents hallucinate past scope conditions without a gate", stated_by="host", kind="measured null (on a mismatched run)",
      claim_ref=(F, "2026-10-31-THE-PIVOT-gate-is-for-agents.md"), kill_ref=(F, "2026-10-31-STATE.md"),
      witness="messages/2026-10-31-STATE.md (24 questions, 12 traps; two frontier models 24/24); Codex correction messages/codex-agent-gate-pre-run-review-ready.md: nonlinear prompts scored against linear labels", caught_by="the measurement itself (author) + independent reviewer (Codex) on the design",
      allowed="Exploratory label agreement on a run whose prompt and scoring target did not match; not a ceiling and not evidence for or against a gate."),
 dict(id="R10", claim="The robustness tax as a headline", stated_by="host", kind="prior art (partial)",
      claim_ref=(F, "2026-10-31-FINDING-robustness-tax.md"), kill_ref=(F, "2026-10-31-THE-REFRAME-zero-for-ten.md"),
      witness="messages/2026-10-31-THE-REFRAME-zero-for-ten.md row 10; critic note in messages/critic-to-director.md (Murray 1982, Maini et al. 2012, arXiv 2309.04741, arXiv 1708.09645)", caught_by="independent reviewer (critic, scout)",
      allowed="Low required ratio costs robustness is a known direction; our quantification is conditional on the stated noise model and kinetics."),
 # ---------- ours-against-ourselves and process rows
 dict(id="R11", claim="Bench v1 Rayleigh-Plateau pinned-end threshold l > pi*r (director's assignment text, adopted unchecked by the critic)", stated_by="director (assignment) + critic (implementation)", kind="convention defect (wrong physics)",
      claim_ref=(C, "c8623a6"), kill_ref=(C, "19fae04", "codex-api"),
      witness="planning/rethink/CODEX-BENCHMARK-SEMANTICS.md (commit 19fae04, work/codex-api): fixed-volume bridge needs zero first-order volume change, so n=1 is inadmissible and the pinned limit is L>2*pi*R (Martinez/Perales/Meseguer)", caught_by="independent reviewer (Codex), not the author's verifier",
      allowed="The benchmark's own scope condition was wrong; it was caught by an independent audit before any agent ran."),
 dict(id="R12", claim="Bench v1 request conventions underspecified (wavelength tolerance, Hamilton kernel, Allee invasion, Turing target) and 4 AT3-disputed ids", stated_by="critic", kind="convention defect",
      claim_ref=(C, "c8623a6"), kill_ref=(C, "d8768fd", "rethink-director"),
      witness="scopedesk/bench/AMENDMENT_001.json; director audit commit d8768fd (132/136); planning/rethink/CODEX-BENCHMARK-SEMANTICS.md", caught_by="independent reviewers (director's subagent, Codex)",
      allowed="v1 was put on hold; v1.1/v1.2 declare targets and conventions in every request."),
 dict(id="R13", claim="Bench v1/v1.1 numeric public ids were label-neutral", stated_by="critic", kind="convention defect (label leak)",
      claim_ref=(C, "c8623a6"), kill_ref=(C, "d23663a", "codex-api"),
      witness="planning/rethink/CODEX-BENCH-V1-1-REVIEW.md (commit d23663a): id-suffix-only depth-3 tree 58/96 vs majority 43/96", caught_by="independent reviewer (Codex)",
      allowed="Public ids encoded generator order; v1.2 uses opaque hashed ids with a private map."),
 dict(id="R14", claim="Three uniform-column density-unlisted items are 'applies' because the printed and exact coefficients agree to 0.04%", stated_by="critic (relabel proposed by a blinded same-family subagent)", kind="convention defect",
      claim_ref=(C, "67cd408"), kill_ref=(C, "8db96d6", "codex-api"),
      witness="planning/rethink/CODEX-AGENT-GATE-PRE-RUN-REVIEW.md (commit 8db96d6): rho=822.256954 kg/m3 gives opposite predictions for the printed 0.788 and the exact constant; items excluded in v1.2 rev3 (commit af7f38e)", caught_by="independent reviewer (Codex)",
      allowed="Approximate agreement does not imply identical binary outcomes at every density; the three items were excluded."),
 dict(id="R15", claim="v1.1 'FROZEN 07:40 PDT' (timestamps estimated, not read from `date`)", stated_by="critic", kind="process defect (unmeasured timestamp, premature freeze)",
      claim_ref=(C, "67cd408"), kill_ref=(C, "b66629f"),
      witness="scopedesk/bench/v1_1/FROZEN.md withdrawn in commit b66629f; correction section in messages/critic-to-director.md", caught_by="author (re-read `date`) and the director's/Codex's hold",
      allowed="Wall times in this project come from git commit times or `date`, never from memory; v1.1 was never frozen."),
 dict(id="R16", claim="The Price equation formalization (lean_price) as a novel node / 'no formalization found'", stated_by="critic", kind="prior art",
      claim_ref=(C, "e776030"), kill_ref=(C, "5eaceb8"),
      witness="lean_price/README.md correction; facebookresearch/atlas-lean MathlibExt/Biology/PopulationGenetics/Selection.lean (Price and Fisher FTNS, no sorry); messages/2026-10-31-ATLAS-and-the-surviving-claim.md", caught_by="independent scout (host) then verified by the author",
      allowed="Price and Fisher are already formalized (atlas-lean); our Queller/Hamilton-form corollary was not found there (code search, not exhaustive)."),
 dict(id="R17", claim="Binder-view fusion beats the best single scorer (collective of scorers)", stated_by="critic (wildcard hypothesis)", kind="measured null (preregistered rule)",
      claim_ref=None, kill_ref=(C, "bd7c894"),
      witness="planning/rethink/wildcard/binder_views_check.json: fused AUROC 0.61 vs best single 0.68; difference interval [-0.17, +0.02] includes 0", caught_by="the author's own frozen acceptance rule",
      allowed="Fusing precomputed views did not beat the best single view on this selected set; no decision improvement was shown."),
 dict(id="R18", claim="Delphi math claims give free machine-checkable ground truth at scale (880 claims)", stated_by="host", kind="measured scale reduction",
      claim_ref=(F, "2026-10-31-rubric-strategy-from-morphoswarm-8c.md"), kill_ref=(C, "bd7c894"),
      witness="planning/rethink/wildcard/claim_decidability.json: of 880 local claims 92 carry math; single-reader triage 33 decidable as written (18 trivial), 29 need an authored model, 12 empirical, 18 prose", caught_by="author-run measurement (single reader; not independently confirmed)",
      allowed="Only a pilot-sized subset of Delphi's math claims is machine-decidable as stated (single-reader triage)."),
 dict(id="R19", claim="A forecasting market of heterogeneous guilds shows a collective advantage; 'Settled Science' tiers", stated_by="host", kind="mis-operationalised (design defect)",
      claim_ref=(F, "2026-10-31-DECISION-settled-science.md"), kill_ref=(F, "primary-market-review.md"),
      witness="messages/primary-market-review.md; planning/rethink/critic-settled-science.md (commit 5586efc): no pooled-information control; tier-3 is a ProteinGym-style label; contamination", caught_by="independent reviewers (primary, critic)",
      allowed="A committee under enforced information asymmetry is not evidence of collective advantage without a pooled-agent control."),
 dict(id="R20", claim="H100s are necessary for counterexample search over reaction-diffusion parameters", stated_by="host", kind="measured (resource claim refuted)",
      claim_ref=(F, "2026-10-31-DECISION-settled-science.md"), kill_ref=(C, "5586efc"),
      witness="planning/rethink/wildcard/turing_scope_prevalence.json: 10,000,000 2x2 Turing screens in 15.5 s on one CPU thread; pde_cost_probe.json: 100 nonlinear solves to T=1000 in 20.4 s (unrefined)", caught_by="author-run measurement",
      allowed="Closed-form and 2x2 checks do not need GPUs; GPUs are justified only for workloads a CPU cannot do in time."),
 dict(id="R21", claim="Our Frontier seed questions and the morphoswarm open-problems register are actionable research content", stated_by="codex-api (the seeds); host (the register framing)", kind="design defect (measured against our own schema; single-reader, NOT Codex-reviewed)",
      claim_ref=(C, "5165177", "rethink-critic"), kill_ref=(C, "4e10ce0", "../delphi-frontier/foundation"),
      witness="repo kganjam/delphi-frontier (local /data/worktrees/delphi-frontier/foundation), commit 4e10ce0: seeds/frontier-problems.json, git blob eeb8ccb033c4322a9a10e777363421c49f416c54, sha256 3bf14a9cfafcf44b348508914f00ff932254d3825be8c2f6a809cc26cc4e12ee (critic re-hashed both from the commit); ledger/README.md row 16 carries the reproduction command (dx-market validator, work/market). Reported by the host, not re-run by the critic: validator returns 0 of 7 bounded, 0 ready, 0 with a consequence estimate, 105 issues (missing 49, bad_enum 14, untyped_edge 14, bad_ref 14, unpinned 7, bad_estimate 7); at 4e10ce0, 0 of 250 morphoswarm register problems could enter the Problem model (it required acceptance_criteria, falsifiers, next_action, cost_stop_bounds, none of which the register has; extra=forbid; no unlocks field). Host correction (the earlier relay said every one of the 250 carried a pmcid, locator and verbatim quote: FALSE): register sha256 a0155552a2bcda40688d38e95c4069828922d21042c87c9c6cf96311de94f7d7; 34 carry why_source with locator/quote, 68 only a references list, 148 no source (critic re-counted from the YAML: 34/68/148); after kganjam/delphi-frontier 42cd967 (09:41:15) 250 of 250 import as 'recorded' and 0 are 'actionable'; that commit's message says '250 sourced', which the counts contradict. The 148 unsourced are curator statements, not sourced open problems. Claim time = seeds authored 5165177 (work/codex-api, 08:20:56); kill time = commit 4e10ce0 (row recorded 09:30:48), i.e. when the finding was recorded, not when the validator first ran.", caught_by="independent worker's validator (dx-market), re-run by host",
      allowed="Says nothing about whether the 250 problems are good problems and nothing about any model's accuracy; a schema/curation defect in our own artifact, not a scientific finding."),
]
controlled = [
 dict(id="M1", claim="Original query-to-certify planner vs a LazySP-style baseline at 1,000 additional assays", result="LazySP-style 96/100 vs original Q2C 78/100 (gain concentrated in one repeated pair; difference interval includes zero)",
      witness="docs/lazysp.md; artifacts/core/replay/table_primary.csv (same panel: 20 seed-selected pairs + 4 fixed pairs x 20 initial sets; not independent biological targets)", record_ref=(A, "docs/lazysp.md"),
      allowed="Matched-budget replay on one panel: the established LazySP-style comparator resolved more episodes than our planner; no general-superiority claim."),
 dict(id="M2", claim="Shared-evidence specialists vs a single planner", result="shared specialists 78/100 = original Q2C 78/100 (isolated 77/100)",
      witness="docs/novelty.md; artifacts/core/replay/table_primary.csv", record_ref=(A, "docs/novelty.md"),
      allowed="No collective completion advantage was demonstrated in this replay."),
]
CLASS = {"R09": "mixed", "R15": "mixed", "R17": "author", "R18": "author", "R20": "author"}   # every other row: independent reviewer / validator / scout
def iso(x): return x.isoformat(timespec="seconds") if x else "not derivable"
out_rows, durs = [], []
for r in rows:
    c = tm(r["claim_ref"]) if r["claim_ref"] else None; k = tm(r["kill_ref"]); d = None
    if c and k and k >= c: d = round((k - c).total_seconds() / 60, 1); durs.append((r["id"], d))
    rr = dict(r); rr["claim_stated_pdt"] = iso(c); rr["kill_recorded_pdt"] = iso(k); rr["duration_min"] = d if d is not None else "not derivable"
    rr["time_source"] = {"claim": r["claim_ref"], "kill": r["kill_ref"]}; out_rows.append(rr)
ctrl = []
for m in controlled:
    t = tm(m["record_ref"]); mm = dict(m); mm["record_time_pdt"] = iso(t); ctrl.append(mm)
vals = [d for _, d in durs]
summary = {"n_rows": len(rows), "n_with_both_times": len(vals), "method": "kill_recorded - claim_stated in minutes, only where both times are derivable and ordered; times are file mtimes (messages) or git commit times; mtime = last modification, commit time = commit not utterance, so durations are rough, may be inflated or deflated, and rows differ in kind (prior-art lookups, audits, measurements)",
           "durations_min_by_row": dict(durs), "median_min": (statistics.median(vals) if vals else "not derivable"), "min_min": (min(vals) if vals else None), "max_min": (max(vals) if vals else None),
           "reading": "descriptive of THIS team on THIS day; not a rate, not generalisable; do not put the median on a slide without n and method and without the not-derivable rows",
           "kind_counts": {k: sum(r["kind"].startswith(k) for r in rows) for k in ("prior art", "counterexample", "measured", "mis-operationalised", "convention defect", "process defect", "design defect")},
           "caught_by_class": {c: sum(CLASS.get(r["id"], "independent") == c for r in rows) for c in ("independent", "mixed", "author")},
           "caught_by_class_rows": CLASS,
           "caught_by_class_note": "explicit per-row classification (v2): substring matching on caught_by text was wrong (R18 'not independently confirmed' matched 'independent'). author = caught only by the author's own measurement or rule (all three are measurements/rules, not reviews); mixed = author found it and an independent hold/review also applied"}
os.makedirs(sys.argv[1], exist_ok=True)
json.dump({"rows": out_rows, "measured_matched_control": ctrl, "summary": summary,
           "notes": ["Message files have only mtimes; THE-REFRAME's own text labels itself '09:05 PDT' but its mtime is 07:27; use mtimes/commit times, not labels inside files.",
                     "claim_stated for R06 is not derivable (no dated statement located); its kill time is the recorded-review commit time of b4e60db (Codex), not a first-utterance time. R17: the acceptance rule was written in the script before the first run and the result was committed together with it, so a claim-to-kill duration is not meaningful (left not derivable). R01/R02 use the earliest kill-recording file (primary-prior-art-verdict.md); later files (POST-AUDIT, ATLAS) add further witnesses."]},
          open(os.path.join(sys.argv[1], "kill_ledger.json"), "w"), indent=1)
with open(os.path.join(sys.argv[1], "KILL-LEDGER.md"), "w") as f:
    f.write("# Kill ledger (critic; generated by build_ledger.py - do not hand-edit)\n\nOne row per claim killed or corrected on 2026-10-31. Kill types are kept separate. Times are COMPUTED (see summary.method). A ledger of failures is not a discovery rate and does not generalise beyond this team and day.\n\n")
    f.write("| id | claim (stated by) | kill type | caught by | claim stated (PDT) | kill recorded (PDT) | min | allowed wording |\n|---|---|---|---|---|---|---|---|\n")
    for r in out_rows:
        f.write(f"| {r['id']} | {r['claim']} ({r['stated_by']}) | {r['kind']} | {r['caught_by']} | {r['claim_stated_pdt'][5:16] if r['claim_stated_pdt']!='not derivable' else 'not derivable'} | {r['kill_recorded_pdt'][5:16] if r['kill_recorded_pdt']!='not derivable' else 'not derivable'} | {r['duration_min']} | {r['allowed']} |\n")
    f.write("\n## Witnesses\n" + "\n".join(f"- **{r['id']}**: {r['witness']}" for r in out_rows) + "\n")
    f.write("\n## Measured, matched control (separate row type)\n\n| id | comparison | result | recorded (PDT) | allowed wording |\n|---|---|---|---|---|\n")
    for m in ctrl: f.write(f"| {m['id']} | {m['claim']} | {m['result']} | {m['record_time_pdt'][5:16]} | {m['allowed']} |\n")
    f.write("\n" + "\n".join(f"- {m['id']} witness: {m['witness']}" for m in ctrl) + "\n")
    s = summary
    f.write(f"\n## Timing summary (descriptive)\nn rows = {s['n_rows']}; rows with both times derivable = {s['n_with_both_times']}; method: {s['method']}.\nDurations (min): {s['durations_min_by_row']}. Median over these {s['n_with_both_times']} rows = {s['median_min']} min (min {s['min_min']}, max {s['max_min']}). {s['reading']}.\n")
    f.write(f"Kill-type counts (prefix match): {s['kind_counts']}. Caught by an independent reviewer/validator/scout: {s['caught_by_class']['independent']} rows; mixed (author found it, independent hold also applied; R09, R15): {s['caught_by_class']['mixed']} rows; by the author's own measurement or rule only (R17, R18, R20; all three are measurements, not reviews): {s['caught_by_class']['author']} rows (no control arm; this supports 'independent audit caught what authors missed', not a collective-vs-single comparison).\n\n## Notes\n" + "\n".join("- " + n for n in json.load(open(os.path.join(sys.argv[1], 'kill_ledger.json')))["notes"]) + "\n")
print(json.dumps(summary)[:1500])
