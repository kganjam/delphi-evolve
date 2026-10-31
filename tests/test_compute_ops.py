"""compute_ops controller tests: fake cloud, no network, no shared-pool load."""
import base64, gzip, hashlib, io, json, tarfile
from pathlib import Path

import pytest

from compute_ops import batch as B


def make_log(files: dict, rc=0, timed_out=False, truncated=False):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for n, d in files.items():
            ti = tarfile.TarInfo(n); ti.size = len(d); tf.addfile(ti, io.BytesIO(d))
    blob = buf.getvalue()
    meta = {"item": "x", "rc": rc, "timed_out": timed_out, "wall_s": 1.0, "bytes": len(blob),
            "sha256": hashlib.sha256(blob).hexdigest(), "truncated": truncated}
    b64 = base64.b64encode(blob).decode()
    lines = ["2026 noise", "COPS_RESULT_BEGIN " + json.dumps(meta)] + ["COPS_B64 " + b64[i:i + 900] for i in range(0, len(b64), 900)]
    return meta, blob, lines + ["COPS_RESULT_END"]


def test_extract_roundtrip_and_duplicate_edge_lines():
    meta, blob, lines = make_log({"a.txt": b"hello" * 5000})
    dup = lines[:3] + [lines[2]] + lines[3:]                   # a windowed fetch can repeat a boundary line
    m, got = B.extract_result(["pre"] + dup)
    assert got == blob and m["rc"] == 0


def test_extract_detects_loss():
    _, _, lines = make_log({"a.bin": __import__("os").urandom(20000)})
    with pytest.raises(ValueError):
        B.extract_result(lines[:3] + lines[4:])               # one chunk lost
    assert B.extract_result(lines[:-1])[1] is None             # no END marker -> no result, not a crash


def test_bundle_chunking_limit(tmp_path):
    import os
    (tmp_path / "s.py").write_text("print(1)\n")
    (tmp_path / "big.bin").write_bytes(os.urandom(900_000))
    with pytest.raises(ValueError):
        B.chunk_bundle(B.build_bundle({"id": "x", "script": "s.py", "files": ["big.bin"]}, tmp_path))
    parts = B.chunk_bundle(B.build_bundle({"id": "x", "script": "s.py"}, tmp_path))
    assert all(len(p) <= B.CHUNK for p in parts)


class Fake:
    def __init__(self):
        self.pool, self.states, self.created, self.cancelled, self.n, self.fail_snapshot = [], {}, [], [], 0, False
        self.log_for = {}

    def snapshot(self):
        if self.fail_snapshot:
            raise RuntimeError("down")
        return list(self.pool)

    def create(self, argv):
        self.n += 1; jid = f"aijob-fake{self.n}"
        name = argv[argv.index("--name") + 1]
        self.created.append((jid, name)); self.states[jid] = "RUNNING"
        self.pool.append(B.W(jid, name, "job", "gpu-h100-sxm" if "gpu-h100" in " ".join(argv) else "cpu-d3",
                             "1gpu-16vcpu-200gb" if "gpu-h100" in " ".join(argv) else "16vcpu-64gb", "RUNNING"))
        return jid

    def state(self, j): return self.states[j]

    def cancel(self, j):
        assert j.startswith("aijob-fake"); self.cancelled.append(j); self.states[j] = "CANCELLED"; return 0

    def logs(self, j, a, b): return self.log_for.get(j, make_log({"r.txt": b"ok"})[2])


def mk(tmp_path, items, fake, **kw):
    (tmp_path / "s.py").write_text("print(1)\n")
    t = [0.0]
    def clock(): return t[0]
    def sleep(s): t[0] += s
    spec = {"run_tag": "t", "items": [{"script": "s.py", **i} for i in items]}
    return B.Batch(spec, cloud=fake, outdir=tmp_path / "out", base=tmp_path, poll=10, sleep=sleep, clock=clock, **kw), t


def test_respects_parallel_and_finishes(tmp_path):
    f = Fake(); b, _ = mk(tmp_path, [{"id": f"i{k}"} for k in range(4)], f, max_parallel=2)
    b.step(); assert len(f.created) == 2
    for jid, _n in f.created: f.states[jid] = "COMPLETED"
    for p in f.pool: p.state = "COMPLETED"
    b.step(); assert len(f.created) == 4
    for jid, _n in f.created: f.states[jid] = "COMPLETED"
    for p in f.pool: p.state = "COMPLETED"
    assert b.step() is False
    assert [r.status for r in b.runs] == ["done"] * 4
    assert (tmp_path / "out/results/t-i0/out/r.txt").read_bytes() == b"ok"


