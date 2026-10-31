"""Nonblinded review of changes from an already audited benchmark snapshot.

Read immutable git blobs only; no critic generator/oracle code is imported.
This is a metadata/statement-change audit, not a new full numerical verification.
Run with the repository's systemd process/memory/runtime caps.
"""
import hashlib
import json
import re
import subprocess
from collections import Counter
from datetime import datetime
from fractions import Fraction as F
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from sklearn.dummy import DummyClassifier
from sklearn.tree import DecisionTreeClassifier

OLD = "e7760307f4cad2040715279949a94ead8437735d"
NEW = "8f4d20c0dd66d410d3b6250c75236ef54fd7d74c"
DIRECTOR = "ecad28a2a09c69eb3e201912f71f86e5d7833398"
ELECTRIC = "bec9a216b867dd927dd4d621ef671118ebd04768"
OUTPUT = Path("artifacts/integration/codex-api/benchmark-v1-2-changes-review.json")


@lru_cache(None)
def blob(revision, name):
    prefix = "scopedesk/bench/v1_1/" if revision == OLD else "scopedesk/bench/v1_2/"
    return subprocess.check_output(["git", "show", f"{revision}:{prefix}{name}"], timeout=15)


def records(revision, name):
    return [json.loads(line) for line in blob(revision, name).splitlines()]


