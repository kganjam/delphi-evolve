"""Delphi Evolve core: measured TrpB graph, query-to-certify replay, demo JSON."""
import os

# AGENTS.md: CPU threads <= 2.  Pin BLAS pools before numpy is imported anywhere.
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

__version__ = "0.1.0"
