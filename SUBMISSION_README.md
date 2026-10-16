# Jakarta air-quality preprocessing project

## Main files

- `air-quality_self.ipynb`: all Python code, explicit dataset sources, executed output, nine figures, cleaning, integration, correlation/covariance analysis, outlier-filtered PCA and findings.
- `air_quality_report.tex`: standalone LaTeX report source with embedded vector figures.
- `air_quality_report.pdf`: visually checked six-page PDF companion. It was rendered separately because the app's native LaTeX compiler failed with “Unable to find standard directories for platform.” Compilation of the `.tex` file remains unverified.
- `air_quality_audit.xlsx`: complete raw/intermediate/final snapshots, source catalog, change log, PCA outputs, four native Excel charts and nine diagnostic figures.
- `graphs/`: the nine diagnostic PNGs.
- `data/air_quality_snapshot/`: unchanged saved API responses and original Meteostat tables needed for offline reproduction.
- `requirements.txt`: Python dependencies.

## Reproduce

1. Extract the whole package, keeping the notebook beside `data/`.
2. Install `requirements.txt` in the selected Jupyter Python environment.
3. Open `air-quality_self.ipynb` and run all cells in order.

`USE_SAVED_DATA = True` is the default and requires no API credentials. A fresh download requires setting it to `False` and setting `OPENAQ_API_KEY` and `PURPLEAIR_READ_KEY` as environment variables. Changing the area or date range requires a new download. New exports are written into a timestamped folder under `outputs/air-quality-review/`.

## Findings

- Final integration: 7,511 sensor-hours and 22 columns.
- Resampling exposes 615 missing hours; short-gap interpolation fills 138 values.
- The primary openly licensed cohort has six OpenAQ sensors linked to Meteostat. Other accessible observations remain supplementary.
- Typical-condition PCA removes 94 IQR extremes and excludes incomplete feature vectors, leaving 1,169 records.
- Five of six components retain 99.28% of standardized variation. A run without IQR removal also requires five components.

## Before submission

Confirm that the dataset selection is unique within the class. No file can establish that independently. The assignment's stated deadline is in September 2025; this snapshot was collected in September 2026 and has not been backdated. Observation dates are January 2024.

The presentation was intentionally not prepared.
