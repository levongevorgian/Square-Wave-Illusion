# Square-wave illusion: physical simulation

**Design and Analysis of Experiments | Group 2**

This project simulates the luminance pattern from a periodic corrugated surface under directional environmental illumination. The current model separates surface shape, light distribution, and the target profile so each can be reviewed independently.

## Repository layout

- `src/` contains the renderer, shape definitions, fitting, and analysis scripts.
- `config.json` contains the shared model and optimizer settings.
- `run_all.py` is the command-line entry point and belongs at the repository root.
- `notebook.ipynb` is an interactive walkthrough; it also belongs at the root because it reads `src/` and `results/` by root-relative paths.
- `results/` contains saved figures and JSON summaries. The currently committed results are historical outputs from the earlier parameterization; regenerate them before using them as results for the current code.
- `docs/` documents methods, results, and limitations; `tests/` contains numerical checks.

## Model and fitting scripts

- `src/model.py` contains surface geometry, visibility, light sampling, and Lambertian rendering.
- `src/fixed_shape.py` parameterizes the flat, sinusoidal, and square-like surfaces. Sinusoid phase is an optimization parameter.
- `src/free_shape.py` parameterizes an N-vertex free surface. At N=32, 31 vertex heights are independent; the last height is determined by the zero-mean constraint.
- `src/fit.py` contains the shared objective and bounded optimization routines.
- `src/fit_fixed.py` fits the three fixed-shape families.
- `src/fit_free.py` fits the free surface, initialized from the best fixed-shape candidate.
- `src/analyze.py` refines fits, scores dense profiles, and creates result figures.
- `src/demo.py` creates forward-simulation figures without running optimization.

The optimizer varies five shared quantities: light azimuth, light elevation, light concentration, light intensity, and the target profile's vertical shift. The target shift is additive, so it moves the triangle wave up or down while keeping its peak-to-trough amplitude unchanged. Their bounds are in `config.json`.

## Run the project

Use Python 3.10 or newer.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python run_all.py --quick
```

The single requirements file includes the notebook dependencies. To open the walkthrough, run `jupyter lab notebook.ipynb` from the repository root.

To refit the models, run:

```sh
python src/fit_fixed.py
python src/fit_free.py
python src/analyze.py
```

Or run the full pipeline with `python run_all.py --full`. It regenerates the fits, analyses, and figures. The default free-shape resolution is N=32. The committed figures and fit summaries were produced with the earlier parameterization and are retained as historical outputs; regenerate them before interpreting them as current results.

## Assumptions

The surface repeats along X, extends along Y, and is viewed orthographically. Albedo is constant and only direct Lambertian illumination is modeled. Interreflection, overhangs, vertical walls, display calibration, and perceptual response are outside the simulation. The target and bounds are modeling choices, not measurements of the historical illusion.

Whole-profile errors should use multiple samples within every surface segment. Midpoint-only evaluation can hide large between-midpoint errors. Increase the number of sampled light directions to check convergence of the illumination integral.

See [methods](docs/METHODS.md), [results](docs/RESULTS.md), and [limitations](docs/LIMITATIONS.md).

