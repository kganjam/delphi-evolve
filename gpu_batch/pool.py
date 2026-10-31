"""Snapshot of the shared Nebius project pool and the launch/yield decision logic.

Pure functions over plain dicts so they can be tested with fixtures (no shared-pool load).

Ownership model (never inferred from naming conventions such as 'kg'):
  owned   IDs in manifest["owned"] AND name starting OWN_PREFIX.  Only these may be cancelled by us.
  peer    IDs listed in manifest["peers"] (the gpu worker's jobs).  Counted against our total; NEVER cancelled.
  other   everything else, including a job we merely suspect is a teammate's.  Never touched.
Counting rule: for the "<= cap of our own H100s" check we count owned + peers + any unlisted
H100 workload whose name starts with one of manifest["count_conservatively_prefixes"] (a possible
follow-up from the gpu worker whose ID we have not been told).  Over-counting only makes us launch less.
"""
from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field

from . import OWN_PREFIX

H100_PLATFORM = "gpu-h100-sxm"
POOL_H100_TOTAL = 16          # per nebius-compute.md; tenant quota itself is unreadable (PermissionDenied)

# Job/endpoint states.  Terminal states hold no GPU.  The Nebius docs do not enumerate the enum for us, so
# anything not recognised is treated conservatively (counted as active; for other teams' items as "maybe waiting").
TERMINAL = {"COMPLETED", "FAILED", "CANCELLED", "CANCELED", "STOPPED", "DELETED", "ERROR", "SUCCEEDED"}
WAITING = {"PENDING", "QUEUED", "WAITING", "SCHEDULING", "CREATING", "PROVISIONING", "INITIALIZING"}
HOLDING = {"RUNNING", "STARTING", "IMAGE_PULLING", "CANCELLING", "STOPPING", "UPDATING"}


@dataclass
class Workload:
    id: str
    name: str
    kind: str                 # job | endpoint
    platform: str
    preset: str
    state: str
    created_at: str = ""
    gpus: int = 0
    raw_state_known: bool = True

    @property
    def is_h100(self):
        return self.platform == H100_PLATFORM

    @property
    def terminal(self):
        return self.state in TERMINAL

    @property
    def active(self):          # may hold or be about to hold a GPU
        return not self.terminal

    @property
    def waiting(self):
        return self.state in WAITING


def _gpus(preset: str) -> int:
    m = re.match(r"(\d+)gpu", preset or "")
    return int(m.group(1)) if m else 0


def parse_items(doc: dict, kind: str) -> list[Workload]:
    out = []
    for it in doc.get("items", []):
        md, sp, st = it.get("metadata", {}), it.get("spec", {}), it.get("status", {})
        state = str(st.get("state", "UNKNOWN")).upper()
        out.append(Workload(id=md.get("id", ""), name=md.get("name", ""), kind=kind, platform=sp.get("platform", ""),
                            preset=sp.get("preset", ""), state=state, created_at=md.get("created_at", ""),
                            gpus=_gpus(sp.get("preset", "")),
                            raw_state_known=state in TERMINAL | WAITING | HOLDING))
    return out


@dataclass
class Snapshot:
    ok: bool
    workloads: list[Workload] = field(default_factory=list)
    error: str = ""
    truncated: bool = False


def take_snapshot(run=None, nebius="nebius", profile="hackathon") -> Snapshot:
    """List jobs and endpoints.  `run(argv)->str` is injectable for tests.  Any failure => ok=False."""
    def default_run(argv):
        r = subprocess.run(argv, capture_output=True, text=True, timeout=45)
        if r.returncode != 0:
            raise RuntimeError(f"exit {r.returncode}: {r.stderr.strip()[:200]}")
        return r.stdout
    run = run or default_run
    try:
        wl, trunc = [], False
        for kind in ("job", "endpoint"):
            doc = json.loads(run([nebius, "--profile", profile, "ai", kind, "list", "--format", "json"]))
            trunc |= bool(doc.get("next_page_token"))
            wl += parse_items(doc, kind)
        return Snapshot(True, wl, truncated=trunc)
    except Exception as e:  # noqa: BLE001 - every failure must degrade to "unknown"
        return Snapshot(False, error=f"{type(e).__name__}: {str(e)[:200]}")


# ------------------------------------------------------------------ classification
def classify(w: Workload, manifest: dict) -> str:
    owned = {j["id"] for j in manifest.get("owned", [])}
    peers = {j["id"] for j in manifest.get("peers", [])}
    if w.id in owned and w.name.startswith(OWN_PREFIX):
        return "owned"
    if w.id in peers:
        return "peer"
    return "other"


