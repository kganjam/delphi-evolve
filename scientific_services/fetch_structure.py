"""Download the OpenFold2 result artifact for a finished operation IN MEMORY (signed URL never persisted),
extract PDB + confidence metrics, write small tracked artifacts with SHA256 provenance."""
import gzip, json, sys, urllib.request
from pathlib import Path
from .common import now_utc, now_seattle, sha256_bytes, strip_url, write_json
from .nebius_mcp import NebiusMCP

OUT = Path("artifacts/services/nebius")

def get_bytes(c, artifact_id):
    pay = c.tool_payload(c.call_tool("download_scientific_artifact", {"artifact_id": artifact_id}))
    url = None
    def walk(o):
        nonlocal url
        if isinstance(o, dict):
            for k, v in o.items():
                if isinstance(v, str) and v.startswith("http") and url is None:
                    url = v
                else:
                    walk(v)
        elif isinstance(o, list):
            [walk(v) for v in o]
    walk(pay)
    if not url:
        raise RuntimeError("no download url in response; keys=" + str(list(pay)[:10]))
    with urllib.request.urlopen(urllib.request.Request(url), timeout=120) as r:
        data = r.read()
    return data, strip_url(url), pay

def main(tag, genotype, op_id, artifact_id, expect_sha):
    c = NebiusMCP(); c.initialize()
    data, url_clean, pay = get_bytes(c, artifact_id)
    got = sha256_bytes(data)
    assert got == expect_sha, f"sha mismatch {got} != {expect_sha}"
    res = json.loads(data)
    (OUT / f"{tag}_raw_result_summary_keys.txt").write_text("\n".join(f"{k}: {type(v).__name__}" for k, v in res.items()) + "\n")
    print("top-level keys:", list(res)[:20])
    json.dump(res, open("/tmp/_of2_result.json", "w"))     # scratch outside repo for parsing
    write_json(OUT / f"{tag}_download_receipt.json", {
        "t_utc": now_utc(), "t_seattle": now_seattle(), "operation_id": op_id, "artifact_id": artifact_id,
        "downloaded_sha256": got, "downloaded_size_bytes": len(data), "url_query_stripped": url_clean,
        "note": "short-lived signed URL used in memory only; query string deliberately not retained"})

if __name__ == "__main__":
    main(*sys.argv[1:6])
