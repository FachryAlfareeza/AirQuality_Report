# %% [markdown]
# # Simple Jakarta Air-Quality Data Integration
#
# This notebook combines:
#
# 1. Reference PM2.5 observations from OpenAQ.
# 2. Low-cost PM2.5 observations from PurpleAir.
# 3. Hourly weather observations from nearby Meteostat/NOAA stations.
#
# The workflow uses familiar libraries and keeps each operation visible:
# `pandas` for tabular work, `numpy` for Haversine distance, `requests` for
# APIs, and `seaborn`/`matplotlib` for a quick final check.
# %%
# =========================== EDIT THESE VALUES ============================
import os

OPENAQ_API_KEY = os.getenv("OPENAQ_API_KEY", "9da770ae15cb8ebb36b84891d96436f03579775b657196f38c7ea35cbea7954c")
PURPLEAIR_READ_KEY = os.getenv("PURPLEAIR_READ_KEY", "A5F0E1A3-B9D9-11F1-9E30-4201AC1DC129")

# Jakarta bounding box: west, south, east, north
JAKARTA_BBOX = (106.689, -6.370, 106.978, -6.079)
JAKARTA_CENTER = (-6.2088, 106.8456)

START_DATE = "2024-01-01 00:00:00+07:00"
END_DATE = "2024-02-01 00:00:00+07:00"
TIMEZONE = "Asia/Jakarta"
FREQUENCY = "1h"

# Leave empty to discover public outdoor PurpleAir sensors in Jakarta.
# Example: PURPLEAIR_SENSOR_IDS = [12345, 67890]
PURPLEAIR_SENSOR_IDS = []

MAX_PM25 = 1000.0
MAX_WEATHER_DISTANCE_KM = 100.0
CORRELATION_LIMIT = 0.95

OUTPUT_CSV = "jakarta_air_quality_analysis_ready.csv"

# %%
# Install only packages which are missing from the current Jupyter kernel.
# You can alternatively run: python -m pip install -r requirements.txt
import importlib.util
import subprocess
import sys

REQUIRED_PACKAGES = {
    "pandas": "pandas",
    "numpy": "numpy",
    "requests": "requests",
    "meteostat": "meteostat",
    "seaborn": "seaborn",
    "matplotlib": "matplotlib",
}

missing_packages = [
    pip_name
    for import_name, pip_name in REQUIRED_PACKAGES.items()
    if importlib.util.find_spec(import_name) is None
]

if missing_packages:
    print("Installing missing packages:", ", ".join(missing_packages))
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", *missing_packages]
    )
    print("Installation complete. Restart the Jupyter kernel if an import fails.")
else:
    print("All required packages are already installed.")

import warnings

import matplotlib.pyplot as plt
import meteostat as ms
import numpy as np
import pandas as pd
import requests
import seaborn as sns

warnings.filterwarnings("ignore", category=FutureWarning)
pd.set_option("display.max_columns", 50)
sns.set_theme(style="whitegrid")

START_UTC = pd.Timestamp(START_DATE).tz_convert("UTC")
END_UTC = pd.Timestamp(END_DATE).tz_convert("UTC")


def check_api_key(key, name):
    """Stop early if an API-key placeholder was not replaced."""
    if not key or key.startswith("PASTE_"):
        raise ValueError(f"Please set {name} in the first cell.")


def get_json(url, headers=None, params=None):
    """Small reusable GET request helper."""
    response = requests.get(url, headers=headers, params=params, timeout=90)
    response.raise_for_status()
    return response.json()


def utc_text(timestamp):
    """Format a pandas Timestamp for API requests."""
    return timestamp.isoformat().replace("+00:00", "Z")


# %% [markdown]
# ## 1. Download OpenAQ reference-monitor data
#
# OpenAQ locations are filtered to fixed sites marked as monitors and containing
# PM2.5 sensors. We request the API's hourly observations directly. Reference
# data receive only basic physical-range and API-flag filtering; unusual but
# valid pollution episodes are not automatically deleted.

# %%
OPENAQ_URL = "https://api.openaq.org/v3"


