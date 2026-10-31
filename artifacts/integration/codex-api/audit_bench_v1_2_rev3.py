"""Pinned metadata/text delta checks, plus exact rechecking of changed 1-D inputs."""
import hashlib
import json
from fractions import Fraction as F
from pathlib import Path
import subprocess

REV = "ffcd3151ea4dc4ac9a7c4bf304c11a402eced056"
PREV = "5eaceb85b034fcd82907264ed1ee96cd00b2e50a"
PREFIX = "scopedesk/bench/v1_2/"


def raw(name, rev=REV):
    return subprocess.check_output(["git", "show", f"{rev}:{PREFIX}{name}"])


def rows(name, rev=REV):
    return [json.loads(line) for line in raw(name, rev).splitlines()]


def exact_turing(s):
    a, b, c, d = map(F, s["J"])
    dv, length = F(s["Dv"]), F(s["r_over_pi"])
    det = a*d-b*c
    if a+d >= 0 or det <= 0:
        return "out_of_scope"
    linear = dv*a+d
    def grows(mult):
        if linear <= 0:
            return False
        for n in range(1, 10000):
            q = (F(mult*n)/length)**2
            if q >= linear/dv:
                return False  # beyond this bound D(q) >= det > 0
            if dv*q*q-linear*q+det < 0:
                return True
        raise RuntimeError("unexpected mode bound")
    if s["bc"] is None:
        x, y = grows(1), grows(2)
        return "underdetermined" if x != y else ("applies" if x else "out_of_scope")
    return "applies" if grows(2 if s["bc"] == "periodic" else 1) else "out_of_scope"


def main():
    files = {n: rows(n) for n in ["instances_public.jsonl", "instances_full.jsonl", "key.jsonl", "model_payload.jsonl"]}
    checks = {}
    for name, values in files.items():
        checks[name + "_128_unique"] = len(values) == len({v["id"] for v in values}) == 128
    pub = files["instances_public.jsonl"]
    conv = json.loads(raw("conventions.json"))
    checks["exact_family_convention_suffix"] = all(
        p["request_text"].endswith(conv["CONV"][p["family"]] + " " + conv["COMMON"]) for p in pub)
    checks["payload_row_order_and_exact_text"] = files["model_payload.jsonl"] == [
        {"id": p["id"], "prompt": p["request_text"]} for p in pub]
    current = {r["id"]: r for r in files["instances_full.jsonl"]}
    old = {r["id"]: r for r in rows("instances_full.jsonl", PREV)}
    old_key = {r["id"]: r for r in rows("key.jsonl", PREV)}
    changed_inputs = [i for i, r in current.items() if r["hidden"] != old[i]["hidden"]]
    changed_keys = [{"id": r["id"], "fields": [k for k in r if r[k] != old_key[r["id"]].get(k)]}
                    for r in files["key.jsonl"] if r != old_key[r["id"]]]
    checks["retained_labels_unchanged"] = all(r["verdict"] == old_key[r["id"]]["verdict"] for r in files["key.jsonl"])
    inverse = {v: k for k, v in json.loads(raw("id_map_PRIVATE.json", PREV)).items()}
    removed = [{"id": i, "legacy_id": inverse[i], "family": old[i]["family"]} for i in sorted(old.keys() - current.keys())]
    checks["only_three_uniform_greenhill_removed"] = {r["legacy_id"] for r in removed} == {"gh-0004", "gh-0012", "gh-0016"}
    gold = {r["id"]: r["verdict"] for r in files["key.jsonl"]}
    turing = [{"id": i, "recomputed": exact_turing(r["hidden"]["structured"]), "gold": gold[i]}
              for i, r in current.items() if r["family"] == "turing_finite_domain"]
    checks["all_22_turing1d_exact_labels_recomputed"] = len(turing) == 22 and all(r["recomputed"] == r["gold"] for r in turing)
    checks["linear_mode_questions_explicit"] = all(
        "Does the uniform state have an admissible, linearly growing diffusion-driven mode" in p["request_text"]
        for p in pub if p["family"] in {"turing_finite_domain", "turing_2d_rectangle"})
    checks["no_unqualified_no_pattern_wavelength"] = all("no pattern wavelength exists" not in p["request_text"] for p in pub)
    scores = json.loads(raw("baseline_scores.json"))
    abstain = scores["always_abstain"]["all"]
    checks["always_abstain_zero_coverage_risk_null"] = abstain["answered"] == 0 and abstain["coverage"] == 0 and abstain["selective_risk"] is None
    gate_name = next(n for n in scores if n.startswith("B0_scope_gate"))
    checks["B0_reports_68_answers_not_128_correct"] = scores[gate_name]["all"]["answered"] == 68 and scores[gate_name]["all"]["N"] == 128
    result = {"revision": REV, "benchmark_revision": "af7f38e24e3750af142dc6cbc0a45709ca0b4001",
              "previous_revision": PREV, "kind": "nonblinded metadata/text delta plus exact determinant recheck of 22 Turing-1D items; not full/blinded revalidation",
              "checks": checks, "all_ok": all(checks.values()), "removed_since_131": removed,
              "changed_hidden_input_ids": changed_inputs, "changed_key_fields": changed_keys,
              "turing1d_recheck": turing,
              "hashes": {n: hashlib.sha256(raw(n)).hexdigest() for n in files},
              "README_corrections": ["Greenhill row retains removed density-unlisted shortcut; replace with current conventions.",
                                      "Final paragraph says 131-item set; candidate is 128.",
                                      "Exclusion paragraph should distinguish seven audit removals from pre-existing wavelength near-tie exclusion."]}
    dest = Path("artifacts/integration/codex-api/bench-v1-2-rev3-delta.json")
    dest.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    if not result["all_ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
