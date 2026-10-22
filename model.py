"""Periodic height-field renderer for the square-wave illusion project.

X: across the corrugations; Y: along the ridges; Z: upward.
Light vectors point FROM the surface TOWARD the source.
Only direct illumination is modeled; no interreflection or perspective.
"""
from dataclasses import dataclass
import numpy as np


def sphere_directions(count=2048):
    """Deterministic Fibonacci quadrature, with equal solid-angle weights.

    Points are approximately uniform, not an exact spherical integration rule.
    Increase count to check numerical convergence.
    """
    if not isinstance(count, (int, np.integer)) or count < 4:
        raise ValueError("Use an integer count of at least four directions.")
    i = np.arange(count)
    z = 1 - 2 * (i + 0.5) / count
    phi = i * np.pi * (3 - np.sqrt(5))
    radius = np.sqrt(1 - z * z)
    return np.column_stack((radius * np.cos(phi), radius * np.sin(phi), z))


def light_direction(azimuth_deg, elevation_deg):
    """Azimuth measured from +X toward +Y; elevation from XY toward +Z."""
    a, e = np.deg2rad([azimuth_deg, elevation_deg])
    return np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])


def vmf_radiance(directions, mean_direction, concentration=0.0):
    """vMF angular radiance, normalized to sphere-average radiance one.

    kappa=0 is uniform radiance; larger kappa means more focused lighting.
    The integral over the sphere stays 4*pi analytically. Finite quadrature
    approximates that integral, so narrow lobes need more sample directions.
    """
    k = float(concentration)
    if not np.isfinite(k) or k < 0:
        raise ValueError("Concentration must be finite and nonnegative.")
    mu = np.asarray(mean_direction, dtype=float)
    if mu.shape != (3,) or not np.isfinite(mu).all() or np.linalg.norm(mu) == 0:
        raise ValueError("Mean direction must be a finite nonzero 3-vector.")
    if k == 0:
        return np.ones(len(directions))
    mu = mu / np.linalg.norm(mu)
    # Stable equivalent of k*exp(k*mu.l)/sinh(k).
    return (2 * k / -np.expm1(-2 * k)) * np.exp(k * (np.clip(directions @ mu, -1, 1) - 1))


@dataclass
class Surface:
    heights: np.ndarray
    period: float = 1.0

    def __post_init__(self):
        self.heights = np.asarray(self.heights, dtype=float).copy()
        if self.heights.ndim != 1 or len(self.heights) < 3 or not np.isfinite(self.heights).all():
            raise ValueError("Supply at least three finite heights.")
        if not np.isfinite(self.period) or self.period <= 0:
            raise ValueError("Period must be positive and finite.")

    def samples(self, samples_per_segment=5):
        """Equal-X midpoint quadrature within each planar segment."""
        q = int(samples_per_segment)
        if q < 1 or q != samples_per_segment:
            raise ValueError("samples_per_segment must be a positive integer.")
        n = len(self.heights)
        dx = self.period / n
        j = np.repeat(np.arange(n), q)
        fraction = np.tile((np.arange(q) + 0.5) / q, n)
        dz = np.roll(self.heights, -1) - self.heights
        x = (j + fraction) * dx
        z = self.heights[j] + fraction * dz[j]
        slopes = dz[j] / dx
        normals = np.column_stack((-slopes, np.zeros_like(slopes), np.ones_like(slopes)))
        normals /= np.linalg.norm(normals, axis=1, keepdims=True)
        return x, z, normals

    def horizons(self, x, z):
        """Exact left/right horizon slopes for a periodic piecewise-linear graph.

        For an upward ray, checking vertices within one period suffices: a
        farther repeat of any vertex has the same height and a larger distance.
        Zero is the limiting horizon at infinity. On each straight segment,
        the slope from the sample is monotonic, so endpoints suffice.
        """
        vertices = np.arange(len(self.heights)) * self.period / len(self.heights)
        right_distance = (vertices[None, :] - x[:, None]) % self.period
        left_distance = (x[:, None] - vertices[None, :]) % self.period
        dh = self.heights[None, :] - z[:, None]
        right = np.maximum(0, np.max(dh / right_distance, axis=1))
        left = np.maximum(0, np.max(dh / left_distance, axis=1))
        return left, right

    def visibility(self, directions, samples_per_segment=5):
        """Binary direct-light visibility at quadrature points, including repeats."""
        x, z, _ = self.samples(samples_per_segment)
        left, right = self.horizons(x, z)
        light = np.atleast_2d(np.asarray(directions, dtype=float))
        if light.shape[1] != 3 or not np.isfinite(light).all():
            raise ValueError("Directions must have shape (M, 3) and be finite.")
        if np.any(np.linalg.norm(light, axis=1) == 0):
            raise ValueError("Light vectors cannot be zero.")
        horizon = np.where(light[None, :, 0] >= 0, right[:, None], left[:, None])
        # Strict > treats exactly grazing rays as blocked. This is measure zero
        # in the spherical integral. The unbounded opaque graph blocks lz<0.
        return light[None, :, 2] > horizon * np.abs(light[None, :, 0])


