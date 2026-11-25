"""Fit the flat, sinusoidal, and square-like fixed-shape families."""
import argparse
from pathlib import Path
from fit import ROOT, fit_families, load_config, output_path
import fixed_shape


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "config.json")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "data")
    args = parser.parse_args()
    fit_families(load_config(args.config), output_path(args.output), fixed_shape.FAMILIES,
                 status="fixed_complete")

