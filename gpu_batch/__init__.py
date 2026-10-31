"""Queue-aware sharded Nebius GPU expansion for query-to-certify TrpB evidence.

Owns: job manifest (our IDs only), shared-pool snapshot parsing, launch/yield policy,
shard runner (job side), assembly/ablation (CPU side).  Does not reimplement ESM2 scoring:
the job-side runner imports the gpu worker's embed_trpb.py (pinned by commit) for model
loading, masking and scoring.
"""
OWN_PREFIX = "delphi-evolve-scale-"
