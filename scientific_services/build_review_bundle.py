"""Assemble the PUBLIC-input review bundle sent to Gemini (spec + prior art + core code + receipts).

Everything included is repository text or a public paper summary: no credentials, no private data.
Code is shown with line numbers so findings can cite file:line and be verified.
Deliberately excluded to keep the review independent: integrator findings, semantics-review note,
and the author's own post-hoc analysis.
"""
import json, subprocess, sys
from pathlib import Path
from .common import sha256_text

CORE = Path("../core")
FILES = ["evolve/data.py", "evolve/graph.py", "evolve/oracle.py", "evolve/policies.py",
         "evolve/model.py", "evolve/replay.py", "evolve/collective.py"]


def numbered(path: Path) -> str:
    return "\n".join(f"{i:4d}| {l}" for i, l in enumerate(path.read_text().splitlines(), 1))


def section(title, body):
    return f"\n\n=================== {title} ===================\n{body}\n"


def plan_excerpt():
    t = Path("planning/PLAN.md").read_text()
    a = t.index("## The bet"); b = t.index("## Twenty ideas")
    c = t.index("## What is new, and what is not"); d = t.index("## Product and demo")
    return t[a:b] + t[c:d]


def protocol_trimmed():
    p = json.loads((CORE / "artifacts/core/protocol.json").read_text())
    p["panel"] = p["panel"][:5] + [f"... {len(p['panel']) - 5} more panel rows omitted ..."]
    return json.dumps(p, indent=1)


def novelty_alde_rows():
    t = Path("../integration/docs/novelty.md").read_text()
    a = t.index("## What is already established"); b = t.index("## What this project proposes")
    return t[a:b]


def build(core_commit):
    parts = []
    parts.append(section("1. PROJECT SPEC (planning/PLAN.md excerpt, verbatim)", plan_excerpt()))
    parts.append(section("2. SCIENTIFIC/INTERFACE CONTRACT (specs/CONTRACT.md, verbatim)", Path("specs/CONTRACT.md").read_text()))
    parts.append(section("3. PRIOR ART as summarised by the project's own novelty note (the authors' reading; verify against sources)", novelty_alde_rows()))
    parts.append(section("4. FROZEN REPLAY PROTOCOL (core artifacts/core/protocol.json; panel truncated)", protocol_trimmed()))
    sm = json.loads(Path("artifacts/services/core_shard_summary_snapshot.json").read_text())
    parts.append(section("5. REPLAY RECEIPT SO FAR (aggregated by an independent script from core's shard files)",
        "Only replay shards whose per-episode `rows` were populated could be aggregated: these are seeds 0-4 for every policy "
        "(shards for seeds 5-19 exist but carry no per-episode rows). 'truth_open' = benchmark truth under the declared edge rule. "
        "Family A has 1 episode/seed, family B has 4 episodes/seed (VFVS -> 4 published targets).\n"
        + json.dumps(sm["summary"], indent=0)))
    code = []
    for f in FILES:
        code.append(f"----- core/{f} -----\n" + numbered(CORE / f))
    parts.append(section(f"6. CORE IMPLEMENTATION (repo commit {core_commit}; line numbers added)", "\n\n".join(code)))
    return "".join(parts)


if __name__ == "__main__":
    commit = subprocess.check_output(["git", "-C", str(CORE), "rev-parse", "--short", "HEAD"], text=True).strip()
    text = build(commit)
    out = Path("artifacts/services/gemini/review_bundle.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    print(len(text), "chars; sha256", sha256_text(text)[:16], "core commit", commit)
