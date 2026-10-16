"""Build a fresh package for the current 2025 notebook; publish after validation."""
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).with_name('build_final_2025.py')), run_name='__main__')
print('Next: execute and export the staging notebook, then validate before replacing FINAL.')