def openaq_get_all(path, params):
    """Read all pages from one OpenAQ endpoint."""
    check_api_key(OPENAQ_API_KEY, "OPENAQ_API_KEY")
    headers = {"X-API-Key": OPENAQ_API_KEY}
    all_rows = []
    page = 1

    while True:
        page_params = {**params, "limit": 1000, "page": page}
        data = get_json(f"{OPENAQ_URL}/{path}", headers, page_params)
        rows = data.get("results", [])
        all_rows.extend(rows)

        if len(rows) < 1000:
            break
        page += 1

    return all_rows


def download_openaq():
    west, south, east, north = JAKARTA_BBOX

    locations = openaq_get_all(
        "locations",
        {
            "bbox": f"{west},{south},{east},{north}",
            "parameters_id": 2,  # OpenAQ parameter 2 is PM2.5
        },
    )

    sensor_rows = []
    for location in locations:
        # Keep fixed locations recognized by OpenAQ as monitors.
        if location.get("isMobile") is True or location.get("isMonitor") is not True:
            continue

        coordinates = location.get("coordinates") or {}
        for sensor in location.get("sensors", []):
            parameter = sensor.get("parameter") or {}
            parameter_name = str(parameter.get("name", "")).lower().replace(".", "")

            if parameter.get("id") == 2 or parameter_name == "pm25":
                sensor_rows.append(
                    {
                        "sensor_id": sensor["id"],
                        "site_name": location.get("name"),
                        "latitude": coordinates.get("latitude"),
                        "longitude": coordinates.get("longitude"),
                        "unit": parameter.get("units"),
                    }
                )

    sensors = pd.DataFrame(sensor_rows).drop_duplicates("sensor_id")
    print(f"OpenAQ PM2.5 sensors found: {len(sensors)}")

    measurements = []
    for sensor in sensors.itertuples(index=False):
        rows = openaq_get_all(
            f"sensors/{sensor.sensor_id}/hours",
            {
                "datetime_from": utc_text(START_UTC),
                "datetime_to": utc_text(END_UTC),
            },
        )

        for row in rows:
            period = row.get("period") or {}
            date_information = period.get("datetimeFrom") or {}
            coverage = row.get("coverage") or {}
            unit = (row.get("parameter") or {}).get("units") or sensor.unit
            value = row.get("value")

            # Standardize PM2.5 to micrograms per cubic metre.
            if value is not None and str(unit).lower() in {"mg/m3", "mg/m³"}:
                value = value * 1000

            measurements.append(
                {
                    "time_utc": date_information.get("utc"),
                    "source": "openaq",
                    "site_id": f"openaq:{sensor.sensor_id}",
                    "site_name": sensor.site_name,
                    "latitude": sensor.latitude,
                    "longitude": sensor.longitude,
                    "pm25": value,
                    "coverage_percent": coverage.get("percentCoverage"),
                    "api_flag": bool((row.get("flagInfo") or {}).get("hasFlags", False)),
                }
            )

    return pd.DataFrame(measurements)


openaq_raw = download_openaq()
print(openaq_raw.head())

# %% [markdown]
# ## 2. Download PurpleAir data
#
# PurpleAir provides two particle-counter channels, A and B. A large difference
# between them often indicates a dirty or failing sensor. Historical requests
# are split into 14-day blocks because the API limits the time span available at
# one-hour resolution.

# %%
PURPLEAIR_URL = "https://api.purpleair.com/v1"
PURPLEAIR_FIELDS = [
    "pm2.5_cf_1_a",
    "pm2.5_cf_1_b",
    "humidity_a",
    "humidity_b",
    "temperature_a",
    "temperature_b",
    "pressure_a",
    "pressure_b",
    "analog_input",
]


def purpleair_table(data):
    "Convert PurpleAir's fields/data JSON format into a DataFrame."
    fields = data.get("fields", [])
    rows = data.get("data", [])
    return pd.DataFrame(rows, columns=fields)


