#!/usr/bin/env bash
# One-command deck rebuild from current committed results, with a number-trace gate.
#   bash presentation/rebuild.sh            # rebuild deck.html/.pdf/notes/appendix/provenance + screenshots, then trace + tests
#   CHECK_ONLY=1 bash presentation/rebuild.sh   # rebuild into a scratch dir and only verify; does not touch tracked files
# Exit non-zero on any validation, layout, trace, or test failure. No network.
set -euo pipefail
cd "$(dirname "$0")/.."
bounded() { if command -v systemd-run >/dev/null; then systemd-run --user --scope -q -p TasksMax=128 -p MemoryMax=4G -p MemorySwapMax=0 -p RuntimeMaxSec=600 "$@"; else "$@"; fi; }

if [ -n "$(git status --porcelain -- artifacts site docs/company-hypothesis.md evolve 2>/dev/null)" ] && [ -z "${ALLOW_DIRTY:-}" ]; then
  echo "REFUSING: uncommitted changes under artifacts/ site/ evolve/ docs/company-hypothesis.md; slide numbers must come from committed files (ALLOW_DIRTY=1 to override, never for the final build)" >&2
  git status --porcelain -- artifacts site docs/company-hypothesis.md evolve >&2
  exit 3
fi

if [ -n "${CHECK_ONLY:-}" ]; then
  OUT="$(mktemp -d)"; trap 'rm -rf "$OUT"' EXIT
  mkdir -p "$OUT/presentation"
  cp presentation/deck.css presentation/deck.js "$OUT/presentation/" 2>/dev/null || true
  bounded python3 presentation/build_deck.py --root . --out-dir "$OUT/presentation"
  bounded python3 presentation/trace_numbers.py --root . --deck "$OUT/presentation/deck.html" --out "$OUT/number_trace.json" \
    || { echo "trace failed against scratch build" >&2; exit 1; }
  echo "CHECK_ONLY ok: scratch deck rebuilt from current commit $(git rev-parse --short HEAD) and every number traced"
  exit 0
fi

bounded python3 presentation/build_deck.py --root .
bounded python3 presentation/export_pdf.py presentation/deck.html --shots presentation/screenshots
bounded python3 presentation/export_pptx.py presentation/deck.html
bounded python3 presentation/trace_numbers.py
bounded python3 -m pytest -q -p no:cacheprovider presentation/tests
echo "pages: $(pdfinfo presentation/deck.pdf | awk '/^Pages:/{print $2}')  spoken words: $(grep -o '"spoken_words"[^,]*' presentation/deck.provenance.json)"
echo "REBUILD OK at $(git rev-parse --short HEAD): deck.html deck.pdf deck.pptx speaker-notes.md appendix.md number_trace.json deck.provenance.json"
