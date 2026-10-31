"""Record Delphi snapshots (no quote text) for offline tests: python3 -I -m frontier_adapters.examples.snapshot_delphi"""
import json, os
from frontier_adapters import delphi_claim as dc
from frontier_adapters.delphi_mcp import Delphi
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "delphi_snapshots")
IDS = ["turing-ddi", "darwin1859-ch02-04", "wolfram2002-ch02-08", "thompson1917-ch03-05", "fisher-ftns"]
if __name__ == "__main__":
    m = Delphi()
    for cid in IDS:
        snap, tr = dc.collect(m, cid)
        ver = dc.verify_source(snap, tr)
        assert not tr["quote"] or tr["quote"][:30] not in json.dumps(snap), "quote text leaked into snapshot"
        json.dump({"snapshot": snap, "verification": ver}, open(os.path.join(OUT, cid + ".json"), "w"), indent=2, sort_keys=True)
        print(cid, snap["kind"], snap["registry"], "verify:", {k: ver.get(k) for k in ("performed", "sha256_match", "quote_at_locator")})
