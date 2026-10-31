"""Independent, read-only aggregation of core's replay shards (does not import evolve/).

Usage: python -m scientific_services.shard_summary <shards_dir> <out.json>
Reports per (policy, family): episodes, truth_open count, certified counts by verdict, censored count,
false certificates, assay quantiles among certified, and shard file hashes. Descriptive only.
"""
import glob, hashlib, json, statistics, sys
from collections import defaultdict
from pathlib import Path

def main(shards_dir, out):
    cells = defaultdict(list); hashes = {}
    for f in sorted(glob.glob(str(Path(shards_dir) / "*.json"))):
        raw = Path(f).read_bytes(); hashes[Path(f).name] = hashlib.sha256(raw).hexdigest()
        for r in json.loads(raw)["rows"]:
            cells[(r["policy"], r["family"])].append(r)
    summ = []
    for (pol, fam), rows in sorted(cells.items()):
        cert = [r for r in rows if r["status"] != "unresolved"]
        a = sorted(r["assays"] for r in cert)
        summ.append({"policy": pol, "family": fam, "episodes": len(rows),
                     "truth_open": sum(r["truth_open"] for r in rows),
                     "cert_open": sum(r["status"] == "open" for r in rows),
                     "cert_blocked": sum(r["status"] == "blocked" for r in rows),
                     "censored_at_budget": sum(r["status"] == "unresolved" for r in rows),
                     "stuck": sum(bool(r.get("stuck")) for r in rows),
                     "false_certificates": sum(r["correct"] is False for r in cert),
                     "median_assays_among_certified": statistics.median(a) if a else None,
                     "max_assays": max((r["assays"] for r in rows), default=None),
                     "truth_open_and_censored": sum(r["truth_open"] and r["status"] == "unresolved" for r in rows)})
    Path(out).write_text(json.dumps({"source_dir": str(shards_dir), "n_shard_files": len(hashes),
                                     "summary": summ, "shard_sha256": hashes}, indent=1) + "\n")
    for s in summ:
        print({k: s[k] for k in ("policy","family","episodes","truth_open","cert_open","cert_blocked","censored_at_budget","false_certificates","median_assays_among_certified")})

if __name__ == "__main__":
    main(*sys.argv[1:3])
