# SPEC-079 — The compounding demonstration: what the hackathon shows, and how each claim in it is measured

**Status:** Draft · **Version:** 0.1.3 · **Owner:** G8 · 2026-10-26 (0.1.3, 2026-10-27: rule 3a, before and during labelled and every stop re-runnable, from research task 45c0a983's proposal 12; 0.1.1, 2026-10-27, director ruling: the compounding pre-registration is the ablation harness's markdown format plus profile fields; the openness record gains the refusal fields; a `still-open` verdict is a SPEC-076 rule 7 null; open questions 1 and 2 ruled; 0.1.2, 2026-10-27, second director ruling: the comparison is registered by the harness's own anchored pre-registration and not through SPEC-020, the 0.5σ cutoff for descriptive analysis is a registered parameter, time to the first supported result is a registered secondary metric, and the Halloween designs record the SPEC-063 screen as unavailable)

## Scope

The ScienceClaw demonstration (Oct 30 – Nov 1 2026) as a set of checked stops, and the
measurements that make each of its sentences true:

- **The stops.** Each is a served page whose numbers come from records, each has a `demo_all`
  check, and none is narrated past a check that does not pass.
- **Openness re-checks.** A problem called open in the pitch has been searched for a resolution,
  recently and on the record.
- **Reproductions of known findings.** These are scored hit or miss against a published value
  that was registered before the attack ran. They show the machinery gets known answers right.
- **The autoformalization funnel.** Every draft from prose or paper to formal statement, counted
  at every stage, failures included, with one paper worked end to end.
- **The compounding comparison.** A pre-registered measurement of whether agents that search the
  claim graph first do better than agents that do not.
- **The scorecard.** What works and what does not, computed from records.
- **Nanopublications** as the network form of claims, in a shape a nanopublication expert would
  accept, published only on the owner's ADR-0005 decision.
- **Halloween design exercises**, labelled as exercises.
- **The deck**, generated from live numbers, and **the event campaign**, the switch that turns
  the platform on.

Not in scope, and owned elsewhere: the register (SPEC-074), attacks and the substrate (SPEC-076),
claim search and the evidence bundle (SPEC-077), problem belief graphs (SPEC-078), the ladder and
autoformalization (SPEC-009, SPEC-041), nanopublication building and conformance (SPEC-007,
SPEC-031), txt2organism (SPEC-005), MorphoBench and its A/B/C/D ablation (SPEC-006, SPEC-025).
This spec composes them and adds the measurements none of them owns.

## Motivation

The owner, 2026-10-26: *"we also need to show core ability to solve real important open problems
in the field. if we need more open problems we should gather more. we should check that they are
still open. or at least we should reproduce known findings. a bit of both might be good. we
should also in the demo pitch and final writeup of the system be able to quantify what works and
what doesnt work in these types of systems. we also need to enumerate what is novel, how we
differentiate."* And: *"we want to show how the solver for a specific bio task added claims, found
existing claims, and that this accelerates research and compounds knowledge. similar to prove2me
but for bio."* And, for spice: *"a couple fun 'design an organism' project demos that are related
to halloween since the hackathon is over that weekend."*

**Where the demonstration stands.** The figures are from the r53 build `b816f2ee5`. They were
measured by the session that wrote the presenter card from the served bundle on 2026-10-26 at
15:50 PDT, and they were not re-measured here.

- 309 register entries, 250 of them called open by the field in its own words.
- 12 attacked problems: 7 `partial`, 5 `attacked`, **0 candidate solutions**. The best level is
  L2 (Rule 30).
- **5 cross-attack uses and 3 statement edges over 258 steps.**

The last line is the gap. "Knowledge compounds" is the claim the rubric pays for most:
*Collective Capability* is 25% and *Decentralized Agency* 20% (`docs/hackathon-strategy.md`,
re-read 2026-10-22). Five reuses cannot carry that claim. A measurement can, whichever way it
comes out.

**Why openness is checked and not assumed.** The research for this spec
([`docs/research/ai-science-landscape-2026.md`](../docs/research/ai-science-landscape-2026.md))
records the public failures of 2025–2026 in which "solved open problems" turned out to be
solutions already in the literature. A register entry attested open in 2019 by a review can be
closed by 2026. A sentence that calls a problem open in front of judges needs a dated search
behind it.

**Why reproductions.** A candidate solution to an open problem cannot be checked against an answer
key, because none exists. A reproduction can. Scoring the same machinery on findings with
published values separates "the pipeline is right" from "the pipeline produced something". The
owner asked for "a bit of both", and this is the half with an answer key.

## Concepts

- **Stop.** One step of the demonstration: a route, a sentence the presenter says, and the
  `demo_all` check that must pass for the sentence to be said.
- **Openness check.** A dated, recorded search for a resolution of one problem since its
  attestation date, with a verdict.
- **Reproduction target.** A quantitative finding from a paper read at full text: a quantity,
  its value and uncertainty, the conditions, and the locator. It is registered before the attack
  that tries to reproduce it starts.
- **Funnel.** The count of formalization drafts reaching each stage, by mode.
- **Arm.** One condition of the compounding comparison: `substrate` (the claim graph and its
  search are available) or `blind` (they are not).

## Schema

```yaml
# appended to a register entry's record: data/problems/openness/<slug>.yaml
checks:
  - outcome: ran | refused       # a refused attempt is recorded, never dropped; only a `ran` check starts the clock
    checked_at: 2026-10-28T10:00:00-07:00
    since: 2019-06-01            # the attestation's date
    sources: [openalex, pubmed, paperclip]         # the sources that answered
    sources_skipped: {paperclip: not-configured}   # a source that did not answer, with the reason
    queries: ["..."]             # verbatim
    hits_reviewed: [{doi, read_level, verdict: irrelevant | partial-progress | claims-resolution}]
    unread: [{doi, reason}]      # found, but not read at abstract level or deeper; never judged
    unjudgeable: [{url, title, read_level, reason}]   # a read with no DOI or PMID; never judged, never given an id
    leads: [...]                 # hits a model pass returned (origin: lead); a lead is not a read
    verdict: still-open | possibly-resolved | resolved   # absent when the outcome is refused
    verdict_limit: "N read(s) had no DOI or PMID ..."    # present only when unjudgeable is non-empty
    refusal: {reason, detail}    # present only when the outcome is refused
    reviewer: {agent | person}
    store: deployment | in-memory
```

The fields `outcome`, `refusal`, `sources_skipped`, `unread`, `leads` and `store` were added in 0.1.1.
They are the ones M2462's brief
([`tasks/briefs/M2462-openness-check-operation.md`](../tasks/briefs/M2462-openness-check-operation.md),
*What to build* 1 to 5 and 7) found a refused check cannot be recorded without, and their meanings
are that brief's:

- `outcome` is `ran` or `refused`. A check that could not run is recorded as `refused`, with
  `refusal: {reason, detail}` and **no `verdict` key**. It is never recorded as `still-open`, and it
  does not move the 14-day clock: only a `ran` check starts the clock. The `reason` is one of
  `read-nothing` (no hit was read at abstract level or deeper: every source failed, all answered
  with no hit, only listing-level hits were found, or only leads), `fewer-than-two-sources-answered`,
  and `no-replayable-read` (a replay whose only reads are not-replayable has no passage to hand the
  re-check).
- `sources_skipped` maps a source name to the reason it did not answer. A source that is
  `not-configured` is a gap listed here, never zero hits.
- `unread` lists each hit that was found and not read at abstract level or deeper, with the reason.
  A hit counts as read at abstract level only when a source in that run supplied its abstract;
  anything else is listing level and is never judged.

**Amendment, 2026-10-27 (M2462 repair, task 2991f10e; director ruling morphoswarm-82, option ii).**
Two additions, and one reason that the code already emitted but this spec did not list.

- **`unjudgeable: [{url, title, read_level, reason}]`** holds every read that has neither a DOI nor a
  PMID. Such a read cannot be keyed, so no judgement can name it. It is kept, with its URL (when the
  source supplied one) and title, under `reason: unidentifiable-read`. It is **never given a
  pseudo-identifier**: a sha256 of URL and title does not go in a `doi` or `pmid` slot, for the same
  reason `urn:sha256:` subjects are refused. A check with unjudgeable reads may reach `ran`, but
  `verdict_limit` states how many were unjudgeable and that they are not counted in `hits_reviewed`,
  so the verdict does not read as if they were judged. A check whose reads are *all* identifier-less
  is refused with `unidentifiable-read`, because a verdict would rest on no judgement at all.
- **Conservation.** In `assemble_check` every read lands in exactly one list: judged
  (`hits_reviewed`), `unjudgeable`, or `unread`. Each `unread` row carries its `doi` or `pmid`. A
  read at abstract level that has an identifier but no hash-matching judgement is written to `unread`
  with `reason: read at abstract level but not judged: missing-judgement`. That is the one case in
  which `unread` holds a read rather than a listing, and it is what the refusal `missing-judgement`
  describes.
- **Refusal reasons, the full list as the code emits it.** `read-nothing`,
  `fewer-than-two-sources-answered`, `no-replayable-read`, `unidentifiable-read` (new), and
  `missing-judgement` (emitted by `decide_verdict` and `_apply_judgements` for a keyed read with no
  judgement; it was in the code and absent here until this amendment).
- `leads` holds the hits a model pass returned (SPEC-077 `origin: lead`). A lead says where to look
  and is not a read: it enters `hits_reviewed` only if the same DOI arrived with an abstract from
  another source (SPEC-077 rule 14).
- `store` is `deployment` or `in-memory`. A check run without a deployment store loads the register
  into a throwaway store and records `in-memory`, because a `last_checked` moved in a throwaway store
  has moved nowhere.

**Amendment, 2026-10-27 (M2462 repair, task 8de9d1e4; one paper is one hit).** Before this, a read
was keyed on its DOI exactly as written, so one eLife paper published as versions and
sub-articles was several hits: segmentation-clock's six eLife 93764 variants counted as six
`claims-resolution` hits. The schema above is amended as follows; nothing was edited silently.

- **Canonical key.** An eLife DOI `10.7554/elife.<n>`, with an optional version `.<v>` and an
  optional sub-article `.sa<k>`, keys a read on `doi:10.7554/elife.<n>`. Every other DOI keys as
  written. No general rule strips trailing digits: `10.1371/journal.pgen.1009812` keeps them, because
  they are its identifier. The `.saN` reading was checked against the titles recorded for these DOIs
  in the recordings, not against a fetch of the DOIs: `.1.sa0` is "Reviewer #2 (Public Review)"
  (93764), `.2.sa1` is "Reviewer #1 (Public Review)" (93764), `.2.sa3` is "eLife Assessment" (86670),
  and `.2.sa0` is "Author Response" (96980).
- **`hits_reviewed` is per paper.** A paper's row carries `doi` (the canonical DOI) and
  `aliases: [doi, …]`, every other DOI the sources wrote for that paper, as written. A spelling that
  differs from the canonical DOI only in case (`10.7554/eLife.22013` for `10.7554/elife.22013`) is the
  same identifier and is not repeated as an alias; its spelling stays in the recording.
- **Conflicting variants are kept, not reconciled.** When the variants of one paper carry different
  verdicts, the row is marked `conflicting: true` and carries `variant_verdicts: {doi: verdict}` with
  every judged variant. The row's `verdict` is the strongest of them (`claims-resolution`, then
  `partial-progress`, then `irrelevant`); it is a summary, and the map is the record. The row carries
  one `abstract_sha256`: the paper's own DOI's when that DOI was read, otherwise the first variant read.
