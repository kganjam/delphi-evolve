"""Nebius batch controller: fan a list of work items out over N GPU/CPU jobs with hard timeouts.

  python -m compute_ops.batch run  items.json --max-parallel 2 [--gpu-cap 10] [--dry-run]
  python -m compute_ops.batch status

items.json = {"run_tag": "x", "items": [{"id": "a", "script": "path/to/file.py", "args": [...],
  "files": ["extra/file", ...], "kind": "gpu"|"cpu", "preset": optional, "timeout": "10m", "image": optional,
  "priority": int (lower = more important; default = list order)}]}

Safety model
 * Ownership: only job IDs recorded in our manifest whose live name starts with OWN_PREFIX are ever cancelled.
 * GPU cap: active H100 workloads that are ours (manifest, or name prefixes in COUNT_PREFIXES) count toward --gpu-cap.
 * Fail closed: an unreadable pool snapshot launches nothing.
 * Yield: if another team has an H100 workload waiting for capacity, launch nothing more and cancel our
   lowest-priority running GPU job (requeued later, bounded by --max-requeues).
 * Hard timeouts: server-side `--timeout` plus a client watchdog that cancels our job after timeout+grace.
All cloud calls go through `Cloud`, so tests use a fake. No credential value is read: the nebius CLI profile does auth.
"""
from __future__ import annotations

import argparse, base64, datetime as dt, gzip, hashlib, io, json, os, re, shlex, subprocess, sys, tarfile, time
from dataclasses import dataclass, field
from pathlib import Path

from . import COUNT_PREFIXES, OWN_PREFIX

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
NEB = os.environ.get("NEBIUS_BIN", os.path.expanduser("~/.nebius/bin/nebius"))
PROFILE = os.environ.get("NEBIUS_PROFILE", "hackathon")
SUBNET = "vpcsubnet-e00tc2metkvjckkqqp"
GPU_IMAGE = "nvcr.io/nvidia/pytorch:25.12-py3"       # validated on the shared H100 by the gpu worker
CPU_IMAGE = "python:3.12-slim"
DEFAULTS = {"gpu": ("gpu-h100-sxm", "1gpu-16vcpu-200gb"), "cpu": ("cpu-d3", "16vcpu-64gb")}
CHUNK = 40 * 1024            # injected files: API rejects >64 KiB plaintext AFTER encoding; 61 KB raw chunks failed live (11:30 PDT), so stay at 40 KiB (x4/3 = 54 KiB)
MAX_CHUNKS = 16
MAX_TOTAL_ENCODED = 60_000    # inferred bound on the summed, base64-encoded inject files (API error: plaintext must not exceed 65536 bytes); inferred from 3 observations, not documented
TERMINAL = {"COMPLETED", "FAILED", "CANCELLED", "CANCELED", "STOPPED", "DELETED", "ERROR", "SUCCEEDED"}
WAITING = {"PENDING", "QUEUED", "WAITING", "SCHEDULING", "CREATING", "PROVISIONING", "INITIALIZING"}
OUTDIR = ROOT / "artifacts/gpuops"


def utc():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_dur(s) -> int:
    m = re.fullmatch(r"(\d+)([smh])", str(s))
    if not m:
        raise ValueError(f"bad duration {s!r} (use 90s, 10m, 2h)")
    return int(m.group(1)) * {"s": 1, "m": 60, "h": 3600}[m.group(2)]


# ------------------------------------------------------------------ bundle
def build_bundle(item: dict, base: Path) -> bytes:
    """tar.gz of the item's script + extra files (paths relative to `base`), deterministic."""
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gz, tarfile.open(fileobj=gz, mode="w") as tf:
        for rel in [item["script"], *item.get("files", [])]:
            p = (base / rel)
            if p.is_dir():
                for q in sorted(p.rglob("*")):
                    if q.is_file() and "__pycache__" not in q.parts and q.suffix != ".pyc":
                        tf.add(q, arcname=str(q.relative_to(base)), recursive=False)
            else:
                tf.add(p, arcname=str(Path(rel)), recursive=False)
    return buf.getvalue()


def chunk_bundle(blob: bytes) -> list[bytes]:
    parts = [blob[i:i + CHUNK] for i in range(0, len(blob), CHUNK)] or [b""]
    if len(parts) > MAX_CHUNKS:
        raise ValueError(f"bundle {len(blob)} B needs {len(parts)} chunks > {MAX_CHUNKS}; stage big inputs another way")
    return parts


