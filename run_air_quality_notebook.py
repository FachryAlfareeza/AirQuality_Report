"""Execute the notebook in order and retain outputs, including any failure."""
from pathlib import Path
import sys

import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpec

path = Path(__file__).with_name("air-quality_self.ipynb")
notebook = nbformat.read(path, as_version=4)
for cell in notebook.cells:
    if cell.cell_type == "code":
        cell.outputs = []
        cell.execution_count = None

manager = KernelManager(kernel_name="python3")
manager._kernel_spec = KernelSpec(
    argv=[sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
    display_name="Python (project .venv)",
    language="python",
)

def report(cell, cell_index, **kwargs):
    print(f"Running cell {cell_index + 1}: {cell.source.splitlines()[0]}", flush=True)

def report_result(cell, cell_index, **kwargs):
    for output in cell.get("outputs", []):
        if output.output_type == "stream":
            print(output.text, end="", flush=True)

client = NotebookClient(
    notebook, km=manager, timeout=1200,
    resources={"metadata": {"path": str(path.parent)}},
    on_cell_start=report,
    on_cell_executed=report_result,
)
try:
    client.execute()
    print("All cells completed successfully.", flush=True)
finally:
    nbformat.write(notebook, path)