- **Conservation counts by variant.** Every read identifier appears in exactly one row, as its `doi`
  or in its `aliases`. `unread` rows carry `aliases` in the same way.
- **Judgements are still per identifier.** A judgement names the DOI as written and the
  `abstract_sha256` of that variant's own text, matched exactly as before. Each read variant needs
  one. `decide_verdict` counts a paper once: any `claims-resolution` among its variants makes the
  paper `possibly-resolved`, as one claim did before.
- **A folded paper's `doi` may be one no source wrote.** The canonical DOI is the paper's key. If only
  `.2` variants were read, `10.7554/elife.<n>` appears as `doi` and is not itself a read; the variants
  that were read are the `aliases`. A reader who needs the literal read identifiers reads the
  recording.
- **Not changed.** The verdict vocabulary, the refusal reasons, and the recording. The recording
  keeps one row per identifier as written. The paper fold is made at replay as it is made live, so the
  same recording reproduces the same record.

```yaml
# data/problems/reproductions/<target-id>.yaml
id: repro-vertex-rigidity-p0
paper: doi:…
locator: "p. 3, Fig. 2b"
read_level: full-text
quantity: "critical shape index p0* of the 2-D vertex model"
value: 3.81
uncertainty: {kind: tolerance, value: 0.02}
conditions: "…"
registered_at: …             # SPEC-020 registry; before any attack on it starts
result:                      # written by the scorer, never by the attack
  attack: …
  step: …
  value: …
  verdict: reproduced | not-reproduced | indeterminate
```

