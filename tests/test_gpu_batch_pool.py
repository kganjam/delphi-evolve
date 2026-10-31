"""Fixture tests for ownership, counting, yielding and cancel-safety. No cloud calls, no load."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gpu_batch import controller as C, pool as P  # noqa: E402


def wl(id, name, state, gpus=1, platform="gpu-h100-sxm", kind="job", created="2026-10-31T08:00:00Z"):
    return P.Workload(id=id, name=name, kind=kind, platform=platform, preset=f"{gpus}gpu-16vcpu-200gb", state=state,
                      created_at=created, gpus=gpus, raw_state_known=state in P.TERMINAL | P.WAITING | P.HOLDING)


def manifest(owned=(), peers=("aijob-peer1",)):
    return {"peers": [{"id": p, "name": "kganjam-delphi-trpb-x"} for p in peers],
            "count_conservatively_prefixes": ["kganjam-delphi-"],
            "owned": [{"id": i, "name": f"delphi-evolve-scale-{i}", "priority": pr, "checkpointed": True} for i, pr in owned]}


def snap(*w, ok=True, truncated=False):
    return P.Snapshot(ok, list(w), truncated=truncated, error="" if ok else "boom")


CFG = P.Config()


def test_parse_items_states_and_gpus():
    doc = {"items": [{"metadata": {"id": "a", "name": "n", "created_at": "t"},
                      "spec": {"platform": "gpu-h100-sxm", "preset": "8gpu-128vcpu-1600gb"}, "status": {"state": "running"}}]}
    w = P.parse_items(doc, "job")[0]
    assert (w.gpus, w.state, w.is_h100, w.active) == (8, "RUNNING", True, True)


def test_counting_includes_peers_and_unlisted_team_prefix_but_not_strangers():
    m = manifest(owned=[("aijob-s1", 1)])
    s = snap(wl("aijob-peer1", "kganjam-delphi-trpb-x", "RUNNING"), wl("aijob-s1", "delphi-evolve-scale-aijob-s1", "RUNNING"),
             wl("aijob-new", "kganjam-delphi-trpb-followup", "RUNNING"),     # unlisted follow-up: counted, not cancellable
             wl("aijob-o", "kg-extract", "RUNNING", kind="endpoint"),           # 'kg' naming is NOT ours
             wl("aijob-done", "delphi-evolve-scale-old", "COMPLETED"))
    c = P.count_ours(s, m)
    assert c["ours"] == 3 and c["others_active"] == 1 and c["pool_free_estimate"] == 16 - 4
    assert P.classify(s.workloads[3], m) == "other"


def test_launch_slots_respect_cap_and_pool_reserve():
    m = manifest(owned=[(f"aijob-s{i}", 1) for i in range(8)])
    s = snap(wl("aijob-peer1", "kganjam-delphi-trpb-x", "RUNNING"), *[wl(f"aijob-s{i}", f"delphi-evolve-scale-aijob-s{i}", "RUNNING") for i in range(8)])
    assert P.decide(s, m, CFG)["launch_slots"] == 1          # 9 of 10 -> exactly one more
    s2 = snap(*s.workloads, wl("aijob-s8", "delphi-evolve-scale-aijob-s8", "RUNNING"))
    m2 = manifest(owned=[(f"aijob-s{i}", 1) for i in range(9)])
    assert P.decide(s2, m2, CFG)["launch_slots"] == 0         # at cap
    # others occupy 5 => 16-5-2(ours)=9 free; fine. others occupy 13 => reserve of 2 blocks launching
    busy = snap(wl("aijob-peer1", "kganjam-delphi-trpb-x", "RUNNING"), wl("aijob-x", "teamB", "RUNNING", gpus=8),
                wl("aijob-y", "teamC", "RUNNING", gpus=5))
    assert P.decide(busy, manifest(), CFG)["launch_slots"] == 0


def test_yield_releases_lowest_priority_first_and_only_as_many_as_needed():
    m = manifest(owned=[("aijob-a", 1), ("aijob-b", 3), ("aijob-c", 2)])
    live = [wl("aijob-peer1", "kganjam-delphi-trpb-x", "RUNNING")] + [wl(f"aijob-{k}", f"delphi-evolve-scale-aijob-{k}", "RUNNING") for k in "abc"]
    full = live + [wl("aijob-o1", "teamB", "RUNNING", gpus=8), wl("aijob-o2", "teamC", "RUNNING", gpus=4)]   # 4 + 12 = 16: pool full
    d = P.decide(snap(*full, wl("aijob-w", "teamD", "PENDING", gpus=1)), m, CFG)
    assert d["release"] == ["aijob-b"] and d["launch_slots"] == 0              # priority 3 goes first, 1 GPU demanded
    d2 = P.decide(snap(*full, wl("aijob-w", "teamD", "PENDING", gpus=2)), m, CFG)
    assert d2["release"] == ["aijob-b", "aijob-c"]                              # 2 GPUs demanded -> next lowest priority
    assert "aijob-peer1" not in d2["release"]


def test_no_release_when_pool_has_free_capacity_for_the_waiting_job():
    m = manifest(owned=[("aijob-a", 1)])
    d = P.decide(snap(wl("aijob-peer1", "kganjam-delphi-trpb-x", "RUNNING"), wl("aijob-a", "delphi-evolve-scale-aijob-a", "RUNNING"),
                      wl("aijob-w", "teamD", "QUEUED", gpus=1)), m, CFG)
    assert d["release"] == [] and d["launch_slots"] == 0                       # do not expand while anyone is waiting


def test_unknown_state_of_other_team_is_treated_as_possible_waiter():
    m = manifest(owned=[("aijob-a", 1)])
    full = [wl("aijob-peer1", "kganjam-delphi-trpb-x", "RUNNING"), wl("aijob-a", "delphi-evolve-scale-aijob-a", "RUNNING"),
            wl("aijob-o1", "teamB", "RUNNING", gpus=14), wl("aijob-w", "teamD", "SOMETHING_NEW")]
    d = P.decide(snap(*full), m, CFG)
    assert d["release"] == ["aijob-a"]


def test_blind_snapshot_launches_nothing_and_requests_drain_after_limit():
    m = manifest(owned=[("aijob-a", 1)])
    assert P.decide(snap(ok=False), m, CFG, blind_polls=0)["launch_slots"] == 0
    assert not P.decide(snap(ok=False), m, CFG, blind_polls=0)["drain_blind"]
    assert P.decide(snap(ok=False), m, CFG, blind_polls=CFG.blind_poll_limit - 1)["drain_blind"]
    assert P.decide(snap(truncated=True), m, CFG)["launch_slots"] == 0


def test_own_job_stuck_waiting_blocks_expansion():
    m = manifest(owned=[("aijob-a", 1)])
    d = P.decide(snap(wl("aijob-peer1", "kganjam-delphi-trpb-x", "RUNNING"), wl("aijob-a", "delphi-evolve-scale-aijob-a", "PROVISIONING")), m, CFG)
    assert d["launch_slots"] == 0


def test_verify_cancellable_refuses_everything_not_verifiably_ours():
    m = manifest(owned=[("aijob-a", 1)])
    good = {"metadata": {"id": "aijob-a", "name": "delphi-evolve-scale-aijob-a"}}
    assert P.verify_cancellable("aijob-a", good, m)[0]
    assert not P.verify_cancellable("aijob-peer1", {"metadata": {"id": "aijob-peer1", "name": "kganjam-delphi-trpb-x"}}, m)[0]
    # another team's job that merely copies our prefix is refused because its id is not in the manifest
    assert not P.verify_cancellable("aijob-evil", {"metadata": {"id": "aijob-evil", "name": "delphi-evolve-scale-fake"}}, m)[0]
    assert not P.verify_cancellable("aijob-a", {"metadata": {"id": "aijob-a", "name": "renamed"}}, m)[0]
    assert not P.verify_cancellable("aijob-a", {"metadata": {"id": "aijob-zzz", "name": "delphi-evolve-scale-aijob-a"}}, m)[0]


class FakeCloud:
    def __init__(self, snaps):
        self.snaps, self.cancelled, self.created = list(snaps), [], []

    def snapshot(self):
        return self.snaps.pop(0) if len(self.snaps) > 1 else self.snaps[0]

    def get(self, jid):
        for w in self.snaps[0].workloads:
            if w.id == jid:
                return {"metadata": {"id": w.id, "name": w.name}}
        raise RuntimeError("not found")

    def cancel(self, jid):
        self.cancelled.append(jid)
        return 0, "ok"

    def create(self, name, timeout, args):
        self.created.append((name, timeout, args))
        return f"aijob-new{len(self.created)}"


def isolate(tmp_path, monkeypatch, manifest_obj, queue_obj):
    monkeypatch.setattr(C, "MANIFEST", tmp_path / "m.json")
    monkeypatch.setattr(C, "QUEUE", tmp_path / "q.json")
    monkeypatch.setattr(C, "QLOG", tmp_path / "log.jsonl")
    C.save_json(C.MANIFEST, manifest_obj)
    C.save_json(C.QUEUE, queue_obj)


def test_cycle_cancels_only_verified_owned_ids_and_logs(tmp_path, monkeypatch):
    m = manifest(owned=[("aijob-a", 1), ("aijob-b", 2)])
    isolate(tmp_path, monkeypatch, m, [])
    s = snap(wl("aijob-peer1", "kganjam-delphi-trpb-x", "RUNNING"), wl("aijob-a", "delphi-evolve-scale-aijob-a", "RUNNING"),
             wl("aijob-b", "delphi-evolve-scale-aijob-b", "RUNNING"), wl("aijob-o1", "teamB", "RUNNING", gpus=12),
             wl("aijob-w", "teamD", "PENDING"))
    cloud = FakeCloud([s])
    C.cycle(cloud, m, [], CFG, 0, do_launch=True)
    assert cloud.cancelled == ["aijob-b"] and not cloud.created
    entry = json.loads(Path(C.QLOG).read_text().splitlines()[-1])
    assert entry["counts"]["waiting_other_ids"] == ["aijob-w"] and entry["released"][0]["released"]
    # dry run never cancels
    cloud2 = FakeCloud([s])
    C.cycle(cloud2, m, [], CFG, 0, do_launch=True, dry_run=True)
    assert cloud2.cancelled == []


def test_cycle_launches_queue_by_priority_with_intent_recorded(tmp_path, monkeypatch):
    m = manifest()
    q = [{"seq": 1, "priority": 3, "model_key": "te15b", "units": "0-1", "status": "queued"},
         {"seq": 2, "priority": 1, "model_key": "te3b", "units": "0-3", "status": "queued"}]
    isolate(tmp_path, monkeypatch, m, q)
    cloud = FakeCloud([snap(wl("aijob-peer1", "kganjam-delphi-trpb-x", "RUNNING"))])
    C.cycle(cloud, m, q, CFG, 0, do_launch=True)
    assert len(cloud.created) == 1 and cloud.created[0][0].startswith("delphi-evolve-scale-te3b-")
    saved = C.load_json(C.MANIFEST, {})
    assert saved["owned"][0]["id"] == "aijob-new1" and saved["owned"][0]["intent_at"]


def test_reconcile_adopts_intent_by_unique_name_only():
    m = {"owned": [{"id": None, "name": "delphi-evolve-scale-te3b-u0-120000"}, {"id": None, "name": "delphi-evolve-scale-never"}]}
    s = snap(wl("aijob-z", "delphi-evolve-scale-te3b-u0-120000", "RUNNING"), wl("aijob-q", "someone-elses", "RUNNING"))
    C.reconcile(m, s)
    assert m["owned"][0]["id"] == "aijob-z" and m["owned"][1]["id"] is None


def test_monitor_polls_at_most_every_60s_and_exits_when_idle(tmp_path, monkeypatch):
    m = manifest(owned=[("aijob-a", 1)])
    isolate(tmp_path, monkeypatch, m, [])
    run = snap(wl("aijob-peer1", "kganjam-delphi-trpb-x", "RUNNING"), wl("aijob-a", "delphi-evolve-scale-aijob-a", "RUNNING"))
    done = snap(wl("aijob-peer1", "kganjam-delphi-trpb-x", "RUNNING"), wl("aijob-a", "delphi-evolve-scale-aijob-a", "COMPLETED"))
    cloud = FakeCloud([run, run, done])
    sleeps, t = [], [0.0]
    def sleep(s):
        sleeps.append(s)
        t[0] += s
    rc = C.monitor(cloud, 60, 30, False, False, CFG, sleep=sleep, clock=lambda: t[0])
    assert rc == 0 and sleeps == [60, 60] and max(sleeps) <= 60
    assert len(Path(C.QLOG).read_text().splitlines()) == 3


def test_blind_drain_releases_lowest_priority_owned_by_id_down_to_floor(tmp_path, monkeypatch):
    m = manifest(owned=[("aijob-a", 1), ("aijob-b", 2), ("aijob-c", 3)])
    for j in m["owned"]:
        j["created_at"] = "x"
    isolate(tmp_path, monkeypatch, m, [])
    good = snap(wl("aijob-a", "delphi-evolve-scale-aijob-a", "RUNNING"), wl("aijob-b", "delphi-evolve-scale-aijob-b", "RUNNING"),
                wl("aijob-c", "delphi-evolve-scale-aijob-c", "RUNNING"))

    class Blind(FakeCloud):
        def snapshot(self):
            return snap(ok=False)

        def get(self, jid):                      # per-ID get still works while the listing does not
            return {"metadata": {"id": jid, "name": f"delphi-evolve-scale-{jid}"}}
    cloud = Blind([good])
    C.cycle(cloud, m, [], CFG, CFG.blind_poll_limit - 1, do_launch=True)
    # floor 2 minus 1 peer => keep 1 owned (the highest priority); cancel the other two, lowest priority first
    assert cloud.cancelled == ["aijob-c", "aijob-b"] and not cloud.created