def create_argv(item: dict, name: str, base: Path, tmpdir: Path) -> list[str]:
    kind = item.get("kind", "gpu")
    platform, preset = DEFAULTS[kind]
    platform, preset = item.get("platform", platform), item.get("preset", preset)
    image = item.get("image", GPU_IMAGE if kind == "gpu" else CPU_IMAGE)
    timeout = item.get("timeout", "10m")
    inner = int(item.get("inner_timeout_s") or max(30, parse_dur(timeout) - 120))    # item may shorten it (e.g. when the image pull eats the server timeout)
    py = item.get("python", "python3")
    argv_in = [py, item["script"], *map(str, item.get("args", []))]
    spec = {"item": item["id"], "argv": argv_in, "inner_timeout": inner,
            "max_result_bytes": item.get("max_result_bytes", 400_000)}
    a = [NEB, "--profile", PROFILE, "ai", "job", "create", "--name", name, "--image", image,
         "--container-command", "python3", "--args", "/work/cops_run.py", "--platform", platform, "--preset", preset,
         "--timeout", timeout, "--disk-size", item.get("disk", "50Gi"), "--subnet-id", SUBNET,
         "--env", "COPS_SPEC=" + json.dumps(spec), "--env", f"JOB_LABEL={name}",
         "--inject-file", f"{HERE / 'cops_run.py'}:/work/cops_run.py"]
    for k, v in (item.get("env") or {}).items():
        a += ["--env", f"{k}={v}"]
    tmpdir.mkdir(parents=True, exist_ok=True)
    parts = chunk_bundle(build_bundle(item, base))
    total_raw = sum(map(len, parts)) + (HERE / "cops_run.py").stat().st_size
    if total_raw * 4 / 3 > MAX_TOTAL_ENCODED:        # observed live: the API rejected 50,147 B (x4/3 = 66.9 KB) and 63,554 B in total, accepted 28.9 KB: the limit is on the SUM of injected files
        raise ValueError(f"injected files total {total_raw} B raw (about {int(total_raw * 4 / 3)} B encoded) > {MAX_TOTAL_ENCODED}; shrink the file list")
    for i, part in enumerate(parts):
        p = tmpdir / f"part-{i:03d}"
        p.write_bytes(part)
        a += ["--inject-file", f"{p}:/work/_b/part-{i:03d}"]
    return a + ["--async"]


# ------------------------------------------------------------------ cloud
def _run(argv, timeout=120):
    r = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout, r.stderr


@dataclass
class W:
    id: str; name: str; kind: str; platform: str; preset: str; state: str; created_at: str = ""

    @property
    def active(self): return self.state not in TERMINAL

    @property
    def gpus(self):
        m = re.match(r"(\d+)gpu", self.preset or ""); return int(m.group(1)) if m else 0


class Cloud:
    def snapshot(self):
        out = []
        for kind in ("job", "endpoint"):
            rc, so, se = _run([NEB, "--profile", PROFILE, "ai", kind, "list", "--format", "json"], 60)
            if rc:
                raise RuntimeError(f"list {kind} rc={rc}: {se.strip()[:200]}")
            doc = json.loads(so)
            if doc.get("next_page_token"):
                raise RuntimeError("pool listing truncated (next_page_token); refusing to guess")
            for it in doc.get("items", []):
                md, sp, st = it.get("metadata", {}), it.get("spec", {}), it.get("status", {})
                out.append(W(md.get("id", ""), md.get("name", ""), kind, sp.get("platform", ""), sp.get("preset", ""),
                             str(st.get("state", "UNKNOWN")).upper(), md.get("created_at", "")))
        return out

    def create(self, argv):
        rc, so, se = _run(argv, 240)
        ids = re.findall(r"aijob-[a-z0-9]+", so + se)
        if rc or not ids:
            raise RuntimeError(f"create rc={rc}: {(se or so).strip()[:900]}")
        return ids[0]

    def state(self, job_id):
        rc, so, se = _run([NEB, "--profile", PROFILE, "ai", "job", "get", "--id", job_id, "--format", "json"], 60)
        if rc:
            raise RuntimeError(f"get rc={rc}: {se.strip()[:200]}")
        return str(json.loads(so).get("status", {}).get("state", "UNKNOWN")).upper()

    def cancel(self, job_id):
        rc, so, se = _run([NEB, "--profile", PROFILE, "ai", "job", "cancel", "--id", job_id], 90)
        return rc

    def logs(self, job_id, since, until, depth=0):
        """All log lines in [since, until]; halves the window while a query hits the 1000-line API cap."""
        def q(a, b):
            rc, so, se = _run([NEB, "--profile", PROFILE, "ai", "job", "logs", job_id, "--since", a.isoformat(),
                               "--until", b.isoformat(), "--tail", "1000"], 300)
            if rc and "in the future" not in se:
                raise RuntimeError(f"logs rc={rc}: {se.strip()[:200]}")
            return [] if rc else so.splitlines()
        lines = q(since, until)
        if len(lines) >= 1000 and (until - since).total_seconds() > 1.0 and depth < 14:
            mid = since + (until - since) / 2
            return self.logs(job_id, since, mid, depth + 1) + self.logs(job_id, mid, until, depth + 1)
        return lines


