"""Shared objective and optimizer for the fixed-shape and free-shape fits."""
import json
import time
import argparse
from pathlib import Path

import numpy as np
from scipy.optimize import differential_evolution, minimize

from model import Surface, sphere_directions, light_direction, render, triangle_target
import fixed_shape
import free_shape

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = {
    "segments": 32, "directions": 1024, "samples_per_segment": 3,
    "seeds": [11, 29, 47], "maxiter": 160, "popsize": 7,
    "curvature_weight": 0.00001, "height_bound": 0.25, "slope_bound": 6.0,
    "target_mean": 1.0, "target_contrast": 0.6,
    "azimuth_bounds": [0.0, 180.0], "elevation_bounds": [5.0, 85.0],
    "kappa_bounds": [0.0, 30.0], "intensity_bounds": [0.2, 3.0],
    "target_shift_bounds": [-0.3, 0.3],
}

FAMILIES = fixed_shape.FAMILIES + free_shape.FAMILIES
LIGHT_PARAMETER_COUNT = 5

# Both shape modules follow the same registry interface. The optimizer does not
# need model-specific branches to decode a shape or assemble parameter bounds.
SHAPE_DECODERS = {
    **{family: (lambda values, count, family=family: fixed_shape.decode(values, family, count))
       for family in fixed_shape.FAMILIES},
    **{family: free_shape.decode for family in free_shape.FAMILIES},
}
SHAPE_PARAMETER_COUNTS = {
    **{family: (lambda count, family=family: fixed_shape.parameter_count(family, count))
       for family in fixed_shape.FAMILIES},
    **{family: free_shape.parameter_count for family in free_shape.FAMILIES},
}
SHAPE_BOUNDS = {
    **{family: (lambda config, family=family: fixed_shape.bounds(family, config))
       for family in fixed_shape.FAMILIES},
    **{family: free_shape.bounds for family in free_shape.FAMILIES},
}


def shape_parameter_count(family, segments):
    try:
        return SHAPE_PARAMETER_COUNTS[family](segments)
    except KeyError as error:
        raise ValueError(f"Unknown shape family: {family}") from error


def decode(parameters, family, segments):
    """Return geometry, direction, concentration, intensity, and target shift."""
    p = np.asarray(parameters, dtype=float)
    shape_count = shape_parameter_count(family, segments)
    shape_values = p[:shape_count]
    azimuth, elevation, kappa, intensity, target_shift = p[shape_count:]
    try:
        surface = SHAPE_DECODERS[family](shape_values, segments)
    except KeyError as error:
        raise ValueError(f"Unknown shape family: {family}") from error
    return surface, light_direction(azimuth, elevation), float(kappa), float(intensity), float(target_shift)


def encode_free(surface, lighting_and_target):
    return np.r_[free_shape.encode(surface), lighting_and_target]


def metrics(prediction, target):
    residual = prediction - target
    total = np.sum((target - target.mean()) ** 2)
    return {
        "rmse": float(np.sqrt(np.mean(residual ** 2))),
        "mae": float(np.mean(np.abs(residual))),
        "max_abs_error": float(np.max(np.abs(residual))),
        "mean_luminance": float(prediction.mean()),
        "sampled_Michelson_contrast": float((prediction.max() - prediction.min()) / (prediction.max() + prediction.min())),
        "r_squared": float(1 - np.sum(residual ** 2) / total) if total > 0 else None,
    }


def bounds_for(family, config):
    try:
        geometry = SHAPE_BOUNDS[family](config)
    except KeyError as error:
        raise ValueError(f"Unknown shape family: {family}") from error
    lighting = [config["azimuth_bounds"], config["elevation_bounds"], config["kappa_bounds"],
                config["intensity_bounds"], config["target_shift_bounds"]]
    return geometry + lighting


def objective(parameters, family, config, directions):
    surface, mean_direction, kappa, intensity, target_shift = decode(parameters, family, config["segments"])
    slopes = np.diff(np.r_[surface.heights, surface.heights[0]]) * config["segments"]
    height_excess = np.maximum(0, np.abs(surface.heights) - config["height_bound"])
    slope_excess = np.maximum(0, np.abs(slopes) - config["slope_bound"])
    penalty = 1000 * (np.sum(height_excess ** 2) + np.sum(slope_excess ** 2))
    if penalty > 1:
        return float(penalty + 10)
    x, luminance = render(surface, directions, mean_direction, kappa,
                          samples_per_segment=config["samples_per_segment"],
                          light_intensity=intensity)
    target = triangle_target(x, mean=config["target_mean"], contrast=config["target_contrast"],
                             vertical_shift=target_shift)
    curvature = (np.roll(surface.heights, 1) - 2 * surface.heights + np.roll(surface.heights, -1)) * config["segments"] ** 2
    return float(np.mean((luminance - target) ** 2) + config["curvature_weight"] * np.mean(curvature ** 2) + penalty)


