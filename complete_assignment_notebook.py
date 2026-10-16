from pathlib import Path
import json

p = Path('air-quality_self.ipynb')
n = json.loads(p.read_text(encoding='utf-8'))
def new(source, kind='code'):
    c = dict(cell_type=kind, metadata={}, source=source.splitlines(keepends=True))
    if kind == 'code': c.update(execution_count=None, outputs=[])
    return c

sources = '''## Dataset sources, reproducibility and assignment scope

**Question:** How do cleaning, hourly alignment and weather integration change a January 2024 Jakarta PM2.5 dataset, and how many standardized components summarize its variation?

- **OpenAQ:** [dataset/API documentation](https://docs.openaq.org/), [location query](https://api.openaq.org/v3/locations?bbox=106.689,-6.370,106.978,-6.079&parameters_id=2&limit=1000), [licensing metadata](https://docs.openaq.org/resources/licenses). Provider names and licenses are retained below. OpenAQ includes several sensor technologies; it is not uniformly a reference-monitor network.
- **Meteostat:** [hourly weather](https://dev.meteostat.net/python/api/meteostat.hourly), [data license](https://dev.meteostat.net/license). Used for temperature, humidity, rainfall, wind speed and pressure.
- **PurpleAir (supplementary comparison):** [API](https://api.purpleair.com/), [access documentation](https://community.purpleair.com/t/about-the-purpleair-api/7145). Public-sensor history requires a key and may require API credits. Public visibility alone does not establish an open redistribution license.

The **primary open-data PCA cohort** uses only OpenAQ sensors whose returned metadata explicitly names US Public Domain, CC0 1.0 or CC BY 4.0, plus Meteostat weather. Other OpenAQ records and PurpleAir remain labeled supplementary observations in the integration audit. This avoids assuming that all accessible data have the same license.

The geographical bounds, fixed month, source combination, sensor selection and before/after audit make the analysis specific. **Uniqueness across classmates must be confirmed with the instructor/class dataset register.** No plagiarism or uniqueness guarantee is possible from these files alone.

Default execution replays the saved, unchanged source responses in `data/air_quality_snapshot` so results do not depend on API availability or credentials. Set `USE_SAVED_DATA = False` and environment variables `OPENAQ_API_KEY` and `PURPLEAIR_READ_KEY` for a fresh download. Install `requirements.txt` into the notebook kernel if necessary. Download snapshots were collected in September 2026; observation dates are January 2024. The assignment's stated 2025 deadline is historical and is not represented as having been met.
'''

