"""Binary log scoring rule for probability estimates.

Uses the standard logarithmic scoring rule, centered at 50% = 0 and scaled
so that 100% correct ≈ +10. The formula is:

    score = (ln(p) - ln(0.5)) * 10 / ln(2)

The `/ ln(2)` factor converts from natural log to log-base-2 scaling, which
makes the score exactly +10 at 100% (since log2(1/0.5) = 1, × 10 = 10).
Without this factor, the max would be ≈ 6.93 (= 10 × ln(2)).
"""

from math import log

# Minimum probability to prevent log(0)
EPSILON = 1e-10


def binary_log_score(estimate: float, outcome: bool) -> float:
    """
    Calculate the log score for a binary probability estimate.

    The log scoring rule rewards calibrated probability estimates.
    - 50% always scores 0
    - Higher confidence in correct outcomes scores higher (up to +10)
    - Higher confidence in incorrect outcomes scores lower (approaching -inf)

    Args:
        estimate: Probability estimate as a percentage (0-100)
        outcome: Whether the predicted event occurred (True/False)

    Returns:
        The log score, scaled so that 50% = 0 and 100% correct = +10
    """
    # Convert percentage to probability
    prob = estimate / 100.0

    # Clamp to avoid log(0)
    prob = max(EPSILON, min(1 - EPSILON, prob))

    # Calculate likelihood: P(outcome | estimate)
    # If outcome is True, likelihood is the estimate
    # If outcome is False, likelihood is 1 - estimate
    likelihood = prob if outcome else (1 - prob)

    # Log score: log(likelihood) - log(0.5), scaled to max of 10
    # At 50%, this equals 0
    # At 100% correct, this equals approximately +10
    score = (log(likelihood) - log(0.5)) * 10 / log(2)

    return score


def binary_score_with_details(estimate: float, outcome: bool) -> dict:
    """
    Calculate binary log score with additional details.

    Args:
        estimate: Probability estimate as a percentage (0-100)
        outcome: Whether the predicted event occurred

    Returns:
        Dictionary with score and explanation details
    """
    score = binary_log_score(estimate, outcome)

    # Determine if this was a "correct" prediction
    # (estimate > 50% and outcome True, or estimate < 50% and outcome False)
    predicted_true = estimate >= 50
    is_correct = predicted_true == outcome

    # Calculate the effective confidence
    if estimate >= 50:
        confidence = estimate
    else:
        confidence = 100 - estimate

    return {
        "score": score,
        "is_correct": is_correct,
        "predicted": predicted_true,
        "actual": outcome,
        "confidence": confidence,
        "estimate": estimate,
    }
