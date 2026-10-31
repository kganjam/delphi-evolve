"""Attention and forecasting schema for the Frontier map (validators + scoring; no storage, no service).

What it does:   validates attention profiles / signals / prediction specs; computes value-of-information for the
                decisions an answer would unlock; builds explainable priority cards and lenses; compares allocation
                policies at a matched budget; scores forecasts of frontier events with the Scope Desk scoring code.
What it does not: persist anything, serve anything, authenticate anyone, federate, or assume models are inaccurate.
                Unguarded frontier models already score ~95% on the frozen benchmark; the value here is the witness,
                the refusal, the repair and the allocation of attention - not an accuracy gap.
"""