```yaml
# benchmarks/compounding/preregistration.md, committed to origin/main before any arm runs.
# The harness's own format (SPEC-006 §The pre-registration artifact): a "## The freeze" heading and the
# first fenced yaml block under it, which bench/ablation.py's load_preregistration reads. [harness]
# marks a field that keeps the harness's name because it means what the harness's field means.
preregistration_version: "1.0"           # [harness]
status: frozen                           # [harness]
hypothesis: "Attacks that search the claim graph first reach a supported result in fewer steps."
arms: [substrate, blind]
primary_comparison: "blind vs substrate" # [harness]; a positive difference means the substrate arm needed fewer steps
primary_metric: steps_to_first_supported # [harness]; steps to the first step reaching supported at L1 or above, censored at the step cap
primary_analysis: "paired by problem; difference in restricted mean steps; bootstrap 95% CI, 10,000 resamples, seed recorded"   # [harness]
secondary_metrics: [duplicate_step_rate, dead_end_reentry_rate, usd_per_supported_result, best_level,
                    approach_diversity, decision_model_agreement, seconds_to_first_supported]   # [harness]; decision_model_agreement is from SPEC-078 rule 11
secondary_contrasts: [{left: blind, right: substrate, metric: …}]   # [harness]
metric_definitions_sha256: {steps_to_first_supported: sha256:…, …}  # [harness]; one hashed definition per metric above
problems: {rule: "…", list: [...]}       # chosen by a stated rule before the run (open question 2)
n_test_instances: …                      # [harness]; the number of problems
runs_per_arm: 3                          # [harness]; per problem (0.1.0: runs_per_arm_per_problem)
minimum_detectable_difference: …         # [harness]; in σ units, at n_test_instances
descriptive_mdd_cutoff_sigma: 0.5        # director ruling 2026-10-27: a registered parameter, fixed before any arm runs
analysis_mode: confirmatory | descriptive   # descriptive when minimum_detectable_difference exceeds the cutoff above (rule 12)
model_policy: {models: […], max_hypotheses: …,
               temperature: {state: not-set, reason: "LLMConfig has no temperature field"}}   # identical across arms
budget_per_attack: {usd, cpu_hours, wall_hours, max_hypotheses}   # the runner's units; identical across arms
step_cap: …                              # the censoring bound: steps per attempted hypothesis × max_hypotheses
budget_check: caps-identical             # declared caps are equal; actual spend is reported per arm, not matched
order: {seed: …, rule: "…"}              # arms interleaved per problem; this seed is the only seed
stopping_rule: "fixed N; no interim looks"   # [harness]
exclusions: "an attack that fails for an infrastructure reason is re-run once and the failure recorded"   # [harness]
analysis_code_sha256: sha256:…           # [harness]; benchmarks/compounding/analysis.py, the frozen analysis
substrate_snapshot: {commit: …, tree_sha256: …}   # what the substrate arm searches (rule 11)
namespace: benchmarks/compounding/runs/<arm>      # where each arm's attacks are written (rule 11)
blind_prompt: "…"                        # the text the blind arm's prompt shows in place of the substrate
```

