"""Update the working notebook while preserving the completed 2024 package."""
from pathlib import Path
import json, shutil

root = Path(__file__).parent
backup = root / 'backups' / 'FINAL_January_2024'
if not backup.exists():
    shutil.copytree(root / 'FINAL', backup)
    shutil.copy2(root / 'air-quality_self.ipynb', backup / 'working_notebook_before_2025.ipynb')
n = json.loads((root / 'air-quality_self.ipynb').read_text(encoding='utf-8'))
def source(i): return ''.join(n['cells'][i]['source'])
def set_source(i, s): n['cells'][i]['source'] = s.splitlines(keepends=True)
set_source(0, source(0).replace('The detailed notebook and existing report describe the more extensive analysis in `air-quality_self_detailed.ipynb`.', 'Period: all of 2025 in Jakarta time, from 1 January 2025 inclusive to 1 January 2026 exclusive. The accompanying article describes this version.'))
set_source(1, source(1).replace('import json', 'import json\nimport time'))
set_source(2, source(2).replace('data/air_quality_snapshot', 'data/air_quality_2025'))
set_source(3, source(3).replace('2024-01-01', '2025-01-01').replace('2024-02-01', '2026-01-01'))
set_source(4, '''# Read archived responses, or download and save each successful request.
def get_api_data(url, headers=None, params=None):
    archive = Path(SNAPSHOT_DIR) / "raw_responses"
    manifest_path = archive / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else []
    match = next((entry for entry in manifest if entry["url"] == url and entry["params"] == params), None)
    if match is not None:
        return json.loads((archive / match["file"]).read_text(encoding="utf-8"))
    if USE_SAVED_DATA:
        raise ValueError(f"Request not in saved snapshot: {url}. Download this period first with USE_SAVED_DATA=False.")
    # Pace live calls and retry temporary server/rate-limit failures.
    for attempt in range(4):
        time.sleep(1.1)
        response = requests.get(url, headers=headers, params=params, timeout=60)
        if response.status_code == 429 or response.status_code >= 500:
            if attempt < 3:
                time.sleep(float(response.headers.get("Retry-After", "60")))
                continue
        response.raise_for_status()
        break
    result = response.json()
    if not isinstance(result, dict) or result.get("error"):
        raise RuntimeError(f"Invalid API response from {url}")
    archive.mkdir(parents=True, exist_ok=True)
    filename = f"response_{len(manifest) + 1:04d}.json"
    (archive / filename).write_text(response.text, encoding="utf-8")
    manifest.append({"url": url, "params": params, "file": filename})
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return result


def key_is_ready(key):
    return bool(key) and not key.startswith("PASTE_")


def get_openaq_results(url, headers, params):
    rows = []
    page = 1
    while True:
        result = get_api_data(url, headers, {**params, "page": page})
        batch = result["results"]
        rows.extend(batch)
        if len(batch) < params["limit"]:
            return rows
        page += 1
''')
s = source(6)
start = s.index('        # One-hour averages')
end = s.index('\n    if not all_rows:', start)
s = s[:start] + '''        # Request hourly data in short windows so the full year is returned.
        window_start = START_UTC
        while window_start < END_UTC:
            window_end = min(window_start + pd.Timedelta(days=14), END_UTC)
            history_url = f"https://api.purpleair.com/v1/sensors/{sensor.sensor_index}/history"
            history_params = {
                "start_timestamp": int(window_start.timestamp()),
                "end_timestamp": int(window_end.timestamp()),
                "average": 60,
                "fields": "pm2.5_cf_1_a,pm2.5_cf_1_b",
            }
            result = get_api_data(history_url, headers, history_params)
            history = purpleair_dataframe(result)
            if not history.empty:
                history["time"] = pd.to_datetime(history["time_stamp"], unit="s", utc=True)
                history = history.loc[history["time"].ge(window_start) & history["time"].lt(window_end)].copy()
                history["source"] = "PurpleAir"
                history["site_id"] = f"PurpleAir_{sensor.sensor_index}"
                history["latitude"] = sensor.latitude
                history["longitude"] = sensor.longitude
                all_rows.append(history)
            window_start = window_end
''' + s[end:]
s = s.replace('return pd.DataFrame()', 'return pd.DataFrame(columns=AIR_COLUMNS + ["pm2.5_cf_1_a", "pm2.5_cf_1_b"])')
set_source(6,s)
set_source(7,source(7).replace('        weather = ms.hourly(station_query, start, end, timezone="UTC").fetch().reset_index()', '''        weather = ms.hourly(station_query, start, end, timezone="UTC").fetch().reset_index()
        Path(SNAPSHOT_DIR).mkdir(parents=True, exist_ok=True)
        station_query.to_csv(Path(SNAPSHOT_DIR) / "Stations_downloaded.csv")
        weather.to_csv(Path(SNAPSHOT_DIR) / "Weather_downloaded.csv", index=False)'''))
for c in n['cells']:
    if c['cell_type']=='code':
        c['outputs']=[]
        c['execution_count']=None
(root/'air-quality_self.ipynb').write_text(json.dumps(n,indent=1,ensure_ascii=False),encoding='utf-8')
print('2024 package backed up; notebook now requests the full 2025 calendar year.')
