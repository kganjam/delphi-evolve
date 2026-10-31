"""Score stored responses against the frozen key (key loaded only here, after responses exist). Exact Clopper-Pearson via beta."""
import hashlib, json, sys
from pathlib import Path
from scipy.stats import beta
from bench_headroom.run import show, KEY_SHA, VERDICTS

DEV = {"turing_finite_domain", "hawk_dove_ess"}


def cp(k, n):
    if n == 0:
        return None
    lo = 0.0 if k == 0 else beta.ppf(0.025, k, n - k + 1)
    hi = 1.0 if k == n else beta.ppf(0.975, k + 1, n - k)
    return [round(float(lo), 4), round(float(hi), 4)]


def score(resp_path: Path, fam_map: dict):
    key_b = show("key.jsonl")
    assert hashlib.sha256(key_b).hexdigest() == KEY_SHA, "key hash mismatch"
    key = {json.loads(l)["id"]: json.loads(l)["verdict"] for l in key_b.decode().splitlines() if l.strip()}
    rows = [json.loads(l) for l in resp_path.read_text().splitlines() if l.strip()]
    def stats(rs):
        n = len(rs); ans = [r for r in rs if r["verdict"]]; err = [r for r in ans if r["verdict"] != key[r["id"]]]
        gold_app = [r for r in rs if key[r["id"]] == "applies"]; gold_not = [r for r in rs if key[r["id"]] != "applies"]
        fa = [r for r in gold_not if r["verdict"] == "applies"]
        fr = [r for r in gold_app if r["verdict"] in ("out_of_scope", "underdetermined")]
        conf = {}
        for r in rs:
            conf[f"{key[r['id']]}|{r['verdict'] or 'ABSTAIN'}"] = conf.get(f"{key[r['id']]}|{r['verdict'] or 'ABSTAIN'}", 0) + 1
        return {"N": n, "answered": len(ans), "coverage": round(len(ans) / n, 4) if n else None, "coverage_cp95": cp(len(ans), n),
                "errors_among_answered": len(err), "selective_risk": round(len(err) / len(ans), 4) if ans else None,
                "selective_risk_cp95": cp(len(err), len(ans)),
                "accuracy_abstain_as_wrong": round((len(ans) - len(err)) / n, 4) if n else None,
                "accuracy_cp95": cp(len(ans) - len(err), n),
                "false_acceptance": {"count": len(fa), "denominator": len(gold_not)}, "false_refusal": {"count": len(fr), "denominator": len(gold_app)},
                "confusion_truth_x_pred": conf, "tokens": sum(r["tokens"] for r in rs)}
    out = {"all": stats(rows), "dev_families": stats([r for r in rows if fam_map[r["id"]] in DEV]),
           "held_out_families": stats([r for r in rows if fam_map[r["id"]] not in DEV]), "by_family": {}}
    for f in sorted(set(fam_map[r["id"]] for r in rows)):
        out["by_family"][f] = stats([r for r in rows if fam_map[r["id"]] == f])
    return out


def main(out_dir: str):
    fam = {json.loads(l)["id"]: json.loads(l)["family"] for l in show("instances_public.jsonl").decode().splitlines() if l.strip()}
    res = score(Path(out_dir) / "responses.jsonl", fam)
    (Path(out_dir) / "SCORES.json").write_text(json.dumps(res, indent=1) + "\n")
    a = res["all"]
    print(json.dumps({k: a[k] for k in ("N", "answered", "coverage", "selective_risk", "accuracy_abstain_as_wrong", "false_acceptance", "false_refusal")}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
