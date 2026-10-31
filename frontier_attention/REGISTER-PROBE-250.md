# Attention cards and lenses over the 250 imported open problems

2026-10-31, Seattle PDT. Single-reader, not Codex-reviewed, not independently reviewed. Machine output: `register_probe_250.json`.

**Answer to the question asked.** Every lens degenerates. All five (`newly_actionable`, `blocking_downstream`, `seeking_review`,
`neglected_important`, `exploratory`) contain **0 of 250** problems, and no ordering of any kind comes out of the cards. This is not
a bug to patch: each lens predicate needs a field that no record has (a bounded next action, a lease, a decision model, a
blocker signal). Populating a lens from the 250 would require inventing one of those, so it stays empty. Cards: 0 bounded, 0 ready,
0 with a consequence estimate (issue codes: missing 1314, bad_enum 500, bad_estimate 250, unpinned 250, bad_ref 83, untyped_edge 83).

## Reproduction (read-only on the register; nothing was written to any other repo)

```
# 1. importer from kganjam/delphi-frontier 42cd967a97becefbb1ce67f43ce4be953ce1ec09 (read before running)
python3 -I scripts/import_register.py /home/ubuntu/git/morphoswarm/data/problems/register.yaml --out drafts250.jsonl
#    register sha256 a0155552a2bcda40688d38e95c4069828922d21042c87c9c6cf96311de94f7d7 -> 250 importable, 0 rejected, 0 actionable
#    provenance (importer's fields) 34 / 68 / 148, as the host reported; drafts250.jsonl sha256 5808c2bd34a20a4838bb8415bdcb483f3f7aee5d6bd3a02d4a1a34515633f6f7
# 2. python -m frontier_attention register-probe --drafts drafts250.jsonl --now 2026-10-31T17:00:00Z --out register_probe_250.json
```
Both ran under `systemd-run --user --scope` caps, exit 0. The importer's enum `sourced_field_open_problem` is mapped here to
`field_open_problem` (inferred, labelled).

## What the records do carry, and how far it orders

| Key carried by the records | Coverage | How much does it order? |
|---|---|---|
| `importance` (foundational 20 / significant 141 / specialist 52) | 213 of 250 | orders **36%** of all pairs (11,192 of 31,125); 11,386 pairs tied; 8,547 pairs involve an unrated record |
| `tractability` (near-term 127 / medium 78 / long 8) | 213 of 250 | orders 37% of pairs |
| both, as a Pareto partial order (higher is better on each; no weights) | 213 | 54% of rated pairs comparable; layers of sizes **4, 96, 97, 15, 1** |

The 37 unrated records are exactly the 37 carrying a `domain` tag (ecology, neuroscience, evolutionary dynamics, ...): a second
cohort the labels do not cover at all. The Pareto layering is the only weight-free ordering the labels support, and it separates
the top 4 and the bottom 1 and leaves **96 and 97 problems indistinguishable** in the middle. These are one curator's ordinal
labels with a rationale string each, no calibration and no consequence estimate. They order the labels, not the value of answering.
I would not present them as a priority ranking.

## Corrections to the provenance numbers (please re-derive before any slide uses 34 / 68 / 148)

The importer reads `why_source` and `references` and **ignores `attestations`**. All 250 records carry `attestations`
(465 in total, each with a `stance` of open or settled): **247 of 250 have at least one with pmcid, locator and quote**, including
**145 of the 148** the importer reports as "no source at all". So 148 is a property of which field the importer reads, not of the
records. Caveats that stay: the quotes are the curator's transcriptions and nobody in this chain has checked them against the
papers; 134 of 250 rest on exactly one distinct source; 465 attestations cite only 331 distinct PMCIDs and one PMCID underlies up
to 5 problems, so counts of sources are not counts of independent evidence.

Also relevant to "what remains open": **37 problems have at least one attestation with stance `settled`** (none has all settled),
so some facet of those questions is treated as settled by a cited source. The importer drops `stance` from the draft body (it
survives only inside `original.register_record`). And the importer's own docstring says an unsourced problem "must not be
presented as" a sourced field-level problem, yet it sets `problem_kind = sourced_field_open_problem` for all 250.

## Structure that exists but is untyped

89 pairs where one record's prose names another record's slug, touching 63 problems (maximum in-degree 3). A slug in prose is
not a dependency; these are untyped candidates (`proposed_connection` at best) that never enter a headline number. No two
statements overlap by token Jaccard >= 0.5 (crude check, 0 pairs). 12 distinct `modules` values appear (1 or 2 on 71 records, none
on 179): these name MorphoSwarm's own modules, a project-internal downstream use, not a decision with a payoff.

## The ordering mechanism that would be needed (not built; none of the inputs exist)

1. **To rank ACTIONS**: for each problem, a typed unlock edge to a named decision, and for that decision a declared model
   (states, actions, utilities, prior, each with a source). That gives EVPI per `voi.py`. Today: 0 of 250. Plus a bounded action
   (type, pinned inputs, estimate, stop rule, reviewer), which the store only now allows once `completeness=actionable`.
2. **To order QUESTIONS without inventing utilities**: a structural, count-based partial order over a typed dependency DAG: the
   number of distinct downstream problems whose acceptance criterion depends on this one, with descendants deduplicated by
   `independent_group`. It outputs ranks and ties, never a score. It needs the 89 candidate edges confirmed or rejected and typed
   (89 human judgements, not 250 decision models). I have not implemented this lens because there is no typed edge to run it on.
3. **To say whether any ordering is good**: resolution records. A priority list is a forecast about which questions will become
   bounded, accepted work; `forecasting.py` and `evaluate.py` can score that, but only after predictions with a resolver and
   horizon are written before anyone acts, and `evaluate.py` refuses a verdict under 6 problems with frozen values. Today:
   none exist.
4. **Before any of that**: curate the cohort-wide gaps the numbers show (37 unrated; 37 with a settled facet needing scope; the
   attestation field read into provenance; a source check of the quotes).

## Not claimed

No lens ordering exists to defend. No claim about the scientific importance of any of the 250 problems. The importance and
tractability labels are reported, not endorsed. Quotes and PMCIDs were not checked against the papers.
