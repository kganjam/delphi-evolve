-- Appended to Price.lean by run_probe.py inside the same compilation unit.
namespace DelphiPriceWitnesses
open DelphiPrice
noncomputable section

def p : Fin 2 → ℝ := fun _ => 1/2
def z : Fin 2 → ℝ := fun i => if i = 0 then 0 else 1
def one : Fin 2 → ℝ := fun _ => 1
def zero : Fin 2 → ℝ := fun _ => 0
def costFitness : Fin 2 → ℝ := fun i => 2 - z i

-- A genuine transmission change with zero selection covariance.
theorem transmission_is_needed :
    mean p one * (descendantMean p one one - mean p zero) = 1 ∧
    cov p one zero = 0 ∧ mean p (fun i => one i * (one i - zero i)) = 1 := by
  norm_num [mean, descendantMean, cov, p, one, zero, Fin.sum_univ_two]

-- A valid nonnegative two-type population; relatedness=1, benefit=0,
-- cost=1, zero regression residual. The correct criterion predicts decrease.
theorem regression_premises_nonvacuous :
    (∑ i, p i) = 1 ∧ cov p z z = 1/4 ∧ cov p zero z = 0 ∧
    mean p costFitness = 3/2 ∧
    descendantMean p costFitness z - mean p z = -(1/6) := by
  norm_num [mean, descendantMean, cov, p, z, zero, costFitness, Fin.sum_univ_two]

theorem reversed_cost_is_false :
    ¬ (0 < descendantMean p costFitness z - mean p z ↔ 0 < (1:ℝ)*0+1) := by
  norm_num [mean, descendantMean, p, z, costFitness, Fin.sum_univ_two]

-- Removing residual orthogonality can reverse the selection sign.
def residual : Fin 2 → ℝ := fun i => 2 * z i
def residualFitness : Fin 2 → ℝ := fun i => 2 - z i + residual i

theorem residual_assumption_is_needed :
    cov p residual z = 1/2 ∧
    0 < descendantMean p residualFitness z - mean p z ∧ ¬ (0 < (1:ℝ)*0-1) := by
  norm_num [mean, descendantMean, cov, p, z, residual, residualFitness, Fin.sum_univ_two]

#print axioms transmission_is_needed
#print axioms regression_premises_nonvacuous
#print axioms reversed_cost_is_false
#print axioms residual_assumption_is_needed
end
end DelphiPriceWitnesses
