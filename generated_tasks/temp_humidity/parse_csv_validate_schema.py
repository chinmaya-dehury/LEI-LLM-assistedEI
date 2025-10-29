import os
import json
import pandas as pd
import numpy as np
from datetime import datetime


def iso_now():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def main():
    TASK_NAME = "parse_csv_validate_schema"
    DESCRIPTION = "Load the CSV, parse timestamps to datetime, enforce float types for temperature and humidity, and verify 5-minute sampling intervals."
    DATA_TYPE = "temp_humidity"
    INPUT_FILE = os.path.join("data", DATA_TYPE, "raw_data.csv")
    OUTPUT_DIR = os.path.join("output", DATA_TYPE)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    result = {
        "task_name": TASK_NAME,
        "description": DESCRIPTION,
        "result_summary": [],
        "result_generated_at": iso_now(),
    }

    try:
        df = pd.read_csv(INPUT_FILE)
    except Exception as e:
        err = {
            "name": "read_error",
            "value": str(e),
            "description": f"Failed to read input file at {INPUT_FILE}",
            "tiemstamp": iso_now(),
        }
        result["result_summary"].append(err)
        out_path = os.path.join(OUTPUT_DIR, f"{TASK_NAME}_result.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(json.dumps(result, indent=2))
        return

    # Ensure required columns exist
    required_cols = ["timestamp", "temperature_c", "humidity_percent"]
    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
        result["result_summary"].append({
            "name": "missing_columns",
            "value": missing_cols,
            "description": "Required columns not found in CSV",
            "tiemstamp": iso_now(),
        })
        out_path = os.path.join(OUTPUT_DIR, f"{TASK_NAME}_result.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(json.dumps(result, indent=2))
        return

    # Parse and enforce types
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    for col in ["temperature_c", "humidity_percent"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Basic counts
    row_count = int(len(df))
    ts_na = int(df["timestamp"].isna().sum())
    temp_na = int(df["temperature_c"].isna().sum())
    rh_na = int(df["humidity_percent"].isna().sum())

    # Range checks (inclusive ranges from metadata)
    temp_invalid = int(((df["temperature_c"] < 15) | (df["temperature_c"] > 40)).fillna(False).sum())
    rh_invalid = int(((df["humidity_percent"] < 20) | (df["humidity_percent"] > 100)).fillna(False).sum())

    # Duplicate and ordering checks
    dup_ts = int(df["timestamp"].duplicated().sum())
    df_sorted = df.sort_values("timestamp").reset_index(drop=True)
    ts_series = df_sorted["timestamp"]
    monotonic_inc = bool(ts_series.is_monotonic_increasing)

    # Sampling interval checks (5 minutes expected)
    diffs = ts_series.diff().dropna()
    if len(diffs) == 0:
        sampling_ok = True
        irregular_intervals_count = 0
        unique_intervals_min = []
    else:
        interval_minutes = diffs.dt.total_seconds() / 60.0
        irregular_mask = np.abs(interval_minutes - 5.0) > 1e-6
        irregular_intervals_count = int(irregular_mask.sum())
        unique_intervals_min = sorted(list({round(float(x), 3) for x in interval_minutes.tolist()}))
        sampling_ok = irregular_intervals_count == 0

    # Extents
    first_ts = ts_series.iloc[0].isoformat() if len(ts_series) > 0 and pd.notna(ts_series.iloc[0]) else None
    last_ts = ts_series.iloc[-1].isoformat() if len(ts_series) > 0 and pd.notna(ts_series.iloc[-1]) else None

    min_temp = float(df["temperature_c"].min()) if temp_na < row_count else None
    max_temp = float(df["temperature_c"].max()) if temp_na < row_count else None
    min_rh = float(df["humidity_percent"].min()) if rh_na < row_count else None
    max_rh = float(df["humidity_percent"].max()) if rh_na < row_count else None

    now_iso = iso_now()

    summaries = [
        {"name": "row_count", "value": row_count, "description": "Total rows in CSV", "tiemstamp": now_iso},
        {"name": "missing_timestamp_count", "value": ts_na, "description": "Rows with unparseable timestamps", "tiemstamp": now_iso},
        {"name": "missing_temperature_count", "value": temp_na, "description": "Rows with missing/invalid temperature values", "tiemstamp": now_iso},
        {"name": "missing_humidity_count", "value": rh_na, "description": "Rows with missing/invalid humidity values", "tiemstamp": now_iso},
        {"name": "invalid_temperature_range_count", "value": temp_invalid, "description": "Temperature values outside [15, 40] Celsius", "tiemstamp": now_iso},
        {"name": "invalid_humidity_range_count", "value": rh_invalid, "description": "Relative humidity outside [20, 100] percent", "tiemstamp": now_iso},
        {"name": "duplicate_timestamps_count", "value": dup_ts, "description": "Number of duplicate timestamp entries", "tiemstamp": now_iso},
        {"name": "timestamps_monotonic_increasing", "value": monotonic_inc, "description": "Timestamps are in non-decreasing order", "tiemstamp": now_iso},
        {"name": "sampling_interval_ok", "value": sampling_ok, "description": "All consecutive samples spaced exactly 5 minutes", "tiemstamp": now_iso},
        {"name": "sampling_unique_intervals_minutes", "value": unique_intervals_min, "description": "Unique observed sampling intervals (minutes)", "tiemstamp": now_iso},
        {"name": "irregular_intervals_count", "value": irregular_intervals_count, "description": "Count of intervals differing from 5 minutes", "tiemstamp": now_iso},
        {"name": "first_timestamp", "value": first_ts, "description": "First timestamp in dataset (ISO)", "tiemstamp": now_iso},
        {"name": "last_timestamp", "value": last_ts, "description": "Last timestamp in dataset (ISO)", "tiemstamp": now_iso},
        {"name": "min_temperature_c", "value": min_temp, "description": "Minimum observed temperature (C)", "tiemstamp": now_iso},
        {"name": "max_temperature_c", "value": max_temp, "description": "Maximum observed temperature (C)", "tiemstamp": now_iso},
        {"name": "min_humidity_percent", "value": min_rh, "description": "Minimum observed relative humidity (%)", "tiemstamp": now_iso},
        {"name": "max_humidity_percent", "value": max_rh, "description": "Maximum observed relative humidity (%)", "tiemstamp": now_iso},
    ]

    result["result_summary"].extend(summaries)

    out_path = os.path.join(OUTPUT_DIR, f"{TASK_NAME}_result.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
