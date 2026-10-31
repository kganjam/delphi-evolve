#!/usr/bin/env bash
# Runs a command against a PRIVATE throwaway PostgreSQL 16 cluster (own socket, no network listener), modelled on delphi-frontier's
# scripts/test_postgres.sh. Frontier source is READ from $FRONTIER_SRC (an extracted `git archive` of a pinned commit); nothing is written there.
# Run only inside the bounded scope:  systemd-run --user --scope -p TasksMax=128 -p MemoryMax=4G -p MemorySwapMax=0 -p RuntimeMaxSec=600 bash scripts/frontier_pub_pg.sh <cmd...>
set -euo pipefail
test -n "${INVOCATION_ID:-}" || { echo 'Run in the documented systemd scope.' >&2; exit 2; }
test "$(id -u)" != 0 || { echo 'Run as an unprivileged user.' >&2; exit 2; }
: "${FRONTIER_SRC:?set FRONTIER_SRC to a directory containing frontier/}"
bin="${FRONTIER_PG_BIN:-/usr/lib/postgresql/16/bin}"
tmp="$(mktemp -d /tmp/frontier-pub-pg.XXXXXXXX)"; chmod 700 "$tmp"
cleanup() { "$bin/pg_ctl" -D "$tmp/data" -m immediate -w stop >/dev/null 2>&1 || true; rm -rf -- "$tmp"; }
trap cleanup EXIT INT TERM
mkdir "$tmp/socket"
"$bin/initdb" -D "$tmp/data" --auth-local=trust --auth-host=reject --no-locale --encoding=UTF8 > "$tmp/init.log"
"$bin/pg_ctl" -D "$tmp/data" -l "$tmp/pg.log" -o "-k $tmp/socket -c listen_addresses='' -c max_connections=20 -c shared_buffers=32MB -c max_worker_processes=2 -c max_parallel_workers=2" -w start >/dev/null
export FRONTIER_TEST_DSN="host=$tmp/socket dbname=postgres"
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$FRONTIER_SRC:$PWD" OMP_NUM_THREADS=1
"$@"
