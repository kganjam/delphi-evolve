"""Local publication ledger (SPEC-007 `published.json` pattern): which signed file corresponds to which Frontier record version, at which
stage, superseding what. It is the only memory of the supersession chain; the registry is the authority once something is published."""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

from .records import NotPublishable

SCHEMA = "frontier-pub-ledger-0.1"
STAGES = (None, "test", "prod")
NP_URI = re.compile(r"^https://w3id\.org/np/RA[A-Za-z0-9_-]{43}$")


class Ledger:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.d = json.loads(self.path.read_text()) if self.path.exists() else {"schema": SCHEMA, "entries": []}
        if self.d.get("schema") != SCHEMA:
            raise NotPublishable("unknown ledger schema")

    def save(self):
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".ledger")
        with os.fdopen(fd, "w") as f:
            json.dump(self.d, f, indent=1, sort_keys=True)
        os.replace(tmp, self.path)

    def head(self, key: str, stage: str):
        """Newest entry for this Frontier key that has actually reached `stage` (so a supersession never points at an unpublished file)."""
        hits = [e for e in self.d["entries"] if e["key"] == key and e["stage"] == stage]
        return hits[-1] if hits else None

    def add_signed(self, *, key, target_version, assessment_version, decision, file, signed_bytes: bytes, np_uri, supersedes=None):
        if not NP_URI.match(np_uri):
            raise NotPublishable("not a trusty nanopub URI")
        if any(e["np_uri"] == np_uri for e in self.d["entries"]):
            raise NotPublishable("this nanopublication is already in the ledger")
        prior = [e for e in self.d["entries"] if e["key"] == key and e["stage"] is not None]
        if supersedes is not None and supersedes not in [e["np_uri"] for e in prior]:
            raise NotPublishable("supersedes names a nanopublication that is not a published entry of this key in the ledger")
        if supersedes is None and prior and prior[-1]["decision"] == "accepted":
            raise NotPublishable("an earlier publication of this key exists; a new one must supersede it (chains must not fork, SPEC-007 rule 4)")
        e = {"key": key, "target_version": target_version, "assessment_version": assessment_version, "decision": decision, "file": str(file),
             "np_uri": np_uri, "content_sha256": hashlib.sha256(signed_bytes).hexdigest(), "supersedes": supersedes, "stage": None,
             "registry": None, "registry_is_test_instance_observed": None, "fetched_back": None, "authorization_sha256": None}
        self.d["entries"].append(e)
        return e

    def mark_test_published(self, np_uri, *, registry, observed_is_test, fetched_back, authorization_sha256):
        e = next(x for x in self.d["entries"] if x["np_uri"] == np_uri)
        if observed_is_test is not True:
            raise NotPublishable("refusing to record a test stage for a registry that did not say it is a test instance")
        head = self.head(e["key"], "test")
        if head is not None and e["supersedes"] != head["np_uri"] and head["np_uri"] != e["np_uri"]:
            raise NotPublishable("this draft does not supersede the published chain head of its key: publishing it would fork the chain (SPEC-007 rule 4); rebuild it")
        e.update(stage="test", registry=registry, registry_is_test_instance_observed=True, fetched_back=bool(fetched_back),
                 authorization_sha256=authorization_sha256)
        return e
