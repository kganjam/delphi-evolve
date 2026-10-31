#!/usr/bin/env python3
"""Container-side runner (stdlib only). Injected at /work/cops_run.py by compute_ops.batch.

Unpacks the work bundle from /work/_b/part-*, runs the item's argv with an inner timeout, then emits
$COPS_OUT (/work/out) as a tar.gz through the job log between COPS_RESULT_BEGIN/END markers, paced to stay
under the 1000-lines-per-query log API limit. Exits with the child's return code.
"""
import base64, glob, hashlib, io, json, os, subprocess, sys, tarfile, time

spec = json.loads(os.environ["COPS_SPEC"])
OUT = "/work/out"; JOB = "/work/job"
os.makedirs(OUT, exist_ok=True); os.makedirs(JOB, exist_ok=True)
t0 = time.time()
print(f"COPS start {time.strftime('%FT%TZ', time.gmtime())} host={os.uname().nodename} item={spec['item']}", flush=True)
blob = b"".join(open(p, "rb").read() for p in sorted(glob.glob("/work/_b/part-*")))
tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz").extractall(JOB, filter="data") if hasattr(tarfile, "data_filter") \
    else tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz").extractall(JOB)
env = dict(os.environ, COPS_OUT=OUT, PYTHONUNBUFFERED="1")
rc, timed_out = None, False
try:
    p = subprocess.Popen(spec["argv"], cwd=JOB, env=env)
    rc = p.wait(timeout=spec["inner_timeout"])
except subprocess.TimeoutExpired:
    timed_out = True; p.terminate()
    try: rc = p.wait(timeout=20)
    except subprocess.TimeoutExpired: p.kill(); rc = p.wait()
except Exception as e:                                   # noqa: BLE001
    rc = 127; print(f"COPS runner error: {type(e).__name__}: {e}", flush=True)
buf = io.BytesIO()
with tarfile.open(fileobj=buf, mode="w:gz") as tf:
    tf.add(OUT, arcname=".")
data = buf.getvalue()
meta = {"item": spec["item"], "rc": rc, "timed_out": timed_out, "wall_s": round(time.time() - t0, 1),
        "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "truncated": False}
if len(data) > spec["max_result_bytes"]:
    meta["truncated"] = True; data = b""
b64 = base64.b64encode(data).decode()
lines = [b64[i:i + 900] for i in range(0, len(b64), 900)]
print("COPS_RESULT_BEGIN " + json.dumps(meta), flush=True)
for i, ln in enumerate(lines):
    print("COPS_B64 " + ln, flush=True)
    if i % 400 == 399: time.sleep(1.2)
print("COPS_RESULT_END", flush=True)
sys.exit(rc if isinstance(rc, int) else 1)
