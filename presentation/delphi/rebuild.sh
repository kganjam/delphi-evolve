#!/usr/bin/env bash
# Rebuild the Delphi deck, site, blog and storyboard from committed artifacts, then gate.
#   bash presentation/delphi/rebuild.sh
# Gate: number trace (23+ claims, no untraced number, pending stays pending, no stale input hash, PDF matches HTML),
# forbidden-phrase scan, local link check, site assets equal sources.  No network.
# Timing (needs a local Piper voice):  python3 presentation/time_script.py --piper-python <venv python> --voice <voice.onnx> \
#   --notes presentation/delphi/speaker-notes.md --out presentation/delphi/timing.json --cut "all six slides=1,2,3,4,5,6" ...
set -euo pipefail
cd "$(dirname "$0")/../.."
bounded() { if command -v systemd-run >/dev/null; then systemd-run --user --scope -q -p TasksMax=128 -p MemoryMax=4G -p MemorySwapMax=0 -p RuntimeMaxSec=600 "$@"; else "$@"; fi; }
if [ -n "$(git status --porcelain -- artifacts planning/rethink/CLAIM-LEDGER.md experiments tasks/results/rethink-director.json 2>/dev/null)" ] && [ -z "${ALLOW_DIRTY:-}" ]; then
  echo "REFUSING: uncommitted inputs (ALLOW_DIRTY=1 to override, never for the final build)" >&2; exit 3; fi
bounded python3 presentation/delphi/build_deck.py
bounded python3 presentation/export_pdf.py presentation/delphi/deck.html --shots presentation/delphi/screenshots
bounded python3 presentation/delphi/build_site.py
bounded python3 presentation/delphi/trace.py
bounded python3 -m pytest -q -p no:cacheprovider presentation/delphi/tests
echo "DELPHI REBUILD OK at $(git rev-parse --short HEAD)"
