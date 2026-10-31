"""Generic Nebius batch controller: ship Python to GPU/CPU jobs, fan out, bound, collect results.

Written by the gpuops role. Independent of the TrpB-specific gpu_batch/ package; shares no state with it
except that jobs named with gpu_batch's prefix are counted (never cancelled) toward our GPU cap.
"""
OWN_PREFIX = "delphi-evolve-ops-"
COUNT_PREFIXES = ("delphi-evolve-", "kganjam-")     # counted against our cap; only OWN ids in our manifest are ever cancelled
