"""SCORECARD v0 builder (critic, director follow-up 9). One row per math-domain Delphi claim (18 population-genetics + 3 Turing) read from the committed
records/ (fetched once from the hosted Delphi MCP, local source, by fetch_records.py). Status taxonomy: (a) CHECKED-SCOPE-FOUND, (b) CHECKED-HOLDS-AS-DECLARED,
(c) FORMAL-NODE-ONLY, (d) SELF-DECLARED NON-FORMAL / EMPIRICAL, (e) NOT ATTEMPTED. Statuses and limits are the critic's judgement written below, NOT computed;
the script copies record fields, hashes them, checks that every evidence path exists in this checkout (or is marked as a path on another branch), and prints counts.
Usage: python3 -I build_scorecard.py"""
import glob, hashlib, json, os, sys
D = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(D, "..", ".."))
B = "scopedesk/bench/v1_2/"
CODEX_BENCH = "Codex (different model family) recomputed all bench keys with its own code, non-blinded (planning/rethink/CODEX-BENCH-V1-1-REVIEW.md @ d23663a; frozen-127 metadata check @ 6c96810, work/codex-api)"
ST = {
 "turing-ddi": dict(status="a", ev=[B + "key.jsonl (families turing_finite_domain 21 items, turing_2d_rectangle 15)", "turing_scope/examples/short_L_pi.json (J=[[1,-2],[2,-3]], Du=1, Dv=10: continuum band 1/5<q<1/2 non-empty, no admissible Neumann mode at L=pi; mode appears at L=2pi)", "turing_scope/lean/Audit.lean (+ docs/turing-scope.md): integer-model determinant/trace and mode-tail algebra, mutants", "scopedesk/bench/audit/oracle_layer_audit_v1_2.json (NCA oracle 50/50 incl. these families)"],
   found="The record's textbook inequality is a continuum statement; on a finite domain with a stated boundary type only the admissible modes count, so a system can satisfy the inequality and have no growing mode (witness above), and mode sets differ between Neumann, Dirichlet and periodic boundaries and between 1-D and 2-D domains (bench witnesses).",
   not_est="Linear stability of a DECLARED two-species Jacobian only; no nonlinear pattern, no biology, no PDE theorem (Lean covers the integer algebra, not the equivalence with the PDE). Finite-domain mode quantisation is classical (textbook-derivable), so this is not a discovery. The record's own text names no boundary condition or domain shape (those are additions listed by the oracle's gate).",
   codex="Bench rows: yes (" + CODEX_BENCH + "). Status wording: no. Turing scorecard fidelity: CODEX-SCORECARD-REVIEW.md (work/codex-api) is a separate review."),
 "turing-wavelength": dict(status="a", ev=[B + "key.jsonl (family wavelength_formula_licence, 14 items)", "scopedesk/oracles gate.wavelength_licence audit: scopedesk/bench/audit/oracle_layer_audit_v1_2.json"],
   found="lambda_c = 2*pi/k_c is not the wavelength of the fastest-growing ADMISSIBLE mode on a finite domain: the bench items show cases where the two differ by more than 10% (near-onset and large-domain conditions in the record are qualitative; the 10% tolerance is the benchmark's declared operationalisation).",
   not_est="Linear fastest-growing mode only (no nonlinear selection, which the NCA study found to differ from the linear prediction in many cases); the 10% threshold and the 'fastest-growing = largest real part' convention are ours; five boundary/length-notation wording issues are disclosed in FROZEN.md.", codex="Bench rows: yes (" + CODEX_BENCH + "). Status wording: no."),
 "turing-morphogen-hypothesis": dict(status="d", ev=["records/turing-morphogen-hypothesis.json (delphi:hypothesisType principle-or-framework; context: 'a framework rather than a mathematical proposition')"], found=None,
   not_est="Nothing is checked. The record declares itself a framework with no canonical formalisation.", codex="no"),
 "fisher-kpp-speed": dict(status="a", ev=[B + "key.jsonl (family fisher_kpp_speed, 16 items)", B + "key_verification.json (independent finite-difference front speeds: logistic ~2, pushed cubic alpha=10/3: 2.062 vs analytic 2.066; Allee 0.2817 vs 0.2828)"],
   found="The speed 2*sqrt(sD) is the pulled-front speed for KPP growth; for a strong-Allee (bistable) term the front is pushed and slower, and for u(1-u)(1+alpha u) it holds iff alpha<=2 (Hadeler-Rothe); the exact-KPP inequality f(u)<=f'(0)u fails for 1<alpha<=2 although the speed still holds (benign items).",
   not_est="Declared reaction terms on the line with wide initial data; the minimal-speed theorem was cited (Crooks-Grinfeld 2020), not reproved; PDE speeds are finite-time estimates.", codex="Bench rows: yes (" + CODEX_BENCH + "; KPP checked by exact front-profile residuals). Status wording: no."),
 "kimura-fixation-probability": dict(status="a", ev=[B + "key.jsonl (family kimura_regime, 16 items)", B + "key_verification.json (power-iteration of the exact haploid Wright-Fisher chain)"],
   found="The record's diffusion formula and its neutral limit 1/N are approximations: within a 10% criterion against the exact haploid Wright-Fisher one-copy fixation probability, the neutral value fails when Ns is not small and the diffusion formula fails at small N with large s (bench witnesses).",
   not_est="Haploid WF chain with binomial sampling after selection (the record concerns the diploid diffusion setting); 10% is a declared tolerance. facebookresearch/atlas-lean (MathlibExt/Biology/PopulationGenetics/Diffusion/KimuraFixationProcess.lean) formalizes related Kimura material; we did not compare statements.", codex="Bench rows: yes (" + CODEX_BENCH + "). Status wording: no."),
 "hamilton-rule": dict(status="a", ev=[B + "key.jsonl (family hamilton_rule_form, 16 items)", "lean_price/Price.lean (queller, hamilton_form; README with prior-art correction; commit e776030)", "experiments/price_probe/ on work/codex-api (Codex's own Price/Hamilton probe; separate artifact)"],
   found="The sign of rb-c equals the sign of the selection covariance exactly when w is exactly linear in own and partner genotype with an orthogonal residual (regression form, which the record's context names); with an interaction (synergy) term and the additive b,c the rule can have the wrong sign (bench witnesses). The record states both readings, so this is an ambiguity the textbook form hides, not a fault in the record.",
   not_est="Haploid pairing model with Malthusian payoffs and a stated pairing kernel; the one-way/algebraic statement only; no claim about real populations or about the generality debate (Nowak et al. 2010 vs Gardner et al. 2011). Price/Queller algebra duplicates existing formalization (atlas-lean Selection.lean has Price); our Queller-form corollary was not found there (code search, not exhaustive).", codex="Bench rows: yes (" + CODEX_BENCH + "). Lean node: lean_price reviewed by the critic only; Codex's separate price_probe is its own work. Status wording: no."),
 "maynardsmith-hawk-dove": dict(status="b", ev=[B + "key.jsonl (family hawk_dove_ess, 16 items)", B + "key_verification.json (replicator-dynamics check)"],
   found=None, not_est="Exact check (E(p*,q)-E(q,q)=(C/2)(p*-q)^2>0) that for C>V the mixed strategy p*=V/C is an ESS and that for C<V p*>1 is not a probability (the record's own 'C > V' scope); the payoff matrix is the one stated in the convention text. Not established: anything beyond the symmetric two-strategy game, finite populations, or biology.", codex="Bench rows: yes (" + CODEX_BENCH + "). Status wording: no."),
 "fisher-ftns": dict(status="c", ev=["lean_price/Price.lean (Price identity; the z=w case gives Var(w) but is not stated as a separate theorem)", "facebookresearch/atlas-lean MathlibExt/Biology/PopulationGenetics/Selection.lean (Price + Fisher FTNS in the exact haploid form) - existing work, not ours", "experiments/price_probe/ on work/codex-api (Codex: fitness_selection is total-variance selection, NOT additive-genetic Fisher FTNS)"],
   found=None, not_est="Only the Price-identity algebra (selection term = covariance with fitness) is machine-checked, with standard axioms and two failing mutants. The record's statement is about ADDITIVE genetic variance and 'partial change'; that partition (and any diploid, multilocus or epistatic setting) is NOT formalized by us. Our Price node duplicates atlas-lean's. No scope-failure was exhibited by a bench family for this record.", codex="Price probe by Codex is separate; Codex's price-target review: planning/rethink/CODEX-21-CLAIM-FREEZE-REVIEW.md and price_probe README. Status wording: no."),
 "kimura-neutral-theory": dict(status="d", ev=["records/kimura-neutral-theory.json (delphi:hypothesisType empirical-law; context: 'not a mathematical statement; an empirical claim')"], found=None, not_est="Nothing is checked; the record declares an empirical claim tested with dN/dS.", codex="no"),
}
NA = {"fisher-infinitesimal": "no bench family, oracle or Lean node attempted", "fisher-sex-ratio": "not attempted", "hamilton-haplodiploidy": "not attempted (record typed 'conjecture'; relatedness coefficients are stated as proved)",
      "hamilton-lmc": "not attempted", "hamilton-senescence": "not attempted", "kimura-fixation-time": "not attempted (the bench's kimura_regime family tests the fixation PROBABILITY only)",
      "kimura-heterozygosity": "not attempted", "kimura-substitution-rate": "not attempted (k=mu arithmetic; trivial but not checked)", "maynardsmith-ess": "not attempted (general ESS definition; only the Hawk-Dove instance is checked)",
      "maynardsmith-hitchhiking": "not attempted", "maynardsmith-twofold-cost": "not attempted", "maynardsmith-war-of-attrition": "not attempted"}
