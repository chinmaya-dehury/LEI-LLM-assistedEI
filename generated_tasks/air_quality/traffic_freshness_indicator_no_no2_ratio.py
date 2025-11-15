import os
import sys
import json
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np


def main():
    DATA_TYPE = "air_quality"
    TASK_NAME = "traffic_freshness_indicator_no_no2_ratio"
    DESCRIPTION = "Compute NO/NO2 ratio per reading and classify source freshness: >1.0 fresh-traffic, 0.3–1.0 mixed, <0.3 aged/oxidized; optionally smooth using a 2-point median."

    data_path = Path("data") / DATA_TYPE / "raw_data.csv"
    output_dir = Path("output") / DATA_TYPE
    output_dir.mkdir(parents=True, exist_ok=True)
    now_iso = datetime.now(timezone.utc).isoformat()

    def write_and_exit(summary_items, code=0):
        result = {"task_name": TASK_NAME, "description": DESCRIPTION, "result_summary": summary_items, "result_generated_at": now_iso}
        out_file = output_dir / f"{TASK_NAME}_result.json"
        with open(out_file, "w") as f:
            json.dump(result, f, indent=2)
        print(json.dumps(result, indent=2))
        sys.exit(code)

    if not data_path.exists():
        write_and_exit([
            {
                "name": "error",
                "value": f"Data file not found: {data_path}",
                "description": "Cannot compute NO/NO2 ratio without data.",
                "timestamp": now_iso
            }
        ], code=1)

    try:
        df = pd.read_csv(data_path)
    except Exception as e:
        write_and_exit([
            {
                "name": "error",
                "value": f"Failed to read CSV: {e}",
                "description": "CSV parsing error.",
                "timestamp": now_iso
            }
        ], code=1)

    required = {"timestamp_utc", "no", "no2"}
    if not required.issubset(df.columns):
        write_and_exit([
            {
                "name": "error",
                "value": f"Missing required columns: {sorted(list(required - set(df.columns)))}",
                "description": "Ensure CSV contains timestamp_utc, no, and no2 columns.",
                "timestamp": now_iso
            }
        ], code=1)

    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp_utc"])
    df = df.sort_values("timestamp_utc").reset_index(drop=True)

    # Safe numeric conversion
    for col in ["no", "no2"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Compute NO/NO2 ratio (avoid divide-by-zero)
    df["ratio_raw"] = np.where(df["no2"] > 0, df["no"] / df["no2"], np.nan)
    # 2-point rolling median smoothing (optional)
    df["ratio_med2"] = df["ratio_raw"].rolling(window=2, min_periods=1).median()

    def classify(r):
        if pd.isna(r):
            return "unknown"
        if r > 1.0:
            return "fresh-traffic"
        elif r >= 0.3:
            return "mixed"
        else:
            return "aged/oxidized"

    df["class_raw"] = df["ratio_raw"].apply(classify)
    df["class_med2"] = df["ratio_med2"].apply(classify)

    valid_mask = df["ratio_raw"].notna()
    num_valid = int(valid_mask.sum())
    counts = df.loc[valid_mask, "class_raw"].value_counts().to_dict() if num_valid > 0 else {}

    def frac_of(k):
        return float(counts.get(k, 0)) / float(num_valid) if num_valid > 0 else 0.0

    mean_ratio = float(df.loc[valid_mask, "ratio_raw"].mean()) if num_valid > 0 else float("nan")
    median_ratio = float(df.loc[valid_mask, "ratio_raw"].median()) if num_valid > 0 else float("nan")

    if df.empty:
        write_and_exit([
            {
                "name": "valid_points",
                "value": 0,
                "description": "Number of readings with valid NO/NO2 ratio.",
                "timestamp": now_iso
            }
        ], code=0)

    last_row = df.iloc[-1]
    end_ts = last_row["timestamp_utc"]

    def safe_round(x, nd=4):
        try:
            if pd.isna(x):
                return None
            return round(float(x), nd)
        except Exception:
            return None

    summary = []
    summary.append({
        "name": "valid_points",
        "value": num_valid,
        "description": "Number of readings with valid NO/NO2 ratio.",
        "timestamp": now_iso
    })
    summary.append({
        "name": "mean_ratio_raw",
        "value": None if np.isnan(mean_ratio) else round(mean_ratio, 4),
        "description": "Mean NO/NO2 ratio across valid readings.",
        "timestamp": now_iso
    })
    summary.append({
        "name": "median_ratio_raw",
        "value": None if np.isnan(median_ratio) else round(median_ratio, 4),
        "description": "Median NO/NO2 ratio across valid readings.",
        "timestamp": now_iso
    })
    summary.append({
        "name": "pct_fresh_traffic",
        "value": round(frac_of("fresh-traffic") * 100.0, 2),
        "description": "Percentage of readings classified as fresh-traffic (ratio > 1.0).",
        "timestamp": now_iso
    })
    summary.append({
        "name": "pct_mixed",
        "value": round(frac_of("mixed") * 100.0, 2),
        "description": "Percentage of readings classified as mixed (0.3–1.0).",
        "timestamp": now_iso
    })
    summary.append({
        "name": "pct_aged_oxidized",
        "value": round(frac_of("aged/oxidized") * 100.0, 2),
        "description": "Percentage of readings classified as aged/oxidized (<0.3).",
        "timestamp": now_iso
    })

    summary.append({
        "name": "last_ratio_raw",
        "value": safe_round(last_row.get("ratio_raw")),
        "description": "NO/NO2 ratio for the latest reading (raw).",
        "timestamp": end_ts.isoformat() if pd.notna(end_ts) else now_iso
    })
    summary.append({
        "name": "last_class_raw",
        "value": last_row.get("class_raw"),
        "description": "Freshness class for the latest reading (raw).",
        "timestamp": end_ts.isoformat() if pd.notna(end_ts) else now_iso
    })
    summary.append({
        "name": "last_ratio_smoothed_med2",
        "value": safe_round(last_row.get("ratio_med2")),
        "description": "NO/NO2 ratio for the latest reading after 2-point median smoothing.",
        "timestamp": end_ts.isoformat() if pd.notna(end_ts) else now_iso
    })
    summary.append({
        "name": "last_class_smoothed_med2",
        "value": last_row.get("class_med2"),
        "description": "Freshness class for the latest reading after 2-point median smoothing.",
        "timestamp": end_ts.isoformat() if pd.notna(end_ts) else now_iso
    })

    result = {"task_name": TASK_NAME, "description": DESCRIPTION, "result_summary": summary, "result_generated_at": now_iso}
    out_file = output_dir / f"{TASK_NAME}_result.json"
    with open(out_file, "w") as f:
        json.dump(result, f, indent=2)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()