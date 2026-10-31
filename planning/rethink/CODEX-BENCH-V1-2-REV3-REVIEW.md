# v1.2 rev3 metadata/text review and kill-ledger R06 mapping

Codex API, October 31, 2026, Seattle PDT. **The 128-item data/prompt candidate passes the requested metadata/text gate.** Correct the README bookkeeping listed below when publishing FROZEN.md. This is not approval of a prover runner or an agent evaluation protocol, and is not a new blinded/full scientific audit.

Benchmark revision: `af7f38e24e3750af142dc6cbc0a45709ca0b4001`.
Metadata checker revision: `ffcd3151ea4dc4ac9a7c4bf304c11a402eced056`.
The latter adds the checker/receipt; its key and payload are unchanged from af7f38e.

- Key SHA256: `774f6a08bf77330b8d46dbcbc0fd7aef52da572921dd600c871228e418974c38`.
- Model payload SHA256: `89ad490e61fb257207f62bff15e53dc83d9e8231eaa96b0d00c5166e030b87b2`.

I materialized the pinned git objects into my own review snapshot and ran the critic's `python3 -I scopedesk/bench/v1_2/metadata_check.py OUT.json` under TasksMax=128, MemoryMax=4G, MemorySwapMax=0, RuntimeMaxSec=600. **Exit 0; 14/14 checks pass.** Receipt: `artifacts/integration/codex-api/bench-v1-2-rev3-metadata.json`. No worker checkout was edited.

Independent additional checks in `audit_bench_v1_2_rev3.py` verify uniqueness in all four files, exact family-specific convention suffixes, payload order/text identity, retained verdicts, exclusions and revised answer/abstention reporting. All pass. The 37 Turing 1-D/2-D questions explicitly ask for a growing linear mode. The wavelength text no longer claims absence of all pattern wavelengths. Always-abstain has zero coverage and undefined selective risk; B0 reports 68 answers of 128, not 128 correct answers. Utility costs and fair information access remain the runner's separate preregistration responsibility.

An initial delta check failed the assumption that retained parameters and full keys were unchanged. Inspection found **21 retained 1-D Turing structured inputs changed**, with witness/repair changes in the key; all retained verdict labels stay the same. The renderer change removes a random draw, consistent with changing subsequent generated parameters. This is a new candidate, not merely the old panel with three rows removed. I independently recomputed all **22 current Turing-1D labels using exact rational determinants and a finite mode bound; 22/22 agree**. This does not repeat the former blinded language audit or validate every repair witness. The initial diagnostic receipt is preserved as `bench-v1-2-rev3-initial-delta.json`; the expanded passing review is `bench-v1-2-rev3-delta.json`.

The three removals since the 131-item candidate are `gh-0004`, `gh-0012`, `gh-0016`, all uniform-column cases with missing density. My initial check mistakenly expected gh-0008 instead of gh-0004; that expectation was corrected from the pinned ID map. The substantive rounded-coefficient objection is addressed by excluding the actual three cases.

Before the freeze announcement, update these README statements without changing the reviewed inputs:

1. The Greenhill table still claims missing-density uniform cases can be settled by 0.04% agreement. Remove that obsolete exception; use the current convention and disclose the exclusions.
2. The final paragraph says “this exact 131-item set”; it is 128.
3. Clarify seven recent audit removals versus the earlier near-tie exclusion, rather than mixing the counts in one sentence.
4. State that retained labels are unchanged while 21 structured Turing inputs and some witnesses/repairs changed. Historical 135-item blinded scores are historical results, not scores on this exact panel.

The review is nonblinded. Eight families still correspond to six mechanism groups. Numerical, linear-model and biological conclusions remain separate. This data freeze does not resolve the independently documented Lean runner defects or authorize new 21-record Mathlib prover arms.

## R06: correct witness mapping and category

Reviewed kill-ledger revision `2722f9f72bb264c5bc2e42a0f10c51ffff79adab`, row R06. The source is **not missing**:

- Codex review commit `b4e60db91050ccaec8cd16f8f57373690c5efa7b`, `planning/rethink/CODEX-21-CLAIM-FREEZE-REVIEW.md`, paragraph for `finite_domain_stable`.
- Exact reviewed original module: `artifacts/integration/codex-api/admissible-review/Admissible.lean`, SHA256 `c51b98a8c4218c5e272223c5d710de0d765804d78beace544850f9749cf07236`, also present at Admissible `d75e245f660f9dfc1e7971d6b71c332b0c31987c`.
- The already cited `messages/codex-price-probe-progress.md` explicitly states the same finding. It is evidence text, not merely a nearby proxy file.

The theorem assumes `∀ n, ¬ Unstable S (neumannMode L n)`, with `Unstable S q := D S q < 0`, and concludes `∀ n, 0 ≤ D S (neumannMode L n)`. It is a true logical restatement. It does not conclude negative trace, strict determinant positivity, or spectral stability.

An explicit **analytic distinguishing witness** is J=diag(2,2), Du=Dv=1 and L=π. For every q, D(q)=(2−q)²≥0, so the theorem's hypothesis holds for every admissible mode. Yet n=1 gives q=1 and J−qD=diag(1,1), with positive eigenvalues. This witness is analytically checked here; no new Lean compilation is claimed. It also shows that the premise is satisfiable: calling the theorem “vacuous” in the sense of impossible premises is incorrect.

Suggested R06 kind: **statement-fidelity defect: determinant nonnegativity presented as stability**. Suggested allowed wording: **“A valid Lean theorem can prove less than its scientific title suggests; inspect the exact conclusion and the missing conditions.”** Non-vacuity controls alone would not catch this defect, and failure of a reused proof on a mutant is not automatically a refutation of that mutant.

Use the review commit time **07:05:34 PDT** if a stable recorded-review timestamp is needed; do not call it the first utterance time. The claim time and elapsed interval remain not derivable. The original progress-file timestamp can be retained if clearly identified as file metadata.

Also retain the repair history: the subsequent `finite_domain_linearly_stable` at Admissible 469874b, independently compiled in Codex 7f9035a, derives negative trace from well-mixed stability and positive diffusion and assumes strict positive determinant for every mode. This is stronger; full matrix/PDE correspondence is still outside that formalization. Do not present the historical R06 defect as though no correction was made. This review verifies R06 only, not all twenty ledger rows or their timing aggregates.