pca = r'''# Primary openly licensed cohort: outlier removal and standardized PCA.
permissive = {"US Public Domain", "CC0 1.0", "CC BY 4.0"}
locations = get_openaq_results("https://api.openaq.org/v3/locations", {"X-API-Key": OPENAQ_API_KEY},
                             {"bbox": f"{WEST},{SOUTH},{EAST},{NORTH}", "parameters_id": 2, "limit": 1000})
source_rows = []
for location in locations:
    for sensor in location.get("sensors", []):
        if sensor.get("parameter", {}).get("id") == 2:
            licenses = [lic.get("name", "") for lic in location.get("licenses") or []]
            source_rows.append({"site_id": f"OpenAQ_{sensor['id']}", "location": location.get("name"),
                                "provider": (location.get("provider") or {}).get("name"),
                                "licenses": "; ".join(licenses) or "Not stated in response",
                                "explicit_open_license": any(x in permissive for x in licenses),
                                "source_url": f"https://api.openaq.org/v3/sensors/{sensor['id']}/hours"})
source_catalog = pd.DataFrame(source_rows)
source_catalog["downloaded_rows"] = source_catalog.site_id.map(openaq_raw.site_id.value_counts()).fillna(0).astype(int)
display(source_catalog.loc[source_catalog.downloaded_rows.gt(0)])
open_ids = source_catalog.loc[source_catalog.explicit_open_license, "site_id"]
primary = analysis_ready.loc[analysis_ready.site_id.isin(open_ids)].copy()
snapshot("Primary open data", primary, "OpenAQ sensors with explicit permissive license metadata, joined to Meteostat.", "Final", ["site_id", "time"])

# Fixed raw sensor-specific IQR bounds from the diagnostics section are reused.
primary_flags = primary.merge(outlier_bounds, on="site_id", how="left", validate="many_to_one")
primary_flags["iqr_outlier"] = primary_flags.pm25.lt(primary_flags.lower) | primary_flags.pm25.gt(primary_flags.upper)
trimmed = primary_flags.loc[~primary_flags.iqr_outlier, primary.columns].copy()
snapshot("Outlier filtered", trimmed, "Sensor-specific 1.5 × IQR extremes removed for typical-condition PCA only; original high readings remain in Final.", "Primary open data", ["site_id", "time"])

candidate_features = [c for c in ["pm25", "temperature", "humidity", "rain", "wind_speed", "pressure"] if c in analysis_ready]
complete = trimmed.dropna(subset=candidate_features).copy()
snapshot("PCA complete cases", complete, "Only rows observed or short-gap-imputed in every selected numerical feature enter PCA.", "Outlier filtered", ["site_id", "time"])
features = [c for c in candidate_features if complete[c].std(ddof=1) > 0]
if len(complete) < 3 or len(features) < 2:
    raise ValueError("Insufficient complete, nonconstant features for PCA")

def fit_pca(frame, selected_features):
    x = frame[selected_features].to_numpy(dtype=float)
    mean, scale = x.mean(axis=0), x.std(axis=0, ddof=1)
    z = (x - mean) / scale
    u, singular, vt = np.linalg.svd(z, full_matrices=False)
    # Fix signs for reproducible loading orientation.
    for j in range(len(vt)):
        if vt[j, np.abs(vt[j]).argmax()] < 0:
            vt[j] *= -1
            u[:, j] *= -1
    eigenvalues = singular ** 2 / (len(x) - 1)
    ratios = eigenvalues / eigenvalues.sum()
    scores = z @ vt.T
    return z, mean, scale, vt, eigenvalues, ratios, scores

z, centers, scales, components, eigenvalues, ratios, scores = fit_pca(complete, features)
cumulative = np.cumsum(ratios)
k = int(np.searchsorted(cumulative, .95) + 1)
variance = pd.DataFrame({"component": [f"PC{i+1}" for i in range(len(ratios))],
                         "eigenvalue": eigenvalues, "variance_fraction": ratios, "cumulative_fraction": cumulative})
loadings = pd.DataFrame(components.T, index=features, columns=variance.component).reset_index(names="feature")
scaling = pd.DataFrame({"feature": features, "mean": centers, "sample_std": scales})
pca_scores = complete[["source", "site_id", "time"]].reset_index(drop=True)
for j in range(k): pca_scores[f"PC{j+1}"] = scores[:, j]
covariance = pd.DataFrame(np.cov(z, rowvar=False), index=features, columns=features).reset_index(names="feature")
reconstruction_rmse = float(np.sqrt(np.mean((z - scores[:, :k] @ components[:k]) ** 2)))
untrimmed_complete = primary.dropna(subset=features)
*_, full_ratios, _ = fit_pca(untrimmed_complete, features)
sensitivity = pd.DataFrame([
    {"cohort": "Complete cases without IQR removal", "rows": len(untrimmed_complete), "components_95pct": int(np.searchsorted(np.cumsum(full_ratios), .95) + 1), "pc1_fraction": full_ratios[0]},
    {"cohort": "Complete cases after IQR removal", "rows": len(complete), "components_95pct": k, "pc1_fraction": ratios[0]},
])
print(f"PCA: {len(complete):,} rows; {len(features)} standardized features -> {k} components; {cumulative[k-1]:.2%} variance retained.")
print(f"IQR rows removed: {primary_flags.iqr_outlier.sum():,}; additional incomplete rows excluded: {len(trimmed)-len(complete):,}")
print(f"Standardized reconstruction RMSE: {reconstruction_rmse:.4f}")
display(variance); display(loadings); display(sensitivity)

fig, axes = plt.subplots(1, 2, figsize=(13, 5))
axes[0].bar(variance.component, ratios * 100, color="#2878b5", label="Individual")
axes[0].plot(variance.component, cumulative * 100, marker="o", color="#d95f02", label="Cumulative")
axes[0].axhline(95, linestyle="--", color="grey", label="95% target")
axes[0].set(title="PCA explained variance", ylabel="Variance (%)", ylim=(0, 105)); axes[0].legend()
sns.heatmap(loadings.set_index("feature").iloc[:, :k], annot=True, fmt=".2f", cmap="vlag", center=0, ax=axes[1])
axes[1].set_title("Retained component coefficients")
save_graph(fig, "08_pca_variance_loadings.png")
fig, ax = plt.subplots(figsize=(9, 6))
for site_id in pca_scores.site_id.unique():
    mask = pca_scores.site_id.eq(site_id)
    ax.scatter(scores[mask, 0], scores[mask, 1], s=8, alpha=.4, label=site_id)
ax.set(xlabel=f"PC1 ({ratios[0]:.1%})", ylabel=f"PC2 ({ratios[1]:.1%})", title="Standardized open-data cohort in PCA space")
ax.legend(fontsize=8, markerscale=2)
save_graph(fig, "09_pca_scores.png")

assert np.allclose(np.cov(z, rowvar=False).diagonal(), 1)
assert np.isclose(ratios.sum(), 1)
assert cumulative[k-1] >= .95
assert k == 1 or cumulative[k-2] < .95
assert not pca_scores.isna().any().any()
'''

