#!/bin/bash
# Fresh-checkout reproduction. Usage: scripts/reproduce.sh <git-url-or-path> <ref> <workdir> <out.json>
# Every step runs under systemd-run caps (TasksMax=256, MemoryMax=4G, no swap, 600 s) with <=2 threads.
# Writes {step, cmd, exit, seconds} for each step to OUT; exit status is nonzero if any REQUIRED step failed.
set -u
if [ "${DELPHI_REPRODUCE_ACTIVE:-}" = 1 ]; then
  echo "Refusing nested reproduction runner" >&2
  exit 2
fi
export DELPHI_REPRODUCE_ACTIVE=1
URL="$1"; REF="$2"; W="$3"; OUT="$4"
if [ -e "$W" ] || [ -e "$OUT" ] || [ -e "$OUT.lines" ]; then
  echo "Use a new work directory and output path; existing reproduction evidence is never overwritten" >&2
  exit 2
fi
mkdir -p "$W" || exit 2
: > "$OUT.lines"
cap() { systemd-run --user --scope -q -p TasksMax=256 -p MemoryMax=4G -p MemorySwapMax=0 -p RuntimeMaxSec=600 \
        env OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 PATH="$HOME/.elan/bin:$PATH" "$@"; }
FAILED=0
step() { # name required cmd...
  local name="$1" req="$2"; shift 2
  local t0=$(date +%s); "$@" > "$W/$name.log" 2>&1; local rc=$?; local t1=$(date +%s)
  python3 -c "import json,sys;print(json.dumps({'step':sys.argv[1],'required':sys.argv[2]=='1','cmd':sys.argv[5],'exit':int(sys.argv[3]),'seconds':int(sys.argv[4]),'log':sys.argv[1]+'.log'}))" \
     "$name" "$req" "$rc" "$((t1-t0))" "$*" >> "$OUT.lines"
  if [ "$rc" != 0 ] && [ "$req" = 1 ]; then FAILED=1; fi
}
step clone 1 git clone -q "$URL" "$W/repo"
step checkout 1 git -C "$W/repo" checkout -q "$REF"
echo "{\"commit\": \"$(git -C "$W/repo" rev-parse HEAD)\"}" > "$W/commit.json"
cd "$W/repo" || exit 2
step fetch_data 1 cap python3 scripts/fetch_data.py
step venv 1 python3 -m venv "$W/venv"
step pip_install 1 cap "$W/venv/bin/pip" install -q ".[test]"
step audit 1 cap "$W/venv/bin/python" -m evolve audit
step pytest 1 cap "$W/venv/bin/python" -m pytest -q tests
step check_proofs 1 cap python3 scripts/check_proofs.py
step integ_mutants 1 cap python3 -I scripts/integ_mutants.py . "$W/mutwork"
step browser_smoke 0 cap python3 scripts/browser_smoke.py site "$W/shots"
step check_demo 1 python3 -I scripts/check_demo.py site/data/demo.json
python3 - "$OUT" "$W/commit.json" <<'P'
import json,sys
lines=[json.loads(l) for l in open(sys.argv[1]+'.lines')]
c=json.load(open(sys.argv[2]))
json.dump({"commit":c["commit"],"steps":lines,"all_required_passed":all(s["exit"]==0 for s in lines if s["required"])},open(sys.argv[1],'w'),indent=1)
P
exit $FAILED
