from pathlib import Path
import json

p = Path('air-quality_self.ipynb')
n = json.loads(p.read_text(encoding='utf-8'))
old = [''.join(c['source']) for c in n['cells']]

def cell(source, kind='code'):
    c = {'cell_type': kind, 'metadata': {}, 'source': source.splitlines(keepends=True)}
    if kind == 'code':
        c.update(execution_count=None, outputs=[])
    return c

helpers = r'''# Record immutable stage snapshots and changes for the notebook and workbook.
from pathlib import Path
from datetime import datetime, timezone
import json
import subprocess
import shutil

OUTPUT_DIR = Path("outputs") / "air-quality-review" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
GRAPH_DIR = OUTPUT_DIR / "graphs"
RAW_DIR = OUTPUT_DIR / "raw_responses"
for folder in [OUTPUT_DIR, GRAPH_DIR, RAW_DIR]:
    folder.mkdir(parents=True, exist_ok=True)
sns.set_theme(style="whitegrid", palette="colorblind")
stage_data, stage_info, changes, request_log, graph_files = {}, [], [], [], []


def snapshot(name, frame, note, previous=None, keys=None):
    data = frame.copy(deep=True)
    stage_data[name] = data
    stage_info.append({
        "stage": name, "previous": previous or "", "rows": len(data),
        "columns": len(data.columns), "missing_cells": int(data.isna().sum().sum()),
        "exact_duplicate_rows": int(data.duplicated().sum()), "note": note,
    })
    print(f"\n{name}: {note}")
    if previous is None:
        display(data.head())
        return
    before = stage_data[previous]
    cols = list(dict.fromkeys([*before.columns, *data.columns]))
    metrics = pd.DataFrame({
        "column": cols,
        "missing_before": [int(before[c].isna().sum()) if c in before else pd.NA for c in cols],
        "missing_after": [int(data[c].isna().sum()) if c in data else pd.NA for c in cols],
    })
    print(f"Rows: {len(before):,} -> {len(data):,}; columns: {len(before.columns)} -> {len(data.columns)}")
    display(metrics)
    # Compare like-for-like records only; aggregation is described with counts instead.
    if keys is None:
        return
    left, right = before.copy(), data.copy()
    if keys == ["_row"]:
        left["_row"], right["_row"] = left.index, right.index
    if left.duplicated(keys).any() or right.duplicated(keys).any():
        print("Record comparison omitted: keys are not unique; inspect the stage tables.")
        return
    left, right = left.set_index(keys), right.set_index(keys)
    start = len(changes)
    for key in left.index.difference(right.index):
        changes.append({"stage": name, "record": str(key), "column": "(row)", "before": "present", "after": None, "change": "removed"})
    for key in right.index.difference(left.index):
        changes.append({"stage": name, "record": str(key), "column": "(row)", "before": None, "after": "present", "change": "added"})
    common = left.index.intersection(right.index)
    for col in left.columns.intersection(right.columns):
        a, b = left.loc[common, col], right.loc[common, col]
        same = a.eq(b).fillna(False) | (a.isna() & b.isna())
        for key in common[~same.to_numpy(dtype=bool)]:
            av, bv = a.loc[key], b.loc[key]
            changes.append({"stage": name, "record": str(key), "column": col,
                            "before": av, "after": bv,
                            "change": "filled" if pd.isna(av) else ("invalidated" if pd.isna(bv) else "changed")})
    detail = pd.DataFrame(changes[start:])
    print(f"Changed cells / added or removed rows: {len(detail):,}")
    if not detail.empty:
        display(detail.head(10))
    added, removed = data.columns.difference(before.columns), before.columns.difference(data.columns)
    if len(added) or len(removed):
        print("Added columns:", list(added), "Removed columns:", list(removed))


def save_graph(fig, filename):
    fig.tight_layout()
    path = GRAPH_DIR / filename
    fig.savefig(path, dpi=160, bbox_inches="tight")
    graph_files.append(str(path.resolve()))
    plt.show()
    plt.close(fig)
'''

# Archive the successful HTTP response bodies without credentials.
old[3] = old[3].replace('    result = response.json()', '''    result = response.json()
    response_file = RAW_DIR / f"response_{len(request_log) + 1:03d}.json"
    response_file.write_text(response.text, encoding="utf-8")
    request_log.append({"url": url, "params": params, "file": response_file.name})''')