def extract_result(lines: list[str]):
    """-> (meta, tar_bytes|None). Verifies sha256 against the job-side digest; raises on mismatch."""
    meta, b64, seen_end, seen, started = None, [], False, set(), False
    for ln in lines:
        i = ln.find("COPS_RESULT_BEGIN ")
        if i >= 0:
            meta = json.loads(ln[i + 18:]); b64 = []; seen = set(); started = True; seen_end = False; continue
        if started and "COPS_RESULT_END" in ln:
            seen_end = True; break
        j = ln.find("COPS_B64 ")
        if started and j >= 0 and ln not in seen:        # windowed fetches can duplicate edge lines
            seen.add(ln); b64.append(ln[j + 9:].strip())
    if meta is None or not seen_end:
        return meta, None
    if meta["truncated"]:
        return meta, None
    blob = base64.b64decode("".join(b64))
    if hashlib.sha256(blob).hexdigest() != meta["sha256"] or len(blob) != meta["bytes"]:
        raise ValueError("result digest mismatch (log lines lost or duplicated)")
    return meta, blob


def extract_parts(lines: list[str]):
    """Warm-worker parts: -> list of (meta, blob|None) for every COMPLETE part (BEGIN ... END) in log order; verifies sha256 per part; a part whose meta says truncated has blob None.
    Tolerates a log cut in the middle of a later part (that part is ignored: it is incomplete)."""
    parts, cur, b64, seen = [], None, [], set()
    for ln in lines:
        i = ln.find("COPS_PART_BEGIN ")
        if i >= 0:
            cur = json.loads(ln[i + 16:]); b64 = []; seen = set(); continue
        if cur is not None and "COPS_PART_END" in ln:
            if cur.get("truncated"):
                parts.append((cur, None))
            else:
                blob = base64.b64decode("".join(b64))
                if hashlib.sha256(blob).hexdigest() != cur["sha256"] or len(blob) != cur["bytes"]:
                    raise ValueError(f"part {cur.get('id')} digest mismatch (log lines lost or duplicated)")
                parts.append((cur, blob))
            cur = None; continue
        j = ln.find("COPS_B64 ")
        if cur is not None and j >= 0 and ln not in seen:
            seen.add(ln); b64.append(ln[j + 9:].strip())
    return parts


def write_parts(parts, outdir):
    """Idempotently write each part's files under <outdir>/parts/<seq>-<id>/ and a parts_manifest.json. Returns the manifest rows."""
    outdir = Path(outdir); rows = []
    for meta, blob in parts:
        d = outdir / "parts" / f"{meta['seq']:02d}-{meta['id']}"
        if blob is not None:
            d.mkdir(parents=True, exist_ok=True)
            tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz").extractall(d, filter="data") if hasattr(tarfile, "data_filter") else tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz").extractall(d)
        rows.append({k: meta.get(k) for k in ("seq", "id", "rc", "timed_out", "start_utc", "end_utc", "wall_s", "bytes", "sha256", "truncated", "NOT_RETURNED")})
    save(outdir / "parts_manifest.json", rows)
    return rows


