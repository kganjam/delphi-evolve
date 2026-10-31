"""TrpB (Tm9D8s*) reference sequence, residue mapping and variant enumeration.

Primary source: CaltechDATA record h5rah-5z170 (CC0 1.0; Johnston et al. 2024,
PNAS 121:e2400439121), archive member ``data/ftmlde_data/tm9d8s_AAs.fasta``
(header ``>Tm9D8*``, 397 aa, C-terminal ``LEHHHHHH`` construct tag).  The same
sequence appears in ``TARGET_b0.3.fa`` (the EVmutation zero-shot target) and the
PDB ``Tm9D8s_refine_19.pdb`` has V183/F184/V227/S228 under identical numbering.

Numbering convention: 1-based index into the FASTA string (initiator Met = 1).
Library positions 183, 184, 227, 228; parent genotype ``VFVS`` (the parent row of
``simplified_AA.csv`` has AAs == "VFVS", fitness 0.408).

Nothing here reads any fitness value.  Variant order is combinatorial, and any
subset ordering uses a seeded permutation that is independent of outcomes.
"""
import hashlib
import itertools
from pathlib import Path

SITES = (183, 184, 227, 228)          # 1-based sequence positions
PARENT = "VFVS"
AA20 = "ACDEFGHIKLMNPQRSTVWY"         # alphabetical; matches `AAs` key letters in the CSVs
FASTA_SHA256 = "d56ebe8d8c556d80bf97329ec34c872b737fb84953f0d83dfe015894e54bbc6c"
EXPECTED_LEN = 397
N_VARIANTS = len(AA20) ** len(SITES)  # 160000
DEFAULT_FASTA = Path(__file__).resolve().parent / "data" / "tm9d8s_AAs.fasta"
PERMUTATION_SEED = 20261031            # fixed before any model output exists


def read_fasta(path=DEFAULT_FASTA, check_hash=True):
    raw = Path(path).read_bytes()
    if check_hash and hashlib.sha256(raw).hexdigest() != FASTA_SHA256:
        raise ValueError("reference FASTA hash mismatch; refusing to proceed")
    lines = raw.decode().splitlines()
    header = lines[0][1:]
    seq = "".join(x.strip() for x in lines[1:])
    return header, seq


def load_reference(path=DEFAULT_FASTA, check_hash=True):
    """Return (header, sequence) after verifying length and the four site residues."""
    header, seq = read_fasta(path, check_hash)
    if len(seq) != EXPECTED_LEN:
        raise ValueError(f"unexpected reference length {len(seq)}")
    got = "".join(seq[p - 1] for p in SITES)
    if got != PARENT:
        raise ValueError(f"site residues {got} != expected parent {PARENT}")
    if set(seq) - set("ACDEFGHIKLMNPQRSTVWY"):
        raise ValueError("non-canonical residue in reference")
    return header, seq


def genotype_sequence(seq, genotype):
    """Substitute a 4-letter genotype at SITES of the reference sequence."""
    if len(genotype) != len(SITES) or set(genotype) - set(AA20):
        raise ValueError(f"bad genotype {genotype!r}")
    s = list(seq)
    for p, aa in zip(SITES, genotype):
        s[p - 1] = aa
    return "".join(s)


def all_genotypes():
    """All 20^4 genotype strings in lexicographic AA20 order (position 183 slowest)."""
    return ["".join(t) for t in itertools.product(AA20, repeat=len(SITES))]


def permuted_order(n=N_VARIANTS, seed=PERMUTATION_SEED):
    """Seeded label-free permutation of range(n) (numpy default_rng/PCG64)."""
    import numpy as np
    return np.random.default_rng(seed).permutation(n)


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()