def find_purpleair_sensors():
    check_api_key(PURPLEAIR_READ_KEY, "PURPLEAIR_READ_KEY")
    west, south, east, north = JAKARTA_BBOX

    data = get_json(
        f"{PURPLEAIR_URL}/sensors",
        headers={"X-API-Key": PURPLEAIR_READ_KEY},
        params={
            "fields": "name,latitude,longitude,location_type",
            "location_type": 0,  # outdoor sensors
            "nwlat": north,
            "nwlng": west,
            "selat": south,
            "selng": east,
        },
    )
    sensors = purpleair_table(data)

    if PURPLEAIR_SENSOR_IDS:
        sensors = sensors[sensors["sensor_index"].isin(PURPLEAIR_SENSOR_IDS)]

    print(f"PurpleAir sensors found: {len(sensors)}")
    return sensors


def download_purpleair_history(sensors):
    all_sensor_data = []

    for sensor in sensors.itertuples(index=False):
        chunk_start = START_UTC

        while chunk_start < END_UTC:
            chunk_end = min(chunk_start + pd.Timedelta(days=14), END_UTC)

            data = get_json(
                f"{PURPLEAIR_URL}/sensors/{sensor.sensor_index}/history",
                headers={"X-API-Key": PURPLEAIR_READ_KEY},
                params={
                    "start_timestamp": int(chunk_start.timestamp()),
                    "end_timestamp": int(chunk_end.timestamp()),
                    "average": 60,
                    "fields": ",".join(PURPLEAIR_FIELDS),
                },
            )

            history = purpleair_table(data)
            if not history.empty:
                history["time_utc"] = pd.to_datetime(
                    history["time_stamp"], unit="s", utc=True
                )
                history["source"] = "purpleair"
                history["site_id"] = f"purpleair:{sensor.sensor_index}"
                history["site_name"] = getattr(sensor, "name", None)
                history["latitude"] = sensor.latitude
                history["longitude"] = sensor.longitude
                all_sensor_data.append(history)

            chunk_start = chunk_end

    if not all_sensor_data:
        return pd.DataFrame()

    return pd.concat(all_sensor_data, ignore_index=True).drop_duplicates()


purpleair_sensors = find_purpleair_sensors()
purpleair_raw = download_purpleair_history(purpleair_sensors)
print(purpleair_raw.head())

# %% [markdown]
# ## 3. Clean and aggregate PM2.5
#
# Both sources are converted to UTC and one row per site per hour. OpenAQ values
# outside 0–1000 µg/m³ or explicitly flagged by its API are removed. PurpleAir
# also receives channel-agreement and rolling median/MAD spike checks. Only
# short internal gaps are interpolated: up to two hours for OpenAQ and one hour
# for PurpleAir. An indicator records every imputed value.

# %%
def hampel_spikes(values, window=7, number_of_sigmas=6):
    """Return a Boolean mask for robust rolling outliers."""
    transformed = np.log1p(values.clip(lower=0))
    rolling_median = transformed.rolling(window, center=True, min_periods=4).median()
    difference = (transformed - rolling_median).abs()
    mad = difference.rolling(window, center=True, min_periods=4).median()
    threshold = number_of_sigmas * 1.4826 * mad.replace(0, np.nan)
    return (difference > threshold).fillna(False)


def clean_openaq(data):
    clean = data.copy()
    clean["time_utc"] = pd.to_datetime(clean["time_utc"], utc=True, errors="coerce")
    clean["pm25"] = pd.to_numeric(clean["pm25"], errors="coerce")

    clean["invalid_pm25"] = ~clean["pm25"].between(0, MAX_PM25) | clean["api_flag"]
    clean.loc[clean["invalid_pm25"], "pm25"] = np.nan

    hourly_parts = []
    for site_id, group in clean.groupby("site_id"):
        metadata = group.iloc[0]
        hourly = (
            group.set_index("time_utc")
            .resample(FREQUENCY)
            .agg(pm25=("pm25", "median"), invalid_pm25=("invalid_pm25", "max"))
            .reset_index()
        )
        hourly["source"] = "openaq"
        hourly["site_id"] = site_id
        hourly["site_name"] = metadata["site_name"]
        hourly["latitude"] = metadata["latitude"]
        hourly["longitude"] = metadata["longitude"]

        was_missing = hourly["pm25"].isna()
        hourly["pm25"] = hourly["pm25"].interpolate(limit=2, limit_area="inside")
        hourly["pm25_imputed"] = was_missing & hourly["pm25"].notna()
        hourly_parts.append(hourly)

    return pd.concat(hourly_parts, ignore_index=True)


