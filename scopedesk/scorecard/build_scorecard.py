"""SCORECARD v0 builder (critic, director follow-up 9). One row per math-domain Delphi claim (18 population-genetics + 3 Turing) read from the committed
records/ (fetched once from the hosted Delphi MCP, local source, by fetch_records.py). Status taxonomy: (a) CHECKED-SCOPE-FOUND, (b) CHECKED-HOLDS-AS-DECLARED,
(c) FORMAL-NODE-ONLY, (d) SELF-DECLARED NON-FORMAL / EMPIRICAL, (e) NOT ATTEMPTED. Statuses and limits are the critic's judgement written below, NOT computed;
the script copies record fields, hashes them, checks that every evidence path exists in this checkout (or is marked as a path on another branch), and prints counts.
Usage: python3 -I build_scorecard.py"""
import glob, hashlib, json, os, sys
D = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(D, "..", ".."))
B = "scopedesk/bench/v1_2/"
CODEX_BENCH = "Codex (different model family) recomputed all bench keys with its own code, non-blinded (planning/rethink/CODEX-BENCH-V1-1-REVIEW.md @ d23663a; frozen-127 metadata check @ 6c96810, work/codex-api)"
CR = "Codex v0 review (planning/rethink/CODEX-SCORECARD-V0-REVIEW.md @ 4fe9fb7, non-blinded): record transcription (hash + copied fields) passes; corrected description below is the one Codex approved. Bench rows: " + CODEX_BENCH
ST = {
 "turing-ddi": dict(status="a", kind="additional domain/spectrum condition made explicit", ev=[B + "key.jsonl (families turing_finite_domain 21 items, turing_2d_rectangle 15)", "turing_scope/examples/short_L_pi.json (J=[[1,-2],[2,-3]], Du=1, Dv=10: continuum band 1/5<q<1/2 non-empty, no admissible Neumann mode at L=pi; a mode appears at L=2pi)", "turing_scope/lean/Audit.lean (+ docs/turing-scope.md): integer-model determinant/trace and mode-tail algebra, mutants", "scopedesk/bench/audit/oracle_layer_audit_v1_2.json (NCA oracle 50/50 incl. these families)"],
   found="The record gives a continuum instability criterion on a fixed domain without specifying the admissible spectrum; the witness shows that the determinant at an ACTUAL admissible mode is the right target, and that mode sets differ between Neumann, Dirichlet and periodic boundaries and between 1-D and 2-D domains.",
   not_est="Linear stability of a DECLARED two-species Jacobian only; no full PDE theorem, no nonlinear-pattern conclusion, no biology, no historical novelty (finite-domain mode quantisation is classical).", codex=CR),
 "turing-wavelength": dict(status="a", kind="declared scope operationalized in a benchmark", ev=[B + "key.jsonl (family wavelength_formula_licence, 14 items)", "scopedesk/bench/audit/oracle_layer_audit_v1_2.json (gate.wavelength_licence)"],
   found="The record's context already states near onset and large domain; the benchmark operationalizes them by comparing lambda_c with the fastest ADMISSIBLE finite-domain linear mode at a 10% tolerance. This does not discover that conditions were omitted.",
   not_est="Keeps three things distinct: the onset formula, the linear fastest mode, and a nonlinear selected pattern (the NCA study found the latter often differs from the linear prediction). The 10% tolerance and the 'largest real part' convention are ours.", codex=CR),
 "turing-morphogen-hypothesis": dict(status="d", kind="framework", ev=["records/turing-morphogen-hypothesis.json (delphi:hypothesisType principle-or-framework; context: 'a framework rather than a mathematical proposition')"], found=None,
   not_est="No single theorem target is specified in this record (that is not a proof that it cannot be formalized). It would have to be narrowed to an identified biological system and discriminating measurements.", codex="Codex v0 review: agrees (framework; no single theorem target). Transcription passes."),
 "fisher-kpp-speed": dict(status="a", kind="scope stress test with specified alternative kinetics", ev=[B + "key.jsonl (family fisher_kpp_speed, 16 items)", B + "key_verification.json (independent finite-difference front speeds: logistic ~2, pushed cubic alpha=10/3: 2.062 vs analytic 2.066; Allee 0.2817 vs 0.2828)"],
   found="The record specifies logistic growth and says Allee effects change the speed; the bench compares it with alternative reaction terms (strong Allee; u(1-u)(1+alpha u), where 2*sqrt(sD) holds iff alpha<=2). These are out-of-model comparisons, not a missing condition and not an erroneous theorem.",
   not_est="Declared reaction terms on the line with wide initial data; exact travelling-profile residuals and PDE speeds do not prove minimal-speed selection or a PDE existence theorem (cited, not reproved).", codex=CR),
 "kimura-fixation-probability": dict(status="a", kind="approximation/regime check with explicit ploidy and parameter mapping", ev=[B + "key.jsonl (family kimura_regime, 16 items)", B + "key_verification.json (power-iteration of the exact haploid Wright-Fisher chain)"],
   found="The record states a diffusion approximation (diploid convention). The bench uses a finite HAPLOID Wright-Fisher chain: in a neutral finite chain eventual fixation equals initial frequency EXACTLY (1/N for one copy of N haploid copies; 1/(2N) for N diploid individuals); using that neutral value under nonzero selection is an approximation, and the diffusion formula can be off at small N and large s (bench witnesses, 10% tolerance).",
   not_est="The 10% tolerance is a benchmark choice, not a universal validity boundary; ploidy mapping between the chain and the record is not validated; atlas-lean (MathlibExt/Biology/PopulationGenetics/Diffusion/KimuraFixationProcess.lean) formalizes related material that we did not compare.", codex=CR),
 "hamilton-rule": dict(status="a", kind="regression-versus-additive-coefficient distinction checked", ev=[B + "key.jsonl (family hamilton_rule_form, 16 items)", "lean_price/Price.lean (queller, hamilton_form; README with prior-art correction; commit e776030)", "experiments/price_probe/ on work/codex-api (Codex's own Price/Hamilton probe; separate artifact)"],
   found="The record defines b, c, r as REGRESSION coefficients and distinguishes this from the original additive assumptions. Our compiled corollary: sign(Cov(w,z)) = sign(r*b - c) under exact linearity in own and partner genotype with an orthogonal residual. A synergy witness with FIXED ADDITIVE payoff coefficients is not a counterexample to the regression identity; it illustrates why the additive reading differs.",
   not_est="No defect in this record and no complete empirical test. The corollary is conditional (sufficient covariance/orthogonality conditions; sign agreement can also occur outside them, so 'exactly when' was overstated in v0). Haploid pairing model with a stated kernel. Price/Queller algebra duplicates existing formalization in part (atlas-lean has Price).", codex=CR),
 "maynardsmith-hawk-dove": dict(status="b", kind="declared game checked on the tested cases", ev=[B + "key.jsonl (family hawk_dove_ess, 16 items)", B + "key_verification.json (replicator-dynamics check)"],
   found=None, not_est="The matrix and C>V are in the record; the checked algebra (E(p*,q)-E(q,q)=(C/2)(p*-q)^2>0) concerns the symmetric two-strategy model, with the physical-payoff condition 0<V<C retained. Not validation in animal populations, finite populations or asymmetric contests.", codex=CR),
 "fisher-ftns": dict(status="c", kind="related formal lemma; target not established", ev=["lean_price/Price.lean (Price identity; the z=w case gives Var(w) but is not stated as a separate theorem)", "facebookresearch/atlas-lean MathlibExt/Biology/PopulationGenetics/Selection.lean (Price and a haploid total-variance selection identity; its docs exclude the diploid additive-genetic statement) - existing work, not ours", "experiments/price_probe/ on work/codex-api (Codex: fitness_selection is total-variance selection, NOT additive-genetic Fisher FTNS)"],
   found=None, not_est="A Price identity and a total-fitness-variance selection identity do NOT establish additive genetic variance or Fisher's partial-change target; the record already states those qualifications. Do not count this as a successful theorem or a faithful target attempt without a target/run receipt; the genetic projection and fixed-average-effect semantics must be frozen before any prover run.", codex="Codex v0 review: target not established; related formal artifact available (CODEX-SCORECARD-V0-REVIEW.md @ 4fe9fb7). Transcription passes."),
 "kimura-neutral-theory": dict(status="d", kind="empirical claim", ev=["records/kimura-neutral-theory.json (delphi:hypothesisType empirical-law; context: 'not a mathematical statement; an empirical claim'; record gives the McDonald-Kreitman estimator)"], found=None,
   not_est="An empirical claim about the world can have formalizable estimators, so it is NOT 'not formalizable'; but a model proof alone cannot settle it. It needs a specified population, estimator, denominator conditions and data.", codex="Codex v0 review: agrees (CODEX-SCORECARD-V0-REVIEW.md @ 4fe9fb7). Transcription passes."),
}
NA = {"fisher-infinitesimal": "no check recorded in this scorecard", "fisher-sex-ratio": "not attempted", "hamilton-haplodiploidy": "not attempted (record typed 'conjecture'; relatedness coefficients are stated as proved)",
      "hamilton-lmc": "not attempted", "hamilton-senescence": "not attempted", "kimura-fixation-time": "not attempted (the bench's kimura_regime family tests the fixation PROBABILITY only)",
      "kimura-heterozygosity": "not attempted", "kimura-substitution-rate": "not attempted (k=mu arithmetic; trivial but not checked)", "maynardsmith-ess": "not attempted (general ESS definition; only the Hawk-Dove instance is checked)",
      "maynardsmith-hitchhiking": "not attempted", "maynardsmith-twofold-cost": "not attempted", "maynardsmith-war-of-attrition": "not attempted"}
