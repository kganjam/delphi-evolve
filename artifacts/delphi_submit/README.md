# artifacts/delphi_submit

`at5_v1_2_frozen127.json`: output of the committed checker on the frozen Scope Desk v1.2 key (127 items, key sha256 28645a12…), produced by dx-submit because the committed AT5 files at that point were for superseded keys (131 and 128 items).

Command (from a checkout containing `scopedesk/bench/v1_2/FROZEN.md`):
`systemd-run --user --scope -p TasksMax=128 -p MemoryMax=4G -p MemorySwapMax=0 -p RuntimeMaxSec=600 env OMP_NUM_THREADS=2 python3 -m scopedesk.oracles.at5 scopedesk/bench/v1_2 artifacts/delphi_submit/at5_v1_2_frozen127.json` (exit 0, about 2 s).

`presentation/delphi/trace.py` re-runs this command into a temporary file and requires the same per-family totals. The checker and the key were written by different workers on the same team and share a convention document, so agreement is not external validation. If the NCA worker or critic commits their own AT5 file for the frozen key, theirs supersedes this one.
