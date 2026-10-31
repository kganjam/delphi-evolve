#!/usr/bin/env python3
"""Time the spoken script by actually reading it aloud with a local neural TTS voice (Piper), per slide.

    python3 presentation/time_script.py --piper-python /path/to/venv/bin/python --voice /path/to/en_US-lessac-medium.onnx

Reads presentation/speaker-notes.md, synthesises each slide's text, measures the audio with ffprobe, and
writes presentation/timing.json.  This is a MEASURED machine read-through, not a human rehearsal: a human
may be faster or slower, and the file says so.  A stopwatch rehearsal by the presenter is a separate,
unperformed checklist item.  No network.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent


def seattle_now():
    u = datetime.now(timezone.utc)
    off, name = (-7, "PDT") if u < datetime(2026, 11, 1, 9, 0, tzinfo=timezone.utc) else (-8, "PST")
    return (u + timedelta(hours=off)).strftime("%Y-%m-%d %H:%M ") + name


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--piper-python", required=True)
    ap.add_argument("--voice", required=True, help="Piper .onnx voice (its .onnx.json must sit beside it)")
    ap.add_argument("--notes", default=str(HERE / "speaker-notes.md"))
    ap.add_argument("--out", default=str(HERE / "timing.json"))
    ap.add_argument("--transition-s", type=float, default=1.5, help="assumed silent gap per slide change (an assumption, reported as such)")
    ap.add_argument("--cut", action="append", default=[], help="name=1,2,3 : slides kept in a shorter version (repeatable)")
    ap.add_argument("--limit-s", type=float, default=180.0, help="the team's own budget; the organizers publish no limit")
    a = ap.parse_args()
    notes = Path(a.notes).read_text()
    parts = re.split(r"\n\*\*Slide (\d)\*\* \([^)]*\)\n\n", notes)
    slides = {int(parts[i]): parts[i + 1].strip() for i in range(1, len(parts), 2)}
    assert sorted(slides) == [1, 2, 3, 4, 5, 6], sorted(slides)
    rows = []
    with tempfile.TemporaryDirectory() as td:
        for k in sorted(slides):
            wav = Path(td) / f"s{k}.wav"
            subprocess.run([a.piper_python, "-m", "piper", "-m", a.voice, "-f", str(wav)], input=slides[k], text=True,
                           check=True, capture_output=True, env={"OMP_NUM_THREADS": "2", "PATH": "/usr/bin:/bin"})
            dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(wav)],
                                       check=True, capture_output=True, text=True).stdout)
            w = len(slides[k].split())
            rows.append({"slide": k, "words": w, "seconds": round(dur, 2), "words_per_minute": round(60 * w / dur, 1)})
    speech = sum(r["seconds"] for r in rows)
    total = speech + a.transition_s * 5
    t = 0.0
    for r in rows:
        r["starts_at_s"] = round(t, 1)
        t += r["seconds"] + a.transition_s
    cuts = {}
    cutdef = {"all six slides": [1, 2, 3, 4, 5, 6], "drop slide 2 (landscape)": [1, 3, 4, 5, 6],
              "drop slides 2 and 5": [1, 3, 4, 6], "slides 1, 4, 6 only": [1, 4, 6]}
    if a.cut:
        cutdef = {c.split("=")[0]: [int(x) for x in c.split("=")[1].split(",")] for c in a.cut}
    for name, keep in cutdef.items():
        s = sum(r["seconds"] for r in rows if r["slide"] in keep) + a.transition_s * (len(keep) - 1)
        cuts[name] = {"slides": keep, "seconds": round(s, 1), "mm_ss": f"{int(s // 60)}:{int(s % 60):02d}"}
    out = {
        "measured_at": seattle_now(),
        "method": "Piper neural TTS read-through of presentation/speaker-notes.md, duration from ffprobe on the rendered audio",
        "voice": Path(a.voice).name, "voice_sha256": hashlib.sha256(Path(a.voice).read_bytes()).hexdigest(),
        "spoken_text_sha256": hashlib.sha256("\n".join(slides[k] for k in sorted(slides)).encode()).hexdigest(),
        "spoken_text_note": "hash of the six spoken paragraphs only (the build stamp line is excluded so a rebuild alone does not invalidate the timing)",
        "synthetic_voice": True, "human_rehearsal": None,
        "limit_s": a.limit_s, "limit_source": "team's own three-minute budget; the organizers publish no time limit",
        "transition_s_assumed": a.transition_s,
        "per_slide": rows, "speech_seconds": round(speech, 1), "total_with_transitions_s": round(total, 1),
        "total_mm_ss": f"{int(total // 60)}:{int(total % 60):02d}",
        "margin_to_limit_s": round(a.limit_s - total, 1),
        "total_words": sum(r["words"] for r in rows),
        "cuts": cuts,
        "caveat": "A synthetic voice at its default pace is not the presenter. Demo clicks, applause and questions are not included.",
    }
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("total_mm_ss", "margin_to_limit_s", "total_words", "speech_seconds")}, indent=1))
    for r in rows:
        print(r)
    for k, v in cuts.items():
        print(k, v["mm_ss"])


if __name__ == "__main__":
    main()
