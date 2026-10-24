"""Build repository-facing summaries and an executed review notebook."""
import base64
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import uuid
import nbformat
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from model import Surface, render, sphere_directions, light_direction, triangle_target
from fit import decode

ROOT=Path(__file__).resolve().parent


def build_best_figure(data):
    record=next(r for r in data['sensitivity'] if r['label']=='N32')
    surface,mu,k=decode(record['parameters'],'free',32)
    x,y=render(surface,sphere_directions(16384),mu,k,samples_per_segment=15)
    fig=plt.figure(figsize=(12,4.3),layout='constrained')
    ax=fig.add_subplot(121,projection='3d')
    xv=np.arange(3*32+1)/32
    yv=np.linspace(0,1,9)
    xx,yy=np.meshgrid(xv,yv)
    zz=np.tile(surface.heights[np.arange(len(xv))%32],(len(yv),1))
    segment_luminance=y.reshape(32,15).mean(axis=1)
    linear=np.clip(segment_luminance[np.arange(96)%32]/2,0,1)
    gray=np.where(linear<=0.0031308,12.92*linear,1.055*linear**(1/2.4)-0.055)
    faces=np.tile(np.column_stack((gray,gray,gray,np.ones(96)))[None,:,:],(8,1,1))
    ax.plot_surface(xx,yy,zz,facecolors=faces,shade=False,linewidth=0.2,edgecolor='#75828c',rstride=1,cstride=1)
    ax.set(xlabel='X / period',ylabel='Y / period',zlabel='Height / period',title='Fitted N=32 surface (Z exaggerated)')
    ax.set_box_aspect((3,1,0.65));ax.view_init(elev=28,azim=-65)
    ax=fig.add_subplot(122)
    ax.plot(x,triangle_target(x),color='#172b45',lw=2,label='Provisional target')
    ax.plot(x,y,color='#0b8b91',lw=1.5,label='Candidate render')
    ax.set(xlabel='X / period',ylabel='Relative linear luminance',title=f"N=32 candidate | dense RMSE {record['evaluation_metrics']['rmse']:.5f}")
    ax.legend(fontsize=9);ax.grid(alpha=0.15)
    fig.suptitle('One additional resolution fit | Visualized geometry and predicted luminance',fontsize=13)
    fig.savefig(ROOT/'results/optimization/best_candidate.png',dpi=160)
    plt.close(fig)


