"""C parameter calculation for scoring."""

from math import log10


def calculate_c(range_min: float, range_max: float, log_scale: bool) -> float:
    """
    Calculate the C parameter for Greenberg scoring.

    The C parameter represents the "natural" width of a confidence interval,
    approximately 1/4 of the plausible range.

    Args:
        range_min: Minimum plausible value for the answer
        range_max: Maximum plausible value for the answer
        log_scale: Whether to use logarithmic scaling

    Returns:
        The C parameter value
    """
    if log_scale:
        if range_min <= 0:
            range_min = 1e-10
        log_range = log10(range_max) - log10(range_min)
        return 10 ** (log_range / 4)
    else:
        return (range_max - range_min) / 4
