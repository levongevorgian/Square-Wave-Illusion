"""Physical/numerical checks independent of the example plots."""
import json
from pathlib import Path
import numpy as np
from model import Surface, sphere_directions, light_direction, vmf_radiance, render, transport_matrix


def ray_reference(surface, x, z, light):
    """Independent explicit ray/segment-intersection reference over 5 cycles."""
    if light[2] <= 0:
        return False
    if abs(light[0]) < 1e-12:
        return True
    n = len(surface.heights)
    dx = surface.period / n
    for j in range(-2*n, 3*n):
        xa, xb = j*dx, (j+1)*dx
        za, zb = surface.heights[j % n], surface.heights[(j+1) % n]
        # x + t*lx = xa + u*(xb-xa); z + t*lz = za + u*(zb-za).
        a = np.array([[light[0], -(xb-xa)], [light[2], -(zb-za)]])
        if abs(np.linalg.det(a)) < 1e-12:
            continue
        t, u = np.linalg.solve(a, np.array([xa-x, za-z]))
        if t > 1e-9 and -1e-10 <= u <= 1+1e-10:
            return False
    return True


def run_checks():
    checks = {}
    directions = sphere_directions(8192)
    checks["unit_sphere_vectors"] = bool(np.allclose(np.linalg.norm(directions, axis=1), 1))
    flat = Surface(np.zeros(16))
    _, lum = render(flat, directions)
    checks["flat_uniform_radiance_is_one"] = bool(np.allclose(lum, 1, atol=1e-10))
    for k in (0, 1, 8, 30):
        mean_radiance = vmf_radiance(directions, light_direction(23, 41), k).mean()
        checks[f"vmf_normalization_kappa_{k}"] = bool(abs(mean_radiance-1) < 0.002)
    surface = Surface(np.array([0, 0.3, -0.1, 0.2, -0.2, 0.05, 0.1, -0.1]))
    x, z, normals = surface.samples(3)
    overhead = np.array([[0., 0., 1.]])
    checks["overhead_light_unblocked"] = bool(surface.visibility(overhead, 3).all())
    checks["overhead_cosine_law"] = bool(np.allclose(transport_matrix(surface, overhead, 3)[:, 0], normals[:, 2]))
    checks["light_from_below_blocked"] = bool(not surface.visibility([[1, 0, -1]], 3).any())
    rng = np.random.default_rng(20261022)
    az = rng.uniform(0, 2*np.pi, 24)
    elev = rng.uniform(0.03, 1.5, 24)
    lights = np.column_stack((np.cos(elev)*np.cos(az), np.cos(elev)*np.sin(az), np.sin(elev)))
    actual = surface.visibility(lights, 3)
    reference = np.array([[ray_reference(surface, a, b, l) for l in lights] for a,b in zip(x,z)])
    checks["horizons_match_independent_ray_intersections"] = bool(np.array_equal(actual, reference))
    checks["test_case_contains_cast_shadows"] = bool((~actual).any())
    shifted = Surface(surface.heights + 7)
    checks["vertical_translation_invariance"] = bool(np.array_equal(actual, shifted.visibility(lights, 3)))
    mirror_lights = lights * [1, -1, 1]
    checks["ridge_direction_reflection_invariance"] = bool(np.allclose(transport_matrix(surface, lights, 3), transport_matrix(surface, mirror_lights, 3)))
    _, unshadowed = render(surface, directions, samples_per_segment=3, shadows=False)
    _, shadowed = render(surface, directions, samples_per_segment=3)
    checks["shadows_cannot_increase_direct_radiance"] = bool(np.all(shadowed <= unshadowed+1e-12))
    checks["nonnegative_output"] = bool(np.all(shadowed >= 0))
    return checks


if __name__ == "__main__":
    results = run_checks()
    output = Path(__file__).parent / "results"
    output.mkdir(exist_ok=True)
    (output / "validation.json").write_text(json.dumps(results, indent=2) + "\n")
    for name, passed in results.items():
        print(f"{'PASS' if passed else 'FAIL'} {name}")
    if not all(results.values()):
        raise SystemExit("Validation failed")
