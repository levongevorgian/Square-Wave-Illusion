"""Regression checks for geometry conventions, optimization, and saved results."""
import json
from pathlib import Path
import unittest
import numpy as np
from scipy.optimize import minimize_scalar
from model import Surface, sphere_directions, light_direction, render, vmf_radiance
from fit import DEFAULT_CONFIG, decode, encode_free, objective
from validate import run_checks


class PhysicsTests(unittest.TestCase):
    def test_physics_suite(self):
        self.assertTrue(all(run_checks().values()))

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
        p=encode_free(surface,[140,25,8])
        recovered,_,_=decode(p,"free",4)
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
        p=[0.25,0.25,0.25,90,30,5]
        self.assertGreater(objective(p,"free",cfg,sphere_directions(64)),1)

    def test_saved_reference_results_if_available(self):
        p=Path(__file__).parent/"results"/"optimization"/"analysis.json"
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
