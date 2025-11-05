#!/usr/bin/env python3
import os
import sys
import json
from datetime import datetime, timezone
import pandas as pd
import numpy as np


def iso_now():
    return datetime.now(timezone.utc).isoformat()


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def print_summary(summary):
    print("Rolling Z-Score Anomaly Detection Summary")
    for k, v in summary.items():
        print(f"- {k}: {v}")


def safe_float(series):
    try:
        return pd.to_numeric(series, errors='coerce')
    except Exception:
        return pd.Series([np.nan] * len(series))


def main():
    TASK_NAME = "rolling_zscore_anomaly_detection"
    DESCRIPTION = (
        "Detect anomalies via rolling z-score for temperature_c and humidity_percent; "
        "flag points with absolute z-score above a threshold."
    )

    # DATA_TYPE controls input and output directories
    DATA_TYPE = "temp_humidity"
    data_path = os.getenv("DATA_FILE", os.path.join("data", DATA_TYPE, "raw_data.csv"))
    out_dir = os.path.join("output", DATA_TYPE)
    ensure_dir(out_dir)
    out_file = os.path.join(out_dir, f"{TASK_NAME}_result.json")

    # Parameters (override via env vars if needed)
    try:
        window = int(os.getenv("ROLLING_WINDOW", "5"))
        threshold = float(os.getenv("ZSCORE_THRESHOLD", "3.0"))
    except ValueError:
        window = 5
        threshold = 3.0

    result = {
        "task_name": TASK_NAME,
        "description": DESCRIPTION,
        "result_summary": [],
        "result_generated_at": iso_now(),
    }

    def make_entry(name, value, description):
        return {
            "name": name,
            "value": value,
            "description": description,
            "timestamp": iso_now(),  # fixed spelling per validation feedback
        }

    # Load data
    if not os.path.exists(data_path):
        msg = f"Input file not found: {data_path}"
        print(msg, file=sys.stderr)
        result["result_summary"].append(make_entry("status", "error", msg))
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"Result saved to {out_file}")
        sys.exit(1)

    try:
        df = pd.read_csv(data_path)
    except Exception as e:
        msg = f"Failed to read CSV: {e}"
        print(msg, file=sys.stderr)
        result["result_summary"].append(make_entry("status", "error", msg))
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"Result saved to {out_file}")
        sys.exit(1)

    # Basic validation
    expected_cols = {"timestamp", "temperature_c", "humidity_percent"}
    missing = expected_cols.difference(df.columns)
    if missing:
        msg = f"Missing required columns: {sorted(list(missing))}"
        print(msg, file=sys.stderr)
        result["result_summary"].append(make_entry("status", "error", msg))
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"Result saved to {out_file}")
        sys.exit(1)

    # Parse and clean
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["temperature_c"] = safe_float(df["temperature_c"])
    df["humidity_percent"] = safe_float(df["humidity_percent"])
    # Drop rows with invalid timestamps and sort
    df = df.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

    total_points = len(df)
    valid_points = df[["temperature_c", "humidity_percent"]].dropna().shape[0]

    if total_points == 0 or valid_points == 0:
        msg = "No valid data rows after cleaning."
        print(msg, file=sys.stderr)
        result["result_summary"].append(make_entry("status", "no_data", msg))
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"Result saved to {out_file}")
        sys.exit(0)

    # Rolling z-scores with strict window (min_periods=window)
    roll_t = df["temperature_c"].rolling(window=window, min_periods=window)
    roll_h = df["humidity_percent"].rolling(window=window, min_periods=window)

    t_mean = roll_t.mean()
    t_std = roll_t.std(ddof=0)  # population std (stable for small windows)
    h_mean = roll_h.mean()
    h_std = roll_h.std(ddof=0)

    # Safe z-score: if std==0 or NaN, result 0.0 (not anomalous)
    def compute_z(x, m, s):
        z = (x - m) / s
        z = z.replace([np.inf, -np.inf], np.nan)
        z = z.fillna(0.0)
        z = np.where((s == 0) | (~np.isfinite(s)), 0.0, z)
        return pd.Series(z, index=x.index)

    df["temp_z"] = compute_z(df["temperature_c"], t_mean, t_std)
    df["hum_z"] = compute_z(df["humidity_percent"], h_mean, h_std)

    # Strictly greater than threshold per feedback ("above a threshold")
    df["temp_anomaly"] = (df["temp_z"].abs() > threshold)
    df["hum_anomaly"] = (df["hum_z"].abs() > threshold)
    df["any_anomaly"] = df["temp_anomaly"] | df["hum_anomaly"]

    anomalies = df[df["any_anomaly"]].copy()

    # Summaries
    summary = {
        "total_points": int(total_points),
        "valid_points": int(valid_points),
        "window": int(window),
        "threshold": float(threshold),
        "temp_anomalies": int(df["temp_anomaly"].sum()),
        "hum_anomalies": int(df["hum_anomaly"].sum()),
        "any_anomalies": int(df["any_anomaly"].sum()),
        "max_abs_temp_z": float(df["temp_z"].abs().max()) if total_points > 0 else None,
        "max_abs_hum_z": float(df["hum_z"].abs().max()) if total_points > 0 else None,
    }

    first_anom_ts = anomalies["timestamp"].min() if not anomalies.empty else None
    last_anom_ts = anomalies["timestamp"].max() if not anomalies.empty else None
    summary["first_anomaly_time"] = first_anom_ts.isoformat() if pd.notna(first_anom_ts) else None
    summary["last_anomaly_time"] = last_anom_ts.isoformat() if pd.notna(last_anom_ts) else None

    # Latest point info
    last_row = df.iloc[-1]
    latest = {
        "timestamp": last_row["timestamp"].isoformat() if pd.notna(last_row["timestamp"]) else None,
        "temperature_c": None if pd.isna(last_row["temperature_c"]) else float(last_row["temperature_c"]),
        "humidity_percent": None if pd.isna(last_row["humidity_percent"]) else float(last_row["humidity_percent"]),
        "temp_z": float(last_row["temp_z"]),
        "hum_z": float(last_row["hum_z"]),
        "temp_anomaly": bool(last_row["temp_anomaly"]),
        "hum_anomaly": bool(last_row["hum_anomaly"]),
        "any_anomaly": bool(last_row["any_anomaly"]),
    }

    # Top anomalies by max(|z|)
    def top_anomaly_rows(df_in, n=5):
        if df_in.empty:
            return []
        df_in = df_in.copy()
        df_in["score"] = np.maximum(df_in["temp_z"].abs(), df_in["hum_z"].abs())
        top = df_in.sort_values("score", ascending=False).head(n)
        recs = []
        for _, r in top.iterrows():
            recs.append({
                "timestamp": r["timestamp"].isoformat() if pd.notna(r["timestamp"]) else None,
                "temperature_c": None if pd.isna(r["temperature_c"]) else float(r["temperature_c"]),
                "humidity_percent": None if pd.isna(r["humidity_percent"]) else float(r["humidity_percent"]),
                "temp_z": float(r["temp_z"]),
                "hum_z": float(r["hum_z"]),
                "score": float(r["score"]),
            })
        return recs

    top5 = top_anomaly_rows(anomalies, n=5)

    # Populate result_summary
    result["result_summary"].append(
        make_entry("overview", summary, "High-level counts and settings for anomaly detection")
    )
    result["result_summary"].append(
        make_entry("latest_point", latest, "Latest observation and its anomaly status")
    )
    result["result_summary"].append(
        make_entry("top_anomalies", top5, "Top anomalies by maximum absolute z-score (up to 5)")
    )

    # Persist result JSON
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # Print concise console summary
    print_summary({
        "input_file": data_path,
        "output_file": out_file,
        **{k: v for k, v in summary.items() if k in ["total_points", "valid_points", "window", "threshold", "any_anomalies"]},
    })

    if top5:
        print("Top anomalies (timestamp, temp, hum, max|z|):")
        for r in top5:
            print(f"  {r['timestamp']}, {r['temperature_c']}C, {r['humidity_percent']}%RH, {r['score']:.2f}")
    else:
        print("No anomalies detected.")


if __name__ == "__main__":
    main()