def test_gpu_cap_counts_foreign_prefix_and_never_exceeds(tmp_path):
    f = Fake()
    for k in range(9):                                          # nine gpu_batch-style jobs of ours still active
        f.pool.append(B.W(f"aijob-old{k}", f"delphi-evolve-scale-x{k}", "job", "gpu-h100-sxm", "1gpu-16vcpu-200gb", "RUNNING"))
    b, _ = mk(tmp_path, [{"id": "a"}, {"id": "b"}, {"id": "c"}], f, max_parallel=3, gpu_cap=10)
    b.step(); assert len(f.created) == 1                        # only one free slot under the cap of 10


def test_fail_closed_on_snapshot_error(tmp_path):
    f = Fake(); f.fail_snapshot = True
    b, _ = mk(tmp_path, [{"id": "a"}], f, max_parallel=2)
    b.step(); assert f.created == []


def test_no_yield_when_pool_has_room_and_foreign_job_is_just_provisioning(tmp_path):
    f = Fake(); b, _ = mk(tmp_path, [{"id": "a"}, {"id": "b"}], f, max_parallel=2)
    b.step(); assert len(f.created) == 2
    f.pool.append(B.W("aijob-theirs", "other-team-job", "job", "gpu-h100-sxm", "1gpu-16vcpu-200gb", "PROVISIONING"))
    b.step()
    assert f.cancelled == []                                    # 3 of 16 H100s in use: their startup is not blocked by us


def test_yield_when_foreign_job_has_waited_past_grace_even_if_pool_not_full(tmp_path):
    f = Fake(); b, t = mk(tmp_path, [{"id": "a"}, {"id": "b"}], f, max_parallel=2)
    b.step(); assert len(f.created) == 2
    t[0] = 1000.0                                               # fake clock: 1000 s after the epoch
    f.pool.append(B.W("aijob-theirs", "other-team-job", "job", "gpu-h100-sxm", "1gpu-16vcpu-200gb", "QUEUED", "1970-01-01T00:01:00.123456789Z"))   # waiting for 940 s
    b.step()
    assert f.cancelled == ["aijob-fake2"]


def test_yield_cancels_only_own_lowest_priority_and_requeues(tmp_path):
    f = Fake(); b, _ = mk(tmp_path, [{"id": "a"}, {"id": "b"}], f, max_parallel=2)
    b.pool_size = 2                                              # pool full: 2 ours + 1 waiting >= 2
    b.step(); assert len(f.created) == 2
    f.pool.append(B.W("aijob-theirs", "other-team-job", "job", "gpu-h100-sxm", "1gpu-16vcpu-200gb", "QUEUED"))
    b.step()
    assert f.cancelled == ["aijob-fake2"]                       # last-priority own job; never aijob-theirs
    assert "aijob-theirs" not in f.cancelled
    assert [r.status for r in b.runs] == ["running", "pending"]
    f.pool = [p for p in f.pool if p.id != "aijob-theirs"]       # their job started; capacity is released
    b.step(); assert len(f.created) == 3 and b.runs[1].attempts == 2


def test_cancel_refuses_non_owned(tmp_path):
    f = Fake(); b, _ = mk(tmp_path, [{"id": "a"}], f)
    r = b.runs[0]; r.job_id, r.name = "aijob-theirs", "other-team-job"
    with pytest.raises(AssertionError):
        b.cancel_own(r, "test")
    assert f.cancelled == []


def test_client_watchdog_cancels_after_timeout_plus_grace(tmp_path):
    f = Fake(); b, t = mk(tmp_path, [{"id": "a", "timeout": "10m"}], f, grace=60)
    b.step(); b.step(); t[0] += 10 * 60 + 61
    b.step()
    assert f.cancelled == ["aijob-fake1"] and b.runs[0].status == "timeout"


def test_failed_job_rc_marks_failed(tmp_path):
    f = Fake(); b, _ = mk(tmp_path, [{"id": "a"}], f)
    b.step(); f.log_for["aijob-fake1"] = make_log({}, rc=3)[2]; f.states["aijob-fake1"] = "FAILED"
    b.step(); assert b.runs[0].status == "failed"


