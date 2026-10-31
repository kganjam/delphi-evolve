"""Forecast market engine and scoring for the Settled Science collective-capability measurement.

Scope: a forecast store (immutable, hash-chained, pre-resolution), proper scoring (Brier / log loss),
several aggregators, the diversity-prediction-theorem decomposition, matched-token-budget arm comparison,
calibration, and cross-family error correlation. It contains NO measured data and NO claims; the numbers
it reports exist only when real frozen claims, real oracle resolutions and real agent forecasts are supplied.

THE LIMIT, stated once here and repeated in diversity.py and in every generated report:
  The diversity prediction theorem guarantees  crowd squared error <= MEAN individual squared error.
  It says NOTHING about beating the BEST individual. Whether the aggregate beats the best single agent
  is an empirical question this package measures, and the answer may be negative.
"""
__all__ = ["store", "scoring", "aggregate", "diversity", "calibration", "arms", "report"]