def count_ours(snap: Snapshot, manifest: dict) -> dict:
    """H100 accounting for the <= cap rule and for free-capacity estimation."""
    prefixes = tuple(manifest.get("count_conservatively_prefixes", []))
    ours, others_active, ours_ids = 0, 0, []
    for w in snap.workloads:
        if not (w.is_h100 and w.active):
            continue
        c = classify(w, manifest)
        if c in ("owned", "peer") or (c == "other" and prefixes and w.name.startswith(prefixes)):
            ours += w.gpus
            ours_ids.append(w.id)
        else:
            others_active += w.gpus
    return {"ours": ours, "ours_ids": ours_ids, "others_active": others_active,
            "pool_free_estimate": POOL_H100_TOTAL - ours - others_active}


def waiting_others(snap: Snapshot, manifest: dict) -> list[Workload]:
    """Other teams' H100 workloads that appear to be queued for capacity."""
    prefixes = tuple(manifest.get("count_conservatively_prefixes", []))
    res = []
    for w in snap.workloads:
        if not (w.is_h100 and w.active):
            continue
        c = classify(w, manifest)
        if c != "other" or (prefixes and w.name.startswith(prefixes)):
            continue
        if w.waiting or not w.raw_state_known:
            res.append(w)
    return res


# ------------------------------------------------------------------ decisions
@dataclass
class Config:
    cap: int = 10                  # total own active H100s including the gpu worker's
    free_reserve: int = 2          # never launch if it would leave fewer than this many pool GPUs free
    max_launch_per_cycle: int = 1  # ramp slowly; look at the queue after each launch
    blind_poll_limit: int = 5      # consecutive failed snapshots (~5 min) before draining expansions
    floor_when_blind: int = 2      # if blind: keep at most this many of ours (counting peers)
    stuck_launch_s: int = 600      # an own job not holding a GPU after this long => pool is saturated


def decide(snap: Snapshot, manifest: dict, cfg: Config, blind_polls: int = 0, now_iso: str | None = None) -> dict:
    """Return {"release": [ids in release order], "launch_slots": n, "reason": str, "counts": {...}}.

    release: owned, lowest-priority-first (higher `priority` number = lower priority), only as many GPUs
    as the waiting demand not covered by free capacity (or all down to floor if blind).
    launch_slots: how many new single-GPU shards may start this cycle (0 if anything is unclear).
    """
    owned_meta = {j["id"]: j for j in manifest.get("owned", [])}
    if not snap.ok or snap.truncated:
        why = snap.error or "listing truncated (next_page_token present)"
        drain = blind_polls + 1 >= cfg.blind_poll_limit
        return {"release": [], "launch_slots": 0, "drain_blind": drain, "counts": {},
                "reason": f"blind: {why}" + (" (blind limit reached: monitor should drain to floor using per-ID `job get`)"
                                              if drain else "")}
    c = count_ours(snap, manifest)
    waiting = waiting_others(snap, manifest)
    demand = sum(max(w.gpus, 1) for w in waiting)
    live_owned = [w for w in snap.workloads if classify(w, manifest) == "owned" and w.is_h100 and w.active]
    # order: lowest priority first; ties: not-yet-running before running, then newest first (least sunk work)
    def key(w):
        m = owned_meta[w.id]
        return (-m.get("priority", 0), 0 if w.state != "RUNNING" else 1, w.created_at)
    live_owned.sort(key=key)
    need = max(0, demand - max(c["pool_free_estimate"], 0)) if waiting else 0
    release, freed = [], 0
    for w in live_owned:
        if freed >= need:
            break
        if not owned_meta[w.id].get("checkpointed", False) and owned_meta[w.id].get("priority", 0) == 0:
            continue                      # priority-0 core jobs are only released when explicitly marked checkpointed
        release.append(w.id)
        freed += w.gpus
    slots = 0
    if not waiting:
        by_cap = cfg.cap - c["ours"]
        by_pool = c["pool_free_estimate"] - cfg.free_reserve
        slots = max(0, min(by_cap, by_pool, cfg.max_launch_per_cycle))
        # a recently launched own job still not holding a GPU => saturated pool; hold
        if any(w.state in WAITING for w in live_owned):
            slots = 0
    reason = ("other teams waiting: demand=%d free=%d -> release %d" % (demand, c["pool_free_estimate"], len(release))
              if waiting else "no external waiting workloads")
    return {"release": release, "launch_slots": slots, "drain_blind": False, "reason": reason,
            "counts": {**c, "waiting_other_ids": [w.id for w in waiting], "demand": demand}}


def verify_cancellable(job_id: str, live: dict, manifest: dict) -> tuple[bool, str]:
    """`live` is the result of `ai job get --format json` for job_id.  Cancel only our own, name+id verified."""
    meta = live.get("metadata", {})
    if meta.get("id") != job_id:
        return False, "live id mismatch"
    owned = {j["id"]: j for j in manifest.get("owned", [])}
    if job_id not in owned:
        return False, "not in manifest.owned"
    if not str(meta.get("name", "")).startswith(OWN_PREFIX):
        return False, "name lacks own prefix"
    if owned[job_id].get("name") != meta.get("name"):
        return False, "name differs from manifest record"
    return True, "ok"