def test_create_failure_does_not_crash_or_orphan(tmp_path):
    class QuotaFake(Fake):
        def create(self, argv):
            if "cpu-d3" in " ".join(argv):
                raise RuntimeError("create rc=24: ResourceExhausted Quota limit exceeded non-gpu.vcpu")
            return super().create(argv)
    f = QuotaFake(); b, _ = mk(tmp_path, [{"id": "g"}, {"id": "c", "kind": "cpu"}], f, max_parallel=2)
    b.step()
    assert len(f.created) == 1 and b.runs[0].status == "running"   # the GPU job is tracked, controller alive
    assert b.runs[1].status == "pending"                           # quota is retried (bounded), not fatal
    for _ in range(4): b.step()
    assert b.runs[1].status == "failed" and b.runs[1].attempts == 3


def test_total_inject_size_guard(tmp_path):
    import os
    (tmp_path / "s.py").write_text("print(1)\n")
    (tmp_path / "big.bin").write_bytes(os.urandom(50_000))      # incompressible: > 48 KB raw in total
    with pytest.raises(ValueError):
        B.create_argv({"id": "x", "script": "s.py", "files": ["big.bin"]}, "delphi-evolve-ops-t-x", tmp_path, tmp_path / "tmp")


def _run_worker(tmp_path, queue):
    import json, subprocess, sys
    (tmp_path / "q.json").write_text(json.dumps(queue))
    (tmp_path / "w.py").write_text("import os,sys,time\nopen(os.path.join(os.environ['COPS_OUT'],'o.txt'),'w').write('x'*int(sys.argv[1]))\ntime.sleep(float(sys.argv[2]))\n")
    env = dict(__import__("os").environ, WARM_PARTS_DIR=str(tmp_path / "parts"), COPS_OUT=str(tmp_path / "out"), WARM_CWD=str(tmp_path))
    p = subprocess.run([sys.executable, str(__import__("pathlib").Path(B.__file__).parent / "warm_worker.py"), str(tmp_path / "q.json")], capture_output=True, text=True, env=env, timeout=120)
    return p, p.stdout.splitlines()


def test_warm_worker_sequential_parts_roundtrip_cap_timeout_and_budget_skip(tmp_path):
    import json, sys
    W = lambda i, n, sl, to, **k: {"id": i, "argv": [sys.executable, "w.py", str(n), str(sl)], "timeout_s": to, **k}
    q = {"queue_id": "t", "max_wall_s": 40, "margin_s": 1, "workloads": [W("a", 5000, 0, 10), W("big", 800000, 0, 10, max_part_bytes=500), W("slow", 10, 30, 2), W("late", 10, 0, 100)]}
    p, lines = _run_worker(tmp_path, q)
    parts = B.extract_parts(lines)
    ids = [m["id"] for m, _ in parts]
    assert ids == ["a", "big", "slow"]                              # 'late' needs 101 s of a 40 s budget: skipped, recorded
    assert parts[0][1] is not None and parts[1][1] is None and parts[1][0]["truncated"] and "NOT_RETURNED" in parts[1][0]   # over-cap output is flagged loudly, not silently dropped
    assert parts[2][0]["timed_out"] is True
    rec = json.loads((tmp_path / "out" / "queue_receipts.json").read_text())["workloads"]
    assert [r["status"] for r in rec] == ["done", "done", "failed", "not_run_budget"]
    rows = B.write_parts(parts, tmp_path / "ret")
    assert (tmp_path / "ret" / "parts" / "00-a" / "o.txt").read_text() == "x" * 5000 and len(rows) == 3


def test_extract_parts_ignores_incomplete_trailing_part_and_detects_loss(tmp_path):
    import json, sys
    q = {"queue_id": "t", "max_wall_s": 60, "margin_s": 1, "workloads": [{"id": "a", "argv": [sys.executable, "w.py", "20000", "0"], "timeout_s": 10}, {"id": "b", "argv": [sys.executable, "w.py", "20000", "0"], "timeout_s": 10}]}
    _, lines = _run_worker(tmp_path, q)
    cut = [i for i, l in enumerate(lines) if "COPS_PART_END" in l][0] + 5          # log cut inside part b
    assert [m["id"] for m, _ in B.extract_parts(lines[:cut])] == ["a"]
    bad = [l for i, l in enumerate(lines) if not (i == 3 and "COPS_B64" in l)]       # one data line lost
    with pytest.raises(ValueError):
        B.extract_parts(bad)
