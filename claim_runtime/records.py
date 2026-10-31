"""Where the committed, hashed Delphi records live, and pin generation."""
from __future__ import annotations

import json
from pathlib import Path

from .common import ClaimStore, claim_iri, sha_file

ROOT = Path(__file__).resolve().parent.parent
REC_DIR = ROOT / "artifacts" / "claim_reuse" / "delphi_records"
NETWORK_FILES = ["kimura-fixation-probability.network.json", "fisher-ftns.network.json"]
LOCAL_FILES = ["kimura-fixation-probability.local.json", "fisher-ftns.local.json"]


def default_store(rec_dir: Path = REC_DIR, source: str = "network") -> ClaimStore:
    names = NETWORK_FILES if source == "network" else LOCAL_FILES
    return ClaimStore.from_files([rec_dir / n for n in names])


def make_pins(rec_dir: Path = REC_DIR) -> dict:
    s = default_store(rec_dir)
    local = default_store(rec_dir, "local")
    pins = {}
    for cid in ("kimura-fixation-probability", "fisher-ftns"):
        iri = claim_iri(cid)
        rec, lrec = s.get(iri).record, local.get(iri).record
        pins[cid] = {
            "claim_iri": iri,
            "content_sha256": rec.content_sha256(),
            "pinned_from_source": rec.source,
            "network_nanopub": rec.nanopubs,
            "network_record_response_sha256": rec.response_sha256,
            "local_record_content_matches_network": lrec.content_sha256() == rec.content_sha256(),
            "local_nanopub_path": lrec.nanopubs,
            "reviewed_by": "hand-authored by the claim-reuse worker (Claude Sonnet 5.5); NOT an independent human review",
            "primary_source": {"kimura-fixation-probability": "Kimura 1962, Genetics 47:713 (PMC1210364) - PDF not retrievable here (PMC bot challenge); assumptions checked against the Delphi record and an exact Wright-Fisher chain instead",
                               "fisher-ftns": "Fisher 1930; Price 1972 (doi 10.1111/j.1469-1809.1972.tb00764.x); Ewens 1989 (doi 10.1016/0040-5809(89)90028-2) as cited by the Delphi record - not re-read by this worker"}[cid],
        }
    return pins
