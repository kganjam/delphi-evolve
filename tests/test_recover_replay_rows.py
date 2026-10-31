"""Tampered query histories must fail recovery (small synthetic fixtures only)."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

spec = spec_from_file_location('recovery', Path(__file__).parents[1] / 'scripts/recover_replay_rows.py')
recovery = module_from_spec(spec)
spec.loader.exec_module(recovery)


@pytest.fixture
def example():
    d = recovery.data
    start, target, query = map(d.encode, ['AAAA', 'CCCC', 'AAAC'])
    score = np.zeros(d.N_GENO, dtype=np.int64)
    measured = np.zeros(d.N_GENO, dtype=bool)
    score[[start, target, query]] = [5, 100, 1]
    measured[[start, target, query]] = True
    land = SimpleNamespace(s=score, measured=measured, intervals=lambda: (score, score))
    ep = {'start': start, 'target': target, 'init': [], 'family': 'test', 'seed': 0}
    row = [1, 'test-policy', query, [1, 1, 1], 'fixture query']
    return land, ep, row


def test_fabricated_observation_is_rejected(example):
    land, ep, row = example
    row[3] = [999, 999, 999]
    with pytest.raises(ValueError, match='source observation mismatch'):
        recovery.restore(land, ep, 'fixture', [row], 100)


def test_duplicated_assay_is_rejected(example):
    land, ep, row = example
    duplicate = list(row)
    duplicate[0] = 2
    with pytest.raises(ValueError, match='duplicate query'):
        recovery.restore(land, ep, 'fixture', [row, duplicate], 100)


def test_missing_query_number_is_rejected(example):
    land, ep, row = example
    row[0] = 2
    with pytest.raises(ValueError, match='broken counter'):
        recovery.restore(land, ep, 'fixture', [row], 100)
