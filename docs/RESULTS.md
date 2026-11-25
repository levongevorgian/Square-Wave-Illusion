# Simulation results

See [Limitations](LIMITATIONS.md) for assumptions that affect how these results should be interpreted.

The fit files and figures currently in `results/` were generated before the updated parameterization. They are kept as historical outputs; they do not show the N=32 reference configuration, fitted light intensity, or fitted target vertical shift.

Regenerate the current results from the repository root with:

```sh
python run_all.py --full
```

The full run fits the three fixed-shape models first, then fits the 32-vertex free surface from the best fixed-shape candidate. It then refines the fits, calculates dense-profile metrics, and rebuilds the result figures and analysis JSON.

The current target retains its specified peak-to-trough amplitude. The fitted vertical shift adds a constant to the target profile, while light intensity scales the rendered illumination. Results should be interpreted as candidate image matches under the documented model assumptions, not as evidence for a unique perceived 3D shape or a psychological mechanism.