LABEL = {"a": "BENCHMARK-LINKED", "b": "BENCHMARK-LINKED", "c": "RELATED FORMAL LEMMA, TARGET NOT ESTABLISHED", "d": "EMPIRICAL / FRAMEWORK", "e": "NO CHECK IN THIS SCORECARD"}
LEGACY = {"a": "(a) CHECKED-SCOPE-FOUND [director taxonomy; Codex: overclaims]", "b": "(b) CHECKED-HOLDS-AS-DECLARED", "c": "(c) FORMAL-NODE-ONLY [Codex: target not established]", "d": "(d) SELF-DECLARED NON-FORMAL / EMPIRICAL", "e": "(e) NOT ATTEMPTED"}
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
      "status": LABEL[s["status"]], "check_kind": s.get("kind", ""), "legacy_status_v0": LEGACY[s["status"]], "status_code": s["status"], "evidence": ev_ok, "scope_finding": s["found"], "does_not_establish": s["not_est"], "codex_reviewed": s["codex"],
      "assessments_in_record": len(d["record"].get("assessments", []))})
order = {"a": 0, "b": 1, "c": 2, "d": 3, "e": 4}; rows.sort(key=lambda r: (order[r["status_code"]], r["claim_id"]))
counts = {}
for k in "abcde": counts[LABEL[k]] = counts.get(LABEL[k], 0) + sum(r["status_code"] == k for r in rows)
assert len(rows) == 21 and sum(counts.values()) == 21 and counts[LABEL['a']] == 6
missing = [e for r in rows for e in r["evidence"] if isinstance(e["path_check"], dict) and not all(e["path_check"].values())]
out = {"scorecard": "SCORECARD v0", "n_claims": 21, "domains": "18 population-genetics + 3 Turing math-domain Delphi records (Thompson's 71 math-bearing records are NOT included)", "counts": counts, "evidence_paths_missing_in_checkout": [(m["evidence"][:80], m["path_check"]) for m in missing],
       "global_limits": ["Source-correspondence of each record to the original paper is NOT reviewed.", "Statuses and 'does not establish' text are the critic's single-reader judgement (not computed).", "Codex reviewed v0 (planning/rethink/CODEX-SCORECARD-V0-REVIEW.md @ 4fe9fb7, non-blinded): 21 hashes and 84 copied fields pass; it approves the CORRECTED descriptions in this version, not the original category labels or an aggregate biological success rate.",
                         "All checks are of DECLARED models (bench conventions, Lean statements); nothing here validates any biological claim; the host's B0-B3 buckets are not used.", "Delphi LLM assessments are not used as evidence (0 assessments present in these records)."],
       "rows": rows}
