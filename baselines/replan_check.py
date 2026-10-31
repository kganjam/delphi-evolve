"""Informational check: forcing a full re-search at every LazySP iteration vs keeping a still-valid incumbent path (run from repo root: python -m baselines.replan_check is NOT supported; use python baselines/replan_check.py)."""
import sys, gzip, json
sys.path.insert(0, '.')
from baselines.lazysp import run as lrun
from baselines.lazysp.policy import LazySP
from evolve import data
land = data.load()
class Always(LazySP):
    def _path_valid(self, ledger): return False
orig = lrun.LazySP
res = []
for sel in ("forward", "alternate", "reverse"):
    for k in (0, 2, 3):
        a, qa = lrun.run_task(land, sel, 0, k, None, 1000)
        lrun.LazySP = Always
        b, qb = lrun.run_task(land, sel, 0, k, None, 1000)
        lrun.LazySP = orig
        same_nodes = [x[2] for x in qa] == [x[2] for x in qb]
        print(sel, k, a["status"], a["assays"], b["assays"], "identical query sequence:", same_nodes, "replans", a["lazysp"]["replans"], b["lazysp"]["replans"], flush=True)