def clean_purpleair(data):
    if data.empty:
        return pd.DataFrame()

    clean = data.copy()
    clean["time_utc"] = pd.to_datetime(clean["time_utc"], utc=True, errors="coerce")

    numeric_columns = [column for column in PURPLEAIR_FIELDS if column in clean.columns]
    clean[numeric_columns] = clean[numeric_columns].apply(pd.to_numeric, errors="coerce")

    channel_a = clean["pm2.5_cf_1_a"]
    channel_b = clean["pm2.5_cf_1_b"]
    channel_average = pd.concat([channel_a, channel_b], axis=1).mean(axis=1)
    channel_difference = (channel_a - channel_b).abs()

    # Flag when A/B differ by more than 10 µg/m³ or 50% of their mean.
    clean["channel_disagreement"] = channel_difference > np.maximum(
        10, 0.50 * channel_average
    )
    clean["pm25"] = channel_average
    clean.loc[
        ~clean["pm25"].between(0, MAX_PM25) | clean["channel_disagreement"],
        "pm25",
    ] = np.nan

    clean["pm25_spike"] = False
    clean["voltage_spike"] = False

    for site_id, indexes in clean.groupby("site_id").groups.items():
        indexes = clean.loc[indexes].sort_values("time_utc").index

        pm_spike = hampel_spikes(clean.loc[indexes, "pm25"])
        clean.loc[indexes, "pm25_spike"] = pm_spike.values
        clean.loc[indexes[pm_spike.values], "pm25"] = np.nan

        if "analog_input" in clean.columns:
            voltage = clean.loc[indexes, "analog_input"]
            voltage_spike = hampel_spikes(voltage, window=7)
            impossible_voltage = ~voltage.between(0, 5.25)
            bad_voltage = voltage_spike | impossible_voltage
            clean.loc[indexes, "voltage_spike"] = bad_voltage.values
            clean.loc[indexes[bad_voltage.values], "analog_input"] = np.nan

    hourly_parts = []
    for site_id, group in clean.groupby("site_id"):
        metadata = group.iloc[0]
        hourly = (
            group.set_index("time_utc")
            .resample(FREQUENCY)
            .agg(
                pm25=("pm25", "median"),
                channel_disagreement=("channel_disagreement", "max"),
                pm25_spike=("pm25_spike", "max"),
                voltage_spike=("voltage_spike", "max"),
            )
            .reset_index()
        )
        hourly["source"] = "purpleair"
        hourly["site_id"] = site_id
        hourly["site_name"] = metadata["site_name"]
        hourly["latitude"] = metadata["latitude"]
        hourly["longitude"] = metadata["longitude"]

        was_missing = hourly["pm25"].isna()
        hourly["pm25"] = hourly["pm25"].interpolate(limit=1, limit_area="inside")
        hourly["pm25_imputed"] = was_missing & hourly["pm25"].notna()
        hourly_parts.append(hourly)

    return pd.concat(hourly_parts, ignore_index=True)


openaq_clean = clean_openaq(openaq_raw)
purpleair_clean = clean_purpleair(purpleair_raw)

air_quality = pd.concat([openaq_clean, purpleair_clean], ignore_index=True)
air_quality = air_quality[
    (air_quality["time_utc"] >= START_UTC) & (air_quality["time_utc"] < END_UTC)
]

print("Hourly air-quality rows:", len(air_quality))
display(air_quality.head())

# %% [markdown]
# ## 4. Download and clean hourly weather data
#
# Meteostat finds nearby weather stations and supplies hourly station records.
# All timestamps remain in UTC. Impossible physical values are removed, and
# only short weather gaps are interpolated within the same station.

