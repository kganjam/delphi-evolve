"""Real release data and publication-blocking corruptions of the scale follow-up."""
import gzip
import json
import shutil
from pathlib import Path

import pytest

from evolve.release_evidence import scale_block

ROOT = Path(__file__).resolve().parents[1]


def copied(tmp_path):
    shutil.copytree(ROOT / "artifacts/scale", tmp_path / "artifacts/scale")
    dest = tmp_path / "artifacts/core/replay"
    dest.mkdir(parents=True)
    shutil.copyfile(ROOT / "artifacts/core/replay/episodes.csv", dest / "episodes.csv")
    return tmp_path


def test_real_followup_complete_and_no_clear_rmst_uplift():
    result = scale_block(ROOT)
    assert result["status"] == "completed" and result["episodes"] == 1100
    assert result["all_rmst_intervals_include_zero"]


@pytest.mark.parametrize("fault", ["missing", "duplicate", "different_target"])
def test_incomplete_or_changed_panel_cannot_publish(tmp_path, fault):
    root = copied(tmp_path)
    path = root / "artifacts/scale/replay_rows.jsonl.gz"
    with gzip.open(path, "rt") as handle:
        rows = [json.loads(line) for line in handle]
    if fault == "missing":
        rows.pop()
    elif fault == "duplicate":
        rows[0] = rows[1].copy()
    else:
        rows[0]["target"] = "AAAA"
    with gzip.open(path, "wt") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")
    with pytest.raises(ValueError, match="episodes"):
        scale_block(root)


def test_modified_prior_rejected(tmp_path):
    root = copied(tmp_path)
    path = root / "artifacts/scale/priors_z.npz"
    path.write_bytes(path.read_bytes() + b"unexpected")
    with pytest.raises(ValueError, match="prior bytes"):
        scale_block(root)
