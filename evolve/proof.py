"""Certificate construction, strict validation and Lean emission for Darwin's Bridge.

TRUST MODEL (read this first)
* The authority is the Lean 4 kernel: ``lean/DarwinBridge/*.lean`` defines the Boolean
  checkers ``routeCertB`` / ``blockedCertB`` and proves (``routeCert_sound``,
  ``blockedCert_sound``) that acceptance implies the mathematical statements.
* Everything in THIS file is untrusted tooling: it finds candidate routes/cuts (search),
  converts source text to exact scaled integers, emits Lean source and runs the compiler.
  ``check_certificate_python`` is a *differential-testing mirror* of the Lean checker; it is
  not a proof and is never used as a certificate.
* No floating point is used to decide anything.  Source values are parsed from their decimal
  text into ``fractions.Fraction``; NaN, inf, empty or non-decimal inputs are rejected.

Scope: the declared graph is the full 20^4 library graph of four-site amino-acid genotypes
with single-substitution adjacency (stop-containing genotypes excluded).  A "blocked"
certificate is a statement about that finite graph under an ASSUMED interval-containment
premise; it is not a statement about sequence space or biology.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import deque
from fractions import Fraction
from pathlib import Path
from typing import Iterable, Mapping, Optional, Sequence

ALPHABET = "ACDEFGHIKLMNPQRSTVWY"  # index <-> one-letter code used by the Lean Geno encoding
POSITIONS = ("AA1", "AA2", "AA3", "AA4")
SCHEMA = "darwin-bridge-proof-cert/1"
THEOREM_ROUTE = "DarwinBridge.routeCert_sound"
THEOREM_BLOCKED = "DarwinBridge.blockedCert_sound"
ASSUMED_BOUND_LABEL = (
    "ASSUMED sensitivity bound (delta): not a confidence interval; two replicates cannot "
    "support simultaneous 95% bounds across 159,129 variants"
)
_DECIMAL = re.compile(r"^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$")
REPO_ROOT = Path(__file__).resolve().parents[1]
LEAN_DIR = REPO_ROOT / "lean"


class ProofInputError(ValueError):
    """Input is not admissible (NaN, missing, non-decimal, malformed genotype, ...)."""


class CannotCertify(Exception):
    """No certificate exists within the stated scope/bound/caps (an honest negative)."""


# --------------------------------------------------------------------------- exact numbers
def parse_exact(value) -> Fraction:
    """Exact rational from decimal text / int / Fraction / finite float (via shortest repr)."""
    if isinstance(value, bool):
        raise ProofInputError("boolean is not a number")
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ProofInputError(f"non-finite float {value!r}")
        value = repr(value)
    if not isinstance(value, str):
        raise ProofInputError(f"unsupported numeric type {type(value).__name__}")
    text = value.strip()
    if not text or not _DECIMAL.match(text):
        raise ProofInputError(f"not a finite decimal literal: {value!r}")
    return Fraction(text)


def decimal_exponent(x: Fraction) -> Optional[int]:
    """Smallest k with x*10^k an integer, or None if x is not a terminating decimal."""
    d = x.denominator
    a = b = 0
    while d % 2 == 0:
        d //= 2
        a += 1
    while d % 5 == 0:
        d //= 5
        b += 1
    return max(a, b) if d == 1 else None


def scaled_exact(x: Fraction, k: int) -> int:
    v = x * (10 ** k)
    if v.denominator != 1:
        raise ProofInputError(f"{x} is not exactly representable at scale 10^{k}")
    return v.numerator


def floor_scaled(x: Fraction, k: int) -> int:
    return math.floor(x * (10 ** k))


def ceil_scaled(x: Fraction, k: int) -> int:
    return math.ceil(x * (10 ** k))


# --------------------------------------------------------------------------- genotype graph
def genotype_indices(g: str) -> tuple[int, int, int, int]:
    if not isinstance(g, str) or len(g) != 4 or any(c not in ALPHABET for c in g):
        raise ProofInputError(f"genotype must be four of {ALPHABET}: {g!r}")
    return tuple(ALPHABET.index(c) for c in g)  # type: ignore[return-value]


def neighbors(g: str) -> list[str]:
    """All 76 single-substitution neighbours in the declared 20^4 graph."""
    genotype_indices(g)
    out = []
    for p in range(4):
        for c in ALPHABET:
            if c != g[p]:
                out.append(g[:p] + c + g[p + 1:])
    return out


def adjacent(g: str, h: str) -> bool:
    genotype_indices(g), genotype_indices(h)
    return sum(a != b for a, b in zip(g, h)) == 1


# --------------------------------------------------------------------------- source data
def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_trpb_observations(path, col1: str = "mu_1-bg", col2: str = "mu_2-bg"):
    """Read the original summary_AA.csv. Returns (observations, counts).

    observations: genotype -> (replicate_1_text, replicate_2_text), exact source text.
    Only rows with '# Stop' == 0 are in the declared graph.  Rows whose replicate fields are
    empty/NaN/non-decimal are NOT silently dropped into the table: they are counted and
    left UNKNOWN (absent), which can never support a certificate.
    """
    obs: dict[str, tuple[str, str]] = {}
    counts = {"rows": 0, "stop_containing": 0, "non_decimal_unknown": 0, "measured_nonstop": 0}
    with open(path, newline="") as fh:
        reader = csv.DictReader(fh)
        for col in ("AAs", "# Stop", col1, col2):
            if col not in (reader.fieldnames or []):
                raise ProofInputError(f"{path}: missing column {col!r}")
        for row in reader:
            counts["rows"] += 1
            if float(row["# Stop"]) != 0.0:
                counts["stop_containing"] += 1
                continue
            g = row["AAs"]
            genotype_indices(g)
            r1, r2 = row[col1].strip(), row[col2].strip()
            try:
                parse_exact(r1), parse_exact(r2)
            except ProofInputError:
                counts["non_decimal_unknown"] += 1
                continue
            if g in obs:
                raise ProofInputError(f"duplicate genotype row {g}")
            obs[g] = (r1, r2)
            counts["measured_nonstop"] += 1
    return obs, counts


# --------------------------------------------------------------------------- instance model
class Instance:
    """Exact scaled-integer instance: observations + assumed sensitivity bound."""

    def __init__(self, obs: Mapping[str, tuple], delta, scale_exponent: Optional[int] = None,
                 outward: bool = False):
        d = parse_exact(delta)
        if d < 0:
            raise ProofInputError("delta must be >= 0")
        parsed = {}
        for g, (a, b) in obs.items():
            genotype_indices(g)
            parsed[g] = (parse_exact(a), parse_exact(b))
        need = []
        for x in [d] + [v for pair in parsed.values() for v in pair]:
            e = decimal_exponent(x)
            need.append(e)
        if scale_exponent is None:
            if any(e is None for e in need):
                if not outward:
                    raise ProofInputError("non-decimal rational input; pass outward=True and an explicit scale_exponent")
                raise ProofInputError("outward mode requires an explicit scale_exponent")
            scale_exponent = max(need) if need else 0
        k = scale_exponent
        if k < 0 or k > 60:
            raise ProofInputError("scale_exponent out of range")
        self.k = k
        self.outward = outward
        self.rounded = 0
        self.delta_text = str(delta)
        if any(e is None or e > k for e in [decimal_exponent(d)]):
            if not outward:
                raise ProofInputError("delta not exact at this scale")
            self.delta = ceil_scaled(d, k)  # outward: larger assumed bound is safe for route? see note
            self.rounded += 1
        else:
            self.delta = scaled_exact(d, k)
        self.table: dict[str, tuple[int, int]] = {}
        self.text: dict[str, tuple[str, str]] = {}
        for g, (a, b) in parsed.items():
            lo, hi = min(a, b), max(a, b)
            exact = all(decimal_exponent(x) is not None and decimal_exponent(x) <= k for x in (lo, hi))
            if exact:
                ia, ib = scaled_exact(a, k), scaled_exact(b, k)
            elif outward:
                # envelope widened outward: r1 = floor(min), r2 = ceil(max)
                ia, ib = floor_scaled(lo, k), ceil_scaled(hi, k)
                self.rounded += 1
            else:
                raise ProofInputError(f"{g}: value not exact at scale 10^{k}")
            self.table[g] = (ia, ib)
            self.text[g] = (str(obs[g][0]), str(obs[g][1]))

    def bounds(self, g: str) -> Optional[tuple[int, int]]:
        if g not in self.table:
            return None
        a, b = self.table[g]
        return min(a, b) - self.delta, max(a, b) + self.delta

    def dominates(self, u: str, v: str) -> bool:  # hi(u) <= lo(v)
        bu, bv = self.bounds(u), self.bounds(v)
        return bu is not None and bv is not None and bu[1] <= bv[0]

    def certified_down(self, u: str, v: str) -> bool:  # hi(v) < lo(u)
        bu, bv = self.bounds(u), self.bounds(v)
        return bu is not None and bv is not None and bv[1] < bu[0]


# --------------------------------------------------------------------------- finders (untrusted)
def find_route(inst: Instance, start: str, target: str, max_nodes: int = 2_000_000) -> list[str]:
    """Shortest sequence of certified-dominance single-substitution steps, or CannotCertify."""
    genotype_indices(start), genotype_indices(target)
    if start == target:
        raise CannotCertify("start == target")
    if start not in inst.table or target not in inst.table:
        raise CannotCertify("start or target has no declared interval (unknown)")
    prev = {start: None}
    q = deque([start])
    while q and len(prev) < max_nodes:
        u = q.popleft()
        if u == target:
            break
        for v in neighbors(u):
            if v not in prev and inst.dominates(u, v):
                prev[v] = u
                q.append(v)
    if target not in prev:
        raise CannotCertify(f"no certified route from {start} to {target} at delta={inst.delta_text} "
                            f"(explored {len(prev)} vertices)")
    path, x = [], target
    while x is not None:
        path.append(x)
        x = prev[x]
    return path[::-1]


def find_blocked_set(inst: Instance, start: str, target: str, cap: int = 400) -> list[str]:
    """Smallest-by-closure set S ∋ start whose every outgoing edge is certified descending.

    Neighbours that are unknown or not certified lower are pulled into S (they are *possible*
    non-decreasing moves).  Fails with CannotCertify if S would reach the target or exceed cap.
    """
    genotype_indices(start), genotype_indices(target)
    if start == target:
        raise CannotCertify("start == target")
    S = [start]
    seen = {start}
    i = 0
    while i < len(S):
        u = S[i]
        i += 1
        for v in neighbors(u):
            if v in seen or inst.certified_down(u, v):
                continue
            if v == target:
                raise CannotCertify(f"target {target} is possibly reachable from {start} (edge {u}->{v} not certified descending)")
            if len(S) >= cap:
                raise CannotCertify(f"closure exceeds cap={cap}")
            seen.add(v)
            S.append(v)
    return S


# --------------------------------------------------------------------------- certificates
def _canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def certificate_digest(cert: Mapping) -> str:
    body = {k: v for k, v in cert.items() if k != "certificate_sha256"}
    return hashlib.sha256(_canonical(body).encode()).hexdigest()


def _base_certificate(kind, inst: Instance, listed: Iterable[str], source: Mapping, label: str,
                      start: str, target: str) -> dict:
    listed = sorted(set(listed))
    cert = {
        "schema": SCHEMA,
        "kind": kind,
        "label": label,
        "theorem": THEOREM_ROUTE if kind == "route" else THEOREM_BLOCKED,
        "graph_scope": {
            "name": "four-site-20^4-single-substitution",
            "vertices": "all 20^4 = 160000 four-letter genotypes over ACDEFGHIKLMNPQRSTVWY (no stop codon)",
            "edges": "two genotypes differing at exactly one of the four positions",
            "positions": list(POSITIONS),
            "alphabet": ALPHABET,
            "not_claimed": "nothing about sequence space beyond these four sites, nor about biology",
        },
        "source": dict(source),
        "scale_exponent": inst.k,
        "delta_scaled": inst.delta,
        "delta_decimal": inst.delta_text,
        "delta_status": ASSUMED_BOUND_LABEL,
        "outward_rounded_values": inst.rounded,
        "interval_rule": "[min(r1,r2) - delta, max(r1,r2) + delta] on scaled exact integers",
        "start": start,
        "target": target,
        "table": [
            {"genotype": g, "idx": list(genotype_indices(g)), "r1": inst.table[g][0],
             "r2": inst.table[g][1], "r1_text": inst.text[g][0], "r2_text": inst.text[g][1]}
            for g in listed
        ],
        "assumptions": [
            "A1 (interval containment): the true scaled growth value of every LISTED genotype lies in "
            "[min(r1,r2)-delta, max(r1,r2)+delta]. This is an assumption about the assay, not proved.",
            "A2 (scope): genotypes not listed, including imputed or stop-containing ones, are UNKNOWN; "
            "the theorem never constrains them and no certificate relies on them except as members of S.",
            "A3 (graph): only the declared four-site single-substitution graph; absence of a route here "
            "is not absence of a biological route.",
        ],
        "limitations": [
            "delta is an assumed sensitivity bound, not a statistical confidence bound.",
            "Python text->integer conversion is checked by evolve.proof.verify_against_source, not by Lean.",
            "Growth in the E. coli selection assay is a proxy for function, not kcat/KM.",
            "Fitness values are real measurements only at listed rows; this certificate is descriptive "
            "(full-data), not a prediction benchmark.",
        ],
    }
    return cert


def build_route_certificate(inst: Instance, start: str, target: str, source: Mapping,
                            label: str = "route") -> dict:
    route = find_route(inst, start, target)
    cert = _base_certificate("route", inst, route, source, label, start, target)
    cert["route"] = route
    cert["certificate_sha256"] = certificate_digest(cert)
    return cert


def build_blocked_certificate(inst: Instance, start: str, target: str, source: Mapping,
                              label: str = "blocked", cap: int = 400) -> dict:
    S = find_blocked_set(inst, start, target, cap=cap)
    needed = set(S)
    for u in S:
        needed.update(neighbors(u))
    # list only vertices with declared intervals; all others stay unknown (and therefore can
    # only be in S, otherwise the Lean checker rejects)
    listed = [g for g in needed if g in inst.table]
    if start not in inst.table:
        raise CannotCertify("start has no declared interval")
    cert = _base_certificate("blocked", inst, listed, source, label, start, target)
    cert["closed_set"] = S
    cert["crossing_edges_checked"] = sum(len(neighbors(u)) for u in S)
    cert["certificate_sha256"] = certificate_digest(cert)
    return cert


# --------------------------------------------------------------------------- python mirror
def check_certificate_python(cert: Mapping) -> tuple[bool, str]:
    """Differential-testing mirror of Lean's routeCertB/blockedCertB (exact integers only).

    NOT authoritative.  Returns (accepted, reason).
    """
    try:
        delta = cert["delta_scaled"]
        if not isinstance(delta, int) or isinstance(delta, bool) or delta < 0:
            return False, "delta must be a non-negative integer"
        tbl = {}
        for e in cert["table"]:
            g = e["genotype"]
            genotype_indices(g)
            if g in tbl:
                return False, f"duplicate key {g}"
            if not all(isinstance(e[k], int) and not isinstance(e[k], bool) for k in ("r1", "r2")):
                return False, "non-integer observation"
            tbl[g] = (e["r1"], e["r2"])
        bnd = lambda g: None if g not in tbl else (min(tbl[g]) - delta, max(tbl[g]) + delta)
        s, t = cert["start"], cert["target"]
        genotype_indices(s), genotype_indices(t)
        if s == t:
            return False, "start == target"
        if cert["kind"] == "route":
            r = cert["route"]
            if not r or r[0] != s or r[-1] != t:
                return False, "route endpoints"
            for u, v in zip(r, r[1:]):
                if not adjacent(u, v):
                    return False, f"non-adjacent step {u}->{v}"
                bu, bv = bnd(u), bnd(v)
                if bu is None or bv is None:
                    return False, f"unknown vertex at step {u}->{v}"
                if not bu[1] <= bv[0]:
                    return False, f"dominance fails {u}->{v}"
            return True, "route accepted"
        S = cert["closed_set"]
        for g in S:
            genotype_indices(g)
        if s not in S or t in S:
            return False, "s must be in S and t not"
        for u in S:
            for v in neighbors(u):
                if v in S:
                    continue
                bu, bv = bnd(u), bnd(v)
                if bu is None or bv is None or not bv[1] < bu[0]:
                    return False, f"open cut edge {u}->{v}"
        return True, "blocked accepted"
    except (KeyError, ProofInputError, TypeError) as exc:
        return False, f"malformed: {exc}"


def verify_against_source(cert: Mapping, csv_path, col1: str = "mu_1-bg", col2: str = "mu_2-bg",
                          observations: Optional[Mapping] = None) -> dict:
    """Tie the certificate to the data: file hash, every table row's exact text, exact scaling,
    and the declared-unknown status of absent genotypes.  Raises ProofInputError on mismatch."""
    actual = sha256_file(csv_path)
    if actual != cert["source"]["sha256"]:
        raise ProofInputError(f"source sha256 mismatch: {actual} != {cert['source']['sha256']}")
    obs = observations if observations is not None else load_trpb_observations(csv_path, col1, col2)[0]
    k = cert["scale_exponent"]
    for e in cert["table"]:
        g = e["genotype"]
        if g not in obs:
            raise ProofInputError(f"{g} is not a measured non-stop row in the source")
        if obs[g] != (e["r1_text"], e["r2_text"]):
            raise ProofInputError(f"{g} text mismatch with source")
        if e["idx"] != list(genotype_indices(g)):
            raise ProofInputError(f"{g} index mismatch")
        if not cert.get("outward_rounded_values"):
            if scaled_exact(parse_exact(e["r1_text"]), k) != e["r1"] or scaled_exact(parse_exact(e["r2_text"]), k) != e["r2"]:
                raise ProofInputError(f"{g} scaled value mismatch")
    if certificate_digest(cert) != cert["certificate_sha256"]:
        raise ProofInputError("certificate digest mismatch")
    return {"source_sha256": actual, "rows_checked": len(cert["table"])}


# --------------------------------------------------------------------------- Lean emission
def _int(n: int) -> str:
    return f"({n} : Int)" if n < 0 else str(n)


def _geno(g: str) -> str:
    a, b, c, d = genotype_indices(g)
    return f"⟨{a}, {b}, {c}, {d}⟩"


def module_name(cert: Mapping) -> str:
    label = re.sub(r"[^A-Za-z0-9]", "", cert["label"].title().replace("_", ""))
    if not label or not label[0].isalpha():
        raise ProofInputError("label must start with a letter")
    return f"DarwinBridge.Certs.{label}"


def render_lean(cert: Mapping) -> str:
    """Lean module with the instance and `decide +kernel` proofs of acceptance.

    Contains only data and the theorem applications; all logic is in Core/Geno/Checker.
    """
    kind = cert["kind"]
    mod = module_name(cert)
    rows = []
    for e in cert["table"]:
        rows.append(f"  -- {e['genotype']}\n  ({_geno(e['genotype'])}, {_int(e['r1'])}, {_int(e['r2'])})")
    L = [
        f"import DarwinBridge.Checker",
        "",
        f"/-! GENERATED by evolve/proof.py from certificate {cert.get('certificate_sha256', '?')}.",
        f"    Do not edit; regenerate with `python scripts/check_proofs.py --regenerate`.",
        f"    kind: {kind}; label: {cert['label']}",
        f"    source sha256: {cert['source'].get('sha256')}",
        f"    scale: values are exact integers x 10^{cert['scale_exponent']}; delta is ASSUMED. -/",
        "",
        f"namespace {mod}",
        "open DarwinBridge",
        "",
        f'def sourceSha256 : String := "{cert["source"].get("sha256")}"',
        f'def certificateSha256 : String := "{cert.get("certificate_sha256", "")}"',
        f"def scaleExponent : Nat := {cert['scale_exponent']}",
        f"def delta : Int := {_int(cert['delta_scaled'])}",
        f"/-- {cert['start']} -/",
        f"def start : Geno := {_geno(cert['start'])}",
        f"/-- {cert['target']} -/",
        f"def target : Geno := {_geno(cert['target'])}",
        "def tbl : Table := [",
        ",\n".join(rows),
        "]",
    ]
    if kind == "route":
        L += [
            f"/-- {' -> '.join(cert['route'])} -/",
            "def route : List Geno := [",
            ",\n".join(f"  {_geno(g)}" for g in cert["route"]),
            "]",
            "",
            "/-- The kernel evaluates the Boolean checker on this concrete dataset instance. -/",
            "theorem cert_ok : routeCertB delta tbl route start target = true := by decide +kernel",
            "",
            "/-- Conditional soundness for THIS instance: under the (assumed) sensitivity containment,",
            "every true-value assignment is non-decreasing along the route. -/",
            "theorem instance_sound {α : Type} [LE α] [LT α] (ι : Int → α) (hα : OrderLaws α)",
            "    (hι : Embedding ι) (F : Geno → α) (hF : SensitivityAssumption ι delta tbl F) :",
            "    NDRoute Adj F route ∧ NDReach Adj F start target ∧ F start ≤ F target ∧",
            "      (∀ x, x ∈ route → F start ≤ F x) :=",
            "  routeCert_sound hα hι cert_ok hF",
        ]
    else:
        L += [
            f"/-- members: {', '.join(cert['closed_set'])} -/",
            "def closedSet : List Geno := [",
            ",\n".join(f"  {_geno(g)}" for g in cert["closed_set"]),
            "]",
            "",
            "/-- The kernel evaluates the Boolean checker, enumerating all 76 neighbours of each member. -/",
            "theorem cert_ok : blockedCertB delta tbl closedSet start target = true := by decide +kernel",
            "",
            "/-- Conditional soundness for THIS instance: under the (assumed) sensitivity containment,",
            "no non-decreasing path exists from `start` to `target` in the full 20^4 graph. -/",
            "theorem instance_sound {α : Type} [LE α] [LT α] (ι : Int → α) (hα : OrderLaws α)",
            "    (hι : Embedding ι) (F : Geno → α) (hF : SensitivityAssumption ι delta tbl F) :",
            "    ¬ NDReach Adj F start target :=",
            "  blockedCert_sound hα hι cert_ok hF",
        ]
    L += ["", f"end {mod}", ""]
    return "\n".join(L)


def render_audit(mods: Sequence[str]) -> str:
    L = ["import DarwinBridge.Checker"] + [f"import {m}" for m in mods] + ["", "-- axiom audit (parsed by scripts/check_proofs.py)"]
    core = ["DarwinBridge.route_sound", "DarwinBridge.route_endpoints", "DarwinBridge.route_floor",
            "DarwinBridge.closed_no_reach", "DarwinBridge.blocked_cut_sound",
            "DarwinBridge.contains_satisfiable", "DarwinBridge.nbrs_complete",
            "DarwinBridge.nbrs_sound", "DarwinBridge.nbrs_length", "DarwinBridge.adjB_sound",
            "DarwinBridge.routeCert_sound", "DarwinBridge.blockedCert_sound",
            "DarwinBridge.sensitivity_satisfiable", "DarwinBridge.route_blocked_exclusive"]
    for n in core:
        L.append(f"#print axioms {n}")
    for m in mods:
        L.append(f"#print axioms {m}.cert_ok")
        L.append(f"#print axioms {m}.instance_sound")
    return "\n".join(L) + "\n"


# --------------------------------------------------------------------------- Lean runner
def find_tool(name: str) -> str:
    p = shutil.which(name)
    if p:
        return p
    cand = Path.home() / ".elan" / "bin" / name
    if cand.exists():
        return str(cand)
    raise FileNotFoundError(f"{name} not found (expected ~/.elan/bin/{name})")


def lean_version() -> str:
    out = subprocess.run([find_tool("lean"), "--version"], capture_output=True, text=True, timeout=60)
    return out.stdout.strip()


def _scoped(cmd: list[str], scope: bool, runtime: int = 600) -> list[str]:
    if scope and shutil.which("systemd-run"):
        return ["systemd-run", "--user", "--scope", "--quiet", "-p", "TasksMax=128", "-p", "MemoryMax=4G",
                "-p", "MemorySwapMax=0", "-p", f"RuntimeMaxSec={runtime}"] + cmd
    return cmd


def run_cmd(cmd: list[str], cwd, timeout: int = 600, scope: bool = False) -> dict:
    env = dict(os.environ)
    env["PATH"] = f"{Path.home() / '.elan' / 'bin'}:{env.get('PATH', '')}"
    full = _scoped(cmd, scope, timeout)
    p = subprocess.run(full, cwd=cwd, capture_output=True, text=True, timeout=timeout + 30, env=env)
    return {"command": " ".join(cmd), "exit_code": p.returncode, "stdout": p.stdout, "stderr": p.stderr}


def lean_compile_file(path, project_dir=LEAN_DIR, scope: bool = False) -> dict:
    """Compile one Lean file against the already-built DarwinBridge library (lake env lean)."""
    return run_cmd([find_tool("lake"), "env", find_tool("lean"), str(path)], cwd=project_dir, scope=scope)


def parse_axiom_report(text: str) -> dict:
    """Map theorem -> list of axioms from `#print axioms` output."""
    out = {}
    for m in re.finditer(r"'([^']+)' depends on axioms: \[([^\]]*)\]", text):
        out[m.group(1)] = [a.strip() for a in m.group(2).split(",") if a.strip()]
    for m in re.finditer(r"'([^']+)' does not depend on any axioms", text):
        out[m.group(1)] = []
    return out


ALLOWED_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}


def demo_proof_block(receipt: Mapping) -> dict:
    """Map a check_proofs receipt to the `proof` object of the demo JSON contract."""
    ok = receipt.get("status") == "completed"
    return {
        "status": "verified" if ok else ("failed" if receipt.get("status") else "unknown"),
        "theorem": "Conditional interval-path soundness (DarwinBridge.routeCert_sound) and closed-set/cut "
                   "no-path soundness (DarwinBridge.blockedCert_sound), assuming interval containment",
        "command": receipt.get("command"),
        "exit_code": receipt.get("compile_exit_code"),
        "mutation_exit_code": receipt.get("min_mutant_exit_code"),
        "receipt": receipt.get("receipt_path"),
    }


def write_json(path, obj) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n")


def read_json(path):
    return json.loads(Path(path).read_text())


# --------------------------------------------------------------------------- committed instances
SOURCE_META = {
    "file": "summary_AA.csv",
    "member_path": "data/figure_data/4-site_merged_replicates/20230827/four-site_summary_AA_data.csv",
    "doi": "10.22002/h5rah-5z170",
    "url": "https://data.caltech.edu/records/h5rah-5z170",
    "license": "CC0 1.0 (CaltechDATA record metadata)",
    "assay": "TrpB four-site (positions 183,184,227,228 of Tm9D8*) E. coli Trp-auxotroph growth selection, "
             "Johnston et al. PNAS 121(32):e2400439121",
    "columns": {"r1": "mu_1-bg", "r2": "mu_2-bg"},
    "row_filter": "'# Stop' == 0 (stop-containing genotypes are outside the declared graph)",
    "unnormalized": True,
}

# Fixed in advance of looking at certificate outcomes: published parent -> published top variant.
CERT_SPECS = [
    {"label": "trpb_route_delta0", "kind": "route", "start": "VFVS", "target": "AIKG", "delta": "0",
     "note": "Envelope of the two replicates only (no added sensitivity margin). Descriptive."},
    {"label": "trpb_route_delta005", "kind": "route", "start": "VFVS", "target": "AIKG", "delta": "0.005",
     "note": "Assumed sensitivity bound 0.005 growth-rate units added each side of the replicate envelope."},
    {"label": "trpb_blocked_delta005", "kind": "blocked", "start": "GCLS", "target": "AIKG", "delta": "0.005",
     "note": "GCLS: all 76 neighbours measured and certifiably lower at delta=0.005 => no non-decreasing path "
             "to AIKG in the declared graph, under the assumed containment."},
]
DEFAULT_CSV_CANDIDATES = [
    "data/raw/summary_AA.csv",
    "/data/artifacts/v2-scout/data/caltech/summary_AA.csv",
]


def find_source_csv(explicit: Optional[str] = None) -> Path:
    cands = [explicit] if explicit else [os.environ.get("DELPHI_TRPB_SUMMARY")] + \
        [str(REPO_ROOT / DEFAULT_CSV_CANDIDATES[0]), DEFAULT_CSV_CANDIDATES[1]]
    for c in cands:
        if c and Path(c).is_file():
            return Path(c)
    raise FileNotFoundError("summary_AA.csv not found; set DELPHI_TRPB_SUMMARY or pass --csv")


def generate_all(csv_path, specs=CERT_SPECS) -> list[dict]:
    obs, counts = load_trpb_observations(csv_path)
    source = dict(SOURCE_META)
    source["sha256"] = sha256_file(csv_path)
    source["counts"] = counts
    certs = []
    for sp in specs:
        inst = Instance(obs, sp["delta"])
        build = build_route_certificate if sp["kind"] == "route" else build_blocked_certificate
        cert = build(inst, sp["start"], sp["target"], source, label=sp["label"])
        cert["note"] = sp["note"]
        cert["certificate_sha256"] = certificate_digest(cert)
        certs.append(cert)
    return certs


def write_lean_tree(certs: Sequence[Mapping], lean_dir=LEAN_DIR) -> list[str]:
    lean_dir = Path(lean_dir)
    cdir = lean_dir / "DarwinBridge" / "Certs"
    cdir.mkdir(parents=True, exist_ok=True)
    mods = []
    for cert in sorted(certs, key=lambda c: c["label"]):
        mod = module_name(cert)
        (cdir / (mod.rsplit(".", 1)[1] + ".lean")).write_text(render_lean(cert))
        mods.append(mod)
    (lean_dir / "DarwinBridge" / "Certs.lean").write_text(
        "-- GENERATED aggregate of dataset certificates\n" + "".join(f"import {m}\n" for m in mods))
    (lean_dir / "DarwinBridge" / "Audit.lean").write_text(render_audit(mods))
    return mods


# --------------------------------------------------------------------------- mutation suite
def _row(cert: dict, g: str) -> dict:
    return next(e for e in cert["table"] if e["genotype"] == g)


def _bounds(cert: Mapping, g: str) -> tuple[int, int]:
    e = _row(dict(cert), g)
    d = cert["delta_scaled"]
    return min(e["r1"], e["r2"]) - d, max(e["r1"], e["r2"]) + d


def _clone(cert: Mapping) -> dict:
    return json.loads(json.dumps(cert))


def data_mutants(cert: Mapping) -> list[dict]:
    """Instance-level mutants. Each has `expect` in {"accept", "reject"}; "accept" mutants are
    boundary controls proving the checker is not rejecting everything or comparing strictly."""
    out = []

    def add(name, c, expect, why):
        out.append({"name": f"{cert['label']}__{name}", "cert": c, "expect": expect, "why": why})

    if cert["kind"] == "route":
        r = cert["route"]
        u, v = r[-2], r[-1]
        hi_u = _bounds(cert, u)[1]
        d = cert["delta_scaled"]
        for name, off, exp, why in (
            ("dominance_tight_equal", 0, "accept", "lo(next) == hi(current): boundary of >= must still be accepted"),
            ("dominance_violated_by_one", -1, "reject", "lo(next) = hi(current)-1 : the dominance inequality fails by one unit"),
        ):
            c = _clone(cert)
            e = _row(c, v)
            e["r1"] = e["r2"] = hi_u + d + off
            add(name, c, exp, why)
        c = _clone(cert)
        c["route"] = r[::-1]
        c["start"], c["target"] = cert["target"], cert["start"]
        add("reversed_route", c, "reject", "descending traversal of an ascending route must fail")
        if len(r) > 3:
            c = _clone(cert)
            c["route"] = r[:2] + r[3:]
            add("skipped_vertex_nonadjacent", c, "reject", "removing a vertex makes consecutive genotypes non-adjacent")
            c = _clone(cert)
            c["table"] = [e for e in c["table"] if e["genotype"] != r[2]]
            add("unknown_intermediate", c, "reject", "an intermediate with no declared interval cannot be certified")
        c = _clone(cert)
        c["delta_scaled"] = -1
        add("negative_delta", c, "reject", "a negative sensitivity bound would make intervals inverted")
        c = _clone(cert)
        c["table"].append(dict(c["table"][0]))
        add("duplicate_key", c, "reject", "duplicate table keys are ambiguous")
        c = _clone(cert)
        c["target"] = c["start"]
        c["route"] = [c["start"]]
        add("start_equals_target", c, "reject", "trivial one-vertex route is not a certificate")
        c = _clone(cert)
        c["target"] = r[-2]
        add("wrong_target", c, "reject", "declared target is not the route's end")
    else:
        s = cert["start"]
        u = s
        lo_u = _bounds(cert, u)[0]
        d = cert["delta_scaled"]
        v = next(g for g in neighbors(u) if g in {e["genotype"] for e in cert["table"]} and g not in cert["closed_set"])
        for name, off, exp, why in (
            ("cut_edge_tight_strict", -1, "accept", "hi(v) == lo(u)-1: strict-descent boundary accepted"),
            ("open_cut_edge_equal", 0, "reject", "hi(v) == lo(u): edge not certifiably descending => cut is open"),
            ("open_cut_edge_higher", 10 ** (cert["scale_exponent"] - 1), "reject", "neighbour clearly higher: a real ascent edge leaves S"),
        ):
            c = _clone(cert)
            e = _row(c, v)
            e["r1"] = e["r2"] = lo_u + off - d  # hi(v) = r + delta = lo(u) + off
            add(name, c, exp, why)
        c = _clone(cert)
        c["table"] = [e for e in c["table"] if e["genotype"] != v]
        add("neighbour_unknown", c, "reject", "a missing neighbour keeps an escape edge possible")
        c = _clone(cert)
        c["closed_set"] = list(c["closed_set"]) + [c["target"]]
        add("target_in_closed_set", c, "reject", "target inside S")
        c = _clone(cert)
        c["closed_set"] = [g for g in c["closed_set"] if g != c["start"]]
        add("start_not_in_closed_set", c, "reject", "start must belong to S")
        c = _clone(cert)
        c["delta_scaled"] = -1
        add("negative_delta", c, "reject", "negative sensitivity bound")
        c = _clone(cert)
        c["table"].append(dict(c["table"][0]))
        add("duplicate_key", c, "reject", "duplicate table keys")
        # the cut's own neighbour list must be complete: drop S membership of a needed vertex
        # (only meaningful for |S|>1) -- covered by source mutant on `nbrs`.
    return out


SOURCE_MUTANTS = [
    ("core_flip_dominance", "DarwinBridge/Core.lean", "| some (_, ha), some (lb, _) => decide (ha ≤ lb)",
     "| some (_, ha), some (lb, _) => decide (lb ≤ ha)", "dominance inequality direction flipped"),
    ("core_dominance_uses_lo", "DarwinBridge/Core.lean", "| some (_, ha), some (lb, _) => decide (ha ≤ lb)",
     "| some (ha, _), some (lb, _) => decide (ha ≤ lb)", "uses lo(u) instead of hi(u)"),
    ("core_unknown_vertex_accepted", "DarwinBridge/Core.lean", "  | _, _ => false\n\n/-- Certified strictly",
     "  | _, _ => true\n\n/-- Certified strictly", "unknown vertices treated as dominated"),
    ("core_flip_descent", "DarwinBridge/Core.lean", "| some (la, _), some (_, hb) => decide (hb < la)",
     "| some (la, _), some (_, hb) => decide (la < hb)", "strict-descent direction flipped"),
    ("core_cut_ignores_descent", "DarwinBridge/Core.lean", "decide (b ∈ S) || downB B a b", "decide (b ∈ S) || true",
     "cut accepts every outgoing edge"),
    ("core_target_may_be_inside", "DarwinBridge/Core.lean", "decide (s ∈ S) && !(decide (t ∈ S)) && cutB",
     "decide (s ∈ S) && cutB", "target-outside-S check dropped"),
    ("geno_incomplete_neighbours", "DarwinBridge/Geno.lean",
     "  ((List.range 20).filter (· ≠ g.c)).map (fun x => ⟨g.a, g.b, x, g.d⟩) ++\n  ((List.range 20).filter (· ≠ g.d)).map (fun x => ⟨g.a, g.b, g.c, x⟩)",
     "  ((List.range 20).filter (· ≠ g.c)).map (fun x => ⟨g.a, g.b, x, g.d⟩)",
     "neighbour enumerator omits the fourth position (missing edges)"),
    ("geno_adjacency_too_loose", "DarwinBridge/Geno.lean", "(g.a ≠ h.a ∧ g.b = h.b ∧ g.c = h.c ∧ g.d = h.d) ∨",
     "(g.a ≠ h.a ∧ g.b = h.b ∧ g.c = h.c) ∨", "adjacency ignores position 4 (accepts double substitutions)"),
]


def apply_source_mutant(tree: Path, mutant: tuple) -> None:
    name, rel, old, new, _ = mutant
    f = Path(tree) / rel
    text = f.read_text()
    if text.count(old) != 1:
        raise RuntimeError(f"mutant {name}: pattern occurs {text.count(old)} times in {rel}")
    f.write_text(text.replace(old, new))


def copy_lean_tree(dest) -> Path:
    dest = Path(dest)
    shutil.copytree(LEAN_DIR, dest, ignore=shutil.ignore_patterns(".lake", "build"))
    return dest


if __name__ == "__main__":  # pragma: no cover
    sys.exit("use scripts/check_proofs.py")
