"""Low-dimensional fixed-shape surface families."""
import numpy as np
from model import Surface

FAMILIES = ("flat", "sinusoid", "square_like")


def parameter_count(family, segments):
    del segments
    if family == "flat":
        return 0
    if family in ("sinusoid", "square_like"):
        return 2  # amplitude and free phase
    raise ValueError(f"Unknown fixed-shape family: {family}")


def decode(parameters, family, segments):
    phase_grid = np.arange(segments) / segments
    if family == "flat":
        heights = np.zeros(segments)
    elif family in ("sinusoid", "square_like"):
        amplitude, phase_shift = np.asarray(parameters, dtype=float)[:2]
        wave = np.cos(2 * np.pi * (phase_grid - phase_shift))
        heights = amplitude * wave
        if family == "square_like":
            heights = amplitude * np.tanh(4 * wave) / np.tanh(4)
    else:
        raise ValueError(f"Unknown fixed-shape family: {family}")
    return Surface(heights - heights.mean())


def bounds(family, config):
    if family == "flat":
        return []
    if family in ("sinusoid", "square_like"):
        return [(0.0, config["height_bound"]), (0.0, 1.0)]
    raise ValueError(f"Unknown fixed-shape family: {family}")
