# Conflicts between this schema and the Frontier store models (finding, not a fix)

Recorded 2026-10-31, Seattle PDT. Machine-readable copy: `store_conflicts.json` (same directory).

* Store: `kganjam/delphi-frontier`, branch `work/frontier-foundation`, commit `1d014d1`, `frontier/models.py`
  (file sha256 as I read it: `54c95cccd195cae84ebee78b589113d0a35f01967492bb894f2c21370bc8fd63`). The store models forbid extra
  fields and use `Literal` types, so a record that does not match is rejected on write. The host reports its Postgres test
  script passed (12 tests); I did not re-run it.
* This schema: `frontier_attention/schema.py` on `work/market` in `kganjam/delphi-evolve`.

**Ruling (host, integration owner): the validators are not changed to match the store.** These stand as findings.

| | Store | This schema | Consequence |
|---|---|---|---|
| agree | `evidence_kind` 5 values; `signal` 4 values; blocking needs a downstream link | identical | none |
| C1 | `problem_kind`: 4 values | `open_kind`: 10 values (7 seed kinds verbatim + 3) | five seed kinds have no exact store value; the mapping is a judgement for the store owner |
| C2 | `verification_status`: unverified / declared / checked (+ reference) | unverified / availability_checked | no counterpart for `declared`; `checked` demands a reference |
| C3 | `next_action` free text; `downstream_uses` free strings; `Action.cost_stop_bounds` free text | typed unlock edges, pinned input hashes, estimate, stop rule, reviewer | the store cannot hold a typed unlock edge, a decision reference, a checkable stop rule, an estimate or a reviewer. **0 of 7 seeds bounded is therefore a property of the store schema as well as of the seed prose.** |

Correction to the first summary of C3: the store does have `downstream_uses` (untyped strings) and a separate, partly
structured `Action` record. What is missing is typing and machine-checkable bounds, not the existence of any such field.

Also different, no decision yet: `Interest.downstream_reference` is a string (schema: versioned reference);
`ResourceOffer.restrictions` must be non-empty (schema: may be empty); store has `capability`, no `resource_type`; store has no
lease record (only lease events); the store has no record kind for prediction specs, forecasts, resolutions, attention credits
or contribution credit — these have no home there yet.

What would resolve it is a person's decision, not a code change here: either the store adds typed fields (or an Action
profile) so a bounded action and a typed unlock can be written, or this schema narrows to what the store can hold and the
ranking stays impossible until it can.
