"""Run the complete local pipeline from preserved raw snapshots."""
import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--skip-preprocess', action='store_true')
args = parser.parse_args()
steps = ([] if args.skip_preprocess else ['preprocess.py']) + ['eda.py', 'model.py']
for step in steps:
    print(f'Running {step}', flush=True)
    subprocess.run([sys.executable, str(ROOT / 'src' / step)], cwd=ROOT, check=True)
print('Completed. Launch: python -m streamlit run dashboard/app.py', flush=True)
