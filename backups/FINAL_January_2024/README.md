# FINAL — Jakarta air quality

Start with air-quality_self.ipynb. Run all cells from top to bottom with FINAL as the working directory. The notebook defaults to saved data and needs no API key in that mode.

## Contents
- air-quality_self.ipynb: simplified notebook with executed tables and four plots.
- data/air_quality_snapshot/: unchanged saved API JSON responses, response manifest, weather observations and station metadata used as inputs.
- outputs/openaq_raw.csv, purpleair_raw.csv, weather_raw.csv: loaded starting tables, before cleaning; original response files remain in data/.
- outputs/analysis_ready.csv: final merged table, 6,159 rows and 12 columns.
- outputs/01_...png through 04_...png: the four notebook figures.
- outputs/summary.json: numerical results from the saved run.
- air_quality_report.pdf: three-page article compiled successfully in Overleaf.
- air_quality_report.tex: plain-language article matching this simplified notebook.
- presentation_notes.md: suggested speaking notes, approximately 7 minutes 30 seconds.
- requirements.txt: Python dependencies.
- run_notebook.py: optional command-line runner that executes and saves the notebook outputs.

## Run
Install the requirements in your Python environment, select it as the notebook kernel, and run all cells. Or run `python run_notebook.py` from this folder (with the requirements installed).

The CSV and PNG outputs were exported when this folder was prepared. The notebook itself displays results and does not automatically rewrite those exports. No Excel spreadsheet is created.

API credentials were removed from the packaged copy. For optional live requests, set the API-key environment variables named in its configuration cell. The original working notebook is preserved outside FINAL.

Canva edit link: https://canva.link/09zg6t50lykrkqz
Overleaf edit link: https://www.overleaf.com/2845167198zwqhgcpzpgqn#a81b27

This simplified version has no PCA or interpolation. It checks correlated weather attributes but removes none for this dataset. It should not be described as completing a PCA analysis.