old[4] += '\nsnapshot("OpenAQ raw", openaq_raw, "Downloaded PM2.5 values before cleaning; full responses are archived separately.")\n'
old[5] += '\nsnapshot("PurpleAir raw", purpleair_raw, "Downloaded channel values before cleaning; full responses are archived separately.")\n'
# Preserve Meteostat's returned table before renaming, time filtering or cleaning.
old[6] = old[6].replace('    stations = station_query', '''    snapshot("Weather downloaded", weather, "Meteostat returned values before column renaming and time filtering.")
    snapshot("Stations downloaded", station_query.reset_index(), "Original Meteostat station metadata.")

    stations = station_query''')
old[6] += '\nsnapshot("Weather raw", weather, "Names standardized and requested date interval selected; measurements unchanged.")\nweather_raw = weather.copy(deep=True)\n'
old[7] = old[7].replace('# Reindex each station', '''snapshot("Weather bounded", weather, "Measurements outside the existing physical limits become missing.", "Weather raw", ["station_id", "time"])

# Reindex each station''')
old[7] += '\nsnapshot("Weather prepared", weather, "Hourly grid; bounded gaps of at most 3 hours filled except rainfall.", "Weather bounded", ["station_id", "time"])\n'
old[8] += '''
snapshot("OpenAQ cleaned", openaq_clean, "Exact duplicates removed; timestamp/numeric types parsed; PM2.5 outside 0–1000 becomes missing.", "OpenAQ raw", ["_row"])
snapshot("PurpleAir cleaned", purpleair_clean, "Exact duplicates removed; both channels must be valid and agree within max(10, 50% of their mean).", "PurpleAir raw", ["_row"])
'''
old[9] = old[9].replace('air_data = air_data.dropna', '''snapshot("Air combined", air_data, "Cleaned source tables concatenated before location and date filtering.")
air_data = air_data.dropna''')
old[9] = old[9].replace('# Hourly mean for each sensor.', '''snapshot("Air filtered", air_data, "Rows without valid keys/coordinates or outside the area/period are removed.", "Air combined", ["_row"])

# Hourly mean for each sensor.''')
old[9] = old[9].replace('# Fill only short gaps', '''snapshot("Air hourly", air_hourly, "Per-sensor hourly means; absent hours between first and last observations are added as missing.", "Air filtered")
air_hourly_before = air_hourly.copy(deep=True)

# Fill only short gaps''')
old[9] += '\nsnapshot("Air filled", air_hourly, "Only complete internal PM2.5 gaps of at most 2 hours are interpolated.", "Air hourly", ["site_id", "time"])\n'
old[10] += '\nsnapshot("Station links", links, "Nearest station with usable weather; distance in kilometres.")\n'
old[11] = old[11].replace('integrated["time_jakarta"]', '''snapshot("Merged", integrated, "Hourly air and weather joined by station and UTC time.", "Air filled", ["site_id", "time"])

integrated["time_jakarta"]''',1)
old[11] += '\nsnapshot("Time features", integrated, "Jakarta timestamp, hour and weekday added (Monday=0).", "Merged", ["site_id", "time"])\n'
old[12] += '\nsnapshot("Final", analysis_ready, "Weather columns with absolute correlation >0.95 removed; rows sorted. Removed: " + (", ".join(drop_columns) or "none"), "Time features", ["site_id", "time"])\n'