def build_summaries(data):
    fits={r['family']:r for r in data['selected_fits']}
    n32=next(r for r in data['sensitivity'] if r['label']=='N32')
    table='| Model | N | Dense RMSE | MAE | R-squared |\n|---|---:|---:|---:|---:|\n'
    for label,r,n in [('Flat control',fits['flat'],16),('Sinusoid',fits['sinusoid'],16),('Square-like',fits['square_like'],16),('Free surface',fits['free'],16),('Free surface: resolution check',n32,32)]:
        m=r['evaluation_metrics']
        table+=f"| {label} | {n} | {m['rmse']:.5f} | {m['mae']:.5f} | {m['r_squared']:.4f} |\n"
    sensitivity='| Change from reference | Dense RMSE |\n|---|---:|\n'
    for r in data['sensitivity']:
        sensitivity+=f"| {r['label']} | {r['evaluation_metrics']['rmse']:.5f} |\n"
    free=fits['free']
    q={r['value']:r['rmse'] for r in data['convergence'] if r['varied']=='samples_per_segment'}
    m={r['value']:r['rmse'] for r in data['convergence'] if r['varied']=='directions'}
    text=f'''# Simulation results

Generated from `results/optimization/analysis.json`. These are deterministic simulations using the provisional target, not measurements from participants.

## Main result

A fitted bounded periodic surface and vMF light field approximate the target within this model. The N=16 free-surface candidate has dense-grid RMSE **{free['evaluation_metrics']['rmse']:.5f}**, versus **{fits['flat']['evaluation_metrics']['rmse']:.5f}** for the flat control. An additional N=32 fit reduces RMSE to **{n32['evaluation_metrics']['rmse']:.5f}**. Target mean luminance is one; those errors are approximately {100*free['evaluation_metrics']['rmse']:.2f}% and {100*n32['evaluation_metrics']['rmse']:.2f}% of the target mean. They are not mean percentage errors or observer accuracy scores.

{table}
Primary comparisons use 16,384 directions and 15 sample points per segment. The N=32 case is an additional one-seed sensitivity run; it does not have the same three-seed search and fine-refinement protocol as the primary N=16 comparison. R-squared is descriptive profile matching, not an inferential test.

![N=32 geometry and luminance](../results/optimization/best_candidate.png)

The 3D view exaggerates the Z axis; its grayscale is illustrative rather than a calibrated display stimulus.

![Fitted geometries and luminance](../results/optimization/fitted_models.png)

## What the fitted surface tells us

The free fit is a shallow corrugation; its geometry is not constrained to look like a rectangular square wave. Its maximum absolute reference height is {free['max_abs_height']:.5f} periods and maximum absolute slope is {free['max_abs_slope']:.5f}. It satisfies the height and slope bounds. The fitted reference light has azimuth {free['azimuth_deg']:.2f} degrees, elevation {free['elevation_deg']:.2f} degrees, and kappa {free['kappa']:.3f}.

This establishes a candidate image match for a bounded height field. It does not demonstrate that the particular square-like surface an observer reports seeing has been recovered. Shape/light parameters are nonunique, and the Y-invariant geometry makes mirror directions equivalent in the exact integral.

## Numerical resolution matters

For the same selected N=16 parameters, midpoint-only evaluation gives RMSE {q[1]:.5f}. Evaluating the entire segments with 15 samples gives {q[15]:.5f}; 31 samples gives {q[31]:.5f}. A midpoint-only error would therefore materially overstate the fit quality.

At fixed 15 samples per segment, raising the direction count from 16,384 to 32,768 changes RMSE from {m[16384]:.5f} to {m[32768]:.5f}. This light-sampling change is small relative to the total residual for this candidate. Geometry resolution remains influential: N=8, 16, and 32 do not represent the same set of surfaces.

{sensitivity}
![Sensitivity and convergence](../results/optimization/sensitivity.png)

The sensitivity cases are warm-started, one-seed diagnostics. They do not exhaust the larger parameter spaces. The kappa=60 case changes the permitted upper bound, not the actual fitted kappa fixed at 60. The selected fitted kappa is saved in JSON.

## Search status and limits

All three reference free-surface differential-evolution searches hit their iteration cap; the final selected local Powell refinements terminated successfully. A local stopping message is not a proof of global optimality. The three free runs share a fixed-shape initialization. Differences across seeds reflect search variability, not biological uncertainty or confidence intervals.

The target is an ideal mathematical triangle wave with provisional mean, contrast, and phase. No brightness gain or offset is fitted. The current model omits interreflection, specular effects, overhangs, display calibration, and any perceptual response model.

## Reproducible evidence

- `results/optimization/fits.json`: all 12 reference searches, parameters, settings, timings, and solver messages.
- `results/optimization/analysis.json`: refined candidates, dense evaluations, all seed reevaluations, sensitivity cases, and convergence values.
- `results/optimization/model_comparison.csv`: primary comparison metrics.
- `results/optimization/fitted_profiles.csv`: target and prediction samples for primary fits.
- `results/optimization/sensitivity.json`: additional cases, including all N=32 height and lighting parameters.
- `results/validation.json`: 15 physical/numerical checks.
- `test_project.py`: eight regression tests, including synthetic kappa recovery.

The findings apply to the specified target, surface class, lighting assumptions, and optimization bounds. See [limitations and future work](LIMITATIONS.md).
'''
    (ROOT/'docs'/'RESULTS.md').write_text(text)
    readme=f'''# Square-wave illusion: physical simulation

**Design and Analysis of Experiments | Group 2 | Computational study, 22 October 2026**

Can a corrugated matte surface under directional environmental illumination reproduce the triangle-wave luminance pattern associated with the square-wave illusion?

**All six computational steps are implemented**, including joint geometry-and-lighting optimization. The repository includes reproducible candidate fits and numerical validation. The target and physical constraints define the baseline model studied here.

## Start here

- **[Readable project report (PDF)](docs/project_report.pdf)**
- **[Executed notebook](simulation_walkthrough.ipynb)**: model explanation, plots, and saved fitted results.
- **[Results and interpretation](docs/RESULTS.md)**
- **[Detailed methods](docs/METHODS.md)**
- **[Limitations and future work](docs/LIMITATIONS.md)**

## Current result

The N=16 free-surface candidate has RMSE **{free['evaluation_metrics']['rmse']:.5f}**; an additional N=32 fit has RMSE **{n32['evaluation_metrics']['rmse']:.5f}**, with target mean luminance one. This is a candidate physical image match within the stated model. It does not establish a unique perceived shape or the cause of the illusion.

{table}
![Candidate surfaces and fitted luminance](results/optimization/fitted_models.png)

## Completed scope

1. Periodic height-field geometry, planar segments, and surface normals.
2. Binary direct-light visibility, with shadows from neighboring cycles.
3. Approximately equal-solid-angle sphere sampling.
4. Lambertian integration of visible light directions.
5. von Mises-Fisher lighting with two direction angles and concentration kappa.
6. Joint fitting of geometry and lighting, with explicit bounds and a curvature penalty.

Validation includes 15 physical/numerical checks and eight regression tests. Reference fitting uses three seeds for each of four families; additional cases examine geometry resolution, smoothness, lighting concentration bounds, and numerical integration. Free-surface global searches reached their iteration budgets; successful local refinement does not prove a global optimum.

## Quick start

Use Python 3.10 or newer. Saved reference outputs were generated with Python 3.12.2; package versions are in `requirements-reference.txt` and `results/environment.json`.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python validate.py
python -m unittest -v test_project.py
python run_demo.py
```

On Windows, activate the environment with `.venv\\Scripts\\activate` instead. To inspect results, no optimization rerun is needed: the notebook, figures, JSON, CSV, and PDF are included.

To edit and rerun notebook cells locally, install the optional notebook tools with `python -m pip install -r requirements-notebook.txt`, then run `jupyter lab simulation_walkthrough.ipynb`. Select the Python environment containing the project dependencies.

## Reproduce the fitted results

From this repository root:

```sh
python run_all.py --full
```

This reruns validation, examples, fitting, analysis, summaries, notebook execution, and tests. It replaces generated outputs in `results/`, the README and result summary, and the notebook. Optimization runtime depends on the computer; the reference fit stage took under two minutes in this environment, with analysis/sensitivity taking additional time. Set `OPENBLAS_NUM_THREADS=1` before running direct individual scripts for comparable CPU behavior; `run_all.py` does this automatically.

The equivalent individual stages are:

```sh
python fit.py --config configs/reference.json
python analyze.py
python build_review.py
```

A quick check without refitting is `python run_all.py --quick`. To rebuild the PDF after a full run, install `requirements-report.txt` and run `python build_report.py`. The PDF build is separate so ordinary scientific use does not depend on the document-authoring libraries.

## Assumptions that affect interpretation

The surface repeats along X, extends along Y, and is viewed orthographically. Albedo is constant; only direct Lambertian light is modeled. Vertical walls, overhangs, light bouncing between surface parts, and calibrated display response are excluded. Square-like surfaces have finite ramps.

The provisional target has period one, mean one, and Michelson contrast 0.6. Total angular radiance is fixed. Fitting uses absolute linear luminance without a free gain or offset. Heights have zero mean to remove translation redundancy. The light mean is limited to one mirror-equivalent azimuth half-sphere and elevations 5–85 degrees.

**Do not assess the fit only at segment midpoints:** that can hide substantial between-midpoint error. Reported primary errors use 15 samples per segment and 16,384 directions. N=32 is an additional one-seed case rather than part of the main three-seed comparison.

## Repository map

```text
model.py                       Geometry, visibility, lighting, renderer
fit.py                         Four model families and bounded fitting
analyze.py                     Refinement, dense evaluation, sensitivity
validate.py                    15 physical/numerical checks
test_project.py                8 regression tests
run_demo.py                    Forward simulation examples
run_all.py                     Reproduction entry point
build_review.py                Summaries and executed notebook
build_report.py                Optional PDF build
configs/reference.json         Target, bounds, and search settings
simulation_walkthrough.ipynb    Explanation with embedded outputs
docs/                          Report, methods, results, review/upload guides
results/                       Generated figures, profiles, settings, fits
.github/workflows/checks.yml   Automated checks on pushes/pull requests
```

## Limitations and future work

The results are conditional on the baseline target and model assumptions. Further work can assess alternative targets, higher geometry resolution, additional illumination models, and perceptual validation. See [limitations and future work](docs/LIMITATIONS.md) and [references](docs/REFERENCES.md).
'''
    (ROOT/'README.md').write_text(readme)