# ------------------------------------------------------------------ controller
@dataclass
class Run:
    item: dict
    status: str = "pending"          # pending|running|done|failed|timeout|yielded_requeued|abandoned
    job_id: str = ""; name: str = ""; attempts: int = 0
    t_create: float = 0.0; t_running: object = None
    result: dict = field(default_factory=dict)


def save(p, obj):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp"); tmp.write_text(json.dumps(obj, indent=1) + "\n"); os.replace(tmp, p)


class Batch:
    def __init__(self, spec, cloud=None, outdir=OUTDIR, base=Path("."), max_parallel=1, gpu_cap=10, poll=20,
                 max_requeues=1, grace=180, deadline_s=None, sleep=time.sleep, clock=time.time, pool_size=16, wait_grace_s=300):
        self.spec, self.cloud, self.outdir, self.base = spec, cloud or Cloud(), Path(outdir), Path(base)
        self.max_parallel, self.gpu_cap, self.poll, self.max_requeues = max_parallel, gpu_cap, poll, max_requeues
        self.grace, self.sleep, self.clock = grace, sleep, clock
        self.pool_size, self.wait_grace_s = pool_size, wait_grace_s
        self.tag = spec.get("run_tag") or dt.datetime.now(dt.timezone.utc).strftime("%m%d%H%M%S")
        self.deadline = clock() + deadline_s if deadline_s else None
        items = sorted(enumerate(spec["items"]), key=lambda t: (t[1].get("priority", t[0]), t[0]))
        self.runs = [Run(it) for _, it in items]
        self.manifest = {"run_tag": self.tag, "owned": [], "events": []}
        self.log = []

    # -- bookkeeping
    def ev(self, msg, **kw):
        e = {"t": utc(), "msg": msg, **kw}; self.log.append(e); print(json.dumps(e), flush=True)
        self.manifest["events"] = self.log[-500:]
        save(self.outdir / f"manifest-{self.tag}.json", self._doc())

    def _doc(self):
        return {**self.manifest, "owned": [{"id": r.job_id, "name": r.name, "item": r.item["id"], "status": r.status,
                "attempts": r.attempts, "result": r.result} for r in self.runs if r.job_id]}

    def owned_ids(self):
        return {r.job_id: r.name for r in self.runs if r.job_id}

    # -- policy (pure; unit-tested)
    def ours_active_gpus(self, snap):
        own = self.owned_ids(); n = 0
        for w in snap:
            if w.platform.startswith("gpu-h100") and w.active and (w.id in own or w.name.startswith(COUNT_PREFIXES)):
                n += w.gpus
        return n

    def pool_active_h100(self, snap):
        return sum(w.gpus for w in snap if w.platform.startswith("gpu-h100") and w.active and w.state not in WAITING) \
            + sum(w.gpus for w in snap if w.platform.startswith("gpu-h100") and w.state in WAITING)

    @staticmethod
    def _age_s(created_at, now):
        try:
            c = re.sub(r"(\.\d{6})\d*", r"\1", created_at).replace("Z", "+00:00")
            return now - dt.datetime.fromisoformat(c).timestamp()
        except Exception:
            return 0.0                                  # unknown age counts as brand new (never triggers the time rule)

    def foreign_waiting(self, snap):
        """Foreign H100 workloads that are plausibly BLOCKED by us: in a waiting state AND (the pool is full, i.e. active+waiting >= pool_size, OR the
        workload has waited longer than wait_grace_s). A provisioning job in a mostly idle pool is normal startup, not a reason to cancel running work
        (a false trigger cancelled our job at the finish line at 13:13 PDT Oct 31; the result was recovered from the log)."""
        own = self.owned_ids()
        cand = [w for w in snap if w.platform.startswith("gpu-h100") and w.state in WAITING
                and w.id not in own and not w.name.startswith(COUNT_PREFIXES)]
        if not cand:
            return []
        full = self.pool_active_h100(snap) >= self.pool_size
        now = self.clock()
        return [w for w in cand if full or self._age_s(w.created_at, now) >= self.wait_grace_s]

    def running(self): return [r for r in self.runs if r.status == "running"]
    def pending(self): return [r for r in self.runs if r.status == "pending"]

    def step(self):
        """One control iteration. Returns False when all runs are final."""
        now = self.clock()
        try:
            snap = self.cloud.snapshot(); snap_ok = True
        except Exception as e:                      # noqa: BLE001 - fail closed
            snap, snap_ok = [], False; self.ev("snapshot_failed_no_launch", error=str(e)[:200])
        # refresh running jobs, enforce hard timeout
        for r in list(self.running()):
            try:
                st = self.cloud.state(r.job_id)
            except Exception as e:                  # noqa: BLE001
                self.ev("state_error", job=r.job_id, error=str(e)[:160]); continue
            if st not in WAITING and r.t_running is None:
                r.t_running = now
            if st in TERMINAL:
                self.finish(r, st)
            elif r.t_running is not None and now - r.t_running > parse_dur(r.item.get("timeout", "10m")) + self.grace:
                self.cancel_own(r, "client_watchdog_timeout"); r.status = "timeout"
        # yield to others (GPU only)
        waiting = self.foreign_waiting(snap) if snap_ok else []
        if waiting:
            gpu_running = [r for r in self.running() if r.item.get("kind", "gpu") == "gpu"]
            if gpu_running:
                victim = max(gpu_running, key=lambda r: (self.runs.index(r)))      # lowest priority = last in order
                self.ev("yield", victim=victim.job_id, waiting=[w.id for w in waiting][:5])
                self.cancel_own(victim, "yield_to_other_team")
                victim.status = "pending" if victim.attempts <= self.max_requeues else "abandoned"
        # launch
        can_launch = snap_ok and not waiting and not (self.deadline and now > self.deadline)
        for r in self.pending():
            if not can_launch or len(self.running()) >= self.max_parallel:
                break
            kind = r.item.get("kind", "gpu")
            if kind == "gpu" and self.ours_active_gpus(snap) + 1 > self.gpu_cap:
                self.ev("gpu_cap_reached", cap=self.gpu_cap); break
            self.launch(r)
            if kind == "gpu":
                snap = snap + [W(r.job_id, r.name, "job", "gpu-h100-sxm", "1gpu", "RUNNING")]
        if self.deadline and now > self.deadline:
            for r in self.pending():
                r.status = "abandoned"; self.ev("abandoned_deadline", item=r.item["id"])
        return bool(self.pending() or self.running())

    def launch(self, r):
        if r.job_id:
            self.manifest.setdefault("history", []).append({"id": r.job_id, "name": r.name, "item": r.item["id"]})
        r.attempts += 1
        r.name = f"{OWN_PREFIX}{self.tag}-{re.sub('[^a-z0-9-]', '-', r.item['id'].lower())}-a{r.attempts}"[:60]
        tmp = self.outdir / "_inject" / r.name
        try:
            argv = create_argv(r.item, r.name, self.base, tmp)
            new_id = self.cloud.create(argv)
        except Exception as e:                      # noqa: BLE001 - one bad create must not kill the controller or orphan other jobs
            msg = str(e)
            quota = "ResourceExhausted" in msg or "Quota" in msg
            r.result = {"error": msg[:900], "create_failed": True}
            r.status = "pending" if quota and r.attempts < 3 else "failed"
            self.ev("create_failed", item=r.item["id"], quota=quota, final=r.status == "failed", error=msg[:600])
            r.job_id = ""
            return
        r.job_id = new_id
        r.status, r.t_create, r.t_running = "running", self.clock(), None
        self.ev("created", job=r.job_id, name=r.name, item=r.item["id"], kind=r.item.get("kind", "gpu"))

    def cancel_own(self, r, why):
        assert r.job_id and r.name.startswith(OWN_PREFIX) and r.job_id in self.owned_ids(), "refusing to cancel non-owned job"
        rc = self.cloud.cancel(r.job_id); self.ev("cancel", job=r.job_id, why=why, rc=rc)

    def finish(self, r, st):
        d = self.outdir / "results" / f"{self.tag}-{r.item['id']}"
        try:
            t0 = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=6)
            lines = self.cloud.logs(r.job_id, t0, dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=2))
            d.mkdir(parents=True, exist_ok=True); (d / "job.log").write_text("\n".join(lines) + "\n")
            meta, blob = extract_result(lines)
            parts = extract_parts(lines)
            if parts:                                # warm-worker item: every complete part is written even if the final result failed
                r.result["parts"] = write_parts(parts, d)
        except Exception as e:                      # noqa: BLE001
            meta, blob = None, None; r.result = {**r.result, "error": f"{type(e).__name__}: {str(e)[:200]}"}
        if blob is not None:
            with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tf:
                tf.extractall(d / "out", filter="data")
        if meta:
            r.result = {**r.result, **{k: meta[k] for k in ("rc", "timed_out", "wall_s", "bytes", "sha256", "truncated")}}
        ok = st == "COMPLETED" and meta and meta.get("rc") == 0 and (blob is not None)
        r.status = "done" if ok else ("timeout" if meta and meta.get("timed_out") else "failed")
        r.result["job_state"] = st
        self.ev("finished", job=r.job_id, item=r.item["id"], status=r.status, **{k: v for k, v in r.result.items() if k != "error"})

    def run(self):
        self.ev("batch_start", items=len(self.runs), max_parallel=self.max_parallel, gpu_cap=self.gpu_cap)
        try:
            while self.step():
                self.sleep(self.poll)
        except KeyboardInterrupt:
            self.ev("interrupted_cancelling_owned")
            for r in self.running():
                self.cancel_own(r, "interrupt")
            raise
        self.ev("batch_end", summary={r.item["id"]: r.status for r in self.runs})
        return self._doc()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run"); r.add_argument("items"); r.add_argument("--max-parallel", type=int, default=1)
    r.add_argument("--gpu-cap", type=int, default=10); r.add_argument("--poll", type=int, default=20)
    r.add_argument("--deadline-min", type=float); r.add_argument("--dry-run", action="store_true")
    r.add_argument("--base", default="."); r.add_argument("--outdir", default=str(OUTDIR))
    sub.add_parser("status")
    pa = sub.add_parser("parts", help="extract every complete warm-worker part from a job's log (works while the job is still running)")
    pa.add_argument("job_id"); pa.add_argument("--outdir", required=True)
    c = sub.add_parser("collect", help="fetch + verify results of an existing job we created (recovery path)")
    c.add_argument("job_id"); c.add_argument("item_id"); c.add_argument("--tag", default="recovered"); c.add_argument("--outdir", default=str(OUTDIR))
    a = ap.parse_args(argv)
    if a.cmd == "status":
        c = Cloud(); snap = c.snapshot(); b = Batch({"items": []}, c)
        act = [w for w in snap if w.active]
        print(json.dumps({"total": len(snap), "active": [vars(w) for w in act],
                          "our_active_h100": b.ours_active_gpus(snap), "foreign_waiting_h100": len(b.foreign_waiting(snap))}, indent=1))
        return 0
    if a.cmd == "parts":
        if not a.job_id.startswith("aijob-"):
            raise SystemExit("job id must look like aijob-...")
        now = dt.datetime.now(dt.timezone.utc)
        rows = write_parts(extract_parts(Cloud().logs(a.job_id, now - dt.timedelta(hours=6), now + dt.timedelta(minutes=2))), a.outdir)
        print(json.dumps(rows, indent=1)); return 0
    if a.cmd == "collect":
        if not a.job_id.startswith("aijob-"):
            raise SystemExit("job id must look like aijob-...")
        b = Batch({"run_tag": a.tag, "items": [{"id": a.item_id, "script": "x"}]}, outdir=Path(a.outdir))
        r = b.runs[0]; r.job_id, r.name = a.job_id, OWN_PREFIX + "recovered"
        b.finish(r, b.cloud.state(a.job_id)); return 0 if r.status == "done" else 1
    spec = json.loads(Path(a.items).read_text())
    b = Batch(spec, base=Path(a.base), outdir=Path(a.outdir), max_parallel=a.max_parallel, gpu_cap=a.gpu_cap, poll=a.poll,
              deadline_s=a.deadline_min * 60 if a.deadline_min else None)
    if a.dry_run:
        for r in b.runs:
            ar = create_argv(r.item, f"{OWN_PREFIX}{b.tag}-{r.item['id']}", b.base, Path(a.outdir) / "_dry")
            print(shlex.join([x if len(x) < 200 else x[:60] + "...<elided>" for x in ar]))
        return 0
    doc = b.run()
    return 0 if all(x["status"] == "done" for x in doc["owned"]) else 1


if __name__ == "__main__":
    sys.exit(main())