diagnostics = r'''# Inspect cleaning effects and statistical outliers without modifying measurements.
raw_pm = openaq_raw.copy()
raw_pm["pm25"] = pd.to_numeric(raw_pm["pm25"], errors="coerce")
purple_plot = purpleair_raw.copy()
channels = ["pm2.5_cf_1_a", "pm2.5_cf_1_b"]
for column in channels:
    if column not in purple_plot:
        purple_plot[column] = np.nan
    purple_plot[column] = pd.to_numeric(purple_plot[column], errors="coerce")
# This mean is for raw diagnostics only. It is not a validated PM2.5 measurement.
purple_plot["pm25"] = purple_plot[channels].mean(axis=1, skipna=False)
purple_plot["source"] = "PurpleAir"
raw_pm = pd.concat([raw_pm, purple_plot], ignore_index=True)
raw_pm["time"] = pd.to_datetime(raw_pm["time"], utc=True, errors="coerce")

distribution = []
for label, frame in [("Raw", raw_pm), ("Cleaned", stage_data["Air combined"]), ("Final", analysis_ready)]:
    d = frame[["source", "pm25"]].copy()
    d["stage"] = label
    distribution.append(d)
distribution = pd.concat(distribution, ignore_index=True)
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
for ax, source in zip(axes, ["OpenAQ", "PurpleAir"]):
    sns.boxplot(data=distribution.loc[distribution.source.eq(source)], x="stage", y="pm25", ax=ax,
                order=["Raw", "Cleaned", "Final"], color="#86b6d9", flierprops={"markersize": 3})
    ax.set(title=source, xlabel="", ylabel="PM2.5 (µg/m³)")
fig.suptitle("PM2.5 distributions before and after processing\nBoxplot points beyond 1.5 × IQR are diagnostic flags, not automatic exclusions")
save_graph(fig, "01_pm25_boxplots.png")

# Raw-channel rejection reasons; multiple flags can apply to one record.
channel_flags = purple_plot.copy()
channel_flags["missing_channel"] = channel_flags[channels].isna().any(axis=1)
channel_flags["invalid_channel"] = ((channel_flags[channels] < 0) | (channel_flags[channels] > 1000)).any(axis=1)
channel_flags["channel_disagreement"] = ((channel_flags[channels[0]] - channel_flags[channels[1]]).abs() > np.maximum(10, channel_flags.pm25 * 0.50))
channel_flags["rejected"] = channel_flags[["missing_channel", "invalid_channel", "channel_disagreement"]].any(axis=1)
display(channel_flags[["missing_channel", "invalid_channel", "channel_disagreement", "rejected"]].sum().to_frame("rows"))
fig, ax = plt.subplots(figsize=(7, 6))
for rejected, label, color in [(False, "Pass channel checks", "#2878b5"), (True, "Fail channel checks", "#d95f02")]:
    rows = channel_flags.loc[channel_flags.rejected.eq(rejected)]
    ax.scatter(rows[channels[0]], rows[channels[1]], s=9, alpha=.5, label=label, color=color)
vals = channel_flags[channels].to_numpy(dtype=float)
finite = vals[np.isfinite(vals)]
if len(finite):
    lo, hi = min(0, finite.min()), max(1, finite.max())
    ax.plot([lo, hi], [lo, hi], color="grey", linestyle="--", linewidth=1, label="Equal channels")
ax.set(title="PurpleAir raw channel agreement", xlabel="Channel A (µg/m³)", ylabel="Channel B (µg/m³)")
ax.legend()
save_graph(fig, "02_purpleair_channels.png")

# Statistical outliers: compute each sensor's raw IQR once, then reuse those bounds.
bounds, flagged = [], []
for site_id, group in raw_pm.groupby("site_id"):
    values = group.pm25.replace([np.inf, -np.inf], np.nan).dropna()
    if len(values) < 4:
        continue
    q1, q3 = values.quantile([.25, .75])
    iqr = q3 - q1
    if iqr == 0:
        continue
    bounds.append({"site_id": site_id, "q1": q1, "q3": q3, "lower": q1 - 1.5 * iqr, "upper": q3 + 1.5 * iqr})
outlier_bounds = pd.DataFrame(bounds, columns=["site_id", "q1", "q3", "lower", "upper"])
for label, frame in [("Raw", raw_pm), ("Final", analysis_ready)]:
    marked = frame.merge(outlier_bounds, on="site_id", how="left", validate="many_to_one")
    marked["iqr_outlier"] = marked.pm25.lt(marked.lower) | marked.pm25.gt(marked.upper)
    marked["stage"] = label
    flagged.append(marked)
outlier_diagnostics = pd.concat(flagged, ignore_index=True)
outlier_rows = outlier_diagnostics.loc[outlier_diagnostics.iqr_outlier].copy()
print("IQR outliers are retained unless they independently fail a cleaning rule.")
display(outlier_diagnostics.groupby(["stage", "source"]).agg(observations=("pm25", "count"), iqr_flags=("iqr_outlier", "sum")))

fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
for ax, source in zip(axes, ["OpenAQ", "PurpleAir"]):
    group = outlier_diagnostics.loc[outlier_diagnostics.source.eq(source) & outlier_diagnostics.stage.eq("Raw")].sort_values("time")
    ax.scatter(group.time, group.pm25, s=5, alpha=.3, color="#2878b5", label="Raw observations")
    unusual = group.loc[group.iqr_outlier]
    ax.scatter(unusual.time, unusual.pm25, s=12, color="#d95f02", label="Sensor-specific IQR flag")
    ax.set(title=source, ylabel="PM2.5 (µg/m³)")
    ax.legend(loc="upper right")
axes[-1].set_xlabel("UTC time")
save_graph(fig, "03_raw_outliers_over_time.png")

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
air_stages = ["Air combined", "Air filtered", "Air hourly", "Air filled", "Final"]
missing_pm = [stage_data[s].pm25.isna().mean() * 100 for s in air_stages]
axes[0].bar(air_stages, missing_pm, color="#2878b5")
axes[0].set(title="PM2.5 missingness by stage", ylabel="Missing observations (%)")
axes[0].tick_params(axis="x", rotation=20)
weather_missing = pd.DataFrame({s: stage_data[s][weather_columns].isna().mean() * 100 for s in ["Weather raw", "Weather bounded", "Weather prepared"]})
weather_missing.plot.bar(ax=axes[1], color=["#9ba7b4", "#d99a32", "#2878b5"])
axes[1].set(title="Weather missingness by stage", ylabel="Missing observations (%)", xlabel="")
axes[1].tick_params(axis="x", rotation=25)
fig.suptitle("Hourly reindexing changes row counts; percentages use each stage's own row count")
save_graph(fig, "04_missingness.png")

fig, ax = plt.subplots(figsize=(14, 5))
fill_counts = air_hourly.groupby("site_id").pm25_imputed.sum()
if fill_counts.max() > 0:
    selected_site = fill_counts.idxmax()
    original = air_hourly_before.loc[air_hourly_before.site_id.eq(selected_site)].sort_values("time")
    filled = air_hourly.loc[air_hourly.site_id.eq(selected_site)].sort_values("time")
    ax.plot(original.time, original.pm25, linewidth=1, color="#2878b5", label="Before interpolation")
    added = filled.loc[filled.pm25_imputed]
    ax.scatter(added.time, added.pm25, color="#d95f02", s=22, label="Interpolated values", zorder=3)
    ax.set_title(f"Short-gap interpolation: {selected_site} (sensor with most filled hours)")
    ax.legend()
else:
    ax.text(.5, .5, "No PM2.5 gaps were eligible for interpolation", ha="center", transform=ax.transAxes)
ax.set(xlabel="UTC time", ylabel="PM2.5 (µg/m³)")
save_graph(fig, "05_interpolation.png")

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
matched_weather = integrated.drop_duplicates(["station_id", "time"])
sns.heatmap(matched_weather[weather_columns].corr(), vmin=-1, vmax=1, cmap="vlag", annot=True, fmt=".2f", ax=axes[0])
axes[0].set_title("Weather correlation (each station-hour counted once)")
links.sort_values("distance_to_weather_km").plot.bar(x="site_id", y="distance_to_weather_km", ax=axes[1], legend=False, color="#2878b5")
axes[1].set(title="Distance to matched weather station", ylabel="Distance (km)", xlabel="Air sensor")
save_graph(fig, "06_weather_merge.png")

fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
for source, color in [("OpenAQ", "#2878b5"), ("PurpleAir", "#d95f02")]:
    rows = analysis_ready.loc[analysis_ready.source.eq(source)]
    series = rows.groupby("time_jakarta").pm25.agg(["mean", "count"])
    axes[0].plot(series.index, series["mean"], label=source, color=color, linewidth=1)
    axes[1].plot(series.index, series["count"], label=source, color=color, linewidth=1)
axes[0].set(title="Final hourly PM2.5 means by source", ylabel="PM2.5 (µg/m³)")
axes[1].set(title="Available readings behind each mean", ylabel="Nonmissing sensor readings", xlabel="Jakarta time (UTC+07:00)")
from matplotlib.dates import DateFormatter
from zoneinfo import ZoneInfo
axes[1].xaxis.set_major_formatter(DateFormatter("%d %b", tz=ZoneInfo("Asia/Jakarta")))
for ax in axes:
    ax.legend()
save_graph(fig, "07_final_time_series.png")
'''

