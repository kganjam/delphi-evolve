"""Publication layer for the Delphi Frontier store: accepted Frontier assessments -> nanopublication DRAFTS.

PREPARE / SIGN LOCALLY / (test registry only, behind an explicit authorization record). There is NO production publish path in
this package. Nothing here is a Frontier writer: it reads records and never calls a Frontier write operation.
Design and status: docs/frontier-publication-layer.md.
"""
PROFILE_VERSION = "frontier-review-publication v0"
