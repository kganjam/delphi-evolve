"""Hand-authored adapter for the existing Delphi claim `fisher-ftns`.

Record (network source): "The rate of increase in mean fitness of a population due to
natural selection equals its additive genetic variance in fitness at that time."
math: Delta_NS wbar = V_A(w)/wbar (discrete generations);
      d mbar/dt |_NS = V_A(m) (Malthusian fitness m).
Recorded conditions (delphi:context): the PARTIAL change holds average effects of alleles
and the environment fixed (Price 1972, Ewens 1989); V_A is the additive genetic variance
in fitness. "Read as a claim about the total change in mean fitness it is false under
dominance, epistasis, frequency dependence or a changing environment."

This adapter therefore only evaluates the partial (selection-component) change, and only
from a declared ADDITIVE genetic variance in fitness. It does not formalise Fisher's
theorem (no Lean here); it enforces the record's stated reading.
"""
from __future__ import annotations

import math

ADAPTER_ID = "fisher-ftns/partial-change"
ADAPTER_VERSION = "1.0.0"
CLAIM_ID = "fisher-ftns"

RECORDED_CONDITIONS = [
    "partial change: average effects of alleles held fixed",
    "environment held fixed",
    "V_A is the additive genetic variance in fitness (not total genotypic, clonal-genotype or phenotypic variance)",
]
ADAPTER_ADDED_CONDITIONS = [
    "frequency-independent selection (the record lists frequency dependence among the reasons the TOTAL reading fails)",
    "the output is a prediction of the selection component only, never an observed or total change",
]

ACCEPTED_INFERENCE = "partial_change_selection_component"
ACCEPTED_VARIANCE = "additive_genetic_variance_in_fitness"

# inference types we recognise and refuse, with the reason that will be returned
REFUSED_INFERENCES = {
    "total_fitness_change": "the record states that the total change in mean fitness is NOT given by V_A under dominance, epistasis, frequency dependence or a changing environment",
    "every_mutation_step_improves_fitness": "FTNS is a statement about the selection component of change in POPULATION mean fitness; it says nothing about whether any particular mutation or route step increases fitness (deleterious and neutral mutations exist; V_A >= 0 does not order individual genotypes)",
    "route_step_nondecreasing": "a route-step nondecreasing-fitness statement is the conditional interval-dominance theorem proved separately in lean/ (assumption: measurement intervals contain true values); it is not a consequence of Fisher's theorem",
}
REFUSED_VARIANCES = {
    "clonal_genotypic_variance": "genotypic variance among clones is not identified with additive genetic variance by this record; a clonal/haploid reading is a separate claim needing its own reviewed adapter",
    "total_genotypic_variance": "total genetic variance includes dominance and epistatic components that the partial-change statement excludes",
    "phenotypic_variance": "phenotypic variance includes environmental variance",
    "assay_replicate_variance": "variance between assay replicates is measurement noise, not genetic variance",
    "landscape_score_variance": "the variance of scores over TrpB genotypes is not a population's additive variance: no genotype frequencies, mating system or fitness definition is available",
}


def _num(name, v, positive=False, nonneg=False):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise ValueError(f"{name} must be a finite number")
    if positive and not v > 0:
        raise ValueError(f"{name} must be > 0")
    if nonneg and v < 0:
        raise ValueError(f"{name} must be >= 0")
    return float(v)


def partial_change(V_A: float, wbar: float | None, scale: str) -> float:
    V_A = _num("V_A", V_A, nonneg=True)
    if scale == "relative_discrete":
        return V_A / _num("mean_fitness", wbar, positive=True)
    if scale == "malthusian":
        return V_A
    raise ValueError("scale must be 'relative_discrete' or 'malthusian'")


def one_locus_check(p: float, w_AA: float, w_Aa: float, w_aa: float) -> dict:
    """Exact one-locus, two-allele, random-mating, constant-fitness check (SIMULATED/ANALYTIC).

    alpha = w_A. - w_a. (difference in marginal allele fitness) = regression slope of
    genotype fitness on allele count; V_A = 2pq alpha^2; the partial change is
    V_A/wbar = 2 alpha dp. The exact total change in mean fitness equals
    partial + d * dp^2 with d = w_AA - 2 w_Aa + w_aa (dominance deviation), because
    wbar(p) is quadratic. Equality of total and partial therefore requires d = 0.
    """
    q = 1 - p
    wbar = p * p * w_AA + 2 * p * q * w_Aa + q * q * w_aa
    wA = p * w_AA + q * w_Aa
    wa = p * w_Aa + q * w_aa
    alpha = wA - wa
    VA = 2 * p * q * alpha ** 2
    dp = p * q * alpha / wbar
    wbar_new = (p + dp) ** 2 * w_AA + 2 * (p + dp) * (q - dp) * w_Aa + (q - dp) ** 2 * w_aa
    d = w_AA - 2 * w_Aa + w_aa
    return {"p": p, "wbar": wbar, "alpha": alpha, "V_A": VA, "delta_p": dp,
            "partial_change_VA_over_wbar": VA / wbar,
            "total_change_exact": wbar_new - wbar,
            "dominance_deviation_d": d,
            "identity_residual": (wbar_new - wbar) - (VA / wbar + d * dp * dp)}
