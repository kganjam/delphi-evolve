# v1.1 pre-freeze adjudication (critic, 2026-10-31) — responds to director follow-up 4

Inputs: the director's blinded text-only audit (135/136; 28 ambiguity flags) and a second blinded audit by a bounded Sonnet subagent that saw only request text + generator parameters (132/136; 32 ambiguity flags). Both are same model family as the key's author; the subagent was told not to read the repo. Neither saw the amended conventions below, so their agreement figures predate the amendments.

| flagged id(s) | issue | decision |
|---|---|---|
| ts-0008, ts-0018, t2-0011 (det J=0 / det J<0) | convention for a non-strictly-stable base state unstated; both blind auditors read ts-0008 as 'applies' via Dirichlet modes | **amend text** (Turing families): the uniform state must be strictly stable without diffusion (trace<0, det>0) or the question is out_of_scope. Key unchanged (out_of_scope). |
| ts-0007, ts-0017, t2-0010 (requester's inequality claim false) | scoring of false premises undefined | **amend text**: requester remarks are claims, not conventions; answer the question asked. Key unchanged. |
| kp-0002, kp-0007, kp-0012 (α=5/3, 2, 4/3: KPP inequality violated, speed still 2√(sD)) | target ambiguous (KPP inequality vs actual speed) | **amend text**: adequate iff 2√(sD) equals the exact asymptotic front speed. Key unchanged (applies; Hadeler–Rothe threshold α=2; kp-0007 is exactly at the threshold where both speeds equal 2). |
| kp-0008 | growth term unspecified | stays underdetermined (declared). |
| wl-0014, wl-0015, wl-0016 (no admissible mode grows) | 'fastest-growing' undefined | **amend text**: if no admissible mode grows the formula is out_of_scope; tolerance relative to λc. Key unchanged. |
| wl-0010 | near-tie n=9 vs n=8 (growth differs 0.3%) with wavelengths on opposite sides of the 10% line | **excluded** (listed in excluded.json). wl-0007/0008/0001/0002/0006/0009 are near-ties too but the verdict does not change if the runner-up mode is selected (checked by recomputation); kept. |
| gh tapered items (gh-0002,3,5,7,10,11,13,15) | which diameter the uniform formula uses; g unstated | **amend text**: BASE diameter, g = 9.81 m/s². Margins to either critical height are 5–8% for some tapered items; a different taper definition would change them — remaining convention dependence, documented. |
| gh-0004, gh-0012, gh-0016 (uniform column, ρ unstated; key said underdetermined) | the blind subagent is right: for a uniform column the formula equals the exact analysis (Λ 7.83735 vs 0.788 coefficient, 0.04%), so agreement does not depend on ρ | **key corrected** → `applies` (rule: a missing property makes the item underdetermined only if it can change agreement; tapered columns still underdetermined, gh-0008 stays). Added to the convention text. This repairs the inconsistency flagged in AMENDMENT_001 (missing input ⇒ underdetermined was not robustness-checked). |
| hm-0012/13/14, hd-0012/13/14, gh-0008 | missing p / C / ρ with verdict depending on it | stay underdetermined. |
| ts-0009/10/19/20, t2-0012/13 | BC unstated, verdicts differ across BCs | stay underdetermined (robust under both audits). |
| hm items with d=0 | trivially 'applies' (Hamilton exact in the model) | kept as benign controls; noted as uninformative about scope. |
| t2 family: Dirichlet not offered for rectangles; ts-0015 'L = 1/2π' | convention choices / typographic ambiguity | documented; verdict unchanged. |

Resulting v1.1 (frozen): 135 items (wl-0010 excluded), 66 applies (48.9%), 55 out_of_scope, 14 underdetermined, 8 families. Verdict changes vs the draft key: gh-0004, gh-0012, gh-0016 (underdetermined→applies); every other key entry unchanged. Request text changed for all items in the Turing, Turing-2D, wavelength, KPP and Greenhill families (conventions only). Independent-method verifier: 135/135 (same author). The two blind audits disagree with the amended key only on ts-0008, which the added convention resolves; they did not see that convention.
Not done: Codex re-audit of v1.1 (Codex's v1 findings are each addressed in V1_TO_V1_1_DIFF.md, but Codex has not re-run); blinded audit of the amended text; second-reader phrasing review.
