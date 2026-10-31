"""Per-request Lean 4 receipt for 1-D linear-instability verdicts.

Generates a Lean file that imports the repository's TuringScope library (turing_scope/lean) and proves, for the
caller's own integer-scaled model and domain, the COMPLETE classification

    forall n : Nat, (not ModeStable m p s n)  <->  n in U

where U is the unstable list found by the exact-rational engine. The tail of the proof is the generic theorem
TuringScope.neumann_tail_hurwitz; the finite head is closed by `decide`.  Lean's kernel then re-derives the
engine's answer from scratch: a bug in engine.py cannot silently pass.

Modelling steps that Lean does NOT check (stated in every receipt):
  * Routh-Hurwitz (ModeStable := trace<0 and det>0) as the meaning of 'linearly stable';
  * rational J, D are multiplied by a common positive integer (signs of det/trace of J - qD are unchanged);
  * dirichlet = neumann spectrum without the constant mode (mode 0 is stable since tr J<0, det J>0 -> same unstable set);
    periodic on length L = neumann spectrum on length L/2 (q_n = (2 n pi/L)^2 = (n pi/(L/2))^2);
  * the PDE itself and the physical meaning of the declared Jacobian.
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import tempfile
import time
from fractions import Fraction
from math import lcm
from pathlib import Path

LEAN_DIR = Path(__file__).resolve().parent.parent / "turing_scope" / "lean"
MAX_N0 = 300
TIMEOUT = int(os.environ.get("FALSIFY_LEAN_TIMEOUT", "120"))
ALLOWED_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}


def _wrapper():
    w = os.environ.get("FALSIFY_LEAN_WRAPPER")
    if w is not None:
        return w.split() if w.strip() else []
    if shutil.which("systemd-run"):
        return ["systemd-run", "--user", "--scope", "-q", "-p", "TasksMax=128", "-p", "MemoryMax=4G",
                "-p", "MemorySwapMax=0", "-p", f"RuntimeMaxSec={TIMEOUT}"]
    return ["timeout", str(TIMEOUT)]


def build_source(J, D, boundary, r: Fraction, unstable_idx: list[int]):
    """-> (lean_source, meta) or raises ValueError('...') when outside Lean receipt scope."""
    rp = r / 2 if boundary == "periodic" else r           # Neumann-equivalent length / pi
    den = lcm(*[Fraction(x).denominator for row in J for x in row], *[Fraction(x).denominator for x in D])
    a, b, c, d = [int(Fraction(x) * den) for row in J for x in row]
    Du, Dv = [int(Fraction(x) * den) for x in D]
    p, s = rp.numerator, rp.denominator
    S = a * Dv + d * Du
    n0 = 0
    while S * p * p > Du * Dv * (n0 * n0 * s * s):
        n0 += 1
        if n0 > MAX_N0:
            raise ValueError(f"first tail mode exceeds the Lean receipt cap ({MAX_N0})")
    U = sorted(int(i) for i in unstable_idx)
    if any(u >= n0 for u in U):
        raise ValueError("internal inconsistency: unstable mode at or beyond the tail cutoff")
    dec = "decide +kernel" if n0 > 40 else "decide"
    src = f"""import TuringScope
open TuringScope
/-! Auto-generated receipt. boundary={boundary}; Neumann-equivalent L=({p}/{s})*pi; J,D scaled by {den}. -/
def mdl : Model := ⟨{a}, {b}, {c}, {d}, {Du}, {Dv}⟩
def U : List Nat := {U}
theorem tail : ∀ n : Nat, {n0} ≤ n → ModeStable mdl {p} {s} n :=
  neumann_tail_hurwitz mdl (by decide) (by decide) (by decide) (by decide) (by decide) (by decide) {n0} (by decide)
theorem head : ∀ n : Nat, n < {n0} → (¬ ModeStable mdl {p} {s} n ↔ n ∈ U) := by {dec}
theorem U_lt : ∀ k ∈ U, k < {n0} := by {dec}
theorem classification : ∀ n : Nat, (¬ ModeStable mdl {p} {s} n ↔ n ∈ U) := by
  intro n
  by_cases h : n < {n0}
  · exact head n h
  · have h' := tail n (by omega)
    constructor
    · intro hn; exact absurd h' hn
    · intro hm; exact absurd (U_lt n hm) h
#print axioms classification
"""
    meta = {"scaling_factor": den, "neumann_equivalent_length_over_pi": f"{p}/{s}", "tail_cutoff_n0": n0,
            "claimed_unstable_modes": U}
    return src, meta


def run(src: str) -> dict:
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix="falsify-lean-") as td:
        f = Path(td) / "Receipt.lean"
        f.write_text(src)
        try:
            p = subprocess.run(_wrapper() + ["lake", "env", "lean", str(f)], cwd=LEAN_DIR, capture_output=True, text=True,
                               timeout=TIMEOUT + 10)
            code, out = p.returncode, (p.stdout + p.stderr)
        except subprocess.TimeoutExpired:
            code, out = 124, "timeout"
        except FileNotFoundError as e:
            return {"status": "unavailable", "detail": f"lean toolchain not found: {e}"}
    axioms = sorted({x.strip() for g in re.findall(r"\[(.*?)\]", out) for x in g.split(",") if x.strip()})
    forbidden = [t for t in ("sorry", "native_decide", "axiom ", "admit") if t in re.sub(r"/-.*?-/", "", src, flags=re.S)]
    ok = code == 0 and "error" not in out.lower() and set(axioms) <= ALLOWED_AXIOMS and not forbidden
    return {"status": "checked" if ok else "failed", "exit": code, "seconds": round(time.time() - t0, 2),
            "axioms": axioms, "output_tail": out.strip().splitlines()[-6:],
            "source_sha256": hashlib.sha256(src.encode()).hexdigest()}


def lean_version() -> str:
    try:
        return subprocess.run(["lean", "--version"], capture_output=True, text=True, timeout=20).stdout.strip()
    except Exception:
        return "unknown"