def transport_matrix(surface, directions, samples_per_segment=5, shadows=True):
    """Per-sample cosine*visibility, with no area factor for image radiance."""
    _, _, normals = surface.samples(samples_per_segment)
    cosine = np.maximum(0, normals @ np.asarray(directions).T)
    if shadows:
        cosine *= surface.visibility(directions, samples_per_segment)
    return cosine


def render(surface, directions=None, mean_direction=None, concentration=0.0,
           samples_per_segment=5, albedo=1.0, shadows=True):
    """Outgoing Lambertian radiance rho/pi * integral(Li * V * cos * dOmega).

    Returns X sample positions and luminance in relative linear units. A flat
    white surface under uniform unit radiance has output approximately one.
    Directions must be unit, equal-solid-angle samples, e.g. sphere_directions.
    """
    if not 0 <= albedo <= 1:
        raise ValueError("Albedo must be between zero and one.")
    directions = sphere_directions() if directions is None else np.asarray(directions, dtype=float)
    if directions.ndim != 2 or directions.shape[1] != 3 or len(directions) < 1:
        raise ValueError("Directions must be a nonempty (M, 3) array.")
    if not np.allclose(np.linalg.norm(directions, axis=1), 1):
        raise ValueError("Use unit light vectors.")
    mu = [0, 0, 1] if mean_direction is None else mean_direction
    radiance = vmf_radiance(directions, mu, concentration)
    response = transport_matrix(surface, directions, samples_per_segment, shadows)
    luminance = (albedo / np.pi) * (4 * np.pi / len(directions)) * (response @ radiance)
    return surface.samples(samples_per_segment)[0], luminance


def triangle_target(x, period=1.0, mean=1.0, contrast=0.6):
    """Provisional triangle-wave luminance with a peak at phase zero.

    Michelson contrast=(max-min)/(max+min). These values are modeling choices,
    not a claim to reproduce the historical apparatus or calibrated display.
    """
    if period <= 0 or mean <= 0 or not 0 <= contrast <= 1:
        raise ValueError("Require period>0, mean>0, and contrast in [0,1].")
    phase = (np.asarray(x) / period) % 1
    return mean * (1 + contrast * (4 * np.abs(phase - 0.5) - 1))


def example_surface(kind="sinusoid", segments=32, amplitude=0.12):
    phase = np.arange(segments) / segments
    if kind == "flat":
        z = np.zeros(segments)
    elif kind == "sinusoid":
        z = amplitude * np.cos(2 * np.pi * phase)
    elif kind == "square_like":
        # Continuous height field with steep ramps, not vertical walls.
        z = amplitude * np.tanh(4 * np.cos(2 * np.pi * phase)) / np.tanh(4)
    else:
        raise ValueError(f"Unknown surface: {kind}")
    return Surface(z)
