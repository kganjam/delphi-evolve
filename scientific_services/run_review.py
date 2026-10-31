"""Submit the independent public-input scientific/novelty review to Gemini Flash, then (separately) Pro."""
import sys
from pathlib import Path
from .gemini_client import Gemini

SYSTEM = ("You are a skeptical, expert reviewer of computational protein-engineering and active-learning "
          "papers. You are reviewing a hackathon project's code and claims. Be specific and adversarial but fair. "
          "Only cite code lines that appear in the supplied listing; if you are unsure, say 'unsure'. "
          "Do not invent literature results: if you mention prior work, say how confident you are in the specifics.")

TASKS = """
TASK. Review the project above (spec, prior art, frozen protocol, partial replay receipt, and the actual
core code with line numbers). The authors' central claim is 'query-to-certify': choosing assays to settle a
reachability (open/blocked) decision on a measured 4-site TrpB landscape, with certificates. Answer, in order:

A. LEAKAGE. List every plausible route by which information about unrevealed labels (or the full dataset)
   reaches a policy, the interval/noise model, the target/start selection, or the truth definition. For each:
   file:line, mechanism, severity (high/med/low), and whether it would favour the proposed policies.
B. MISLEADING UNCERTAINTY. Where do intervals, 'kappa', 'certificates', or 'false certificate rate' give the
   appearance of statistical or biological guarantees that they do not provide? Is 'false certificates = 0'
   informative or structural? Show why with code references.
C. COMPARISON VALIDITY. Are the policies compared on equal footing (information, budget, tie-breaks, seeds,
   censoring, initial observations, what an 'assay' costs, what counts as resolved)? Is the benchmark
   primary outcome meaningful given how unresolved/censored episodes are handled? Does comparison with ALDE-style
   active learning make sense or not, and what is NOT comparable?
D. EXACT COUNTEREXAMPLES. Give concrete minimal counterexamples (small numbers/genotypes/intervals/graphs)
   where a certificate, a verdict label, or a comparison conclusion is wrong or misleading. State precisely
   what input produces what output.
E. WHAT RESULT WOULD JUSTIFY THE PITCH, and which claims in the spec the current evidence does NOT support.
   Give a prioritised list of at most 6 concrete fixes naming file paths.

FORMAT. Return Markdown. For A-D use a numbered list; each item: **ID** (e.g. A1), one-sentence claim,
evidence (file:line), severity, confidence (high/med/low) that the issue is real as stated.
Keep the whole answer under 2200 words; be concise (one short paragraph per item) and cover ALL of A-E.
"""

PRO_TASKS = """
TASK (second, deeper pass). Do not summarise everything. Identify the SINGLE most serious threat to the
validity of the headline benchmark claim ('query-to-certify policies need fewer assays than baselines to
reach a correct certificate'), and the next two most serious. For each: (1) the precise mechanism with
file:line references from the listing, (2) an exact counterexample with concrete values that you could be
checked by running a few lines of code, (3) a falsifiable prediction of what a corrected benchmark would
show, and (4) whether the conclusion survives. Also say whether it is meaningful to report 'false
certificates = 0', and what the minimum defensible pitch sentence is given only the evidence in the bundle.
Mark each claim you are not sure of. Under 2500 words.
"""

def main(which, label_suffix=""):
    bundle = Path("artifacts/services/gemini/review_bundle.md").read_text()
    g = Gemini()
    if which == "flash":
        rec = g.generate("gemini-3.8-flash", bundle + "\n\n" + TASKS, system=SYSTEM, max_output_tokens=6500,
                         temperature=0.2, label="review_flash_independent" + label_suffix, thinking_level="low")
    elif which == "pro":
        rec = g.generate("gemini-3.1-pro-preview", bundle + "\n\n" + PRO_TASKS, system=SYSTEM, max_output_tokens=9000,
                         temperature=0.2, label="review_pro_serious_claim" + label_suffix, thinking_level="low")
    print(rec["model_version_returned"], rec["usage_metadata"], rec["finish_reason"], len(rec["response_text"]))

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "")