# %%
def download_weather():
    point = ms.Point(JAKARTA_CENTER[0], JAKARTA_CENTER[1])
    station_query = ms.stations.nearby(point, limit=5).fetch()

    start_without_timezone = START_UTC.tz_localize(None).to_pydatetime()
    end_without_timezone = END_UTC.tz_localize(None).to_pydatetime()

    # Meteostat expects the original station DataFrame with an index named id.
    weather = ms.hourly(
        station_query,
        start_without_timezone,
        end_without_timezone,
        timezone="UTC",
    ).fetch().reset_index()

    stations = station_query.reset_index()

    stations = stations.rename(
        columns={
            "id": "weather_station_id",
            "lat": "weather_latitude",
            "lon": "weather_longitude",
        }
    )

    weather = weather.rename(
        columns={
            "station": "weather_station_id",
            "time": "time_utc",
            "temp": "temperature_c",
            "dwpt": "dew_point_c",
            "rhum": "humidity_pct",
            "prcp": "precipitation_mm",
            "wdir": "wind_direction_deg",
            "wspd": "wind_speed_kmh",
            "wpgt": "wind_gust_kmh",
            "pres": "pressure_hpa",
        }
    )

    weather["weather_station_id"] = weather["weather_station_id"].astype(str)
    stations["weather_station_id"] = stations["weather_station_id"].astype(str)
    weather["time_utc"] = pd.to_datetime(weather["time_utc"], utc=True)

    return stations, weather


weather_stations, weather = download_weather()

# Remove impossible weather values.
valid_ranges = {
    "temperature_c": (-30, 60),
    "dew_point_c": (-40, 40),
    "humidity_pct": (0, 100),
    "precipitation_mm": (0, 500),
    "wind_direction_deg": (0, 360),
    "wind_speed_kmh": (0, 250),
    "wind_gust_kmh": (0, 350),
    "pressure_hpa": (850, 1100),
}

for column, limits in valid_ranges.items():
    if column in weather.columns:
        weather[column] = pd.to_numeric(weather[column], errors="coerce")
        weather.loc[~weather[column].between(*limits), column] = np.nan

# Wind direction is circular: 359° and 1° are close, not far apart.
weather["wind_direction_sin"] = np.sin(np.radians(weather["wind_direction_deg"]))
weather["wind_direction_cos"] = np.cos(np.radians(weather["wind_direction_deg"]))
weather = weather.drop(columns="wind_direction_deg")

weather_columns = [
    "temperature_c",
    "dew_point_c",
    "humidity_pct",
    "precipitation_mm",
    "wind_speed_kmh",
    "wind_gust_kmh",
    "pressure_hpa",
]
weather_columns = [column for column in weather_columns if column in weather.columns]

weather["weather_imputed"] = False
for station_id, indexes in weather.groupby("weather_station_id").groups.items():
    indexes = weather.loc[indexes].sort_values("time_utc").index
    before = weather.loc[indexes, weather_columns].isna()
    weather.loc[indexes, weather_columns] = weather.loc[indexes, weather_columns].interpolate(
        limit=3, limit_area="inside"
    )
    after = weather.loc[indexes, weather_columns].notna()
    weather.loc[indexes, "weather_imputed"] = (before & after).any(axis=1).values

print("Weather stations:", len(weather_stations))
display(weather.head())

# %% [markdown]
# ## 5. Spatial and temporal integration
#
# The datasets do not share an ID. For each air-quality sensor, the Haversine
# formula selects the nearest weather station. The selected station ID and the
# UTC hour then form the composite linkage key. This is more defensible than
# joining every Jakarta sensor to one city-wide weather record.

# %%
def haversine_km(latitude_1, longitude_1, latitude_2, longitude_2):
    """Great-circle distance between coordinates in kilometres."""
    earth_radius = 6371.0088

    lat1 = np.radians(latitude_1)
    lon1 = np.radians(longitude_1)
    lat2 = np.radians(latitude_2)
    lon2 = np.radians(longitude_2)

    delta_latitude = lat2 - lat1
    delta_longitude = lon2 - lon1

    a = (
        np.sin(delta_latitude / 2) ** 2
        + np.cos(lat1) * np.cos(lat2) * np.sin(delta_longitude / 2) ** 2
    )
    return 2 * earth_radius * np.arcsin(np.sqrt(a))


