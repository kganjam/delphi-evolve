"""Queue-aware controller: launches bounded 1-GPU shard jobs and yields them to other teams.

  python -m gpu_batch.controller status
  python -m gpu_batch.controller monitor [--interval 60] [--duration-min 120] [--launch] [--dry-run]

Everything that touches the cloud goes through `Cloud` so tests can use fixtures instead of the shared pool.
Cancellation is limited to jobs recorded in the manifest under "owned" whose live id AND name match.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import time
from pathlib import Path

from . import OWN_PREFIX, nebius_cli, pool

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "artifacts/scale/job_manifest.json"
QUEUE = ROOT / "artifacts/scale/launch_queue.json"
QLOG = ROOT / "artifacts/scale/queue_log.jsonl"
SEATTLE_NOTE = "timestamps are UTC (Z); Seattle is PDT (UTC-7) until 2026-11-01 02:00 local, then PST (UTC-8)"


def now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(p, default):
    return json.loads(Path(p).read_text()) if Path(p).exists() else default


def save_json(p, obj):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1, sort_keys=False) + "\n")
    os.replace(tmp, p)


class Cloud:
    """Real cloud operations; tests substitute a fake with the same four methods."""
    def snapshot(self):
        return pool.take_snapshot(nebius=nebius_cli.NEB, profile=nebius_cli.PROFILE)

    def create(self, name, timeout, runner_args):
        return nebius_cli.create_job(name, timeout, runner_args)

    def get(self, job_id):
        return nebius_cli.get_job(job_id)

    def cancel(self, job_id):
        return nebius_cli.cancel_job(job_id)


# ------------------------------------------------------------------ manifest bookkeeping
def reconcile(manifest, snap):
    """Adopt intents whose unique name now exists live (crash between create and record); refresh states."""
    live = {w.id: w for w in snap.workloads}
    by_name = {w.name: w for w in snap.workloads}
    for it in manifest.get("owned", []):
        if not it.get("id") and it.get("name") in by_name and it["name"].startswith(OWN_PREFIX):
            it["id"] = by_name[it["name"]].id
            it["adopted_from_intent"] = True
    for it in manifest.get("owned", []):
        w = live.get(it.get("id"))
        if w:
            it["last_state"] = w.state
            if w.terminal and not it.get("ended_at"):
                it["ended_at"] = now()
    return manifest


def release(cloud, manifest, ids, why, dry_run=False):
    results = []
    for jid in ids:
        try:
            live = cloud.get(jid)
        except Exception as e:  # noqa: BLE001
            results.append({"id": jid, "released": False, "why": f"get failed: {e}"})
            continue
        ok, msg = pool.verify_cancellable(jid, live, manifest)
        if not ok:
            results.append({"id": jid, "released": False, "why": f"refused: {msg}"})
            continue
        if dry_run:
            results.append({"id": jid, "released": False, "why": "dry-run"})
            continue
        rc, out = cloud.cancel(jid)
        results.append({"id": jid, "released": rc == 0, "why": why, "cli": out})
        if rc == 0:
            for it in manifest["owned"]:
                if it["id"] == jid:
                    it["released_at"], it["released_reason"] = now(), why
    return results


def launch_next(cloud, manifest, queue, dry_run=False):
    """Launch the highest-priority queued spec (lowest priority number first).  Records an intent first."""
    pending = sorted([q for q in queue if q.get("status", "queued") == "queued"], key=lambda q: (q["priority"], q["seq"]))
    if not pending:
        return None
    q = pending[0]
    name = f"{OWN_PREFIX}{q['model_key']}-u{q['units'].replace(',', '_')}-{dt.datetime.now(dt.timezone.utc).strftime('%H%M%S')}"
    args = ["--model-key", q["model_key"], "--units", q["units"], "--batch", str(q.get("batch", 64)),
            "--rp-dim", str(q.get("rp_dim", 32)), "--max-minutes", str(q.get("max_minutes", 95)), "--out", "/output/scale"]
    rec = {"name": name, "id": None, "model_key": q["model_key"], "units": q["units"], "priority": q["priority"],
           "checkpointed": True, "timeout": q.get("timeout", "2h"), "intent_at": now(), "runner_args": args,
           "purpose": q.get("purpose", "")}
    if dry_run:
        return {"dry_run": True, **rec}
    manifest.setdefault("owned", []).append(rec)
    save_json(MANIFEST, manifest)                       # intent is durable BEFORE the job exists
    try:
        rec["id"] = cloud.create(name, rec["timeout"], args)
    except Exception as e:  # noqa: BLE001
        rec["create_error"] = str(e)[:300]
        q["status"] = "queued"
        save_json(MANIFEST, manifest)
        return rec
    rec["created_at"] = now()
    q["status"], q["job_id"] = "launched", rec["id"]
    save_json(MANIFEST, manifest)
    save_json(QUEUE, queue)
    return rec


def cycle(cloud, manifest, queue, cfg, blind_polls, do_launch, dry_run=False):
    snap = cloud.snapshot()
    reconcile(manifest, snap) if snap.ok else None
    d = pool.decide(snap, manifest, cfg, blind_polls)
    actions = {"released": [], "launched": None}
    if d["release"]:
        actions["released"] = release(cloud, manifest, d["release"], "yield: " + d["reason"], dry_run)
    if d.get("drain_blind"):
        # cannot list; fall back to per-ID verification and release lowest-priority owned jobs down to the floor
        owned = sorted([j for j in manifest.get("owned", []) if j.get("id") and not j.get("ended_at") and not j.get("released_at")],
                       key=lambda j: -j["priority"])
        keep = max(cfg.floor_when_blind - len(manifest.get("peers", [])), 0)
        actions["released"] += release(cloud, manifest, [j["id"] for j in owned[:max(len(owned) - keep, 0)]],
                                       "drain: listing unavailable", dry_run)
    if do_launch and d["launch_slots"] > 0 and snap.ok:
        actions["launched"] = launch_next(cloud, manifest, queue, dry_run)
    save_json(MANIFEST, manifest)
    entry = {"t": now(), "snapshot_ok": snap.ok, "error": snap.error, "counts": d.get("counts"), "reason": d["reason"],
             "launch_slots": d["launch_slots"], "released": actions["released"],
             "launched": (actions["launched"] or {}).get("name"), "blind_polls": blind_polls}
    QLOG.parent.mkdir(parents=True, exist_ok=True)
    with open(QLOG, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return snap, d, actions


def monitor(cloud, interval, duration_min, do_launch, dry_run, cfg, sleep=time.sleep, clock=time.time):
    manifest = load_json(MANIFEST, {})
    queue = load_json(QUEUE, [])
    t_end, blind = clock() + duration_min * 60, 0
    while True:
        manifest = load_json(MANIFEST, manifest)           # re-read: another tool may have appended
        snap, d, act = cycle(cloud, manifest, queue, cfg, blind, do_launch, dry_run)
        blind = 0 if snap.ok else blind + 1
        active_owned = [w for w in snap.workloads if pool.classify(w, manifest) == "owned" and w.active] if snap.ok else None
        queued = [q for q in queue if q.get("status", "queued") == "queued"]
        print(json.dumps({"t": now(), "reason": d["reason"], "slots": d["launch_slots"], "counts": d.get("counts"),
                          "released": [r["id"] for r in act["released"] if r.get("released")],
                          "launched": (act["launched"] or {}).get("name")}), flush=True)
        if snap.ok and not active_owned and not (do_launch and queued):
            print("monitor: no active owned jobs and nothing queued; exiting", flush=True)
            return 0
        if clock() >= t_end:
            print("monitor: duration reached", flush=True)
            return 0
        sleep(interval)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    m = sub.add_parser("monitor")
    m.add_argument("--interval", type=int, default=60)
    m.add_argument("--duration-min", type=float, default=120)
    m.add_argument("--launch", action="store_true", help="also launch queued specs when the policy allows")
    m.add_argument("--dry-run", action="store_true")
    m.add_argument("--cap", type=int, default=10)
    a = ap.parse_args()
    cloud, cfg = Cloud(), pool.Config(cap=getattr(a, "cap", 10))
    if a.cmd == "status":
        manifest = load_json(MANIFEST, {})
        snap = cloud.snapshot()
        print(json.dumps({"ok": snap.ok, "error": snap.error, "count": pool.count_ours(snap, manifest) if snap.ok else None,
                          "decision": pool.decide(snap, manifest, cfg)}, indent=1))
        return 0
    return monitor(cloud, min(a.interval, 60), a.duration_min, a.launch, a.dry_run, cfg)


if __name__ == "__main__":
    raise SystemExit(main())
