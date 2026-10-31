#!/usr/bin/env python3
"""Warm batch worker (stdlib only), runs INSIDE one GPU/CPU allocation: executes a frozen queue of workloads sequentially so one image pull and one setup serve many jobs.
Shipped as the item script by compute_ops.batch; the queue file is part of the bundle, so every workload is frozen (and hashable) before submission.

  python3 compute_ops/warm_worker.py warm_queue.json
queue.json = {"queue_id": str, "max_wall_s": <= 7200, "margin_s": 60, "env": {...shared env, e.g. HF_HOME}, "max_part_bytes": 3000000,
              "workloads": [{"id": str, "argv": [...], "timeout_s": int, "env": {...}, "max_part_bytes": optional, "setup": false}]}
For each workload, in order: run argv in the bundle directory with COPS_OUT=<fresh dir>, inner timeout; then pack that dir as tar.gz and emit it to the job log between
COPS_PART_BEGIN {meta} / COPS_B64 ... / COPS_PART_END (flushed BEFORE the next workload starts, so a later crash or timeout keeps earlier outputs); append a receipt row.
Stops when the queue is empty or when the remaining wall budget cannot cover the next workload's timeout plus margin (that workload is recorded not_run_budget, never dropped silently).
Per-workload output over its cap is NOT emitted, and the part says so loudly with per-file sha256. Shared state that persists across workloads: the container's pip packages and any
cache directory named in env (HF_HOME etc.); nothing is persisted outside the container. The final COPS_OUT (queue_receipts.json, telemetry) is returned by cops_run as usual."""
import base64, hashlib, io, json, os, shutil, subprocess, sys, tarfile, time

T0 = time.time()
Q = json.load(open(sys.argv[1]))
OUT = os.environ.get("COPS_OUT", "/work/out"); os.makedirs(OUT, exist_ok=True)
PARTS = os.environ.get("WARM_PARTS_DIR", "/work/parts")
MAX_WALL = min(float(Q.get("max_wall_s", 7200)), 7200.0)
MARGIN = float(Q.get("margin_s", 60))
utc = lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
sha = lambda b: hashlib.sha256(b).hexdigest()
receipts = []


def save_receipts():
    json.dump({"queue_id": Q.get("queue_id"), "started_utc": receipts_start, "max_wall_s": MAX_WALL, "elapsed_s": round(time.time() - T0, 1), "workloads": receipts},
              open(os.path.join(OUT, "queue_receipts.json"), "w"), indent=1)


def emit_part(seq, wid, meta, data):
    b64 = base64.b64encode(data).decode()
    lines = [b64[i:i + 900] for i in range(0, len(b64), 900)]
    print("COPS_PART_BEGIN " + json.dumps(meta, sort_keys=True), flush=True)
    for i, ln in enumerate(lines):
        print("COPS_B64 " + ln, flush=True)
        if i % 400 == 399:
            time.sleep(1.2)
    print("COPS_PART_END", flush=True)


if os.environ.get("PREFLIGHT"):       # validate the frozen queue locally: run every workload with PREFLIGHT=1 (entries exit after imports/inputs), emit nothing
    bad = 0
    for seq, w in enumerate(Q["workloads"]):
        e = dict(os.environ, **{k: str(v) for k, v in {**Q.get("env", {}), **w.get("env", {})}.items()}, COPS_OUT=OUT, PREFLIGHT="1")
        r = subprocess.run(w["argv"], cwd=os.environ.get("WARM_CWD", "."), env=e, capture_output=True, text=True, timeout=180)
        print(f"preflight {seq} {w['id']} rc={r.returncode} {(r.stdout + r.stderr).strip()[-160:]}"); bad += r.returncode != 0
    sys.exit(1 if bad else 0)
