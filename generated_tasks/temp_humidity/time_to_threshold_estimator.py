#!/usr/bin/env python3
import os
import sys
import json
from datetime import datetime, timezone
import argparse
import pandas as pd
import numpy as np

def main():
    parser = argparse.ArgumentParser(description="Estimate time until temperature or humidity thresholds are breached using a linear fit over last N readings.")
    parser.add_argument("--window", type=int, default=6, help="Number of most recent readings to use for linear fit (default: 6)")
    parser.add_argument("--temp_threshold", type=float, default=30.0, help="Temperature threshold in Celsius (default: 30.0)")
    parser.add_argument("--hum_threshold", type=float, default=65.0, help="Humidity threshold in percent (default: 65.0)")
    args = parser.parse_args()

    data_type = "temp_humidity"
    task_name = "time_to_threshold_estimator"
    description = "Using a linear fit on the last N readings (default N=6), estimate minutes until temperature_c > 30.0°C or humidity_percent > 65.0% if the slope is positive; output predicted breach time or None."

    data_path = os.path.join("data", data_type, "raw_data.csv")
    out_dir = os.path.join("output", data_type)
    os.makedirs(out_dir, exist_ok=True)

    if not os.path.exists(data_path):
        print(f"Data file not found: {data_path}")
        sys.exit(1)

    try:
        df = pd.read_csv(data_path)
    except Exception as e:
        print(f"Failed to read CSV: {e}")
        sys.exit(1)

    required_cols = {"timestamp", "temperature_c", "humidity_percent"}
    if not required_cols.issubset(df.columns):
        print("Required columns missing. Expected: timestamp, temperature_c, humidity_percent")
        sys.exit(1)

    # Parse and clean
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp", "temperature_c", "humidity_percent"]).sort_values("timestamp")

    if len(df) < 2:
        print("Not enough rows to perform estimation (need at least 2).")
        sys.exit(1)

    N = int(max(2, min(args.window, len(df))))
    window_df = df.tail(N).copy()
    t0 = window_df["timestamp"].iloc[0]
    window_df["minutes"] = (window_df["timestamp"] - t0).dt.total_seconds() / 60.0

    x = window_df["minutes"].to_numpy(dtype=float)
    temp = window_df["temperature_c"].to_numpy(dtype=float)
    hum = window_df["humidity_percent"].to_numpy(dtype=float)

    def lin_fit(xv, yv):
        if len(xv) < 2:
            return np.nan, np.nan
        try:
            slope, intercept = np.polyfit(xv, yv, 1)
            return float(slope), float(intercept)
        except Exception:
            return np.nan, np.nan

    temp_slope, temp_intercept = lin_fit(x, temp)
    hum_slope, hum_intercept = lin_fit(x, hum)

    last_ts = window_df["timestamp"].iloc[-1]
    last_x = float(x[-1])
    last_temp = float(temp[-1])
    last_hum = float(hum[-1])

    def estimate(threshold, slope, intercept, current_x, current_value):
        # Returns (minutes_from_now, predicted_timestamp, status)
        if np.isnan(slope) or slope <= 0:
            return None, None, "non_positive_slope"
        if current_value > threshold:
            return 0.0, last_ts.to_pydatetime(), "already_above"
        try:
            t_cross = (threshold - intercept) / slope
        except Exception:
            return None, None, "fit_error"
        minutes_from_last = float(t_cross - current_x)
        if minutes_from_last < 0:
            return None, None, "cross_in_past_inconsistent"
        predicted_time = t0 + pd.to_timedelta(t_cross, unit="m")
        return minutes_from_last, pd.Timestamp(predicted_time).to_pydatetime(), "predicted"

    temp_minutes, temp_pred_time, temp_status = estimate(args.temp_threshold, temp_slope, temp_intercept, last_x, last_temp)
    hum_minutes, hum_pred_time, hum_status = estimate(args.hum_threshold, hum_slope, hum_intercept, last_x, last_hum)

    def to_iso(ts):
        if ts is None:
            return None
        if isinstance(ts, pd.Timestamp):
            return ts.tz_localize(None).isoformat()
        if hasattr(ts, "isoformat"):
            return ts.replace(tzinfo=None).isoformat()
        return str(ts)

    last_ts_iso = to_iso(last_ts)
    now_iso = datetime.now(timezone.utc).isoformat()

    # Determine earliest breach
    candidates = []
    if temp_minutes is not None:
        candidates.append(("temperature_c", temp_minutes, to_iso(temp_pred_time)))
    if hum_minutes is not None:
        candidates.append(("humidity_percent", hum_minutes, to_iso(hum_pred_time)))
    if candidates:
        earliest_metric, earliest_minutes, earliest_time = min(candidates, key=lambda t: t[1])
    else:
        earliest_metric, earliest_minutes, earliest_time = None, None, None

    result_summary = [
        {
            "name": "temperature_slope_degC_per_min",
            "value": None if np.isnan(temp_slope) else round(float(temp_slope), 5),
            "description": f"Slope of linear fit over last {N} readings for temperature.",
            "timestamp": last_ts_iso,
        },
        {
            "name": "humidity_slope_percent_per_min",
            "value": None if np.isnan(hum_slope) else round(float(hum_slope), 5),
            "description": f"Slope of linear fit over last {N} readings for humidity.",
            "timestamp": last_ts_iso,
        },
        {
            "name": "minutes_until_temperature_breach",
            "value": None if temp_minutes is None else round(float(temp_minutes), 2),
            "description": f"Estimated minutes until temperature exceeds {args.temp_threshold}C. Status: {temp_status}.",
            "timestamp": last_ts_iso if temp_pred_time is None or (isinstance(temp_minutes, (int, float)) and temp_minutes == 0.0) else to_iso(temp_pred_time),
        },
        {
            "name": "predicted_temperature_breach_time",
            "value": to_iso(temp_pred_time),
            "description": f"Predicted timestamp when temperature crosses {args.temp_threshold}C, if applicable.",
            "timestamp": last_ts_iso,
        },
        {
            "name": "minutes_until_humidity_breach",
            "value": None if hum_minutes is None else round(float(hum_minutes), 2),
            "description": f"Estimated minutes until humidity exceeds {args.hum_threshold}%. Status: {hum_status}.",
            "timestamp": last_ts_iso if hum_pred_time is None or (isinstance(hum_minutes, (int, float)) and hum_minutes == 0.0) else to_iso(hum_pred_time),
        },
        {
            "name": "predicted_humidity_breach_time",
            "value": to_iso(hum_pred_time),
            "description": f"Predicted timestamp when humidity crosses {args.hum_threshold}%, if applicable.",
            "timestamp": last_ts_iso,
        },
        {
            "name": "earliest_predicted_breach_metric",
            "value": earliest_metric,
            "description": "Metric expected to breach threshold first among temperature and humidity.",
            "timestamp": last_ts_iso,
        },
        {
            "name": "earliest_predicted_breach_minutes",
            "value": None if earliest_minutes is None else round(float(earliest_minutes), 2),
            "description": "Minutes until earliest breach.",
            "timestamp": last_ts_iso if earliest_time is None or (isinstance(earliest_minutes, (int, float)) and earliest_minutes == 0.0) else earliest_time,
        },
        {
            "name": "earliest_predicted_breach_time",
            "value": earliest_time,
            "description": "Predicted timestamp of earliest breach.",
            "timestamp": last_ts_iso,
        },
    ]

    output = {
        "task_name": task_name,
        "description": description,
        "result_summary": result_summary,
        "result_generated_at": now_iso,
    }

    out_path = os.path.join(out_dir, f"{task_name}_result.json")
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)
    except Exception as e:
        print(f"Failed to write output JSON: {e}")
        sys.exit(1)

    print(json.dumps(output, indent=2))

if __name__ == "__main__":
    main()