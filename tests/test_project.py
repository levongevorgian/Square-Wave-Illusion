"""Physical checks and regression tests for geometry, optimization, and saved results."""
import json
from pathlib import Path
import sys
import unittest
import numpy as np
from scipy.optimize import minimize_scalar

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/"src"))
from model import Surface, sphere_directions, light_direction, render, vmf_radiance, transport_matrix
from fit import DEFAULT_CONFIG, decode, encode_free, objective


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


class PhysicsTests(unittest.TestCase):
    def test_physics_suite(self):
        for name, passed in run_checks().items():
            with self.subTest(check=name):
                self.assertTrue(passed)

    def test_periodic_closure_and_normals(self):
        surface=Surface([0,0.1,0,-0.1])
        _,_,normals=surface.samples(1)
        expected=np.array([[-0.4,0,1],[0.4,0,1],[0.4,0,1],[-0.4,0,1]])
        expected/=np.linalg.norm(expected,axis=1,keepdims=True)
        np.testing.assert_allclose(normals,expected)

    def test_uniform_radiance_on_tilted_unoccluded_facets(self):
        _,y=render(Surface([0,0.2,-0.1,0.1]),sphere_directions(16384),shadows=False)
        np.testing.assert_allclose(y,1,atol=0.0001)

    def test_free_surface_parameter_roundtrip(self):
        surface=Surface([0.1,-0.05,0,-0.05])
        p=encode_free(surface,[140,25,8,1.2,0.1])
        recovered,_,_,intensity,target_shift=decode(p,"free",4)
        self.assertEqual(intensity,1.2)
        self.assertEqual(target_shift,0.1)
        np.testing.assert_allclose(recovered.heights,surface.heights,atol=1e-14)

    def test_invalid_input(self):
        for count in (0,3,4.5):
            with self.assertRaises(ValueError):sphere_directions(count)
        with self.assertRaises(ValueError):Surface([0,np.nan,1])
        with self.assertRaises(ValueError):vmf_radiance(sphere_directions(16),[0,0,0],2)
        with self.assertRaises(ValueError):render(Surface([0,0,0]),np.array([[2,0,0]]))


class InverseRenderingTests(unittest.TestCase):
    def test_synthetic_lighting_recovery_on_known_surface(self):
        surface=Surface(0.08*np.cos(2*np.pi*np.arange(16)/16))
        directions=sphere_directions(1024)
        _,target=render(surface,directions,light_direction(150,25),6,samples_per_segment=3)
        def loss(k):
            _,y=render(surface,directions,light_direction(150,25),k,samples_per_segment=3)
            return float(np.mean((y-target)**2))
        result=minimize_scalar(loss,bounds=(0,15),method="bounded",options={"xatol":1e-7})
        self.assertTrue(result.success)
        self.assertLess(abs(result.x-6),1e-4)
        self.assertLess(result.fun,1e-12)

    def test_height_constraint_penalizes_inadmissible_shape(self):
        cfg={**DEFAULT_CONFIG,"segments":4}
        # The recovered fourth height is -0.75, outside the 0.25 bound.
        p=[0.25,0.25,0.25,90,30,5,1.0,0.0]
        self.assertGreater(objective(p,"free",cfg,sphere_directions(64)),1)

    def test_saved_reference_results_if_available(self):
        p=ROOT/"results"/"data"/"analysis.json"
        if not p.exists():self.skipTest("Reference analysis not yet generated")
        data=json.loads(p.read_text())
        self.assertEqual(data["status"],"complete")
        fits={r["family"]:r for r in data["selected_fits"]}
        self.assertLess(fits["free"]["evaluation_metrics"]["rmse"],fits["flat"]["evaluation_metrics"]["rmse"])
        for r in fits.values():
            self.assertLessEqual(r["max_abs_height"],data["config"]["height_bound"]+1e-6)
            self.assertLessEqual(r["max_abs_slope"],data["config"]["slope_bound"]+1e-6)
            self.assertTrue(np.isfinite(r["evaluation_metrics"]["rmse"]))
        for r in data["sensitivity"]:
            self.assertLessEqual(r["max_abs_height"],r["config"]["height_bound"]+1e-6)
            self.assertLessEqual(r["max_abs_slope"],r["config"]["slope_bound"]+1e-6)


if __name__=="__main__":
    unittest.main(verbosity=2)
