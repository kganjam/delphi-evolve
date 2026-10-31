"""build -> conform -> sign (LOCAL, throwaway/owner key outside the repo) -> independent verify -> ledger entry (stage null).
Publishing is a separate step (registry.post_test) that needs a user authorization record."""
from __future__ import annotations

import json
from pathlib import Path

from falsify.nanopub import sign_local, verify_signed

from .binding import build_trig, check_bundle, conform, conform_signed, key_of
from .ledger import Ledger
from .records import NotPublishable


def prepare(bundle: dict, ledger: Ledger, *, out_dir: Path, key_pem: Path, code_commit: str, created: str, status_change: bool = False,
            stage_for_chain: str = "test") -> dict:
    v = check_bundle(bundle, status_change=status_change)        # raises before anything is written
    key = key_of(bundle)
    head = ledger.head(key, stage_for_chain)
    supersedes = None
    if head is not None:
        if head["target_version"] == v["target"]["version"] and not status_change:
            raise NotPublishable("this exact record version is already published; published nanopublications are never edited or re-issued")
        if head["decision"] != "accepted" and status_change:
            raise NotPublishable("chain head is not an acceptance publication")
        supersedes = head["np_uri"]
    elif status_change:
        raise NotPublishable("a dispute/rejection is published only as a correction of an existing acceptance publication; none is in the ledger")
    if status_change and head["target_version"] != v["target"]["version"]:
        raise NotPublishable("the published acceptance concerns a different version than this dispute")
    trig = build_trig(bundle, code_commit=code_commit, created=created, supersedes=supersedes, status_change=status_change)
    bad = conform(trig)
    if bad:
        raise NotPublishable("conformance failed: " + "; ".join(bad))
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{v['target']['kind']}-{v['target']['id']}-{v['target']['version'][:12]}-{v['decision']}" + (f"-after-{supersedes[-8:]}" if supersedes else "")
    unsigned, signed = out_dir / (stem + ".unsigned.trig"), out_dir / (stem + ".signed.trig")
    unsigned.write_text(trig)
    info = sign_local(unsigned, key_pem, signed)
    chk = verify_signed(signed)
    if chk.get("exit") != 0 or chk.get("trusty_uri") != info["trusty_uri"]:
        raise NotPublishable(f"independent verification failed: {chk}")
    bad2 = conform_signed(signed.read_text())
    if bad2:
        raise NotPublishable("signed file fails conformance: " + "; ".join(bad2))
    entry = ledger.add_signed(key=key, target_version=v["target"]["version"], assessment_version=v["assessment"]["version"], decision=v["decision"],
                              file=signed.name, signed_bytes=signed.read_bytes(), np_uri=info["trusty_uri"], supersedes=supersedes)
    ledger.save()
    return {"entry": entry, "unsigned": str(unsigned), "signed": str(signed), "verified": chk}
