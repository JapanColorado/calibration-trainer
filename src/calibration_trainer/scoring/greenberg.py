"""Greenberg scoring rule for confidence intervals.

This implements a simplified variant of the Greenberg scoring rule. The original
formulation uses a calibration-aware penalty that adjusts based on the expected
coverage rate. This implementation instead uses a simpler width-based hit score
(SMAX * C / (width + C)) and a distance-proportional miss penalty, which avoids
the complexity of the full Greenberg formula while preserving the key incentives:

- Tighter intervals that hit are rewarded more
- Wider misses are penalized more
- Higher confidence amplifies both rewards and penalties

The C parameter (from calibration.py) represents approximately 1/4 of the
plausible answer range and serves as the "natural" interval width.
"""

from math import log10

from calibration_trainer.scoring.calibration import calculate_c

# Scoring constants
SMAX = 10.0  # Maximum score for a hit
SMIN = -57.27  # Minimum score
EPSILON = 1e-10  # Small value to prevent division by zero


def greenberg_score(
    lower: float,
    upper: float,
    true_value: float,
    confidence_level: int,
    range_min: float,
    range_max: float,
    log_scale: bool = False,
) -> tuple[float, bool]:
    """
    Calculate the Greenberg score for a confidence interval prediction.

    Args:
        lower: Lower bound of the confidence interval
        upper: Upper bound of the confidence interval
        true_value: The actual correct answer
        confidence_level: The confidence level (e.g., 50, 60, 70, 80, 90)
        range_min: Minimum plausible value for the answer
        range_max: Maximum plausible value for the answer
        log_scale: Whether to use logarithmic scaling

    Returns:
        Tuple of (score, is_hit) where is_hit indicates if the true value
        was within the interval
    """
    c = calculate_c(range_min, range_max, log_scale)

    if log_scale:
        # Convert to log space for calculations
        lower = max(lower, EPSILON)
        upper = max(upper, EPSILON)
        true_value = max(true_value, EPSILON)

        log_lower = log10(lower)
        log_upper = log10(upper)
        log_true = log10(true_value)
        log_c = log10(c) if c > 0 else 0

        width = log_upper - log_lower
        is_hit = log_lower <= log_true <= log_upper

        if is_hit:
            score = _hit_score(width, log_c, confidence_level)
        else:
            if log_true < log_lower:
                miss_distance = log_lower - log_true
            else:
                miss_distance = log_true - log_upper
            score = _miss_score(miss_distance, width, log_c, confidence_level)
    else:
        # Linear scale calculations
        width = upper - lower
        is_hit = lower <= true_value <= upper

        if is_hit:
            score = _hit_score(width, c, confidence_level)
        else:
            if true_value < lower:
                miss_distance = lower - true_value
            else:
                miss_distance = true_value - upper
            score = _miss_score(miss_distance, width, c, confidence_level)

    # Clamp score to valid range
    score = max(SMIN, min(SMAX, score))

    return score, is_hit


def _hit_score(width: float, c: float, confidence_level: int) -> float:
    """Calculate score when the true value is within the interval.

    Uses a simplified formula: base = SMAX * C / (width + C), which gives a
    hyperbolic decay from SMAX (at width=0) toward 0 (as width→∞). When the
    interval is tighter than C, a confidence-scaled bonus is added.

    This differs from the original Greenberg hit score, which uses
    S = -k * ln(width/R) where R is the answer range. The simplified version
    here is monotonically decreasing in width and bounded in [0, SMAX].
    """
    if c <= EPSILON:
        c = 1.0

    # Base score: tighter intervals score higher, always positive
    base_score = SMAX * c / (width + c)

    # Confidence bonus: higher confidence with tight intervals gets bonus
    conf_factor = confidence_level / 100.0
    width_ratio = width / c

    if width_ratio < 1:
        # Bonus for being tighter than expected
        bonus = (1 - width_ratio) * conf_factor * 2
        base_score = min(SMAX, base_score + bonus)

    return base_score


def _miss_score(miss_distance: float, width: float, c: float, confidence_level: int) -> float:
    """Calculate score when the true value is outside the interval.

    Penalty starts at -2 for barely missing and grows linearly with
    miss_distance/C. Higher confidence levels multiply the penalty via
    (0.5 + confidence/100), so a 90% miss is penalized ~1.4x vs 50%.

    The original Greenberg formula uses a log-based miss penalty; this linear
    version is simpler but less forgiving of large misses.
    """
    if c <= EPSILON:
        c = 1.0

    conf_factor = confidence_level / 100.0

    # Miss ratio: how far outside relative to C
    miss_ratio = miss_distance / c

    # Base penalty increases with miss distance
    # Starts at -2 for barely missing, gets worse with distance
    base_penalty = -2 - (miss_ratio * SMAX * 0.5)

    # Higher confidence = higher penalty for misses
    confidence_multiplier = 0.5 + conf_factor

    score = base_penalty * confidence_multiplier

    return max(SMIN, score)