export = r'''# Export every stage, detailed changes, diagnostics, and native Excel charts.
stage_summary = pd.DataFrame(stage_info)
change_log = pd.DataFrame(changes, columns=["stage", "record", "column", "before", "after", "change"])
missing_summary = pd.DataFrame([
    {"stage": name, "column": col, "rows": len(frame), "missing": int(frame[col].isna().sum()),
     "missing_fraction": frame[col].isna().mean() if len(frame) else np.nan}
    for name, frame in stage_data.items() for col in frame.columns
])
numeric_summary = pd.concat([
    frame.select_dtypes(include="number").describe().T.reset_index(names="column").assign(stage=name)
    for name, frame in stage_data.items() if len(frame) and len(frame.select_dtypes(include="number").columns)
], ignore_index=True)
display(stage_summary)
display(change_log.groupby(["stage", "change"]).size().to_frame("entries"))

notes = pd.DataFrame([
    ["Period", f"{START_DATE} inclusive to {END_DATE} exclusive"],
    ["Workbook", "Frozen snapshots of this notebook run. Rerun the notebook to refresh all stages and graphs."],
    ["Raw data", "OpenAQ raw and PurpleAir raw preserve extracted measurements. Full API responses are in raw_responses. Weather downloaded preserves the Meteostat returned table."],
    ["Times", "Excel timestamps are numeric dates: time is UTC; time_jakarta is Jakarta local time. Raw JSON/CSV keeps timezone offsets."],
    ["Units", "PM2.5: µg/m³; temperature: °C; humidity: %; rain: mm per hour; wind_speed: km/h; pressure: hPa; distance: km."],
    ["Row changes", "Hourly resampling can add rows. Missing percentages are calculated using each stage's row count."],
    ["Changes", "Changes lists common-column value changes and rows added/removed on unique keys. Column additions/removals and aggregation are described in Stages."],
    ["Outliers", "Sensor-specific raw quartiles define 1.5 × IQR bounds, reused for final flags. At least 4 readings and nonzero IQR required. Flags do not remove data."],
    ["PurpleAir", "Raw PM2.5 diagnostic mean requires both channels. Final values require both valid channels and agreement within max(10, 50% of mean). CF1 values are uncalibrated."],
    ["Comparability", "Sources have different sensors and coverage. Source means are descriptive and are not a calibrated citywide estimate."],
    ["Missing values", "Blank Excel cells represent missing values; zero remains zero. Rainfall and long gaps are not filled."],
    ["Stages", "Processing outputs are computed in Python; workbook charts read the exported summary cells."],
], columns=["topic", "explanation"])

tables = {"Stages": stage_summary, "Final": analysis_ready, "Changes": change_log,
          "Missingness": missing_summary, "Statistics": numeric_summary,
          "Outlier flags": outlier_rows, "IQR bounds": outlier_bounds,
          "Channel checks": channel_flags, **{k: v for k, v in stage_data.items() if k != "Final"},
          "Method": notes}

def export_table(name, frame):
    # CSV preserves the original timezone-bearing strings; Excel uses explicit wall-clock dates.
    frame.to_csv(OUTPUT_DIR / (name.replace(" ", "_") + ".csv"), index=False)
    values = frame.copy()
    date_cols = []
    for col in values.columns:
        if pd.api.types.is_datetime64_any_dtype(values[col]):
            date_cols.append(col)
            values[col] = values[col].map(lambda value: None if pd.isna(value) else value.isoformat())
    # Raw OpenAQ timestamps are returned as strings; give Excel sortable UTC dates.
    if "time" in values and "time" not in date_cols:
        parsed = pd.to_datetime(values["time"], utc=True, errors="coerce")
        if values["time"].notna().sum() == parsed.notna().sum():
            values["time"] = parsed.map(lambda value: None if pd.isna(value) else value.isoformat())
            date_cols.append("time")
    records = json.loads(values.to_json(orient="split", date_format="iso", default_handler=str))
    return {"name": name, "columns": list(values.columns), "rows": records["data"], "date_columns": date_cols}

# Compact chart tables. These are snapshots of Python diagnostics from this run.
chart_rows = pd.DataFrame({"stage": ["Air combined", "Air filtered", "Air hourly", "Air filled", "Final"]})
chart_rows["rows"] = chart_rows.stage.map(lambda name: len(stage_data[name]))
chart_rows["missing_pm25"] = chart_rows.stage.map(lambda name: int(stage_data[name].pm25.isna().sum()))
daily = analysis_ready.assign(day=analysis_ready.time_jakarta.dt.strftime("%Y-%m-%d")).groupby(["day", "source"]).pm25.mean().unstack().reset_index()
bins = np.arange(0, 1001, 50)
histogram = pd.DataFrame({"PM2.5 bin (µg/m³)": [f"{a}–<{b}" if b < 1000 else f"{a}–{b}" for a, b in zip(bins[:-1], bins[1:])]})
for source in ["OpenAQ", "PurpleAir"]:
    histogram[source] = np.histogram(analysis_ready.loc[analysis_ready.source.eq(source), "pm25"].dropna(), bins=bins)[0]
tables.update({"Chart stages": chart_rows, "Chart daily": daily, "Chart distribution": histogram})

payload = {"tables": [export_table(name, frame) for name, frame in tables.items()],
           "output_dir": str(OUTPUT_DIR.resolve()), "graph_files": graph_files,
           "period": f"{START_DATE} to {END_DATE}"}
payload_file = OUTPUT_DIR / "workbook_data.json"
payload_file.write_text(json.dumps(payload, ensure_ascii=False, allow_nan=False), encoding="utf-8")
(RAW_DIR / "manifest.json").write_text(json.dumps(request_log, indent=2), encoding="utf-8")

# The adjacent builder uses Codex's bundled spreadsheet runtime. Environment overrides
# make the locations configurable when moving the project to another computer.
runtime = Path(os.environ.get("CODEX_ARTIFACT_RUNTIME", str(Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node")))
node = os.environ.get("ARTIFACT_NODE", str(runtime / "bin/node.exe"))
if not Path(node).is_file():
    node = shutil.which("node")
if not node:
    raise RuntimeError("Node.js is needed for the Excel export. Set ARTIFACT_NODE; all stage CSVs and PNG graphs have already been saved.")
result = subprocess.run([node, "export_air_quality.mjs", str(payload_file.resolve())], capture_output=True, text=True, encoding="utf-8")
if result.returncode:
    raise RuntimeError("Excel export failed: " + result.stderr[-4000:])
print(result.stdout)
analysis_ready.to_csv("airQuality_clean.csv", index=False)
print("Workbook:", (OUTPUT_DIR / "air_quality_audit.xlsx").resolve())
print("Graphs:", GRAPH_DIR.resolve())
print("Full raw API responses:", RAW_DIR.resolve())
'''

