"""Reproducible bounded inverse rendering; no human data or perceptual claims."""
import argparse
import csv
import json
import time
from pathlib import Path
import numpy as np
from scipy.optimize import differential_evolution, minimize
from model import Surface, sphere_directions, light_direction, render, triangle_target

ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG = {
    "segments": 16, "directions": 1024, "samples_per_segment": 3,
    "seeds": [11, 29, 47], "maxiter": 160, "popsize": 7,
    "curvature_weight": 0.00001,
    "height_bound": 0.25, "slope_bound": 6.0,
    "target_mean": 1.0, "target_contrast": 0.6,
    "azimuth_bounds": [0.0, 180.0], "elevation_bounds": [5.0, 85.0],
    "kappa_bounds": [0.0, 30.0],
}


def decode(parameters, family, segments):
    p = np.asarray(parameters)
    if family == "flat":
        z = np.zeros(segments)
    elif family in ("sinusoid", "square_like"):
        amplitude, phase = p[:2]
        c = np.cos(2*np.pi*(np.arange(segments)/segments-phase))
        z = amplitude*c if family == "sinusoid" else amplitude*np.tanh(4*c)/np.tanh(4)
    elif family == "free":
        # N-1 coordinates; recover the last to fix the mean-height gauge.
        z = np.r_[p[:-3], -np.sum(p[:-3])]
    else:
        raise ValueError(f"Unknown family {family}")
    z = z-z.mean()
    return Surface(z), light_direction(p[-3], p[-2]), float(p[-1])


def encode_free(surface, lighting):
    return np.r_[surface.heights[:-1]-surface.heights.mean(), lighting]


def metrics(prediction, target):
    residual = prediction-target
    total = np.sum((target-target.mean())**2)
    return {"rmse": float(np.sqrt(np.mean(residual**2))),
            "mae": float(np.mean(np.abs(residual))),
            "max_abs_error": float(np.max(np.abs(residual))),
            "mean_luminance": float(prediction.mean()),
            "sampled_Michelson_contrast": float((prediction.max()-prediction.min())/(prediction.max()+prediction.min())),
            "r_squared": float(1-np.sum(residual**2)/total) if total > 0 else None}


def objective(parameters, family, config, directions):
    surface, mu, kappa = decode(parameters, family, config["segments"])
    slopes = np.diff(np.r_[surface.heights, surface.heights[0]])*config["segments"]
    height_excess = np.maximum(0, np.abs(surface.heights)-config["height_bound"])
    slope_excess = np.maximum(0, np.abs(slopes)-config["slope_bound"])
    penalty = 1000*(np.sum(height_excess**2)+np.sum(slope_excess**2))
    if penalty > 1:
        return float(penalty+10)
    x, y = render(surface, directions, mu, kappa,
                  samples_per_segment=config["samples_per_segment"])
    target = triangle_target(x, mean=config["target_mean"], contrast=config["target_contrast"])
    curvature = (np.roll(surface.heights, 1)-2*surface.heights+np.roll(surface.heights, -1))*config["segments"]**2
    return float(np.mean((y-target)**2)+config["curvature_weight"]*np.mean(curvature**2)+penalty)


def bounds_for(family, config):
    light = [config["azimuth_bounds"], config["elevation_bounds"], config["kappa_bounds"]]
    if family == "flat":
        return light
    if family == "free":
        return [(-config["height_bound"], config["height_bound"])]*(config["segments"]-1)+light
    return [(0, config["height_bound"]), (0, 1)]+light


def fit_one(family, seed, config, initial=None):
    directions = sphere_directions(config["directions"])
    bounds = bounds_for(family, config)
    fun = lambda p: objective(p, family, config, directions)
    start = time.perf_counter()
    options = dict(bounds=bounds, seed=seed, maxiter=config["maxiter"], popsize=config["popsize"],
                   tol=1e-6, atol=1e-9, polish=False, updating="immediate")
    candidates = []
    if initial is not None:
        # Build a population around an already fitted admissible surface, with
        # additional global samples. Preserve that baseline as a candidate.
        rng = np.random.default_rng(seed)
        low, high = np.array(bounds).T
        size = config["popsize"]*len(bounds)
        population = rng.uniform(low, high, size=(size, len(bounds)))
        population[:size*3//4] = np.clip(initial+rng.normal(size=(size*3//4,len(bounds)))*(high-low)*0.025, low, high)
        population[0] = initial
        options["init"] = population
        candidates.append((fun(initial), np.array(initial), "fixed-shape initialization"))
        # A local pass first can make progress from a useful geometric start.
        local = minimize(fun, initial, method="Powell", bounds=bounds,
                         options={"maxiter": 100, "maxfev": 8000, "xtol": 1e-6, "ftol": 1e-7})
        candidates.append((float(local.fun), local.x, "initial Powell refinement"))
        options["init"][1] = local.x
    global_result = differential_evolution(fun, **options)
    candidates.append((float(global_result.fun), global_result.x, "differential evolution"))
    local_result = minimize(fun, global_result.x, method="Powell", bounds=bounds,
                            options={"maxiter": 100, "maxfev": 10000, "xtol": 1e-6, "ftol": 1e-7})
    candidates.append((float(local_result.fun), local_result.x, "final Powell refinement"))
    value, parameters, selected = min(candidates, key=lambda item: item[0])
    surface, mu, kappa = decode(parameters, family, config["segments"])
    x,y = render(surface, directions, mu, kappa, samples_per_segment=config["samples_per_segment"])
    target = triangle_target(x, mean=config["target_mean"], contrast=config["target_contrast"])
    return {"family": family, "seed": seed, "parameters": parameters.tolist(),
            "heights": surface.heights.tolist(), "mean_light_vector": mu.tolist(),
            "azimuth_deg": float(parameters[-3]), "elevation_deg": float(parameters[-2]), "kappa": kappa,
            "objective": value, "training_metrics": metrics(y,target),
            "selected_candidate": selected,
            "global_optimizer_success": bool(global_result.success),
            "global_optimizer_message": str(global_result.message),
            "global_evaluations": int(global_result.nfev),
            "local_optimizer_success": bool(local_result.success),
            "local_optimizer_message": str(local_result.message),
            "seconds": time.perf_counter()-start}


def run(config, destination):
    destination.mkdir(parents=True, exist_ok=True)
    result = {"config": config, "status": "in_progress", "runs": []}
    save = lambda: (destination/"fits.json").write_text(json.dumps(result,indent=2)+"\n")
    initial = None
    for family in ("flat", "sinusoid", "square_like", "free"):
        for seed in config["seeds"]:
            record = fit_one(family, seed, config, initial if family == "free" else None)
            result["runs"].append(record)
            save()
            print(f"{family:12s} seed={seed} RMSE={record['training_metrics']['rmse']:.5f} objective={record['objective']:.6f} {record['seconds']:.1f}s", flush=True)
        if family == "square_like":
            fixed = min((r for r in result["runs"] if r["family"] in ("sinusoid", "square_like")), key=lambda r:r["objective"])
            initial = encode_free(Surface(fixed["heights"]), fixed["parameters"][-3:])
    result["status"] = "complete"
    save()
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT/"configs"/"reference.json")
    parser.add_argument("--output", type=Path, default=ROOT/"results"/"optimization")
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    run(config, args.output)