os.makedirs(PARTS, exist_ok=True)
receipts_start = utc()
tel = None
if shutil.which("nvidia-smi"):                                     # one sampler for the whole allocation; per-workload windows are in the receipts
    try:
        f = open(os.path.join(OUT, "telemetry_device.csv"), "w")
        f.write("timestamp,utilization.gpu,utilization.memory,memory.used,memory.total,power.draw,temperature.gpu\n"); f.flush()
        tel = subprocess.Popen(["timeout", str(int(MAX_WALL) + 300), "nvidia-smi", "--query-gpu=timestamp,utilization.gpu,utilization.memory,memory.used,memory.total,power.draw,temperature.gpu",
                                "--format=csv,noheader,nounits", "-lms", "1000"], stdout=f, stderr=subprocess.DEVNULL)
    except Exception as e:                                          # noqa: BLE001
        print("telemetry unavailable:", repr(e), flush=True)
print(f"WARM start {receipts_start} queue={Q.get('queue_id')} n={len(Q['workloads'])} max_wall_s={MAX_WALL}", flush=True)
for seq, w in enumerate(Q["workloads"]):
    wid = w["id"]
    left = MAX_WALL - (time.time() - T0)
    if left < float(w["timeout_s"]) + MARGIN:
        receipts.append({"seq": seq, "id": wid, "status": "not_run_budget", "left_s": round(left, 1), "needs_s": w["timeout_s"] + MARGIN}); save_receipts()
        print(f"WARM skip {wid}: {left:.0f}s left < {w['timeout_s'] + MARGIN}s needed", flush=True); continue
    d = os.path.join(PARTS, f"{seq:02d}-{wid}"); os.makedirs(d, exist_ok=True)
    env = dict(os.environ, **{k: str(v) for k, v in {**Q.get("env", {}), **w.get("env", {})}.items()}, COPS_OUT=d, PYTHONUNBUFFERED="1")
    t1 = time.time(); start = utc(); rc, timed_out = None, False
    print(f"WARM begin {seq} {wid} {start}", flush=True)
    try:
        p = subprocess.Popen(w["argv"], cwd=os.environ.get("WARM_CWD", "/work/job"), env=env)
        rc = p.wait(timeout=w["timeout_s"])
    except subprocess.TimeoutExpired:
        timed_out = True; p.terminate()
        try: rc = p.wait(timeout=20)
        except subprocess.TimeoutExpired: p.kill(); rc = p.wait()
    except Exception as e:                                          # noqa: BLE001
        rc = 127; print(f"WARM runner error {type(e).__name__}: {e}", flush=True)
    files = sorted(os.path.join(a, b) for a, _, bs in os.walk(d) for b in bs)
    per_file = {os.path.relpath(x, d): {"sha256": sha(open(x, "rb").read()), "bytes": os.path.getsize(x)} for x in files}
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        tf.add(d, arcname=".")
    data = buf.getvalue()
    cap = int(w.get("max_part_bytes", Q.get("max_part_bytes", 3000000)))
    meta = {"seq": seq, "id": wid, "rc": rc, "timed_out": timed_out, "start_utc": start, "end_utc": utc(), "wall_s": round(time.time() - t1, 1), "bytes": len(data), "sha256": sha(data),
            "truncated": False, "cap": cap, "files": per_file if len(per_file) <= 200 else {"n": len(per_file)}}
    if len(data) > cap:
        meta["truncated"] = True; meta["NOT_RETURNED"] = f"archive {len(data)} B exceeds cap {cap} B; per-file hashes above are the only record"; data = b""
        print(f"WARM LOUD: part {wid} NOT returned (over cap)", flush=True)
    emit_part(seq, wid, meta, data)                                  # flushed before the next workload starts
    receipts.append({k: meta[k] for k in ("seq", "id", "rc", "timed_out", "start_utc", "end_utc", "wall_s", "bytes", "sha256", "truncated")} | {"status": "done" if rc == 0 else "failed"})
    save_receipts()
    print(f"WARM end {seq} {wid} rc={rc} wall={meta['wall_s']}s bytes={meta['bytes']}", flush=True)
if tel:
    tel.terminate()
save_receipts()
print(f"WARM done elapsed={time.time() - T0:.0f}s ran={sum(1 for r in receipts if r['status'] in ('done', 'failed'))}/{len(Q['workloads'])}", flush=True)
sys.exit(0 if all(r["status"] != "failed" for r in receipts) else 1)
