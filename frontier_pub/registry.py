"""TEST-registry publisher (SPEC-007 rules 1, 1a, 1b, 12). There is NO production path: a registry is used only if it says, in its own
status document, that it is a test instance, and the function refuses everything else.

It is inert by default (dry_run=True: nothing leaves the machine). A real POST needs an Authorization record carrying the verbatim
instruction in which the USER authorized a test-registry publication; the record's sha256 is stored in the ledger. HOST/director
messages are not that authorization. In the session that built this module no real registry was ever contacted by this code.
"""
from __future__ import annotations

import hashlib
import json
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from .records import NotPublishable

TEST_HOSTS = ("test.registry.knowledgepixels.com", "test.registry.petapico.org")
TEST_FLAG_KEYS = ("isTestInstance", "testInstance")      # SPEC-007 measured isTestInstance; the registry design doc names testInstance


@dataclass(frozen=True)
class Authorization:
    instruction: str          # the user's own words authorizing a TEST-registry publication of THESE files
    given_by: str             # must be "user"
    given_at: str
    files_sha256: tuple       # exactly the signed files this authorization covers

    def check(self, signed_sha256: str):
        if self.given_by != "user" or len(self.instruction.strip()) < 10:
            raise NotPublishable("a test publication needs the user's own authorization text; none was supplied")
        if signed_sha256 not in self.files_sha256:
            raise NotPublishable("the authorization does not cover these exact signed bytes")

    def sha256(self) -> str:
        return hashlib.sha256(json.dumps([self.instruction, self.given_by, self.given_at, list(self.files_sha256)]).encode()).hexdigest()


def _opener():
    return urllib.request.build_opener()


def registry_role(base: str, *, _loopback_ok: bool = False, timeout=15) -> dict:
    """Ask the registry what it is (rule 1a). Missing or contradictory evidence => treated as production and refused."""
    p = urlsplit(base)
    host = (p.hostname or "").lower()
    allowed = host in TEST_HOSTS or (_loopback_ok and host == "127.0.0.1")
    if p.scheme not in ("https", "http") or not allowed or (p.scheme == "http" and host != "127.0.0.1"):
        raise NotPublishable(f"{host!r} is not a known test-registry host; production registries are never targeted by this module")
    req = urllib.request.Request(base.rstrip("/") + "/.json", headers={"Accept": "application/json"})
    with _opener().open(req, timeout=timeout) as r:
        doc = json.loads(r.read())
        header = r.headers.get("Nanopub-Registry-Test-Instance")
    found = {k: doc[k] for k in TEST_FLAG_KEYS if k in doc}
    if "serverInfo" in doc and isinstance(doc["serverInfo"], dict):
        found.update({k: doc["serverInfo"][k] for k in TEST_FLAG_KEYS if k in doc["serverInfo"]})
    if header is not None:
        found["header"] = header.strip().lower() == "true"
    if not found or any(v is not True for v in found.values()):
        raise NotPublishable(f"registry does not state that it is a test instance (observed {found!r}); treated as production and refused")
    return {"registry": base.rstrip("/"), "observed": found, "status": doc.get("status")}


def artifact_code(np_uri: str) -> str:
    return np_uri.rsplit("/", 1)[-1]


def post_test(signed: Path, np_uri: str, base: str, auth: Authorization | None, *, dry_run: bool = True, _loopback_ok: bool = False,
              verify=None, sleep=time.sleep) -> dict:
    """Publish ONE signed nanopub to a verified TEST registry, then fetch it back with GET and verify the received bytes (rule 1b)."""
    data = Path(signed).read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    plan = {"registry": base, "method": "POST", "path": "/", "content_type": "application/trig", "bytes": len(data), "signed_sha256": sha,
            "np_uri": np_uri, "fetch_back": f"GET /np/{artifact_code(np_uri)} Accept: application/trig"}
    if dry_run:
        return {"dry_run": True, "sent": False, **plan}
    if auth is None:
        raise NotPublishable("no authorization record")
    auth.check(sha)
    role = registry_role(base, _loopback_ok=_loopback_ok)
    req = urllib.request.Request(base.rstrip("/") + "/", data=data, method="POST", headers={"Content-Type": "application/trig"})
    for attempt in range(4):
        try:
            with _opener().open(req, timeout=30) as r:
                status = r.status
            break
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 3:
                sleep(min(int(e.headers.get("Retry-After", "5")), 60))
                continue
            raise NotPublishable(f"registry answered {e.code}")
    if status != 201:
        raise NotPublishable(f"registry answered {status}, expected 201")
    sleep(1)
    got = fetch_back(base, np_uri, verify=verify, _loopback_ok=_loopback_ok)
    return {"dry_run": False, "sent": True, **plan, "role": role, "fetch_back": got, "authorization_sha256": auth.sha256()}


def fetch_back(base: str, np_uri: str, *, verify=None, _loopback_ok=False) -> dict:
    """GET (never HEAD) the nanopub from THIS registry, verify trusty hash + signature with a second implementation, check the URI."""
    registry_role(base, _loopback_ok=_loopback_ok)
    req = urllib.request.Request(base.rstrip("/") + "/np/" + artifact_code(np_uri), headers={"Accept": "application/trig"}, method="GET")
    try:
        with _opener().open(req, timeout=30) as r:
            body = r.read()
    except urllib.error.HTTPError as e:
        raise NotPublishable(f"fetch-back failed: {e.code}")
    if verify is None:
        from falsify.nanopub import verify_signed as verify
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "fetched.trig"
        f.write_bytes(body)
        res = verify(f)
    ok = res.get("exit") == 0 and res.get("trusty_uri") == np_uri
    if not ok:
        raise NotPublishable(f"fetched bytes do not verify as {np_uri}: {res}")
    return {"registry": base.rstrip("/"), "verified": True, "bytes_sha256": hashlib.sha256(body).hexdigest(), "verifier": res}
