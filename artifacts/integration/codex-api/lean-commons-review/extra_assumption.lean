

theorem review_helper : True := by trivial
variable (h : False)
include h

theorem review_target : False := by exact h

#check @review_target
#print axioms review_helper
#print axioms review_target