0.1.1 replaced the 0.1.0 block, a `.yaml` file with its own key names. That block's `primary`,
`secondary`, `analysis`, `stopping` and `runs_per_arm_per_problem` are the harness's `primary_*`,
`secondary_metrics`, `stopping_rule` and `runs_per_arm`; its `budget_per_attack: {steps, tokens, usd}`
is the runner's units; and `approach_diversity` joined `secondary_metrics` because rule 10 names it.
0.1.2 added `seconds_to_first_supported` for the same reason, and took the registry out: 0.1.1's
block carried `registration` and `anchor` states, which the second director ruling replaced with the
harness's own anchor.

**There is no `registered_at`, `frozen_at_commit`, `registration` or `anchor` key.** Neither the time
nor the commit at which the file was frozen can sit inside the file whose bytes the harness's
OpenTimestamps anchor commits to. The freeze is read from git (rule 10: the first commit on main's
first-parent history that holds the file, with the file and its analysis byte-identical to the
working tree's and no run record yet) and the anchor from the proof file beside the pre-registration
(`preregistration.ots` and `preregistration-headers.json`). A missing proof is the named gap of rule
10. `not_preregistered` appears only when a measure rule 10 names is not registered as a secondary
metric: a list of `{measure, reason}`, absent otherwise, because the harness reads an empty list as a
placeholder.

`budget_check: caps-identical` is a choice and not the harness's five-percent match on actual spend
(made on tokens, wall-clock seconds and simulate calls): the `substrate` arm reads search results, so
matching its actual spend to the `blind` arm's would flag the treatment's own cost, which
`usd_per_supported_result` measures.

## Rules

### The stops

1. **Every stop has a `demo_all` check, and a stop whose check does not PASS is cut, not
   narrated.** The checks are `demo_all.py --only hackathon/<stop>`. A check observes the served
   page or its panel record, as `--only open-problems/graph` already does (M2368). It never
   observes a bundle that could stand in for the page.
2. **Every number said aloud or printed in the deck is read from the served bundle at a named
   `producing_commit`.** The deck generator reads the numbers, and a typed number is a defect.
3. **The stops, in order.** The routes are SPEC-075's. Each stop is a capability, never one
   specimen.

   | # | stop | route | says |
   |---|---|---|---|
   | 1 | Ask the graph | `/claims` | a question returns the four groups and a suggestion, with the arms that ran |
   | 2 | Evidence, beyond Paperclip | `/claims/<id>` | the bundle by origin, with the structural comparison against `claims/support` beside it |
   | 3 | From paper to formal claim | `/problems/<slug>` and the funnel | one paper's claims through every formalization mode, and the funnel counts |
   | 4 | The engine decides | `/problems/<slug>/belief` | evidence weight, the prior control, the tornado, a what-if, and the next action with its robustness and the decision models' views |
   | 5 | An attack that reuses | `/problems/<slug>/attacks/<id>` | the exploration graph replays; each step shows what it searched, what it found and what it used |
   | 6 | Results, honestly | `/problems` | the scoreboard with openness dates and the reproduction hit rate |
   | 7 | Claims on the network | the nanopub view | a claim and a null as `mira:Claim` nanopublications with their evidence, study and review, signed offline. Until ADR-0005 is decided this is "Level 0": a published MIRA claim fetched from the network and ours checked side by side by the same tools, with nothing published |
   | 8 | Does it compound? | `/problems/compounding` | the pre-registered comparison's result with its interval, whatever its sign |
   | 9 | What works, what doesn't | `/system/scorecard` | the computed scorecard |
   | 10 | Turn it on | the campaign | the event campaign enqueued, and live counters read from records |
   | 11 | Spice | the demos menu | the Halloween design exercises |

3a. **What was built before the event and what was built during it are labelled, and every stop
    can be re-run.** The organisers have published no rule on pre-existing work.
    `docs/sources/hackathon/scienceclaw-2026.md` records that as still absent on 2026-10-27, and
    `organiser-answers.md` records the question as unanswered. So the demo takes the strict
    reading in `docs/demo-plan.md` risk 1.
    - **Each stop says which of its records were produced before hacking started and which
      after.** Hacking starts 2026-10-30 at 18:00 PDT (21:00 EDT at the venue). The split is read
      from the committer times of the records' `producing_commit`s, never stated by hand.
    - **Each stop's `demo_all` check runs from a clean clone at a pinned commit**, so a judge who
      asks for a re-run can have one. A stop that cannot be re-run inside its slot is shown as a
      replay and labelled as one. The submission is slides, so live running is a bonus and not a
      condition (demo-plan risk 2).
    - **This rule does not decide whether pre-event work counts.** That is the organisers' call.
      This rule only makes the answer checkable whichever way they rule.

### Words

4. **Status words come from SPEC-076 rules 13 and 14, plus one.** `reproduced` is the status of a
   reproduction target met within its tolerance. A reproduction is never a candidate solution,
   and a problem is never "solved" unless a cited source says so (`field-resolved`).
4a. **Every result named in the deck carries four labels, or says `unlabelled`.** They follow how
   the field now reports such results: Feng et al. 2026 (arXiv:2601.22401) label results and
   publish the whole funnel, and the landscape report records why. The labels are:
   - its SPEC-076 reading and ladder level;
   - its autonomy: human-led, collaborative or autonomous, with the count of human interventions
     taken from its R8 provenance;
   - its significance, on a 0–4 scale. Most results here are expected to be 0 or 1, and the deck
     says so;
   - its relation to the literature: autonomous resolution, partial, independent rediscovery,
     literature identification, or reproduction.

   A person named on the result assigns the autonomy and significance labels. An agent never
   assigns them to its own result.

### Openness

5. **A problem called open in the pitch, or shown as `candidate-solution`, has an openness check
   no older than 14 days.**
   - The check searches at least two independent sources (OpenAlex and PubMed, with Paperclip
     where configured) for the problem's own terms since its attestation date. It also follows
     the attesting paper's later citers through OpenAlex.
   - One model pass may be told to find a solution despite the open label, as the GPT-5 Erdős
     search did (the landscape report). Its hits are leads, and none of them is a read until a
     person or an agent reads the cited work at a read-level.
   - It reads every hit at least at abstract level and judges each one.
   - `possibly-resolved` blocks the word "open" until a person reviews the hits, and the problem
     page shows the check's date and verdict.
   - The check is a SPEC-073 operation with its queries recorded. A check that could not run is
     recorded with the reason. It is never recorded as `still-open`.
   - **It is a SPEC-074 re-check, not a second mechanism.** It runs through
     `problems/staleness.py`'s `recheck`, with the hits it judged as its reads, so the register's
     `last_checked` advances only when the check read something (SPEC-074 rule 5, M2185).
   - **A `resolved` verdict goes through `problems/resolution.py`** (SPEC-074 rules 6 and 7,
     M2186). It needs an evidence item naming the work that resolved the problem, and that work
     cannot be our own.
   - **A `still-open` verdict is stored as a SPEC-076 rule 7 null.** The null states what it
     covered: the literature published between the attestation date (`since`) and the check date,
     searched through the named sources and queries, with the method `heuristic` and a sampling
     design that names them. It is a record in the claim graph, so a claim search returns it in
     `dead_end` for a region inside that span. A check that was refused, or that ended
     `possibly-resolved`, covered nothing and is not stored as a null.
   - The 14-day window belongs to the pitch. It is separate from the register's staleness
     window, which is measured in months, and it changes nothing in that window.

### Reproductions

6. **A reproduction target is read at full text and registered before its attack starts**, with
   its tolerance declared at registration.
7. **The attack never reads the target.** The target file is not among the attack's inputs. The
   scorer compares afterwards, and the comparison counts only when the result is re-executable
   (SPEC-076 R5).
8. **The hit rate is reported with its denominator.** That includes the `not-reproduced` and
   `indeterminate` targets. The caveat is stated beside it: a reproduction tests execution, not
   discovery, and a model may know the published value.

### The funnel

9. **The autoformalization funnel is computed from formalization records, with every
   denominator.** The stages, per mode, are drafted, parsed, compiled (L1), past the gate (L2 and
   the SPEC-009 anti-triviality gate), correspondence reviewed (agent and person counted
   separately), disputed, and used by a claim. A failed draft is counted and never deleted. The
   worked paper shows every stage of its own claims, failures included.

### The compounding comparison

10. **Pre-registered before any arm runs, on the harness that already exists.**
    - `bench/ablation.py` (SPEC-006 §The pre-registered ablation) already has the pre-registration
      loader, the frozen-analysis check, budget matching within 5%, the anchor-before-arms check
      and a results verifier that recomputes intervals rather than reading them. The comparison is
      a two-arm configuration of that harness. It is not a second harness. SPEC-006's arms A–D
      compare architectures, and this comparison holds the architecture fixed and varies substrate
      access, so the two experiments answer different questions and share one instrument. It uses
      the harness's markdown pre-registration format and calls the harness's check functions from a
      profile module, `bench/compounding.py`, which adds the compounding fields. The harness itself
      is not modified, and no second pre-registration format is added.
    - The pre-registration is committed to `origin/main` with its frozen analysis, and anchored by the
      harness's own check. It is not registered through SPEC-020, and not as a `Prediction`: a
      `Prediction` needs a distribution and this comparison states none (none is invented), and an
      `AnalysisPlan` analyses data that already exist, where these runs have not happened, so there is
      no outcome partition to digest (SPEC-020 open question 9). The director ruled this on
      2026-10-27, reversing the first round's registry route.
    - The commit-level order is proved from git trees and not from ancestry, because Orchestra
      squash-merges and a squash orphans the branch commit an ancestry test would name (M2387's pack
      freeze guard is the case, and the landed form). The freeze commit is the first commit on `HEAD`'s
      first-parent history that holds the pre-registration. Its tree holds the pre-registration and
      its analysis byte-identical to the working tree's, with `status: frozen`, and no run record and
      no result; and the first commit that holds a run record carries the same bytes. A shallow
      checkout, no freeze commit and no run yet are each reported as not checked, never as a pass.
    - OpenTimestamps anchoring is outward-facing, so the owner confirms the first one (AGENTS.md
      §5). It is the same step M2272 waits for, so one confirmation unblocks both. Without an
      anchor the result says "pre-registered by commit, not time-anchored", and the harness's anchor
      check reports that as a gap rather than as a pass. A missing proof never stops a run: the gap
      is recorded and the run records say `anchored: false`. The harness requires every run of both
      arms to start after the anchor's confirmation (`check_anchor_precedes_arms`), so an anchor
      confirmed after an arm started fails the check and cannot upgrade the claim: the label is
      earned clause by clause, and "time-anchored" is printed only when the anchor clause is green.
      Bitcoin confirmation takes hours (SPEC-020 open question 1), so the anchor may still be
      pending when the arms must run, and the comparison then says it is not time-anchored.
    - Secondary measures, named before the run: duplicated steps, time to the first supported
      result (`seconds_to_first_supported`, from the clock stamp on each step and the attack's start
      time; descriptive, with no threshold), and the diversity of approaches tried
      (`approach_diversity`). The last is the anchoring check: the landscape report records that
      preserved failures helped a weaker model and could constrain a stronger one. A measure named
      here is registered as a secondary metric or listed under `not_preregistered` with its reason,
      and is never silently absent.
11. **The arms differ only in substrate access.**
    - The `blind` arm cannot read the substrate: its claim search returns nothing and says why
      (SPEC-077 rule 3's reason for a skipped arm). That is the harness's setting and not a field of
      the search request, so an agent cannot turn it off. The arm keeps the problem register and the
      operators' inputs, which are not the substrate: an empty root would remove those too, and the
      arm would then differ for a reason that is not substrate access. (0.1.0 said "an empty
      substrate root".)
    - The `substrate` arm searches a snapshot of the substrate pinned at the pre-registration
      commit, so the runs in a cell are exchangeable. A live-substrate variant, where the substrate
      grows with the experiment's own runs, is a later question.
    - Both arms have the same literature tools, models, budgets and problems. A run records the
      model that answered and the temperature of the call, `not-set` where the call layer accepts
      none.
    - Neither arm's outputs are written under the substrate. Each arm's attacks go to its own
      namespace, so the snapshot cannot move during the experiment and the `substrate` arm cannot
      see the `blind` arm's work until the analysis is done.
    - The arms are interleaved per problem, in an order drawn from a recorded seed. That seed is
      the only seed.
12. **The result is reported whatever its sign, with its interval and its N.** If the interval
    includes zero, the page says the measurement did not find an effect at this N, never that it
    found none. No sentence anywhere says knowledge compounds unless this rule's result supports
    it, and `scripts/check_claims.py` covers the deck. The pre-registration states its minimum
    detectable difference at its N (SPEC-006 §The pre-registration must state what the design can
    resolve). A design that cannot resolve the difference it looks for is analysed descriptively,
    with intervals, and the page labels it so (`analysis_mode: descriptive`). The line is drawn at a
    registered cutoff: the design is descriptive when its minimum detectable difference exceeds
    `descriptive_mdd_cutoff_sigma`, 0.5σ by director ruling (2026-10-27), fixed in the
    pre-registration before any arm runs.

### The scorecard

13. **The scorecard is computed, with denominators, and every sentence about it links to a
    cell.** It covers:
    - the funnel;
    - reuse-bar conditions unmet, by condition;
    - attack outcomes by mode, model and domain;
    - the search record (searches per step, hits used, dead ends skipped);
    - the comparison's result;
    - reproduction hits;
    - decision-model agreement;
    - cost per supported result.

    The "what works, what doesn't" lines in the deck and the write-up are written from these
    cells, and each cites the cell it rests on.

### Nanopublications

14. **A claim reaches the network as several nanopublications, each made from an existing
    Knowledge Pixels template.** The shape is the one recorded in
    [`docs/research/nanopubs-claims-and-knowledge-pixels.md`](../docs/research/nanopubs-claims-and-knowledge-pixels.md)
    §(2) and §(3):
    - **the claim**, a `mira:Claim` whose title is one self-contained declarative sentence (the
      AIDA form), with its limits in `sioc:content`. A null has the same shape, with its coverage
      inside the sentence;
    - **its evidence, its study** (the attack run) **and its protocol**, each a nanopublication of
      its own;
    - **one argumentative link** (`mira:supports` or `mira:opposes`) per link;
    - **one review per assessor**, from the "Declaring to have reviewed something" template. A
      review never uses `npx:approvesOf`, which approves a nanopublication and feeds the
      network's trust layer;
    - **an index nanopublication** for the set.

    Each nanopublication:
    - is built only after the reuse bar is met (SPEC-076);
    - uses http(s) IRIs only, because Knowledge Pixels' checker rejects `urn:` and `ms:`;
    - declares the templates it was made from;
    - is signed offline;
    - carries its problem context so that it can be read alone.

    **Not for the hackathon.** Logical links (`implies`, `refutes`, `special_case_of`) and a
    null's structured covered space have no template yet. They stay in the claim graph and are
    proposed to Knowledge Pixels as templates afterwards. Belief is never published as a fact.
    The inputs and the method that compute it are published instead.

    The builders already exist, and this rule extends them rather than adding a third.
    `attacks/nanopub.py` builds and signs a result or a null offline, and `attacks/export.py`'s
    `claim_nanopub_trig` builds a claim with its CiTO-linked edges. The new work is the template
    alignment and the split into one nanopublication per kind.
15. **Network publication waits for ADR-0005 and goes to the test registry first** (SPEC-007,
    AGENTS.md §5). Until then the stop says "signed, not published", and it shows "Level 0":
    - a published MIRA claim fetched from the network with `GET` and `Accept: application/trig`
      (a `HEAD` returns 200 even for an id that does not exist);
    - our offline-signed set beside it, both checked by the same tools.

    A review of the shape by the nanopublication expert on the team is recorded as an Assessment
    by that person. The provenance of a published nanopublication must point at something
    public, and this repository is private, so publishing waits for the owner's decision on what
    is made public as well as on the key.

### Spice

16. **The Halloween designs are labelled design exercises.**
    - They are built with txt2organism (SPEC-005) and, where useful, the chimera tools (SPEC-059).
    - Every component claim carries its evidence tier.
    - SPEC-063's DNA-level screen is not built (the spec is aspirational and no screen is integrated),
      so none is run and none is claimed. The designs are component-level: named parts with a role in
      words, no nucleotide sequence, no protocol, non-human organisms only, and a framing that would
      modify a person is refused first. Each design records that the five refusal classes were checked
      and how, the screen as `outcome: unavailable`, and `exported: false`. The test refuses a run of
      20 or more nucleotide characters and a FASTA header; it does not catch a protein sequence.
    - No design claims viability, and the page says these are for fun, in plain words.

### Novelty, and turning it on

17. **Every novelty sentence in the pitch has its closest prior art beside it.** It comes from
    the landscape report's comparison table, and a "first" needs a negative search with its
    scope stated (AGENTS.md §1b).
18. **Turning it on is enqueueing a campaign under a spending cap.** The event campaign lists its
    problems, budgets and model policy, and its spend is capped at the owner's daily OpenRouter
    limit. Live counters (claims, searches, uses, nulls, spend) are read from records. The file
    is the existing `data/attacks/campaigns/hackathon.yaml` (M2367), extended with the
    reproduction wave and the cap. It is not a second campaign. `attacks/campaign.py`'s
    `enqueue` prints the Orchestra commands by default, and creating the tasks stays an explicit
    act, so the switch is the owner's.

## Acceptance

| id | what | test |
|---|---|---|
| M2462 | The openness check as a SPEC-073 operation, the record, the 14-day rule on the problem page and the scoreboard | `uv run pytest tests/test_problem_openness.py -q` |
| M2463 | Reproduction targets, the registration-before-attack rule, the scorer, and the hit rate with its denominator | `uv run pytest tests/test_reproductions.py -q` |
| M2464 | A reproduction campaign wave over at least eight registered targets, enqueued by the existing campaign machinery | `uv run pytest tests/test_campaign_reproductions.py -q` |
| M2465 | The autoformalization funnel, computed, and one paper worked end to end through every mode | `uv run pytest tests/test_autoformalization_funnel.py -q` |
| M2466 | The compounding comparison's pre-registration as a profile of the ablation harness (markdown, `bench/compounding.py`), and the runner's `blind` mode (arms differ only in substrate access) | `uv run pytest tests/test_compounding_prereg.py tests/test_bench_ablation.py tests/test_attacks_runner.py tests/test_claim_search.py -q && uv run ruff check .` |
| M2467 | The comparison run and its analysis, published at `/problems/compounding` | `uv run pytest tests/test_compounding_result.py -q` |
| M2468 | The scorecard at `/system/scorecard`, computed with denominators | `uv run pytest tests/test_studio_scorecard.py -q` |
| M2469 | Claim, null, evidence, study, link, review and index nanopublications from existing Knowledge Pixels templates, signed offline | `uv run pytest tests/test_claim_nanopubs_kp.py -q` |
| M2470 | Test-registry publication of the demonstration's nanopublications and their resolution (waits for ADR-0005) | `uv run pytest tests/test_claim_nanopubs_network.py -q` |
| M2471 | Two or more Halloween design exercises, component-level, with an evidence tier on every component, the SPEC-063 position recorded as it is (refusal classes checked, screen unavailable, nothing exported), listed in the Tour rail | `uv run pytest tests/test_halloween_designs.py tests/test_studio_demos.py tests/test_studio_router.py tests/test_studio_ia.py -q && uv run ruff check .` |
| M2472 | `demo_all --only hackathon` with one check per stop | `uv run pytest tests/test_demo_all_hackathon.py -q` |
| M2473 | The deck for these stops, generated from the served bundle | `uv run pytest tests/test_deck_hackathon.py -q` |
| M2474 | The event campaign with its spending cap, and the live counters | `uv run pytest tests/test_event_campaign.py -q` |
| M2475 | Openness checks run and recorded for every attacked problem and every problem named in the deck | `uv run pytest tests/test_openness_records.py -q` |
| M2476 | The write-up: what works, what doesn't, and what is new, every number linked to a scorecard cell | `uv run pytest tests/test_writeup_links.py -q` |

## Open questions

1. ~~**The primary metric's censoring.**~~ **Ruled 2026-10-27 (director):** the proposal is
   adopted. Restricted mean steps, with an attack that never reaches `supported` scored at the step
   cap plus one. An alternative is a survival analysis; with about this many problems the simpler
   estimator is easier to defend.
2. ~~**Which problems enter the comparison.**~~ **Ruled 2026-10-27 (director):** the proposal is
   adopted, counting results plus nulls. The attacked problems with at least five recorded results
   or nulls in the substrate at the pinned commit, because the substrate arm can only help where
   there is something to find. The rule is stated before the run, the problems it excludes are
   listed, and n is the count the rule gives at that commit.
3. **Whether to show a decision model's ranking on stage at all** if the comparison has not
   resolved enough actions. Proposed: show it as a recorded view with its agreement count, and
   never as better or worse.

## References

- The plan this spec makes checkable: [`docs/hackathon-goal.md`](../docs/hackathon-goal.md);
  the previous plan, kept: [`docs/demo/open-problems-plan.md`](../docs/demo/open-problems-plan.md);
  the rubric: [`docs/hackathon-strategy.md`](../docs/hackathon-strategy.md).
- Components: [SPEC-074](SPEC-074-open-problems-register.md), [SPEC-076](SPEC-076-open-problem-attacks.md),
  [SPEC-077](SPEC-077-claim-search-and-evidence-api.md), [SPEC-078](SPEC-078-problem-belief-graphs.md),
  [SPEC-009](SPEC-009-autoformalization.md), [SPEC-041](SPEC-041-formalization-workbench.md),
  [SPEC-007](SPEC-007-nanopub-timestamping.md), [SPEC-031](SPEC-031-nanopub-conformance.md),
  [SPEC-020](SPEC-020-prediction-registry.md), [SPEC-005](SPEC-005-txt2organism.md),
  [SPEC-059](SPEC-059-chimeras-inverse-design.md), [SPEC-063](SPEC-063-dna-level-screening-and-review.md),
  [SPEC-073](SPEC-073-everything-is-an-operation.md), [SPEC-075](SPEC-075-studio-information-architecture.md).
- Research: [`ai-science-landscape-2026.md`](../docs/research/ai-science-landscape-2026.md),
  [`nanopubs-claims-and-knowledge-pixels.md`](../docs/research/nanopubs-claims-and-knowledge-pixels.md),
  [`intermediate-results-substrate.md`](../docs/research/intermediate-results-substrate.md),
  [`rule30-center-column-periodicity.md`](../docs/research/rule30-center-column-periodicity.md).
- Decision: [ADR-0005](../docs/decisions/ADR-0005-signing-key.md).
