#!/usr/bin/env bash
# The 18:00 PDT cut, in order. Run from a clean checkout of the integrated tree.
#   bash presentation/delphi/final_cut.sh
# 1 rebuild + gate (deck, PDF, PPTX, site, blog, storyboard, 41+ traced claims, tests)
# 2 90-second captioned video  3 rehearsal checklist (cites the video hash)  4 downloadable bundle + sha256 (contains the checklist)
# Timing needs a local Piper voice: run presentation/time_script.py first if the script text changed (see rebuild.sh header).
# Nothing here publishes or uploads anything.
set -euo pipefail
cd "$(dirname "$0")/../.."
bounded() { if command -v systemd-run >/dev/null; then systemd-run --user --scope -q -p TasksMax=128 -p MemoryMax=4G -p MemorySwapMax=0 -p RuntimeMaxSec=600 "$@"; else "$@"; fi; }
bash presentation/delphi/rebuild.sh
bounded python3 presentation/delphi/video/record_delphi_video.py
python3 presentation/delphi/build_rehearsal.py
bounded python3 presentation/delphi/make_bundle.py
echo "FINAL CUT OK at $(git rev-parse --short HEAD) $(date '+%H:%M %Z'); commit presentation/delphi/ and site/delphi/, then report the SHA"