def fit_one(family, seed, config, initial=None):
    directions = sphere_directions(config["directions"])
    bounds = bounds_for(family, config)
    fun = lambda p: objective(p, family, config, directions)
    start = time.perf_counter()
    options = dict(bounds=bounds, seed=seed, maxiter=config["maxiter"], popsize=config["popsize"],
                   tol=1e-6, atol=1e-9, polish=False, updating="immediate")
    candidates = []
    if initial is not None:
        rng = np.random.default_rng(seed)
        low, high = np.array(bounds).T
        size = config["popsize"] * len(bounds)
        population = rng.uniform(low, high, size=(size, len(bounds)))
        spread = (high - low) * 0.025
        population[:size * 3 // 4] = np.clip(initial + rng.normal(size=(size * 3 // 4, len(bounds))) * spread, low, high)
        population[0] = initial
        options["init"] = population
        candidates.append((fun(initial), np.array(initial), "fixed-shape initialization"))
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
    surface, mean_direction, kappa, intensity, target_shift = decode(parameters, family, config["segments"])
    x, luminance = render(surface, directions, mean_direction, kappa,
                          samples_per_segment=config["samples_per_segment"], light_intensity=intensity)
    target = triangle_target(x, mean=config["target_mean"], contrast=config["target_contrast"],
                             vertical_shift=target_shift)
    light_values = parameters[shape_parameter_count(family, config["segments"]):]
    return {
        "family": family, "seed": seed, "parameters": parameters.tolist(),
        "heights": surface.heights.tolist(), "mean_light_vector": mean_direction.tolist(),
        "azimuth_deg": float(light_values[0]), "elevation_deg": float(light_values[1]),
        "kappa": kappa, "light_intensity": intensity, "target_vertical_shift": target_shift,
        "objective": value, "training_metrics": metrics(luminance, target),
        "selected_candidate": selected, "global_optimizer_success": bool(global_result.success),
        "global_optimizer_message": str(global_result.message), "global_evaluations": int(global_result.nfev),
        "local_optimizer_success": bool(local_result.success), "local_optimizer_message": str(local_result.message),
        "seconds": time.perf_counter() - start,
    }


def fit_families(config, destination, families, initial_by_family=None, prior=None, status="complete"):
    destination.mkdir(parents=True, exist_ok=True)
    result = prior or {"config": config, "status": "in_progress", "runs": []}
    result["config"] = config
    result["status"] = "in_progress"
    initial_by_family = initial_by_family or {}
    save = lambda: (destination / "fits.json").write_text(json.dumps(result, indent=2) + "\n")
    for family in families:
        initial = initial_by_family.get(family)
        for seed in config["seeds"]:
            record = fit_one(family, seed, config, initial)
            result["runs"].append(record)
            save()
            print(f"{family:12s} seed={seed} RMSE={record['training_metrics']['rmse']:.5f} objective={record['objective']:.6f} {record['seconds']:.1f}s", flush=True)
    result["status"] = status
    save()
    return result


def load_config(path=None):
    path = Path(path) if path else ROOT / "config.json"
    return json.loads(path.read_text())


def output_path(path=None):
    return Path(path) if path else ROOT / "results" / "data"


def run(config=None, destination=None):
    """Run both stages in order; dedicated entrypoints can run either stage."""
    config = config or load_config()
    destination = output_path(destination)
    fixed = fit_families(config, destination, fixed_shape.FAMILIES, status="fixed_complete")
    fixed_candidates = [r for r in fixed["runs"] if r["family"] in fixed_shape.FAMILIES]
    selected = min(fixed_candidates, key=lambda record: record["objective"])
    initial = encode_free(Surface(selected["heights"]), selected["parameters"][-LIGHT_PARAMETER_COUNT:])
    return fit_families(config, destination, free_shape.FAMILIES,
                        initial_by_family={"free": initial}, prior=fixed, status="complete")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "config.json")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "data")
    args = parser.parse_args()
    run(load_config(args.config), output_path(args.output))

