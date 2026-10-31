# Minimal scientific and interface contract

## Scope and stable artifacts

The only scientific system required is the four-site TrpB assay. Canonical source files currently exist at /data/artifacts/v2-scout/data/caltech/{simplified_AA,summary_AA,KNN_imputed_TrpB}.csv. They are primary CaltechDATA archive members. Copy them into ignored data/raw/ only as a cache; implement a reproducible source fetch and checksums. Never train/evaluate on the KNN labels as observations. Raw growth columns avoid max-normalization leakage.

Python package: evolve/. Core CLI: python -m evolve demo --output artifacts/demo.json, with documented additional commands. Demo JSON is the integration boundary. Site fetches ./data/demo.json and presents unavailable fields as unknown. Workers may implement richer APIs, but preserve this boundary.

Minimal demo JSON fields:

```
schema_version, generated_at, source {url, doi, sha256, license, assay, counts},
nodes [{id, genotype, observed_score, replicate_1, replicate_2, lower, upper, evidence_kind}],
edges [{source, target, status}],
routes [{id, nodes, status, assumptions, certificate_path}],
claims [{id, source_uri, statement, relation_to_test, status}],
benchmark {status, protocol, metrics, limitations},
proof {status, theorem, command, exit_code, mutation_exit_code, receipt},
compute {status, provider, model, job_id, artifacts},
limitations []
```

null is unknown, not zero. Empty results are not passes. Display source measurements as such; model outputs as predictions. Node layout is a projection, not physical geometry.

## Query-to-certify

Fix start/target pairs and graph scope before evaluation. Full finite graph consists of four-letter amino-acid genotypes, single-substitution adjacency. Missing labels leave edges possible. Restricting to measured or sampled nodes is permitted only with an explicit restricted-graph claim. A proof of no route in that graph is never a proof of no evolutionary route in biology.

An oracle exposes the same initial observations and bounded additional measurements to each policy. Record immutable query/reveal/proposal/challenge/decision events. Policy inputs contain no unseen labels. Use matched budgets/seeds and retain unresolved cases. Include a competent single-policy baseline, not only random. Centralized software orchestration and decentralized decision-making are different; explain actual boundaries.

Primary report: assays-to-correct-certificate, false certificates, abstentions, domain coverage. Best-score optimization is secondary. At least 20 fixed seeds if cheap enough, with paired uncertainty and an explicit reason if fewer. No significant-improvement claim without supporting analysis.

Two assay replicates do not supply rigorous simultaneous confidence bands. Use empirical sensitivity bounds explicitly assumed, or point-observation statements. Validate decisions against held-out replicate data; account for adaptive selection and multiple edges before claiming probability coverage. A GPU prior may guide measurement but never discharge a missing empirical premise.

## Lean

Generic interval path-soundness theorem and closed-set/cut no-path theorem; executable finite checker tied to theorem, not a parallel unproved Python checker. A certificate contains dataset hash, graph scope, exact rational or outward-rounded integer intervals, route/cut, assumptions and software versions. Kernel compile original, inspect axiom dependencies, reject meaningful mutant, and record correspondence. No sorry, admit, trusted native_decide shortcut, or proof by an unrelated constant identity. Invalidating the dominance inequality or opening a cut edge must change acceptance. No false certificates through rounding, missing vertices or NaN.

## Claims and nanopubs

Preserve Delphi IDs and source local/network. An operational enzyme hypothesis is not synonymous with a broad Darwin claim. Link as motivation unless justified. Distinguish observed finding, simulated selection replay, mathematical theorem, interpretation and proposal. Emit valid RDF nanopub named graphs with source/author provenance, mark unsigned drafts. Never invent a public trusty URI, verified network publication or an identified scientist's endorsement.

## Acceptance

Fresh checkout can acquire/cache exact data, produce demo JSON, reproduce its summary, run targeted tests, compile proofs and reject mutants. Site works from static files and reports absent integrations honestly. All advertised scientific numbers are derived from saved artifacts. Each integration reports real run identifier/exit or an explicit blocker. Every worker owns its tests and run receipts. Coordinator reviews all receipts before pitch claims.
