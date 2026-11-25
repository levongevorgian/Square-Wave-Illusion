"""Run the quick checks or reproduce the full fitting and analysis pipeline."""

import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--full", action="store_true")
    mode.add_argument("--quick", action="store_true")
    args = parser.parse_args()

    env = os.environ.copy()
    env["OPENBLAS_NUM_THREADS"] = "1"
    env.setdefault("MPLBACKEND", "Agg")

    commands = [["src/demo.py"]]
    if args.full:
        commands.extend(
            [["src/fit_fixed.py"], ["src/fit_free.py"], ["src/analyze.py"]]
        )
    commands.append(["-m", "unittest", "discover", "-s", "tests", "-v"])

    for command in commands:
        print("\nRunning " + " ".join(command), flush=True)
        subprocess.run(
            [sys.executable, *command], cwd=ROOT, env=env, check=True
        )

    print("\nCompleted. Figures are in results/figures and data in results/data.")


if __name__ == "__main__":
    main()
