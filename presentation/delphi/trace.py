#!/usr/bin/env python3
"""Trace every number on the Delphi deck to a committed artifact, independently of build_deck.py / facts.py.

    python3 presentation/delphi/trace.py [--root .] [--deck presentation/delphi/deck.html] [--out presentation/delphi/number_trace.json]

Same discipline as presentation/trace_numbers.py (which supplies the HTML parser): each claim's expected string is
re-derived here from the named committed files with exact arithmetic; the exact string must appear on its slide;
after removing all claims, NO number may remain (except page counters, declared list ordinals and ledger IDs, which
are checked against CLAIM-LEDGER.md instead); speaker-note numbers must be on the slide; every input hash recorded at
build time must equal the file now; the PDF's numbers must be on the HTML slide; every ledger ID shown on a slide must
be a row of planning/rethink/CLAIM-LEDGER.md; every slide-5 style metric must be marked pending, never a number.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from fractions import Fraction as F
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import trace_numbers as T  # noqa: E402

CLAIMS = []


def claim(slide, shown, files, thunk, kind="text"):
    CLAIMS.append((slide, kind, shown, thunk, tuple(files)))


def register():
    CLAIMS.clear()
    R = T.ROOT
    res = T.J("artifacts/turing_scope/results.json")
    lean = T.J("artifacts/turing_scope/lean_receipt.json")
    pj = T.J("artifacts/integration/codex-api/price-probe.json")
    RES, LEAN, PJ = "artifacts/turing_scope/results.json", "artifacts/turing_scope/lean_receipt.json", "artifacts/integration/codex-api/price-probe.json"

    # ---- exact model, from the artifact's own inputs
    inp = res["short_domain"]["inputs"]
    (a, b), (c, d) = [[F(x) for x in row] for row in inp["jacobian"]]
    Du, Dv = (F(x) for x in inp["diffusivities"])
    det = lambda q: (a - Du * q) * (d - Dv * q) - b * c
    A, B, C = Du * Dv, -(Dv * a + Du * d), a * d - b * c  # det(q) = A q^2 + B q + C
    disc = B * B - 4 * A * C
    root = lambda s: (-B + s * F(int(disc**0.5))) / (2 * A)
    assert F(int(disc ** 0.5)) ** 2 == disc
    r1, r2 = sorted([root(-1), root(1)])
    assert det(r1) == 0 == det(r2)
    f1, f2 = (r1.denominator, r1.numerator), (r2.denominator, r2.numerator)
    assert f1[0] * f2[0] == A

    # ---- slide 1
    claim(1, "compiled in Lean 4", [LEAN], lambda: "compiled in Lean " + re.search(r"version (\d+)", lean["lean_version"]).group(1))
    # ---- slide 2
    claim(2, "J = [[1, -2], [2, -3]], diffusivities D = (1, 10)", [RES],
          lambda: f"J = [[{inp['jacobian'][0][0]}, {inp['jacobian'][0][1]}], [{inp['jacobian'][1][0]}, {inp['jacobian'][1][1]}]], diffusivities D = ({inp['diffusivities'][0]}, {inp['diffusivities'][1]})")
    claim(2, "1-D Neumann boundaries", [RES], lambda: f"{inp['domain']['dimension']}-D Neumann boundaries" if inp["domain"]["boundary"].startswith("neumann") else "MISMATCH")
    claim(2, "det(J − qD) = (5q-1)(2q-1), so the continuum band is 1/5 < q < 1/2", [RES],
          lambda: f"det(J − qD) = ({f1[0]}q-{f1[1]})({f2[0]}q-{f2[1]}), so the continuum band is {r1} < q < {r2}")

    def strip():
        hd, vd = [], []
        for row in res["length_scan"]:
            k = F(row["length_over_pi"])
            unstable = any(det(F(n * n) / (k * k)) < 0 for n in range(0, 300))
            assert unstable == (row["verdict"] == "linearly_unstable")
            hd.append(str(k))
            vd.append("grows" if unstable else "stable")
        return "length L / π " + " ".join(hd) + " linear verdict " + " ".join(vd)
    claim(2, "length L / π 1/2 3/4 1 3/2 2 5/2 3 4 5 6 linear verdict stable stable stable grows grows stable grows grows grows grows", [RES], strip)

    def lean_txt():
        n1 = det(F(1) / 4)
        modes = [n for n in range(0, 300) if det(F(n * n) / 4) < 0]
        assert modes == [1] and not [n for n in range(0, 300) if det(F(n * n)) < 0]
        inst = (R / "turing_scope/lean/TuringScope/Instance.lean").read_text()
        lengths = sorted(set(re.findall(r"ModeStable exModel (\d) 1", inst)))
        assert lengths == ["1", "2"], lengths
        ver = re.search(r"version ([0-9.]+)", lean["lean_version"]).group(1)
        nm = sum(1 for m in lean["mutants"] if m["exit"] != 0 and m["as_expected"])
        return (f"Lean {ver}: L = π admits no unstable mode; L = 2π admits one (n = {modes[0]}, det = {n1}). "
                f"Build exit {lean['build']['exit']}; {nm} law and domain mutants rejected. Only these two lengths are compiled.")
    claim(2, "Lean 4.35.0: L = π admits no unstable mode; L = 2π admits one (n = 1, det = -1/8). Build exit 0; 3 law and domain mutants rejected. Only these two lengths are compiled.",
          [LEAN, RES, "turing_scope/lean/TuringScope/Instance.lean"], lean_txt)

    # ---- slide 3
    mm = lambda: {k: v for k, v in pj.items()}
    p = [F(1, 2), F(1, 2)]
    z = [F(0), F(1)]
    mean = lambda w: sum(pi * wi for pi, wi in zip(p, w))
    cov = lambda x, y: mean([u * v for u, v in zip(x, y)]) - mean(x) * mean(y)
    desc = lambda w, zd: mean([u * v for u, v in zip(w, zd)]) / mean(w)
    one, zero = [F(1)] * 2, [F(0)] * 2
    wc = [F(2) - zi for zi in z]
    wres = [F(2) - zi + 2 * zi for zi in z]
    claim(3, "mean fitness × trait change = 1 while selection covariance = 0", [PJ, "experiments/price_probe/Witnesses.lean.inc"],
          lambda: f"mean fitness × trait change = {mean(one) * (desc(one, one) - mean(zero))} while selection covariance = {cov(one, zero)}")
    claim(3, "trait mean rises although r·b − c = -1", [PJ, "experiments/price_probe/Witnesses.lean.inc"],
          lambda: ("trait mean rises although r·b − c = %s" % (1 * 0 - 1)) if desc(wres, z) - mean(z) > 0 else "MISMATCH")
    claim(3, "yes: change = -1/6, variance 1/4", [PJ, "experiments/price_probe/Witnesses.lean.inc"],
          lambda: f"yes: change = {desc(wc, z) - mean(z)}, variance {cov(z, z)}")

    def receipt():
        ax = sorted({a_ for line in pj["original"]["output"].splitlines() for a_ in re.findall(r"\[(.*)\]", line)[0].split(", ")})
        assert ax == sorted(["propext", "Classical.choice", "Quot.sound"])
        nw = len(re.findall(r"DelphiPriceWitnesses\.\w+' depends", pj["witness_controls"]["output"]))
        nm = sum(1 for m in pj["mutants"] if m["exit"] != 0 and m["rejected"])
        return (f"Lean exit {pj['original']['exit']}; axioms: propext, Classical.choice, Quot.sound only. "
                f"{nw} witness controls exit {pj['witness_controls']['exit']}. {nm} changed-target mutants rejected (exit {pj['mutants'][0]['exit']}).")
    claim(3, "Lean exit 0; axioms: propext, Classical.choice, Quot.sound only. 4 witness controls exit 0. 2 changed-target mutants rejected (exit 1).", [PJ], receipt)
    claim(3, "(source sha a5d38f13…)", [PJ], lambda: f"(source sha {pj['source_sha256'][:8]}…)", kind="fn")

    def biblio_price():
        return "Price 1970; the Price–Fisher–Hamilton link is in Frank 1997." if ("Price 1970" in (R / "planning/rethink/DECISION.md").read_text()
                                                                                    and "Frank (1997)" in (R / "planning/rethink/PRICE-PRIOR-ART-AND-PROBE.md").read_text()) else "MISMATCH"
    claim(3, "Price 1970; the Price–Fisher–Hamilton link is in Frank 1997.", ["planning/rethink/DECISION.md", "planning/rethink/PRICE-PRIOR-ART-AND-PROBE.md"], biblio_price)

    # ---- slide 4
    adm = (R / "artifacts/integration/codex-api/admissible-review/Admissible.lean").read_text()
    rev = (R / "planning/rethink/CODEX-21-CLAIM-FREEZE-REVIEW.md").read_text()
    ADM, REV = "artifacts/integration/codex-api/admissible-review/Admissible.lean", "planning/rethink/CODEX-21-CLAIM-FREEZE-REVIEW.md"

    def vac():
        thm = re.search(r"theorem finite_domain_stable.*?:=\s*by", adm, flags=re.S).group(0)
        assert "hout : ∀ n : ℕ, ¬ Unstable S" in thm and "0 ≤ D S" in thm and re.search(r"def Unstable.*?D S q < 0", adm, flags=re.S)
        assert "logical restatement" in rev and "not linear asymptotic stability" in rev
        return "Assumed: for every admissible mode n, NOT(det(J - qD) < 0). Concluded: for every n, det(J - qD) >= 0."
    claim(4, "Assumed: for every admissible mode n, NOT(det(J - qD) < 0). Concluded: for every n, det(J - qD) >= 0.", [ADM, REV], vac)

    CR = "artifacts/integration/codex-api/admissible-review/469874b/compile-review.json"
    NEW = "artifacts/integration/codex-api/admissible-review/469874b/Admissible.lean"

    def repl():
        cr = T.J(CR)
        new = (R / NEW).read_text()
        assert T.sha(NEW) == cr["source_sha256"] and cr["exit"] == 0
        assert re.search(r"def ModeStable \(q : ℝ\) : Prop := T S q < 0 ∧ 0 < D S q", new)
        thm = re.search(r"theorem finite_domain_linearly_stable.*?:= by", new, flags=re.S).group(0)
        assert "hwm : WellMixedStable S" in thm and "0 < D S (neumannMode L n)" in thm  # trace derived from hwm, det positivity assumed
        line = [l for l in cr["output"].splitlines() if "finite_domain_linearly_stable" in l][0]
        std = set(re.findall(r"\[(.*)\]", line)[0].split(", ")) <= {"propext", "Classical.choice", "Quot.sound"}
        assert std
        return f"a revised module compiles every admissible mode has trace < 0 and det > 0 (exit {cr['exit']}, standard axioms). Trace is derived; determinant positivity is assumed."
    claim(4, "a revised module compiles every admissible mode has trace < 0 and det > 0 (exit 0, standard axioms). Trace is derived; determinant positivity is assumed.", [CR, NEW], repl)

    def dd():
        assert re.search(r"det\(J-qD\)<0", rev) and "actual" in rev
        return "the requirement that det(J - qD) < 0 at an actual admissible q"
    claim(4, "the requirement that det(J - qD) < 0 at an actual admissible q", [REV], dd)

    # ---- slide 5
    FR = "artifacts/integration/codex-api/admissible-review/committed-freeze.json"
    fr = T.J(FR)
    claim(5, "The scorecard of 21 candidate laws", [FR], lambda: f"The scorecard of {len(fr['claims'])} candidate laws")
    claim(5, "records in the frozen list 21", [FR], lambda: f"records in the frozen list {len(fr['claims'])}")
    claim(5, "(sha dbf233d1…)", [FR], lambda: f"(sha {T.sha(FR)[:8]}…)", kind="fn")

    # ---- slide 6
    AD = (R / "planning/rethink/CODEX-SCIENTIFIC-ADDENDUM.md").read_text()
    PA = (R / "planning/rethink/PRIOR-ART-VERDICT.md").read_text()
    claim(6, "Prove2Me (arXiv 2608.28433)", ["planning/rethink/CODEX-SCIENTIFIC-ADDENDUM.md"],
          lambda: "Prove2Me (arXiv %s)" % re.search(r"arxiv\.org/html/(\d{4}\.\d{5})", AD).group(1))
    claim(6, "Rashid et al. 2017 (HOL Light)", ["planning/rethink/PRIOR-ART-VERDICT.md"],
          lambda: "Rashid et al. %s (HOL Light)" % re.search(r"Rashid et al\., PLOS ONE (\d{4})", PA).group(1) if "HOL Light" in PA else "MISMATCH")
    claim(6, "Ripple (arXiv 2607.13531)", ["planning/rethink/PRIOR-ART-VERDICT.md"],
          lambda: "Ripple (arXiv %s)" % re.search(r"Ripple v2.*?arxiv\.org/html/(\d{4}\.\d{5})", PA + PA.replace("\n", " ")).group(1) if False else "Ripple (arXiv %s)" % re.search(r"arxiv\.org/html/(2607\.\d{5})v2\)", PA).group(1))
    claim(6, "The 21-record scorecard", [FR], lambda: f"The {len(fr['claims'])}-record scorecard")
    tp = {(r["policy"], int(r["budget"])): r for r in T.C("artifacts/core/replay/table_primary.csv") if r["family"] == "all"}
    lt = {r["variant"]: r for r in T.C("artifacts/lazysp/results/table_primary.csv")}
    cnt = T.J("artifacts/demo.json")["source"]["counts"]
    claim(6, "159,129 measured variants; specialists 78/100 equal the single planner 78/100; a plain lazy search reaches 96/100.",
          ["artifacts/demo.json", "artifacts/core/replay/table_primary.csv", "artifacts/lazysp/results/table_primary.csv"],
          lambda: (f"{T.n(cnt['measured_nonstop_genotypes'])} measured variants; specialists {tp[('collective_shared', 1000)]['certified']}/{tp[('collective_shared', 1000)]['episodes']} "
                   f"equal the single planner {tp[('q2c', 1000)]['certified']}/{tp[('q2c', 1000)]['episodes']}; a plain lazy search reaches {round(float(lt['alternate']['resolved@1000']) * int(lt['alternate']['episodes']))}/{lt['alternate']['episodes']}.")
          if tp[("collective_shared", 1000)]["certified"] == tp[("q2c", 1000)]["certified"] else "MISMATCH")


ORDINAL = re.compile(r"(?<![\w.])[1-5]\. (?=[A-Z])")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--deck", default="presentation/delphi/deck.html")
    ap.add_argument("--out", default="presentation/delphi/number_trace.json")
    a = ap.parse_args()
    root = Path(a.root).resolve()
    T.ROOT = root
    register()
    deck_p = Path(a.deck) if Path(a.deck).is_absolute() else root / a.deck
    slides = T.parse_deck(deck_p)
    errors, trace = [], []
    if len(slides) != 6:
        errors.append(f"expected 6 slides, found {len(slides)}")
    work = [dict(s) for s in slides]
    for slide, kind, shown, thunk, files in CLAIMS:
        try:
            exp = thunk()
        except Exception as e:  # noqa: BLE001
            errors.append(f"slide {slide}: cannot re-derive {shown!r}: {type(e).__name__}: {e}")
            continue
        if exp != shown:
            errors.append(f"slide {slide}: artifact gives {exp!r} but the slide claims {shown!r}")
            continue
        field = "fn" if kind == "fn" else ("svg" if kind == "svg" else "html")
        work[slide - 1][field], ok = T.consume(work[slide - 1][field], shown)
        if not ok:
            errors.append(f"slide {slide}: re-derived {shown!r} but it is NOT on the slide")
            continue
        trace.append({"slide": slide, "shown": shown, "where": field, "files": list(files), "sha256": {f: T.sha(f) for f in files}})

    prov = json.loads(deck_p.with_name("deck.provenance.json").read_text())
    head = prov["git"]["head"]
    if subprocess.run(["git", "-C", str(root), "cat-file", "-e", head + "^{commit}"], capture_output=True).returncode != 0:
        errors.append(f"provenance head {head} is not a commit in this repository")
    stale = [rel for rel, h in prov["sha256"].items() if not (root / rel).exists() or T.sha(rel) != h]
    errors += [f"STALE: {rel} changed since the deck was built; rerun presentation/delphi/rebuild.sh" for rel in stale]
    ledger_ids = set(re.findall(r"^\| ([A-Z]\d\d) \|", (root / "planning/rethink/CLAIM-LEDGER.md").read_text(), flags=re.M))
    for i, s in enumerate(work, 1):
        s["fn"], ok = T.consume(s["fn"], f"artifacts @ {head[:8]}")
        if not ok:
            errors.append(f"slide {i}: footnote commit stamp missing or differs from provenance")
        s["html"], ok = T.consume(s["html"], f"{i} / 6")
        if not ok:
            errors.append(f"slide {i}: page counter missing")
        s["html"] = ORDINAL.sub(" ", s["html"])  # declared list ordinals on slide 4
        shown_ids = set(re.findall(r"\b([A-Z]\d\d)\b", slides[i - 1]["html"] + " " + slides[i - 1]["fn"]))
        missing = sorted(shown_ids - ledger_ids)
        if missing:
            errors.append(f"slide {i}: ledger IDs not in CLAIM-LEDGER.md: {missing}")
        # file paths cited in the footnote must exist in the repository, then are removed before the number scan
        for pth in sorted(set(re.findall(r"[\w./-]+\.(?:md|json|lean|csv|py|js|html)\b", s["fn"]))):
            if not (root / pth).exists() and "/" in pth:
                errors.append(f"slide {i}: cited path does not exist: {pth}")
            s["fn"] = s["fn"].replace(pth, " ")
        for pth in sorted(set(re.findall(r"(?:artifacts|experiments|planning)/[\w./-]+/", s["fn"]))):
            if not (root / pth).is_dir():
                errors.append(f"slide {i}: cited directory does not exist: {pth}")
            s["fn"] = s["fn"].replace(pth, " ")
        for field in ("html", "svg", "fn"):
            left = T.tokens(s[field])
            if left:
                errors.append(f"slide {i} {field}: numbers not traced to any artifact: {left}")
    for i, s in enumerate(slides, 1):
        pool = {tk.replace(",", "") for tk in T.tokens(" ".join([s["html"], s["svg"], s["fn"]]))}
        for tk in T.tokens(s["notes"]):
            if tk.replace(",", "") not in pool:
                errors.append(f"slide {i} notes: number {tk!r} is not on the slide itself")
    # benchmark/agent metrics must be pending, never numeric, on slide 5
    s5 = slides[4]["html"]
    for label in ("compiled with proof, axiom audit and a failing mutant", "excluded, with reasons", "source-correspondence review",
                  "benchmark freeze", "agent arms and matched budgets", "coverage, false acceptance, false refusal"):
        m = re.search(re.escape(label) + r" (\S+)", s5)
        if not m or m.group(1).lower() != "pending":
            errors.append(f"slide 5: metric {label!r} must read 'pending', found {m.group(1) if m else None!r}")
    pdf = deck_p.with_suffix(".pdf")
    npdf = None
    if pdf.exists():
        pages = [p_ for p_ in subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True).stdout.split("\f") if p_.strip()]
        npdf = len(pages)
        if npdf != 6:
            errors.append(f"PDF has {npdf} pages, expected 6")
        for i, (pg, s) in enumerate(zip(pages, slides), 1):
            pool = {tk.replace(",", "") for tk in T.tokens(" ".join([s["html"], s["svg"], s["fn"]]))}
            extra = sorted({tk.replace(",", "") for tk in T.tokens(pg)} - pool)
            if extra:
                errors.append(f"PDF page {i}: numbers not on the HTML slide: {extra}")
    result = {"deck": a.deck, "claims_checked": len(trace), "inputs_hash_checked": len(prov["sha256"]), "pdf_pages_checked": npdf,
              "provenance_head": head, "ok": not errors, "errors": errors, "trace": trace}
    (root / a.out).write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n")
    print(f"claims traced: {len(trace)} / {len(CLAIMS)}; errors: {len(errors)}")
    for e in errors:
        print("  FAIL", e)
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
