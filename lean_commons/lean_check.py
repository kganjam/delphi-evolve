"""Sound verification for the commons: assemble a file from frozen text + verified commons +
agent text, compile with the Lean kernel (core only), and audit axioms.

The agent controls only (a) helper theorems and (b) the proof term/tactic block of a frozen
target. The target's statement text is inserted by this module from the frozen target file, so a
weakened statement is impossible by construction.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).parent
LEAN_BIN = os.environ.get("LEAN_BIN", str(Path.home() / ".elan/bin/lean"))
ALLOWED_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}
# Anything that could smuggle an unchecked fact, change elaboration globally, or run code.
FORBIDDEN = re.compile(
    r"\b(sorry|admit|native_decide|axiom|unsafe|implemented_by|extern|opaque|macro|macro_rules|syntax|elab|"
    r"notation|infix|infixl|infixr|prefix|postfix|instance|def|abbrev|structure|inductive|class|set_option|"
    r"import|open|namespace|section|end|attribute|run_cmd|initialize|partial|noncomputable|deriving|"
    r"example|local|scoped|private|protected|decreasing_by|termination_by|ofReduceBool|trustCompiler|"
    r"variable|include|omit|universe|mutual|where|unseal|seal|irreducible_def|register_option|declare_syntax_cat|"
    r"add_decl_doc|export|deprecated|builtin_initialize|run_elab|run_meta|elab_rules|open_privacy)\b|#[a-zA-Z_]+|@\[|`\(|\$\{")
THEOREM_RE = re.compile(r"^\s*theorem\s+([A-Za-z_][A-Za-z0-9_'.]*)", re.M)


def strip_comments(src: str) -> str:
    src = re.sub(r"/-.*?-/", "", src, flags=re.S)
    return re.sub(r"--[^\n]*", "", src)


@dataclass
class CheckResult:
    ok: bool
    errors: str = ""
    axioms: dict = field(default_factory=dict)
    forbidden: list = field(default_factory=list)
    seconds: float = 0.0
    sha256: str = ""
    lean_version: str = ""
    raw: str = ""


def helper_structure_error(helpers: str) -> str:
    """Helpers must be a sequence of top-level `theorem name ...` declarations and nothing else."""
    body = strip_comments(helpers)
    for line in body.splitlines():
        if line.strip() and not line[0].isspace():
            if not re.match(r"theorem\s+[A-Za-z_][A-Za-z0-9_']*\b", line):
                return f"helper text must consist only of top-level `theorem name ...` declarations; offending line starts: {line[:40]!r}"
    return ""


FID_CMD = '''
open Lean Elab Command Term in
elab "#fid " n:ident " : " s:term : command => liftTermElabM do
  let ty ← instantiateMVars (← elabType s)
  Term.synthesizeSyntheticMVarsNoPostponing
  let ty ← instantiateMVars ty
  let ci ← getConstInfo n.getId
  if ci.type == ty then logInfo m!"FID_OK {n.getId}" else logInfo m!"FID_MISMATCH {n.getId}"
'''


def fidelity_suffix(target_id: str, statement: str) -> str:
    """Appended by the trusted checker (never by an agent): the target's ELABORATED type must equal the frozen statement's."""
    return FID_CMD + f"\n#fid {target_id} : {statement}\n"


def lean_version() -> str:
    return subprocess.run([LEAN_BIN, "--version"], capture_output=True, text=True).stdout.strip()


def theorem_names(src: str) -> list[str]:
    return THEOREM_RE.findall(strip_comments(src))


def run_lean(source: str, timeout: int = 90) -> tuple[int, str, float]:
    import time
    with tempfile.TemporaryDirectory(prefix="lean-") as d:
        p = Path(d) / "Check.lean"
        p.write_text(source)
        t0 = time.time()
        try:
            r = subprocess.run([LEAN_BIN, "-j2", str(p)], capture_output=True, text=True, timeout=timeout, cwd=d)
            return r.returncode, (r.stdout + r.stderr).replace(d, "<tmp>"), time.time() - t0
        except subprocess.TimeoutExpired:
            return 124, f"error: lean timed out after {timeout}s", time.time() - t0


def parse_axioms(output: str) -> dict:
    out = {}
    for m in re.finditer(r"'([^']+)' depends on axioms: \[(.*?)\]", output):
        out[m.group(1)] = sorted(a.strip() for a in m.group(2).split(",") if a.strip())
    for m in re.finditer(r"'([^']+)' does not depend on any axioms", output):
        out[m.group(1)] = []
    return out


def check_source(source: str, audit: list[str], *, scan_text: str = "", timeout: int = 90,
                 fidelity: tuple[str, str] | None = None) -> CheckResult:
    """Compile `source`; `audit` names get `#print axioms`; `scan_text` (agent-authored text) is
    scanned for forbidden tokens."""
    bad = sorted(set(m.group(0) for m in FORBIDDEN.finditer(strip_comments(scan_text))))
    if bad:
        return CheckResult(False, errors=f"forbidden token(s) in submitted text: {bad}", forbidden=bad, sha256=hashlib.sha256(source.encode()).hexdigest())
    full = source + "\n" + "\n".join(f"#print axioms {n}" for n in audit) + "\n"
    if fidelity is not None:
        full += fidelity_suffix(*fidelity)
    rc, out, secs = run_lean(full, timeout)
    errs = "\n".join(l for l in out.splitlines() if "error" in l.lower() or l.startswith(" ") and "error" in out)
    has_error = rc != 0 or "error" in out.lower().replace("'", "")
    axioms = parse_axioms(out)
    unexpected = {n: a for n, a in axioms.items() if set(a) - ALLOWED_AXIOMS}
    missing = [n for n in audit if n not in axioms]
    fid_ok = True
    if fidelity is not None:
        fid_ok = f"FID_OK {fidelity[0]}" in out
    ok = (rc == 0) and not has_error and not unexpected and not missing and fid_ok
    msg = ""
    if not ok:
        msg = out if has_error else ""
        if fidelity is not None and not fid_ok:
            msg += "\nfidelity check failed: elaborated type of the target differs from the frozen statement"
        if unexpected:
            msg += f"\nunexpected axioms: {unexpected}"
        if missing and not has_error:
            msg += f"\naxiom audit missing for: {missing}"
    return CheckResult(ok, errors=msg[:3500], axioms=axioms, seconds=secs,
                       sha256=hashlib.sha256(full.encode()).hexdigest(), lean_version=lean_version(), raw=out)


def load_targets() -> list[dict]:
    return json.loads((HERE / "targets" / "targets.json").read_text())


def load_defs() -> str:
    return (HERE / "targets" / "Defs.lean").read_text()


def render_signature(name: str, statement: str) -> str:
    return f"theorem {name} : {statement}"


def assemble(defs: str, library: list[dict], helpers: str, target_id: str | None, target_statement: str | None,
             proof: str | None) -> str:
    """defs + verified library (statement+proof each) + agent helpers + frozen target with agent proof."""
    parts = ["import Lean", defs, ""]
    for e in library:
        parts.append(e["source"])
        parts.append("")
    if helpers.strip():
        parts.append(helpers.strip())
        parts.append("")
    if target_id is not None:
        parts.append(f"theorem {target_id} : {target_statement} := {proof.strip()}")
    return "\n".join(parts) + "\n"