def main():
    old_full = {r["id"]: r for r in records(OLD, "instances_full.jsonl")}
    old_key = {r["id"]: r for r in records(OLD, "key.jsonl")}
    full = {r["id"]: r for r in records(NEW, "instances_full.jsonl")}
    pub = records(NEW, "instances_public.jsonl")
    key = {r["id"]: r for r in records(NEW, "key.jsonl")}
    payload = records(NEW, "model_payload.jsonl")
    idmap = json.loads(blob(NEW, "id_map_PRIVATE.json"))
    split = json.loads(blob(NEW, "split.json"))
    inverse = {new: old for old, new in idmap.items()}
    hashes = []
    for line in blob(NEW, "KEY.sha256").decode().splitlines():
        expected, name = line.split()
        actual = hashlib.sha256(blob(NEW, name)).hexdigest()
        hashes.append({"path": name, "sha256": actual, "matches": actual == expected})

    changes = []
    for row in pub:
        nid = row["id"]
        oid = inverse[nid]
        previous, current = old_full[oid], full[nid]
        changes.append({
            "legacy_id": oid, "id": nid,
            "structured_unchanged": previous["hidden"]["structured"] == current["hidden"]["structured"],
            "verdict_unchanged": old_key[oid]["verdict"] == key[nid]["verdict"],
            "verdict_old": old_key[oid]["verdict"], "verdict_new": key[nid]["verdict"],
            "prompt_changed": previous["request_text"] != current["request_text"],
            "request_prefix_changed": previous["request_text"].split(" Conventions:")[0] != current["request_text"].split(" Conventions:")[0],
            "violated_conditions_old": old_key[oid].get("violated_conditions"),
            "violated_conditions_new": key[nid].get("violated_conditions"),
        })
    ids = [r["id"] for r in pub]
    checks = {
        "all_manifest_hashes_match": all(h["matches"] for h in hashes),
        "exactly_135_unique_public_ids": len(ids) == len(set(ids)) == 135,
        "opaque_hex_id_format": all(re.fullmatch(r"q[0-9a-f]{8}", i) for i in ids),
        "all_files_same_id_set": set(ids) == set(full) == set(key) == set(inverse) == {r["id"] for r in payload},
        "model_payload_only_id_prompt": all(set(r) == {"id", "prompt"} for r in payload),
        "payload_order_and_text_match_public": payload == [{"id": r["id"], "prompt": r["request_text"]} for r in pub],
        "public_and_full_prompts_match": all(r["request_text"] == full[r["id"]]["request_text"] for r in pub),
        "hidden_legacy_ids_match_private_map": all(full[n]["hidden"]["legacy_id"] == o for o, n in idmap.items()),
        "retained_parameters_unchanged": all(r["structured_unchanged"] for r in changes),
        "retained_verdicts_unchanged": all(r["verdict_unchanged"] for r in changes),
        "only_wl0010_dropped": set(old_full) - set(idmap) == {"wl-0010"},
        "shared_turing_mechanism_declared": set(split["mechanism_groups"]["linear_reaction_diffusion_stability"]) == {"turing_finite_domain", "turing_2d_rectangle", "wavelength_formula_licence"},
        "hamilton_synergy_diagnosis_completed": all("HAMILTON_NONADDITIVE" in key[idmap[o]]["violated_conditions"] for o in ["hm-0005", "hm-0015"]),
    }

    # Same two decision-tree complexities as the v1.1 diagnostic. No text,
    # family identity or hidden science parameter is a classifier feature.
    dev = [r for r in pub if r["family"] in split["dev_families"]]
    heldout = [r for r in pub if r["family"] not in split["dev_families"]]
    features = lambda rows: [[int(r["id"][1:], 16)] for r in rows]
    labels = lambda rows: [key[r["id"]]["verdict"] for r in rows]
    id_diagnostic = []
    for model in [DummyClassifier(strategy="most_frequent"), DecisionTreeClassifier(max_depth=3, random_state=0), DecisionTreeClassifier(random_state=0)]:
        model.fit(features(dev), labels(dev))
        predicted = list(model.predict(features(heldout)))
        id_diagnostic.append({
            "classifier": type(model).__name__, "depth": getattr(model, "max_depth", None),
            "correct": sum(a == b for a, b in zip(predicted, labels(heldout))),
            "n": len(heldout), "training_n": len(dev),
        })

    special = []
    for oid in ["ts-0008", "ts-0018", "t2-0011"]:
        nid = idmap[oid]
        a, b, c, e = map(F, full[nid]["hidden"]["structured"]["J"])
        special.append({"legacy_id": oid, "id": nid, "trace": str(a+e), "determinant": str(a*e-b*c),
                        "verdict": key[nid]["verdict"],
                        "strict_base_stability_now_stated": "strictly linearly stable without diffusion" in full[nid]["request_text"]})

    unsafe_phrase = "no pattern wavelength exists"
    wavelength_overstatement = [r["id"] for r in payload if unsafe_phrase in r["prompt"]]
    dual_wording = [r["id"] for r in payload if "form a Turing pattern" in r["prompt"] and "linear stability only" in r["prompt"]]
    counts = Counter(r["verdict"] for r in key.values())
    # Reuse the already executed independent shooting calculation, with its
    # refinement delta explicitly labelled. This is not an interval proof.
    prior_receipt_path = Path("artifacts/integration/codex-api/benchmark-v1-1-review.json")
    prior_receipt = json.loads(prior_receipt_path.read_bytes())
    root_receipt = next(r["witness"] for r in prior_receipt["label_checks"] if r["id"] == "gh-0001")
    lam = F(str(root_receipt["lambda_shooting"]))
    rounded_coefficient = F("0.788")
    greenhill_witnesses = []
    for oid in ["gh-0004", "gh-0012", "gh-0016"]:
        nid = idmap[oid]
        x = full[nid]["hidden"]["structured"]
        E, D, H = [F(str(x[k])) for k in ("E", "D", "H")]
        # H > threshold iff rho exceeds the corresponding critical density.
        scale = E * D**2 / (F("9.81") * H**3)
        rho_printed, rho_exact = rounded_coefficient**3 * scale, lam/16 * scale
        mid = (rho_printed + rho_exact)/2
        low = min(rho_printed, rho_exact)/2
        assert rho_printed < mid < rho_exact and 0 < low < rho_printed
        greenhill_witnesses.append({
            "legacy_id": oid, "id": nid, "key_verdict": key[nid]["verdict"],
            "printed_formula_critical_density": float(rho_printed),
            "independent_shooting_critical_density": float(rho_exact),
            "disagreement_completion": {"rho_kg_m3": float(mid), "rho_rational": str(mid),
                                        "printed_formula_buckles": True, "shooting_model_buckles": False},
            "agreement_completion": {"rho_kg_m3": float(low), "rho_rational": str(low),
                                      "printed_formula_buckles": False, "shooting_model_buckles": False},
            "review_verdict": "underdetermined for literal 0.788 formula and unrestricted positive unknown density",
        })
    report = {
        "updated_at": datetime.now(ZoneInfo("America/Los_Angeles")).isoformat(),
        "evidence_kind": "nonblinded_metadata_and_statement_change_review",
        "source_commit": NEW, "prior_audited_commit": OLD,
        "director_commit": DIRECTOR, "electric_commit": ELECTRIC,
        "review_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "key_sha256": hashlib.sha256(blob(NEW, "key.jsonl")).hexdigest(),
        "model_payload_sha256": hashlib.sha256(blob(NEW, "model_payload.jsonl")).hexdigest(),
        "checks": checks, "hashes": hashes,
        "counts": {"n": len(pub), "families": dict(Counter(r["family"] for r in pub)), "verdicts": dict(counts)},
        "changes": changes, "special_base_states": special,
        "greenhill_changed_label_review": {
            "prior_receipt_sha256": hashlib.sha256(prior_receipt_path.read_bytes()).hexdigest(),
            "root_receipt": root_receipt,
            "witnesses": greenhill_witnesses,
            "limit": "Constructed numerical witnesses using the prior independently computed shooting root; refinement delta is not a rigorous error bound. No measured densities or new solver run.",
            "repair_options": "Freeze the exact uniform critical constant consistently in prompt/oracle, explicitly restrict missing-parameter completions away from threshold, or retain underdetermined for the printed rounded formula."
        },
        "id_only_diagnostic": id_diagnostic,
        "id_diagnostic_limit": "Diagnostic at one fixed split, not proof of independence. Seeded IDs and private map are public repository material; the runner must isolate keys/generators/map and log actual model-visible requests/tools.",
        "wording_findings": {"unqualified_no_pattern_wavelength_ids": wavelength_overstatement,
                             "pattern_question_followed_by_linear_override_ids": dual_wording},
        "scoring_findings": [
            "score.py reports categorical accuracy/false alarms, not coverage/selective risk/utility/always-refuse.",
            "baselines.py converts parse failures and exceptions to underdetermined, conflating abstention/error with a substantive missing-information verdict.",
            "predict_R always returns applies; it performs no retrieval.",
            "B0 receives family metadata; model_payload contains id/prompt only. Freeze information and preprocessing for each comparator.",
            "No committed scopedesk/arms runner or preregistration exists at the inspected electric revision; no implementation-level scoring approval is possible."
        ],
        "constant_label_baselines": {v: {"correct": counts[v], "n": len(pub)} for v in ["applies", "out_of_scope", "underdetermined"]},
        "always_abstain_policy": {"issued_answers": 0, "n": len(pub), "coverage": 0, "selective_risk": None,
                                  "note": "Analytical baseline: risk undefined at zero issued answers; utility requires a preregistered abstention cost."},
        "approval": "Metadata repairs verified where checks pass; freeze withheld. Three changed Greenhill labels, wording, explicit abstention schema/scoring, independent text audit and frozen actual runner/payload remain gates.",
        "limitations": [
            "Not a fresh blinded or full numerical audit. Existing conditional arithmetic review is carried forward only for identical parameters/verdicts.",
            "No agent, prover, PDE or GPU run. No claim of accuracy improvement, biological pattern prediction or universal robustness threshold.",
            "This source snapshot is not a certificate for later commits."
        ],
    }
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"source_commit": NEW, "checks": checks, "counts": report["counts"],
                      "id_only_diagnostic": id_diagnostic, "wording_counts": {k: len(v) for k, v in report["wording_findings"].items()},
                      "constant_label_baselines": report["constant_label_baselines"],
                      "greenhill_witnesses": greenhill_witnesses}, indent=2))


if __name__ == "__main__":
    main()