writer = r'''# Streaming Python Excel export: keeps all snapshots without loading a million styled cells.
import xlsxwriter
from importlib.metadata import version
tables.update({"Source catalog": source_catalog, "PCA variance": variance, "PCA loadings": loadings,
               "PCA scaling": scaling, "PCA covariance": covariance, "PCA scores": pca_scores,
               "PCA sensitivity": sensitivity})
# Ensure the added PCA and primary-cohort tables also have CSV copies.
for name, frame in tables.items():
    frame.to_csv(OUTPUT_DIR / (name.replace(" ", "_") + ".csv"), index=False)

workbook_path = OUTPUT_DIR / "air_quality_audit.xlsx"
with xlsxwriter.Workbook(workbook_path, {"constant_memory": True, "strings_to_formulas": False, "strings_to_urls": False}) as book:
    header = book.add_format({"bold": True, "bg_color": "#233B5D", "font_color": "white", "text_wrap": True, "valign": "vcenter", "font_name": "Arial", "font_size": 10})
    body = book.add_format({"font_name": "Arial", "font_size": 10})
    number = book.add_format({"num_format": "0.00", "font_name": "Arial", "font_size": 10})
    date = book.add_format({"num_format": "yyyy-mm-dd hh:mm", "font_name": "Arial", "font_size": 10})
    percent = book.add_format({"num_format": "0.0%", "font_name": "Arial", "font_size": 10})
    title = book.add_format({"bold": True, "font_size": 16, "font_name": "Arial", "font_color": "#233B5D"})
    note_format = book.add_format({"text_wrap": True, "valign": "top", "font_name": "Arial", "font_size": 10})
    overview = book.add_worksheet("Overview")
    overview.hide_gridlines(2); overview.set_column(0, 0, 32); overview.set_column(1, 17, 12)
    overview.write(1, 0, "Jakarta air quality: preprocessing review", title)
    overview.write(2, 0, f"{START_DATE} inclusive to {END_DATE} exclusive")
    for row, (label, value) in enumerate([
        ("Final sensor-hours", len(analysis_ready)), ("Processing snapshots", len(stage_data)),
        ("PM2.5 hours imputed", int(air_hourly.pm25_imputed.sum())),
        ("Primary PCA rows", len(complete)), ("Components retained", k),
        ("Variance retained", float(cumulative[k-1]))], 4):
        overview.write(row, 0, label); overview.write(row, 1, value, percent if label == "Variance retained" else body)
    overview.write(11, 0, "Frozen run snapshots. Raw data are preserved; IQR removal applies only to the PCA cohort.")
    for name, frame in tables.items():
        sheet = book.add_worksheet(name)
        sheet.hide_gridlines(2); sheet.freeze_panes(1, 0)
        sheet.set_row(0, 34); sheet.set_column(0, max(0, len(frame.columns)-1), 19, body)
        for col, label in enumerate(frame.columns):
            sheet.write(0, col, str(label), header)
            if label in ["time", "time_jakarta"]: sheet.set_column(col, col, 23, date)
            if label in ["record", "source_url"]: sheet.set_column(col, col, 65)
            if label in ["note", "explanation"]: sheet.set_column(col, col, 105, note_format)
        for row_index, row in enumerate(frame.itertuples(index=False, name=None), 1):
            if name in ["Method", "Stages"]: sheet.set_row(row_index, 44)
            for col, value in enumerate(row):
                if value is None or (not isinstance(value, (list, dict)) and pd.isna(value)): continue
                label = str(frame.columns[col])
                if isinstance(value, (pd.Timestamp, datetime)):
                    stamp = pd.Timestamp(value)
                    if stamp.tzinfo is not None: stamp = stamp.tz_localize(None)
                    sheet.write_datetime(row_index, col, stamp.to_pydatetime(), date)
                elif isinstance(value, (bool, np.bool_)): sheet.write_boolean(row_index, col, bool(value))
                elif isinstance(value, (int, np.integer)): sheet.write_number(row_index, col, int(value))
                elif isinstance(value, (float, np.floating)):
                    if np.isfinite(value): sheet.write_number(row_index, col, float(value), percent if "fraction" in label else number)
                else: sheet.write_string(row_index, col, str(value))
        if len(frame.columns): sheet.autofilter(0, 0, len(frame), len(frame.columns)-1)

    def excel_chart(sheet_name, chart_type, chart_title, position, y_label):
        frame = tables[sheet_name]
        chart = book.add_chart({"type": chart_type})
        for col in range(1, len(frame.columns)):
            chart.add_series({"name": [sheet_name, 0, col], "categories": [sheet_name, 1, 0, len(frame), 0],
                              "values": [sheet_name, 1, col, len(frame), col]})
        chart.set_title({"name": chart_title}); chart.set_y_axis({"name": y_label})
        chart.set_legend({"position": "bottom"}); chart.set_size({"width": 670, "height": 340})
        overview.insert_chart(position, chart)
    excel_chart("Chart stages", "column", "Rows and missing PM2.5 by stage", "A15", "Rows")
    excel_chart("Chart daily", "line", "Daily means by source", "I15", "PM2.5 (µg/m³)")
    excel_chart("Chart distribution", "column", "Final PM2.5 distribution", "A33", "Readings")
    # Native editable PCA chart includes variance fractions, not eigenvalues.
    chart = book.add_chart({"type": "line"})
    for col in [2, 3]:
        chart.add_series({"name": ["PCA variance", 0, col], "categories": ["PCA variance", 1, 0, len(variance), 0], "values": ["PCA variance", 1, col, len(variance), col]})
    chart.set_title({"name": "PCA explained variance"}); chart.set_y_axis({"num_format": "0%"})
    chart.set_size({"width": 670, "height": 340}); overview.insert_chart("I33", chart)
    gallery = book.add_worksheet("Diagnostic figures")
    gallery.hide_gridlines(2)
    for i, file in enumerate(graph_files):
        gallery.insert_image(i * 38, 0, file, {"x_scale": .45, "y_scale": .45})

source_means = analysis_ready.groupby("source").pm25.agg(["count", "mean", "median", "max"])
metrics = {
    "raw_openaq": len(openaq_raw), "raw_purpleair": len(purpleair_raw), "final_rows": len(analysis_ready),
    "final_columns": len(analysis_ready.columns), "hourly_added": len(air_hourly)-len(air_data),
    "imputed_pm25": int(air_hourly.pm25_imputed.sum()), "missing_pm25": int(analysis_ready.pm25.isna().sum()),
    "missing_rain": int(analysis_ready.rain.isna().sum()), "source_summary": json.loads(source_means.to_json(orient="index")),
    "rejected_purpleair": int(channel_flags.rejected.sum()), "primary_rows": len(primary),
    "primary_sites": int(primary.site_id.nunique()), "iqr_removed": int(primary_flags.iqr_outlier.sum()),
    "pca_rows": len(complete), "pca_excluded_missing": len(trimmed)-len(complete), "features": features, "pca_k": k,
    "variance": ratios.tolist(), "cumulative": cumulative.tolist(), "rmse": reconstruction_rmse,
    "loadings": loadings.to_dict(orient="records"), "sensitivity": sensitivity.to_dict(orient="records"),
    "weather_corr": matched_weather[weather_columns].corr().to_dict(),
    "distance_min": float(links.distance_to_weather_km.min()), "distance_max": float(links.distance_to_weather_km.max()),
    "dropped_correlated": drop_columns, "graph_files": graph_files, "output_dir": str(OUTPUT_DIR.resolve()),
    "packages": {name: version(name) for name in ["pandas", "numpy", "meteostat", "matplotlib", "seaborn", "xlsxwriter"]},
}
(OUTPUT_DIR / "report_metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
analysis_ready.to_csv("airQuality_clean.csv", index=False)
assert len(analysis_ready) == len(stage_data["Merged"])
assert not analysis_ready.duplicated(["source", "site_id", "time"]).any()
print("Workbook:", workbook_path.resolve())
print("Graphs:", GRAPH_DIR.resolve())
print("PCA and report metrics saved. All validation checks passed.")
'''