intro = '''# Jakarta air quality: visible preprocessing and export

Run all cells in order using the project's `.venv` Python environment. Each processing stage preserves a copy of its data and displays row counts, missing values and examples of changed records. Downloads use the configured API keys.

The final cells save a timestamped run under `outputs/air-quality-review/`: an Excel workbook, one CSV per stage, full raw API responses and seven diagnostic PNG graphs. The adjacent `export_air_quality.mjs` file supplies the Excel export using the bundled spreadsheet runtime.

**Outlier flags are descriptive:** extreme valid pollution readings are retained. The existing physical-range and channel-agreement rules remain the cleaning criteria.
'''
cells = [cell(intro, 'markdown')]
titles = {4: '## 1. Download and preserve source data', 7: '## 2. Prepare weather data',
          8: '## 3. Clean air-quality measurements', 9: '## 4. Combine, filter, resample and fill short gaps',
          10: '## 5. Match weather stations and merge', 12: '## 6. Select final columns and sort'}
for i, s in enumerate(old[:13]):
    if i in titles:
        cells.append(cell(titles[i], 'markdown'))
    cells.append(cell(s))
    if i == 2:
        cells.append(cell(helpers))
cells += [cell('## 7. Diagnose outliers, missing values and interpolation', 'markdown'), cell(diagnostics),
          cell('## 8. Export raw, intermediate and final data', 'markdown'), cell(export)]
n['cells'] = cells
p.write_text(json.dumps(n, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
print('Notebook updated:', len(cells), 'cells')
