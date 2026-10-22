"""Reproduce the reference pipeline or run a quick physics/regression check."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent


def main():
    p=argparse.ArgumentParser(description=__doc__)
    group=p.add_mutually_exclusive_group(required=True)
    group.add_argument('--full',action='store_true')
    group.add_argument('--quick',action='store_true')
    args=p.parse_args()
    env=os.environ.copy()
    env['OPENBLAS_NUM_THREADS']='1'
    env.setdefault('MPLBACKEND','Agg')
    commands=[['validate.py'],['run_demo.py']]
    if args.full:
        commands += [['fit.py'],['analyze.py'],['build_review.py']]
    commands += [['-m','unittest','-v','test_project.py']]
    for command in commands:
        print('\nRunning '+' '.join(command),flush=True)
        subprocess.run([sys.executable,*command],cwd=ROOT,env=env,check=True)
    print('\nCompleted. See README.md and docs/RESULTS.md. PDF rebuild is optional: python build_report.py')


if __name__=='__main__':main()
