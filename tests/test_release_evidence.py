import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from evolve.release_evidence import claim_block, compute_block, lazysp_block

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def recorded_gpu(tmp_path):
    (tmp_path / "artifacts/gpu").mkdir(parents=True)
    (tmp_path / "tasks/results").mkdir(parents=True)
    raw = b"prediction artifact"
    (tmp_path / "prediction.bin").write_bytes(raw)
    block = {"status": "completed", "provider": "test", "model": "test-model",
             "job_id": "job-real", "evidence_kind": "predicted",
             "artifacts": [{"path": "prediction.bin", "bytes": len(raw),
                            "sha256": hashlib.sha256(raw).hexdigest()}]}
    receipt = {"status": "completed", "nebius_jobs": [
        {"id": "job-real", "state": "COMPLETED", "exit": 0},
        {"id": "job-failed", "state": "FAILED", "exit": 1}]}
    (tmp_path / "artifacts/gpu/compute_block.json").write_text(json.dumps(block))
    (tmp_path / "tasks/results/gpu.json").write_text(json.dumps(receipt))
    return tmp_path, block


def test_gpu_artifact_replacement_invalidates_completed_receipt(recorded_gpu):
    root, _ = recorded_gpu
    assert compute_block(root)["job_id"] == "job-real"
    (root / "prediction.bin").write_bytes(b"replacement artifact")
    with pytest.raises(ValueError, match="content does not match"):
        compute_block(root)


@pytest.mark.parametrize("field,value", [("job_id", "job-failed"), ("job_id", "invented"),
                                        ("evidence_kind", "observed")])
def test_failed_job_and_measurement_mislabel_cannot_be_published(recorded_gpu, field, value):
    root, block = recorded_gpu
    block[field] = value
    (root / "artifacts/gpu/compute_block.json").write_text(json.dumps(block))
    with pytest.raises(ValueError):
        compute_block(root)


def test_actual_release_receipts_bind_artifacts():
    assert compute_block(ROOT)["variants"] == 160000
    claims = claim_block(ROOT)
    assert {s["decision"] for s in claims["scenarios"]} >= {"compute", "refuse"}
    assert lazysp_block(ROOT)["primary"]["certified"] == 96


def test_incomplete_lazysp_panel_cannot_be_published(tmp_path):
    import shutil
    base = tmp_path / "artifacts/lazysp/results"
    base.mkdir(parents=True)
    for name in ("episodes.csv", "summary.json", "audit.json"):
        shutil.copyfile(ROOT / "artifacts/lazysp/results" / name, base / name)
    assert lazysp_block(tmp_path)["status"] == "completed"
    lines = (base / "episodes.csv").read_text().splitlines()
    (base / "episodes.csv").write_text("\n".join(lines[:-1]) + "\n")
    with pytest.raises(ValueError, match="all 300"):
        lazysp_block(tmp_path)


@pytest.mark.parametrize("mutation", ["failed-kernel", "surviving-mutant", "missing-receipt", "late-fake-observation"])
def test_completed_demo_cannot_hide_failed_proof_or_unchecked_nodes(tmp_path, mutation):
    spec = importlib.util.spec_from_file_location("check_demo", ROOT / "scripts/check_demo.py")
    check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(check)
    demo = json.loads((ROOT / "artifacts/demo.json").read_text())
    path = tmp_path / "demo.json"
    path.write_text(json.dumps(demo))
    assert check.main(str(path)) == 0
    assert demo["proof"]["status"] == "completed"
    if mutation == "failed-kernel":
        demo["proof"]["exit_code"] = 1
    elif mutation == "surviving-mutant":
        demo["proof"]["mutation_exit_code"] = 0
    elif mutation == "missing-receipt":
        demo["proof"]["receipt"] = None
    else:
        demo["nodes"] += [dict(demo["nodes"][0], id=f"extra-{i}") for i in range(5001)]
        demo["nodes"][-1]["evidence_kind"] = "predicted"
        demo["nodes"][-1]["observed_score"] = 1
    path.write_text(json.dumps(demo))
    assert check.main(str(path)) == 1