for c in n['cells']:
    s=''.join(c['source'])
    if s.startswith('# Jakarta air quality'):
        s=s.replace('seven diagnostic PNG graphs', 'nine diagnostic PNG graphs').replace('The adjacent `export_air_quality.mjs` file supplies the Excel export using the bundled spreadsheet runtime.', 'The Excel export is implemented in Python inside this notebook.')
    if s.startswith('#API Keys'):
        s='''# API keys are only needed for a fresh download. Never embed credentials in a submission.
OPENAQ_API_KEY = os.getenv("OPENAQ_API_KEY", "")
PURPLEAIR_READ_KEY = os.getenv("PURPLEAIR_READ_KEY", "")
USE_SAVED_DATA = True
SNAPSHOT_DIR = "data/air_quality_snapshot"
'''
    if s.startswith('# Universal API'):
        s=s.replace('    response = requests.get', '''    if USE_SAVED_DATA:
        archive = Path(SNAPSHOT_DIR) / "raw_responses"
        manifest = json.loads((archive / "manifest.json").read_text(encoding="utf-8"))
        match = next((entry for entry in manifest if entry["url"] == url and entry["params"] == params), None)
        if match is None:
            raise ValueError(f"Request not in saved snapshot: {url}. Use the original settings or set USE_SAVED_DATA=False.")
        response_text = (archive / match["file"]).read_text(encoding="utf-8")
        response_file = RAW_DIR / f"response_{len(request_log)+1:03d}.json"
        response_file.write_text(response_text, encoding="utf-8")
        request_log.append({"url": url, "params": params, "file": response_file.name})
        return json.loads(response_text)
    response = requests.get''')
    if s.startswith('#Download OpenAQ') or s.startswith('#Download PurpleAir'):
        s=s.replace('if not key_is_ready(', 'if not USE_SAVED_DATA and not key_is_ready(')
    if s.startswith('#Download weather'):
        start=s.index('    point = ms.Point')
        end=s.index('    snapshot("Weather downloaded"')
        s=s[:start]+'''    if USE_SAVED_DATA:
        station_query = pd.read_csv(Path(SNAPSHOT_DIR) / "Stations_downloaded.csv", dtype={"id": str}).set_index("id")
        weather = pd.read_csv(Path(SNAPSHOT_DIR) / "Weather_downloaded.csv", dtype={"station": str})
        weather["time"] = pd.to_datetime(weather["time"], utc=True)
    else:
        point = ms.Point(JAKARTA_LAT, JAKARTA_LON)
        station_query = ms.stations.nearby(point, limit=5)
        if station_query.empty:
            raise ValueError("No nearby weather stations found")
        start = START_UTC.tz_localize(None).to_pydatetime()
        end = END_UTC.tz_localize(None).to_pydatetime()
        weather = ms.hourly(station_query, start, end, timezone="UTC").fetch().reset_index()

'''+s[end:]
    if s.startswith('# Export every stage'):
        s=s[:s.index('# The adjacent builder')] + writer
        s=s.replace('Seven detailed', 'Nine detailed')
    c['source']=s.splitlines(keepends=True)

# Insert explicit source explanation immediately after the introduction.
n['cells'].insert(1,new(sources,'markdown'))
# Add PCA after outlier diagnostics and before export.
idx=next(i for i,c in enumerate(n['cells']) if ''.join(c['source']).startswith('## 8. Export'))
n['cells'][idx:idx]=[new('## 8. Outlier removal and PCA dimensionality reduction\n\nPCA uses standardized, complete numerical records from the explicitly licensed primary cohort. IQR filtering estimates typical-condition structure; a sensitivity comparison retains extremes. This is descriptive analysis, not a predictive train/test experiment.','markdown'),new(pca)]
for c in n['cells']:
    s=''.join(c['source']).replace('## 8. Export raw','## 9. Export raw')
    c['source']=s.splitlines(keepends=True)
    if c['cell_type']=='code': c.update(outputs=[],execution_count=None)
p.write_text(json.dumps(n,ensure_ascii=False,indent=1)+'\n',encoding='utf-8')
print('Notebook completed:',len(n['cells']),'cells')
