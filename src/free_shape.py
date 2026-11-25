"""N-vertex free periodic surface with its mean-height gauge removed."""
import numpy as np
from model import Surface

FAMILIES = ("free",)


def parameter_count(segments):
    return segments - 1


def decode(parameters, segments):
    coordinates = np.asarray(parameters, dtype=float)[:segments - 1]
    heights = np.r_[coordinates, -np.sum(coordinates)]
    return Surface(heights)


def encode(surface):
    heights = np.asarray(surface.heights, dtype=float)
    return heights[:-1] - heights.mean()


def bounds(config):
    return [(-config["height_bound"], config["height_bound"])] * parameter_count(config["segments"])
