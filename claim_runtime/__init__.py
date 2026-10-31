"""claim_runtime: a small executable claim-reuse service.

Scope (deliberately narrow): hand-authored adapters for two existing Delphi
population-genetics claims (kimura-fixation-probability, fisher-ftns) and a typed
evidence-claim store for observed TrpB assay results. Not a generic framework:
only the claims listed in ADAPTERS are executable; everything else is refused.
Standard library only (numpy/rdflib are optional, used by tests and validation).
"""
__version__ = "0.1.0"
