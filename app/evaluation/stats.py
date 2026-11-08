import math


def wilson_interval(successes, trials, z=1.96):
    """Wilson score interval for a binomial proportion (95% by default).

    Preferred over the normal approximation because it stays inside [0, 1]
    and behaves sensibly for small samples and rates near 0% or 100%,
    which is exactly the situation with 20 runs per scenario.
    Returns None when there are no trials.
    """
    if trials < 0 or successes < 0 or successes > trials:
        raise ValueError("Require 0 <= successes <= trials")
    if trials == 0:
        return None

    p = successes / trials
    z2 = z * z
    denominator = 1 + z2 / trials
    center = (p + z2 / (2 * trials)) / denominator
    half_width = (
        z * math.sqrt(p * (1 - p) / trials + z2 / (4 * trials * trials))
        / denominator
    )
    return max(0.0, center - half_width), min(1.0, center + half_width)
