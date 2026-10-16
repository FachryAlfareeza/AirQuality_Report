# FINAL — Jakarta air quality, January–December 2025

## Period and result
The interval is January 1, 2025 at 00:00 inclusive to January 1, 2026 at 00:00 exclusive, in Asia/Jakarta (UTC+7). It includes all of December 31, 2025. Timestamps in the CSV tables use UTC.

All 17 code cells ran successfully in order. Final result: **41,629 rows and 12 columns**. Available air readings span January 1 at 00:00 through December 31 at 23:00 Jakarta time. All 12 months are represented; individual sensors have gaps.

Starting tables: 24,316 OpenAQ records, 21,024 PurpleAir records, and 38,724 weather station-hours. Cleaning retains 21,356 OpenAQ and 20,273 PurpleAir records. The selected weather station is 96745 (Jakarta / Observatory), with 8,627 available hours. The final table has 909 unmatched station/weather entries per column and 1,093 missing rain entries. Missing weather stays missing.

## Files
- air-quality_self.ipynb — simplified code with executed tables and four graphs.
- data/air_quality_2025/raw_responses/ — archived API responses and request manifest used by the notebook. No API keys are stored here.
- data/air_quality_2025/Stations_downloaded.csv and Weather_downloaded.csv — saved weather inputs.
- outputs/openaq_raw.csv, purpleair_raw.csv, weather_raw.csv — loaded starting tables before cleaning.
- outputs/analysis_ready.csv — final merged table.
- outputs/01_cleaning_boxplots.png through 04_hourly_air_quality.png — regenerated notebook figures.
- outputs/monthly_coverage.csv — rows and reporting sensors per source and Jakarta month.
- outputs/row_counts.csv, weather_correlation.csv, summary.json — results from this run.
- air_quality_report.tex and air_quality_report.pdf — matching 2025 article; PDF compiled in Overleaf.
- run_notebook.py — executes and saves all notebook outputs.
- export_outputs.py — regenerates the exported CSV tables, summaries, and PNG graphs from the notebook code and saved inputs.
- requirements.txt — Python dependencies.
- SHA256SUMS.json — file checksums for this completed package.

## Rerun
Install requirements in your Python environment with `python -m pip install -r requirements.txt`.
Open the notebook with that environment and run all cells, or run `python run_notebook.py` from FINAL.
To refresh the separate CSV and PNG outputs, run `python export_outputs.py` as well.
Saved data are enabled by default, so rerunning needs no network requests or API keys. For a new download, set the API-key environment variables listed in the configuration cell and set USE_SAVED_DATA=False. Successful requests are cached. OpenAQ uses 30-day windows and pagination; PurpleAir uses windows of up to 180 days. The exported files must be regenerated after changing code or inputs.

Overleaf edit link: https://www.overleaf.com/2845167198zwqhgcpzpgqn#a81b27

The Canva presentation was intentionally left unchanged and still describes the earlier January 2024 run. Its old speaking notes and the old package are preserved outside FINAL in backups/FINAL_January_2024. They are not part of these 2025 results.

This simplified version has no interpolation or PCA. The correlation check removes no weather columns in this run. No Excel workbook is generated.

Sources: https://docs.openaq.org/ ; https://api.purpleair.com/ ; https://dev.meteostat.net/python/api/meteostat.hourly
PurpleAir request-window reference: https://community.purpleair.com/t/loop-api-calls-for-historical-data/4623