def build_notebook():
    cells=[]
    def md(s):cells.append(nbformat.v4.new_markdown_cell(s))
    def code(s):cells.append(nbformat.v4.new_code_cell(s))
    md('# Square-wave illusion: simulation and inverse rendering\n\nComputational study, 22 October 2026. All six computational steps are implemented. This notebook explains the renderer and loads the saved optimization results; the searches can be reproduced separately. The target is provisional. See docs/METHODS.md and docs/LIMITATIONS.md.')
    code('import json\nfrom pathlib import Path\nimport numpy as np\nimport matplotlib.pyplot as plt\nfrom model import Surface, example_surface, sphere_directions, light_direction, render, triangle_target\nfrom validate import run_checks\nfrom fit import decode\nroot = Path.cwd()')
    md('## 1. Surface geometry\n\nN heights form a periodic, piecewise planar cross-section. The surface extends along Y. Height values are not luminance values. The last segment joins the next cycle.')
    code('surface = example_surface("sinusoid", segments=32, amplitude=0.12)\nplt.figure(figsize=(9, 2.8))\nplt.plot(np.arange(33)/32, np.r_[surface.heights, surface.heights[0]], ".-")\nplt.xlabel("X / period"); plt.ylabel("Height / period"); plt.show()')
    md('## 2. Lighting, shadows, and Lambertian output\n\nLight vectors point toward the source. A source at azimuth 180 degrees is on the left. Kappa zero means uniform illumination; higher values concentrate the light. A single segment can be partially shadowed, so several positions are sampled.')
    code('directions = sphere_directions(4096)\nmean_light = light_direction(180, 30)\nx, luminance = render(surface, directions, mean_light, 8, samples_per_segment=7)\n_, no_shadows = render(surface, directions, mean_light, 8, samples_per_segment=7, shadows=False)\nplt.figure(figsize=(9,3))\nplt.plot(x, luminance, label="With shadows")\nplt.plot(x, no_shadows, "--", label="Shadows disabled")\nplt.xlabel("X / period"); plt.ylabel("Relative linear luminance"); plt.legend(); plt.show()')
    md('## 3. Physical checks\n\nThese include an independent ray-intersection check, a flat-surface analytic case, light normalization, and invariances.')
    code('checks = run_checks()\nfor name, passed in checks.items():\n    print(("PASS" if passed else "FAIL"), name)\nassert all(checks.values())')
    md('## 4. Inverse rendering\n\nThe optimizer adjusts geometry and three lighting parameters to match the provisional triangle wave. It fixes mean height to zero, uses fixed total angular radiance, and adds a small curvature penalty. Four geometry families are compared. Read saved results below; to reproduce the searches separately, run `python run_all.py --full`.')
    code('analysis = json.loads((root / "results/optimization/analysis.json").read_text())\nassert analysis["status"] == "complete"\nfor record in analysis["selected_fits"]:\n    scores = record["evaluation_metrics"]\n    print(f"{record[\'family\']:12s} RMSE={scores[\'rmse\']:.5f}  MAE={scores[\'mae\']:.5f}  R²={scores[\'r_squared\']:.4f}")\nprint("Evaluation uses 16,384 directions and 15 samples per segment.")')
    md('## 5. Inspect a fitted candidate\n\nThe free surface is not constrained to be a rectangular square wave. A good luminance match does not prove that the shape is the one perceived by observers.')
    code('best = next(r for r in analysis["selected_fits"] if r["family"] == "free")\nfitted, mu, kappa = decode(best["parameters"], "free", analysis["config"]["segments"])\nx, y = render(fitted, sphere_directions(16384), mu, kappa, samples_per_segment=15)\nfig, axes = plt.subplots(1, 2, figsize=(11, 3.3))\naxes[0].plot(np.arange(17)/16, np.r_[fitted.heights, fitted.heights[0]], "o-")\naxes[0].set(xlabel="X / period", ylabel="Height / period", title="Fitted free geometry")\naxes[1].plot(x, triangle_target(x), label="Provisional target")\naxes[1].plot(x, y, label="Candidate render")\naxes[1].set(xlabel="X / period", ylabel="Relative linear luminance")\naxes[1].legend(); plt.tight_layout(); plt.show()\nprint("Lighting:", {key: best[key] for key in ("azimuth_deg", "elevation_deg", "kappa")})')
    md('## 6. Numerical resolution and sensitivity\n\nMidpoint-only evaluation can make the fit look almost exact while hiding variation within segments. Increasing N changes geometry flexibility; increasing the direction count checks the light integral for a fixed geometry. The N=32 case below is one additional warm-started search, not a three-seed comparison.')
    code('print("Within-segment sampling (same N=16 fit):")\nfor row in analysis["convergence"]:\n    if row["varied"] == "samples_per_segment":\n        print(f"{row[\'value\']:2d} samples: RMSE {row[\'rmse\']:.5f}")\nprint("Sensitivity cases:")\nfor record in analysis["sensitivity"]:\n    print(f"{record[\'label\']:20s} RMSE {record[\'evaluation_metrics\'][\'rmse\']:.5f}")')
    md('## 7. Limits and next decisions\n\nThe global free-surface searches reached iteration limits; local Powell termination does not prove global optimality. The model excludes interreflection and overhangs. Shape and light are not uniquely identifiable from one profile. No participant study has been run. Further evaluation can vary the target, admissible shapes, lighting constraints, and error tolerance. See docs/RESULTS.md for the full findings and docs/LIMITATIONS.md for limitations and future work.')
    notebook=nbformat.v4.new_notebook(cells=cells,metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python','version':sys.version.split()[0]}})
    ns={}
    count=0
    old_cwd=Path.cwd()
    os.chdir(ROOT)
    try:
        for cell in notebook.cells:
            if cell.cell_type!='code':continue
            count+=1
            outputs=[]
            stream=io.StringIO()
            def show(*args,**kwargs):
                for number in plt.get_fignums():
                    fig=plt.figure(number)
                    buf=io.BytesIO();fig.savefig(buf,format='png',dpi=130,bbox_inches='tight')
                    outputs.append(nbformat.v4.new_output('display_data',data={'image/png':base64.b64encode(buf.getvalue()).decode(),'text/plain':'<matplotlib figure>'}))
                    plt.close(fig)
            plt.show=show
            with contextlib.redirect_stdout(stream):exec(compile(cell.source,'simulation_walkthrough.ipynb','exec'),ns)
            if stream.getvalue():outputs.append(nbformat.v4.new_output('stream',name='stdout',text=stream.getvalue()))
            cell.outputs=outputs;cell.execution_count=count
        nbformat.validate(notebook)
        nbformat.write(notebook,ROOT/'simulation_walkthrough.ipynb')
    finally:os.chdir(old_cwd)
    print('Executed and saved',count,'notebook code cells.')


if __name__=='__main__':
    data=json.loads((ROOT/'results/optimization/analysis.json').read_text())
    build_best_figure(data)
    build_summaries(data)
    build_notebook()
