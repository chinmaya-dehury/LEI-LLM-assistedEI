import os
import json
import pandas as pd
import numpy as np
from math import log, exp
from datetime import datetime


def iso_now():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def dew_point_c(temp_c, rh_percent):
    # Magnus formula constants for water over liquid
    a = 17.62
    b = 243.12
    rh = np.clip(rh_percent, 1e-6, 100.0)
    gamma = np.log(rh / 100.0) + (a * temp_c) / (b + temp_c)
    return (b * gamma) / (a - gamma)


def humidex(temp_c, rh_percent):
    # Compute vapor pressure from dew point (hPa)
    td = dew_point_c(temp_c, rh_percent)
    # Avoid invalid values
    valid = np.isfinite(td)
    e = np.full_like(temp_c, np.nan, dtype=float)
    # 6.11 hPa * exp(5417.7530 * (1/273.16 - 1/(273.15 + Td)))
    e[valid] = 6.11 * np.exp(5417.7530 * (1.0 / 273.16 - 1.0 / (273.15 + td[valid])))
    h = temp_c + (5.0 / 9.0) * (e - 10.0)
    return h


def categorize_humidex(h):
    if pd.isna(h):
        return "unknown"
    if h < 30:
        return "comfortable"
    elif h < 40:
        return "some discomfort"
    elif h <= 45:
        return "great discomfort"
    elif h < 54:
        return "dangerous"
    else:
        return "heat stroke likely"


def main():
    TASK_NAME = "comfort_index_humidex"
    DESCRIPTION = "Compute Humidex from temperature and relative humidity and assign comfort categories (e.g., comfortable, some discomfort, great discomfort)."
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
        result["result_summary"].append({
            "name": "read_error",
            "value": str(e),
            "description": f"Failed to read input file at {INPUT_FILE}",
            "tiemstamp": iso_now(),
        })
        out_path = os.path.join(OUTPUT_DIR, f"{TASK_NAME}_result.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(json.dumps(result, indent=2))
        return

    # Parse and clean
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    for col in ["temperature_c", "humidity_percent"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["timestamp", "temperature_c", "humidity_percent"]).sort_values("timestamp").reset_index(drop=True)

    if df.empty:
        result["result_summary"].append({
            "name": "no_valid_rows",
            "value": 0,
            "description": "No valid rows after parsing and cleaning.",
            "tiemstamp": iso_now(),
        })
        out_path = os.path.join(OUTPUT_DIR, f"{TASK_NAME}_result.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(json.dumps(result, indent=2))
        return

    T = df["temperature_c"].to_numpy(dtype=float)
    RH = df["humidity_percent"].to_numpy(dtype=float)

    H = humidex(T, RH)
    df["humidex"] = H
    df["comfort_category"] = df["humidex"].apply(categorize_humidex)

    # Metrics
    now_iso = iso_now()
    mean_h = float(np.nanmean(H)) if np.isfinite(H).any() else None
    max_idx = int(np.nanargmax(H)) if np.isfinite(H).any() else None
    max_h = float(H[max_idx]) if max_idx is not None else None
    max_h_ts = df.loc[max_idx, "timestamp"].isoformat() if max_idx is not None else None

    latest_idx = len(df) - 1
    latest_h = float(df.loc[latest_idx, "humidex"]) if latest_idx >= 0 else None
    latest_ts = df.loc[latest_idx, "timestamp"].isoformat() if latest_idx >= 0 else None

    discomfort_mask = df["humidex"] >= 30
    percent_discomfort = float(round(100.0 * discomfort_mask.mean(), 2)) if len(df) > 0 else 0.0

    cat_counts = df["comfort_category"].value_counts(dropna=False).to_dict()

    alert_triggered = bool((df["humidex"] >= 40).any())

    result["result_summary"].extend([
        {"name": "mean_humidex", "value": round(mean_h, 2) if mean_h is not None else None, "description": "Average Humidex across dataset", "tiemstamp": now_iso},
        {"name": "max_humidex", "value": {"value": round(max_h, 2) if max_h is not None else None, "at": max_h_ts}, "description": "Maximum Humidex and when it occurred", "tiemstamp": now_iso},
        {"name": "latest_humidex", "value": {"value": round(latest_h, 2) if latest_h is not None else None, "at": latest_ts}, "description": "Most recent Humidex value", "tiemstamp": now_iso},
        {"name": "percent_time_discomfort_or_worse", "value": percent_discomfort, "description": "Percentage of time Humidex >= 30", "tiemstamp": now_iso},
        {"name": "category_counts", "value": cat_counts, "description": "Counts by comfort category", "tiemstamp": now_iso},
        {"name": "alert_great_discomfort_or_worse", "value": alert_triggered, "description": "True if any Humidex >= 40 (great discomfort or worse)", "tiemstamp": now_iso},
    ])

    out_path = os.path.join(OUTPUT_DIR, f"{TASK_NAME}_result.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