def create_spatial_links(air_data, stations):
    links = []
    sites = air_data[["site_id", "latitude", "longitude"]].drop_duplicates("site_id")

    for site in sites.itertuples(index=False):
        distances = haversine_km(
            site.latitude,
            site.longitude,
            stations["weather_latitude"].to_numpy(),
            stations["weather_longitude"].to_numpy(),
        )
        nearest_position = np.argmin(distances)
        nearest_station = stations.iloc[nearest_position]
        nearest_distance = float(distances[nearest_position])

        if nearest_distance > MAX_WEATHER_DISTANCE_KM:
            raise ValueError(
                f"No suitable weather station for {site.site_id}; "
                f"nearest is {nearest_distance:.1f} km away."
            )

        links.append(
            {
                "site_id": site.site_id,
                "weather_station_id": nearest_station["weather_station_id"],
                "weather_distance_km": nearest_distance,
            }
        )

    return pd.DataFrame(links)


spatial_links = create_spatial_links(air_quality, weather_stations)

integrated = air_quality.merge(
    spatial_links,
    on="site_id",
    how="left",
    validate="many_to_one",
)

# Drop weather station coordinates because the distance already represents the
# spatial relationship and the air-sensor coordinates are retained.
weather_for_join = weather.drop(
    columns=["weather_latitude", "weather_longitude"], errors="ignore"
)

integrated = integrated.merge(
    weather_for_join,
    on=["weather_station_id", "time_utc"],
    how="left",
    validate="many_to_one",
)

integrated["time_jakarta"] = integrated["time_utc"].dt.tz_convert(TIMEZONE)
integrated["hour"] = integrated["time_jakarta"].dt.hour
integrated["day_of_week"] = integrated["time_jakarta"].dt.dayofweek
integrated["month"] = integrated["time_jakarta"].dt.month

display(spatial_links)

# %% [markdown]
# ## 6. Reduce redundant features
#
# Highly correlated meteorological variables can provide nearly the same
# information. The code below drops the second variable in any pair with an
# absolute Pearson correlation of at least 0.95. PM2.5 and identifiers are not
# included in this decision.

# %%
possible_weather_features = [
    "temperature_c",
    "dew_point_c",
    "humidity_pct",
    "precipitation_mm",
    "wind_speed_kmh",
    "wind_gust_kmh",
    "pressure_hpa",
]
possible_weather_features = [
    column for column in possible_weather_features if column in integrated.columns
]

correlation_matrix = integrated[possible_weather_features].corr().abs()
upper_triangle = correlation_matrix.where(
    np.triu(np.ones(correlation_matrix.shape), k=1).astype(bool)
)

columns_to_drop = [
    column
    for column in upper_triangle.columns
    if any(upper_triangle[column] >= CORRELATION_LIMIT)
]

print("Highly correlated weather columns removed:", columns_to_drop)

analysis_ready = integrated.drop(columns=columns_to_drop)

# Remove source-specific columns which are completely empty for all records.
analysis_ready = analysis_ready.dropna(axis=1, how="all")

# Keep one standard site ID and remove the descriptive name to reduce redundant
# location identifiers. Coordinates remain useful for maps and spatial models.
analysis_ready = analysis_ready.drop(columns="site_name", errors="ignore")
analysis_ready = analysis_ready.sort_values(
    ["time_utc", "source", "site_id"]
).reset_index(drop=True)

# Basic quality assertions.
assert not analysis_ready.duplicated(["source", "site_id", "time_utc"]).any()
assert analysis_ready["pm25"].dropna().between(0, MAX_PM25).all()
assert analysis_ready["weather_distance_km"].le(MAX_WEATHER_DISTANCE_KM).all()

print("Final shape:", analysis_ready.shape)
display(analysis_ready.head())

# %% [markdown]
# ## 7. Quick visual check and save
#
# A line plot is a simple way to notice remaining impossible jumps, long gaps,
# or timezone mistakes. The final condensed DataFrame is `analysis_ready`.

# %%
plt.figure(figsize=(13, 5))
sns.lineplot(
    data=analysis_ready,
    x="time_jakarta",
    y="pm25",
    hue="source",
    estimator="median",
    errorbar=None,
)
plt.title("Hourly PM2.5 in Jakarta after cleaning")
plt.xlabel("Jakarta time")
plt.ylabel("PM2.5 (µg/m³)")
plt.tight_layout()
plt.show()

analysis_ready.to_csv(OUTPUT_CSV, index=False)
print(f"Saved {len(analysis_ready):,} rows to {OUTPUT_CSV}")

analysis_ready