LABEL = {"a": "(a) CHECKED-SCOPE-FOUND", "b": "(b) CHECKED-HOLDS-AS-DECLARED", "c": "(c) FORMAL-NODE-ONLY", "d": "(d) SELF-DECLARED NON-FORMAL / EMPIRICAL", "e": "(e) NOT ATTEMPTED"}
def canon(x): return json.dumps(x, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
rows = []
for f in sorted(glob.glob(os.path.join(D, "records", "*.json"))):
    d = json.load(open(f)); cid = d["claim_id"]; fl = d["record"]["fields"]
    s = ST[cid] if cid in ST else dict(status="e", ev=[], found=None, not_est=NA[cid], codex="no")
    ev_ok = []
    import re
    for e in s["ev"]:
        external = ("work/codex-api" in e) or ("atlas-lean" in e)
        paths = re.findall(r"[A-Za-z0-9_./-]+(?:\.(?:jsonl|json|lean|md|py)|/)", e.split(" (")[0] if not external else e)
        paths = [p for p in paths if "/" in p or "." in p]
        status = "other branch/repo (not checked here)" if external else ({p: (os.path.exists(os.path.join(ROOT, p)) or os.path.exists(os.path.join(D, p))) for p in paths} or "no file path")
        ev_ok.append({"evidence": e, "path_check": status})
    rows.append({"claim_id": cid, "claim_uri": d["record"]["claim"], "content_sha256": hashlib.sha256(canon({"claim": d["record"]["claim"], "fields": fl}).encode()).hexdigest(),
      "raw_tool_text_sha256": d["raw_text_sha256"], "retrieved_utc": d["retrieved_utc"], "hypothesis_type": fl.get("delphi:hypothesisType"),
      "headline_point1_dct_description": fl.get("dct:description"), "label": fl.get("rdfs:label"), "source_point2_dct_source": fl.get("dct:source"), "seeAlso": fl.get("rdfs:seeAlso"),
      "math_point7_skos_notation": fl.get("skos:notation"), "record_context": fl.get("delphi:context"),
      "status": LABEL[s["status"]], "status_code": s["status"], "evidence": ev_ok, "scope_finding": s["found"], "does_not_establish": s["not_est"], "codex_reviewed": s["codex"],
      "assessments_in_record": len(d["record"].get("assessments", []))})
order = {"a": 0, "b": 1, "c": 2, "d": 3, "e": 4}; rows.sort(key=lambda r: (order[r["status_code"]], r["claim_id"]))
counts = {LABEL[k]: sum(r["status_code"] == k for r in rows) for k in "abcde"}
assert len(rows) == 21 and sum(counts.values()) == 21
missing = [e for r in rows for e in r["evidence"] if isinstance(e["path_check"], dict) and not all(e["path_check"].values())]
out = {"scorecard": "SCORECARD v0", "n_claims": 21, "domains": "18 population-genetics + 3 Turing math-domain Delphi records (Thompson's 71 math-bearing records are NOT included)", "counts": counts, "evidence_paths_missing_in_checkout": [(m["evidence"][:80], m["path_check"]) for m in missing],
       "global_limits": ["Source-correspondence of each record to the original paper is NOT reviewed.", "Statuses and 'does not establish' text are the critic's single-reader judgement (not computed).", "Codex has not approved this scorecard; 'Codex-reviewed' refers to the cited artifacts only.",
                         "All checks are of DECLARED models (bench conventions, Lean statements); nothing here validates any biological claim; the host's B0-B3 buckets are not used.", "Delphi LLM assessments are not used as evidence (0 assessments present in these records)."],
       "rows": rows}
json.dump(out, open(os.path.join(D, "scorecard.json"), "w"), indent=1)
with open(os.path.join(D, "SCORECARD.md"), "w") as f:
    f.write("# SCORECARD v0 (critic; generated by build_scorecard.py - do not hand-edit)\n\n21 math-domain Delphi claims (18 population-genetics + 3 Turing). Status counts: " + "; ".join(f"{k}: {v}" for k, v in counts.items()) + f". **{counts[LABEL['e']]} of 21 are NOT ATTEMPTED.**\n\n")
    f.write("Global limits: " + " ".join(out["global_limits"]) + "\n\n| claim | status | evidence in short | Codex-reviewed |\n|---|---|---|---|\n")
    for r in rows: f.write(f"| {r['claim_id']} | {r['status']} | {'; '.join(e['evidence'].split(' (')[0] for e in r['evidence']) or '-'} | {r['codex_reviewed'][:60]} |\n")
    f.write("\n## Rows\n")
    for r in rows:
        f.write(f"\n### {r['claim_id']} - {r['status']}\n- content sha256 `{r['content_sha256']}` (canonical JSON of record fields); retrieved {r['retrieved_utc'][:19]}Z; type {r['hypothesis_type']}\n- Point 1 (headline, as in record): {r['headline_point1_dct_description']}\n- Point 2 (source, as in record): {r['source_point2_dct_source']}\n- Point 7 (math, as in record): `{r['math_point7_skos_notation']}`\n")
        f.write("- Evidence: " + ("; ".join(e["evidence"] for e in r["evidence"]) or "none") + "\n")
        if r["scope_finding"]: f.write(f"- Scope finding: {r['scope_finding']}\n")
        f.write(f"- Does NOT establish: {r['does_not_establish']}\n- Codex-reviewed: {r['codex_reviewed']}\n")
print(json.dumps(counts, indent=1)); print("missing evidence paths:", out["evidence_paths_missing_in_checkout"])