json.dump(out, open(os.path.join(D, "scorecard.json"), "w"), indent=1)
with open(os.path.join(D, "SCORECARD.md"), "w") as f:
    f.write("# SCORECARD v0 (critic; generated by build_scorecard.py - do not hand-edit)\n\n21 math-domain Delphi claims (18 population-genetics + 3 Turing). Status counts: " + "; ".join(f"{k}: {v}" for k, v in counts.items()) + f". **Use this wording (Codex-approved): '21 extracted records: 6 linked to scope-check benchmark families, 1 with a related formal lemma but its target unestablished, 2 requiring empirical/framework treatment, 12 without a corresponding check.' If an 'attempted' count is wanted (director ruling): 7 artifact-linked records (6 benchmark-linked + 1 related lemma that lacks a faithful target check); statuses are single-reader and Codex reviewed the corrected descriptions. The 12 are a project backlog, not 12 open scientific problems; the 6 are NOT 6 false laws, omitted assumptions or Delphi errors.**\n\n")
    f.write("Global limits: " + " ".join(out["global_limits"]) + "\n\n| claim | status | evidence in short | Codex-reviewed |\n|---|---|---|---|\n")
    for r in rows: f.write(f"| {r['claim_id']} | {r['status']} | {'; '.join(e['evidence'].split(' (')[0] for e in r['evidence']) or '-'} | {r['codex_reviewed'][:60]} |\n")
    f.write("\n## Rows\n")
    for r in rows:
        f.write(f"\n### {r['claim_id']} - {r['status']}\n- content sha256 `{r['content_sha256']}` (canonical JSON of record fields); retrieved {r['retrieved_utc'][:19]}Z; type {r['hypothesis_type']}\n- Point 1 (headline, as in record): {r['headline_point1_dct_description']}\n- Point 2 (source, as in record): {r['source_point2_dct_source']}\n- Point 7 (math, as in record): `{r['math_point7_skos_notation']}`\n")
        f.write("- Evidence: " + ("; ".join(e["evidence"] for e in r["evidence"]) or "none") + "\n")
        if r["scope_finding"]: f.write(f"- Scope finding: {r['scope_finding']}\n")
        f.write(f"- Does NOT establish: {r['does_not_establish']}\n- Codex-reviewed: {r['codex_reviewed']}\n")
print(json.dumps(counts, indent=1)); print("missing evidence paths:", out["evidence_paths_missing_in_checkout"])
