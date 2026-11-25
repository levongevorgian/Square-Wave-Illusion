"""Fit the N-vertex free surface, warm-started from fixed-shape results."""
import argparse
import json
from pathlib import Path

from fit import ROOT, encode_free, fit_families, load_config, output_path, LIGHT_PARAMETER_COUNT
from model import Surface
import fixed_shape
import free_shape


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "config.json")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "data")
    args = parser.parse_args()
    config = load_config(args.config)
    destination = output_path(args.output)
    result_path = destination / "fits.json"
    if not result_path.exists():
        raise FileNotFoundError("Run fit_fixed.py first to create fixed-shape starting results.")
    prior = json.loads(result_path.read_text())
    if prior.get("status") != "fixed_complete":
        raise ValueError("Expected completed fixed-shape fits. Run fit_fixed.py first.")
    candidates = [record for record in prior["runs"] if record["family"] in fixed_shape.FAMILIES]
    selected = min(candidates, key=lambda record: record["objective"])
    initial = encode_free(Surface(selected["heights"]), selected["parameters"][-LIGHT_PARAMETER_COUNT:])
    fit_families(config, destination, free_shape.FAMILIES,
                 initial_by_family={"free": initial}, prior=prior, status="complete")

