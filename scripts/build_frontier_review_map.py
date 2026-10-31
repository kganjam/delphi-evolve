"""Export the pinned critic inventory with explicit, separately authored review states.

This checks transcription and counts. It does not run theorem provers or judge
the truth of a source. No network calls or writes outside the named outputs.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
REV = "0c2d4f258ea82f25115b543493b090a906550f08"
BASE = "scopedesk/scorecard/"
URL = "https://github.com/kganjam/delphi-evolve/blob/"
BENCH = URL + "70c12544a952fbdcfa370e8249c980092b522785/scopedesk/bench/v1_2/FROZEN.md"
PROOF = URL + "b4e60db91050ccaec8cd16f8f57373690c5efa7b/experiments/price_probe/Price.lean"
PROOF_RECEIPT = URL + "b4e60db91050ccaec8cd16f8f57373690c5efa7b/artifacts/integration/codex-api/price-probe.json"
SHORT = {
    "fisher-kpp-speed": "Wave speed", "fisher-ftns": "Fisher partial change",
    "fisher-infinitesimal": "Infinitesimal model", "fisher-sex-ratio": "Sex ratio",
    "hamilton-rule": "Hamilton regression", "hamilton-haplodiploidy": "Haplodiploidy",
    "hamilton-lmc": "Local mate competition", "hamilton-senescence": "Senescence",
    "kimura-fixation-probability": "Fixation probability", "kimura-fixation-time": "Fixation time",
    "kimura-heterozygosity": "Heterozygosity", "kimura-substitution-rate": "Substitution rate",
    "kimura-neutral-theory": "Neutral theory", "maynardsmith-ess": "General ESS",
    "maynardsmith-hawk-dove": "Hawk–Dove", "maynardsmith-hitchhiking": "Hitchhiking",
    "maynardsmith-twofold-cost": "Cost of sex", "maynardsmith-war-of-attrition": "War of attrition",
    "turing-ddi": "Linear instability", "turing-wavelength": "Onset wavelength",
    "turing-morphogen-hypothesis": "Morphogen mechanism",
}
NOTES = {
    "turing-ddi": ("Additional domain condition made explicit", "The continuum inequality does not ensure an unstable mode on a particular finite domain.", "Specify the domain and boundary conditions; check the determinant at admissible modes.", "index.html"),
    "turing-wavelength": ("Declared scope operationalized", "Near onset and large domain are already in the record. Our tolerance and finite-mode comparison are additional benchmark choices.", "Map the onset formula to a specified domain and distinguish a linear mode from the nonlinear selected pattern.", None),
    "fisher-kpp-speed": ("Alternative-kinetics scope check", "The record already specifies logistic growth and warns that Allee effects change the speed.", "Specify kinetics and initial conditions before importing a front-speed formula.", None),
    "kimura-fixation-probability": ("Approximation regime checked", "The record declares a diffusion approximation. The benchmark's finite haploid chain needs an explicit mapping to its diploid convention. Neutral fixation equals initial frequency exactly.", "Align ploidy and selection conventions, then compare the approximation with the specified finite chain.", None),
    "hamilton-rule": ("Conditional regression corollary compiled", "The record explicitly uses regression coefficients. A witness with fixed causal payoff coefficients does not refute that identity.", "Review the genotype, transmission and regression mapping for the intended application.", PROOF_RECEIPT),
    "maynardsmith-hawk-dove": ("Declared game checked", "The checked ESS calculation concerns the specified symmetric payoff matrix and 0 < V < C.", "Supply the payoff interpretation and test whether role asymmetries change the applicable game.", None),
    "fisher-ftns": ("Related formal lemma; target unestablished", "Price and total-fitness variance are available. Additive genetic variance and the fixed-average-effect partial-change target are not established by our probe.", "Freeze genetic projection and partial-change semantics, then prove the missing correspondence.", PROOF_RECEIPT),
    "kimura-neutral-theory": ("Empirical question", "The estimator is formalizable. A model proof alone cannot settle what fraction of substitutions in nature is neutral.", "Specify a population, data, estimator assumptions and a discriminating analysis.", None),
    "turing-morphogen-hypothesis": ("Target needs specification", "No single theorem target is specified here. A matching pattern alone does not identify its mechanism.", "Choose a biological system and measurements that distinguish reaction–diffusion from alternatives.", None),
}


def read_json(path):
    return json.loads(subprocess.check_output(["git", "show", f"{REV}:{BASE}{path}"], cwd=ROOT))


def canonical_hash(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    score = read_json("scorecard.json")
    rows = score["rows"]
    assert len(rows) == 21 and len({r["claim_id"] for r in rows}) == 21
    assert {r["claim_id"] for r in rows} == set(SHORT)
    assert Counter(r["status_code"] for r in rows) == dict(a=5, b=1, c=1, d=2, e=12)
    nodes, checks = [], []
    for row in sorted(rows, key=lambda x: x["claim_id"]):
        cid = row["claim_id"]
        record = read_json(f"records/{cid}.json")["record"]
        fields = record["fields"]
        digest = canonical_hash({"claim": record["claim"], "fields": fields})
        assert digest == row["content_sha256"], cid
        for target, source in (("headline_point1_dct_description", "dct:description"),
                               ("math_point7_skos_notation", "skos:notation"),
                               ("source_point2_dct_source", "dct:source"),
                               ("record_context", "delphi:context")):
            assert row[target] == fields[source], (cid, target)
        assert not record.get("assessments") and row["assessments_in_record"] == 0
        category = {"a": "checked", "b": "checked", "c": "related", "d": "question", "e": "unchecked"}[row["status_code"]]
        if cid.startswith("turing") or cid == "fisher-kpp-speed":
            group = "Pattern formation"
        elif cid.startswith("kimura") or cid == "maynardsmith-hitchhiking":
            group = "Molecular evolution"
        elif cid.startswith("maynardsmith"):
            group = "Evolutionary games"
        else:
            group = "Selection and inheritance"
        title, finding, action, receipt = NOTES.get(cid, (
            "No check recorded here", "This inventory contains no corresponding check. That does not mean the claim is unknown to science.",
            "Review the source-to-statement mapping, choose a precise target and record its acceptance conditions.", None))
        evidence = []
        if category == "checked":
            evidence.append({"label": "Frozen benchmark and limitations", "url": BENCH, "kind": "declared-model benchmark"})
        if receipt:
            evidence.append({"label": "Explore exact calculation" if receipt == "index.html" else "Recorded compilation receipt", "url": receipt, "kind": "browser calculation" if receipt == "index.html" else "recorded compilation"})
        if cid in ("hamilton-rule", "fisher-ftns"):
            evidence.append({"label": "Inspect Price / Hamilton source", "url": PROOF, "kind": "related formal source"})
        nodes.append({"id": cid, "short": SHORT[cid], "label": row["label"], "group": group,
                      "category": category, "review_title": title, "finding": finding, "next_action": action,
                      "statement": fields["dct:description"], "math": fields["skos:notation"],
                      "context": fields["delphi:context"], "source": fields["dct:source"],
                      "record_sha256": digest, "source_url": URL + REV + "/" + BASE + f"records/{cid}.json",
                      "evidence": evidence})
        checks.append({"id": cid, "content_sha256": digest, "field_copy_checks": 4, "assessments": 0})
    data = {"title": "Delphi Frontier · review map", "source_revision": REV,
            "scope": "21 extracted records; colors describe this project's review coverage, not scientific truth.",
            "counts": dict(Counter(n["category"] for n in nodes)), "nodes": nodes,
            "bridges": [
                {"from": "fisher-ftns", "to": "hamilton-rule", "kind": "proposed", "label": "Shared Price route; Fisher genetic partition remains unestablished"},
                {"from": "turing-ddi", "to": "turing-wavelength", "kind": "scope", "label": "Both require a specified admissible spectrum; not a proof edge"},
                {"from": "turing-ddi", "to": "turing-morphogen-hypothesis", "kind": "proposed", "label": "From mathematical mechanism to biological identification: measurements required"},
                {"from": "kimura-fixation-probability", "to": "kimura-neutral-theory", "kind": "proposed", "label": "Model-to-world transfer requires population evidence"},
                {"from": "maynardsmith-hawk-dove", "to": "maynardsmith-ess", "kind": "scope", "label": "A checked special case does not establish the general target"},
            ]}
    receipt = {"source_revision": REV, "review_type": "non-blinded transcription and count audit",
               "n_records": len(nodes), "field_copy_checks": 84, "original_counts": dict(Counter(r["status_code"] for r in rows)),
               "review_coverage_counts": data["counts"], "records": checks,
               "limits": "Does not establish source-to-paper faithfulness, mathematical validity, empirical truth, novelty or a new prover/evaluation result."}
    outputs = {ROOT / "site/review/frontier-data.json": data,
               ROOT / "artifacts/integration/codex-api/scorecard-v0-record-audit.json": receipt}
    for path, obj in outputs.items():
        content = json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
        if args.check:
            assert path.read_text() == content, str(path)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
    print(json.dumps({"records": len(nodes), "field_copy_checks": 84, "counts": data["counts"], "mode": "check" if args.check else "write"}))


if __name__ == "__main__":
    main()
