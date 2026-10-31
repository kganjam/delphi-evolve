#!/usr/bin/env python3
"""Countdown to the ScienceClaw deadlines, computed from the tz database (not hand-subtracted offsets).

    python3 scripts/submission_countdown.py [--now 2026-10-31T09:00:00-07:00]

Source of the instants: scienceclawhack.ai schedule (Sunday, Nov 1: "1:00 PM End of hacking - final slides due",
2:30 PM presentations, 4:30 PM awards) and the Luma event record, whose event timezone field is America/New_York
(retrieved 2026-10-31).  Boston and Seattle both change clocks at 02:00 local on Nov 1, so Boston goes EDT->EST
(UTC-4 -> UTC-5) and Seattle PDT->PST (UTC-7 -> UTC-8).  The 3 h difference holds at the deadline.
Internal targets are the team's own, not the organizers'.
"""
import argparse
from datetime import datetime
from zoneinfo import ZoneInfo

NY, LA = ZoneInfo("America/New_York"), ZoneInfo("America/Los_Angeles")
EVENTS = [
    # (label, local Boston wall time, official?)
    ("Internal: freeze target recorded in STATUS.md (not official)", datetime(2026, 10, 31, 23, 48, tzinfo=LA), False),
    ("Recommendation (mine): first upload attempt done by here, 3 h margin", datetime(2026, 11, 1, 7, 0, tzinfo=LA), False),
    ("OFFICIAL: end of hacking - final slides due", datetime(2026, 11, 1, 13, 0, tzinfo=NY), True),
    ("OFFICIAL: presentations & judging begin", datetime(2026, 11, 1, 14, 30, tzinfo=NY), True),
    ("OFFICIAL: awards & closing", datetime(2026, 11, 1, 16, 30, tzinfo=NY), True),
]


def fmt(dt, tz):
    return dt.astimezone(tz).strftime("%a %b %d %H:%M %Z")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--now", help="ISO time with offset (testing)")
    a = ap.parse_args()
    now = datetime.fromisoformat(a.now) if a.now else datetime.now(ZoneInfo("UTC"))
    deadline = next(dt for lab, dt, off in EVENTS if lab.startswith('OFFICIAL: end of hacking'))
    assert deadline.astimezone(LA).strftime("%H:%M %Z") == "10:00 PST", "deadline conversion changed; recheck"
    print(f"now: {fmt(now, LA)}  |  {fmt(now, NY)}")
    for label, dt, off in EVENTS:
        d = dt - now
        s = int(d.total_seconds())
        sign = "-" if s < 0 else ""
        s = abs(s)
        print(f"{label}\n    Seattle {fmt(dt, LA)}   Boston {fmt(dt, NY)}   in {sign}{s // 3600}h {s % 3600 // 60:02d}m")


if __name__ == "__main__":
    main()
