import math


def smooth_noise(t: float, seed: float) -> float:
    """Combines sines at different frequencies for natural, organic motion."""
    return (
        math.sin(t * 0.8 + seed) * 0.5
        + math.sin(t * 1.9 + seed * 1.3) * 0.3
        + math.sin(t * 3.7 + seed * 2.1) * 0.2
    )
