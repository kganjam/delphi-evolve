# Review walkthrough

Standalone static page at `site/review/index.html`, for integration by the director.
No npm, external fonts, API calls, Lean server, GPU process or tracking code.

The three interactive cases use reduced BigInt fractions for decisions. Floating
point draws the SVG geometry only. Browser calculations are labelled separately
from linked, pinned historical Lean receipts. The volume example is analytic/source
review, not Lean-compiled. Price/Hamilton is a collapsed appendix, following the
director's four-part FINAL SHAPE at e0a376f.

Internal links expect the existing `site/` tree to be packaged with this subdirectory.
Scientific claims trace to ledger F01/F02/F04/F05/F07/F08; scorecard and agent scores
remain pending. Recorded compilation does not establish source correspondence,
nonlinear pattern selection, or biological truth.

Validation: `scripts/check_review_walkthrough.py` starts a loopback HTTP server,
checks desktop/mobile behavior and links, exercises scientific control changes,
and writes screenshots and an executed receipt. Run under the standard systemd
resource caps. Publication is the director/primary handoff, not a side effect of
building this page. Do not edit the separate site-hosting checkout.
