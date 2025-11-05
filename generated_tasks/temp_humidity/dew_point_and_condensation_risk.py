#!/usr/bin/env python3
import argparse
import json
import os
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

def iso_now():
    return datetime.now(timezone.utc).isoformat()

def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Compute dew point (Magnus formula) and flag condensation risk.\n"
            "Reads CSV with columns: timestamp, temperature_c, humidity_percent."
        )
    )
    parser.add_argument(
        "--data-type",
        default="temp_humidity",
        help="Data type folder name used to resolve default paths (default: temp_humidity)",
    )
    parser.add_argument(
        "--input",
        default=None,
        help=(
            "Optional explicit path to input CSV. If provided, it must exist. "
            "If omitted, will use data/{DATA_TYPE}/raw_data.csv"
        ),
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=20.0,
        help="Dew point threshold in °C for condensation risk (default: 20.0)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help=(
            "Optional output directory. If omitted, will use output/{DATA_TYPE}"
        ),
    )
    return parser.parse_args()

def resolve_paths(args):
    if args.input is not None:
        input_path = args.input
        if not os.path.isfile(input_path):
            print(f"Error: --input path not found: {input_path}", file=sys.stderr)
            sys.exit(2)
    else:
        input_path = os.path.join("data", args.data_type, "raw_data.csv")
        if not os.path.isfile(input_path):
            print(
                f"Error: default input path not found: {input_path}. "
                f"Provide --input or ensure the file exists.",
                file=sys.stderr,
            )
            sys.exit(2)

    output_dir = args.output_dir or os.path.join("output", args.data_type)
    os.makedirs(output_dir, exist_ok=True)

    result_filename = "dew_point_and_condensation_risk_result.json"
    result_path = os.path.join(output_dir, result_filename)
    return input_path, result_path

def validate_dataframe(df):
    required_cols = ["timestamp", "temperature_c", "humidity_percent"]
    for col in required_cols:
        if col not in df.columns:
            print(
                f"Error: Missing required column '{col}' in input CSV.",
                file=sys.stderr,
            )
            sys.exit(3)

    # Ensure datetime
    if not np.issubdtype(df["timestamp"].dtype, np.datetime64):
        try:
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        except Exception as e:
            print(f"Error parsing timestamps: {e}", file=sys.stderr)
            sys.exit(3)

    before = len(df)
    df = df.dropna(subset=["timestamp", "temperature_c", "humidity_percent"]).copy()
    if len(df) == 0:
        print("Error: No valid rows after dropping missing values.", file=sys.stderr)
        sys.exit(3)

    # Sort by time for consistency
    df = df.sort_values("timestamp").reset_index(drop=True)

    # Range checks per metadata
    temp_out = ~df["temperature_c"].between(15, 40)
    rh_out = ~df["humidity_percent"].between(20, 100)
    out_stats = {
        "temperature_out_of_range_count": int(temp_out.sum()),
        "humidity_out_of_range_count": int(rh_out.sum()),
        "dropped_missing_rows": int(before - len(df)),
    }

    return df, out_stats

def dew_point_celsius(t_c, rh_percent):
    # Magnus-Tetens over water (above 0°C)
    # a=17.62, b=243.12°C is a common parameterization
    a = 17.62
    b = 243.12
    t = np.asarray(t_c, dtype=float)
    rh = np.asarray(rh_percent, dtype=float)
    rh = np.clip(rh, 1e-6, 100.0)  # avoid log(0) and cap at 100
    gamma = (a * t) / (b + t) + np.log(rh / 100.0)
    dp = (b * gamma) / (a - gamma)
    return dp

def find_risk_periods(df, risk_col="risk"):
    periods = []
    in_period = False
    start_ts = None
    count = 0
    for i, row in df.iterrows():
        if bool(row[risk_col]) and not in_period:
            in_period = True
            start_ts = row["timestamp"]
            count = 1
        elif bool(row[risk_col]) and in_period:
            count += 1
        elif (not bool(row[risk_col])) and in_period:
            end_ts = df.loc[i - 1, "timestamp"]
            periods.append(
                {
                    "start": pd.to_datetime(start_ts).isoformat(),
                    "end": pd.to_datetime(end_ts).isoformat(),
                    "points": int(count),
                }
            )
            in_period = False
            start_ts = None
            count = 0
    # Close if ended in risk
    if in_period:
        end_ts = df.iloc[-1]["timestamp"]
        periods.append(
            {
                "start": pd.to_datetime(start_ts).isoformat(),
                "end": pd.to_datetime(end_ts).isoformat(),
                "points": int(count),
            }
        )
    return periods

def main():
    args = parse_args()
    input_path, result_path = resolve_paths(args)

    try:
        df = pd.read_csv(
            input_path,
            dtype={"temperature_c": float, "humidity_percent": float},
            parse_dates=["timestamp"],
        )
    except Exception as e:
        print(f"Error reading CSV '{input_path}': {e}", file=sys.stderr)
        sys.exit(2)

    df, out_stats = validate_dataframe(df)

    # Compute dew point
    df["dew_point_c"] = dew_point_celsius(df["temperature_c"], df["humidity_percent"])

    # Condensation risk
    threshold = float(args.threshold)
    df["risk"] = df["dew_point_c"] >= threshold

    # Summaries
    dp_min = float(np.nanmin(df["dew_point_c"]))
    dp_max = float(np.nanmax(df["dew_point_c"]))
    dp_mean = float(np.nanmean(df["dew_point_c"]))

    risk_count = int(df["risk"].sum())
    total = int(len(df))
    risk_pct = float((risk_count / total) * 100.0) if total > 0 else 0.0

    first_risk_ts = (
        pd.to_datetime(df.loc[df["risk"], "timestamp"].iloc[0]).isoformat()
        if risk_count > 0
        else None
    )
    last_risk_ts = (
        pd.to_datetime(df.loc[df["risk"], "timestamp"].iloc[-1]).isoformat()
        if risk_count > 0
        else None
    )

    periods = find_risk_periods(df, risk_col="risk")

    now_iso = iso_now()

    result = {
        "task_name": "dew_point_and_condensation_risk",
        "description": "Estimate dew point using a Magnus formula and flag potential condensation risk when dew_point >= configurable threshold (default 20°C).",
        "result_summary": [
            {
                "name": "dew_point_c_stats",
                "value": {
                    "min": round(dp_min, 2),
                    "max": round(dp_max, 2),
                    "mean": round(dp_mean, 2),
                },
                "description": "Summary statistics of computed dew point in °C.",
                "timestamp": now_iso,
            },
            {
                "name": "condensation_risk_threshold_c",
                "value": round(threshold, 2),
                "description": "Threshold used for flagging condensation risk (dew_point >= threshold).",
                "timestamp": now_iso,
            },
            {
                "name": "condensation_risk_counts",
                "value": {"risk_points": risk_count, "total_points": total, "risk_percent": round(risk_pct, 2)},
                "description": "Number and percentage of samples exceeding the dew point threshold.",
                "timestamp": now_iso,
            },
            {
                "name": "first_last_risk_timestamps",
                "value": {"first": first_risk_ts, "last": last_risk_ts},
                "description": "First and last timestamps where condensation risk was flagged (if any).",
                "timestamp": now_iso,
            },
            {
                "name": "risk_periods",
                "value": periods,
                "description": "Contiguous periods where dew point was at or above the threshold.",
                "timestamp": now_iso,
            },
            {
                "name": "data_quality_summary",
                "value": out_stats,
                "description": "Counts of out-of-range values and dropped missing rows based on metadata ranges.",
                "timestamp": now_iso,
            },
            {
                "name": "time_range",
                "value": {
                    "start": pd.to_datetime(df["timestamp"].iloc[0]).isoformat(),
                    "end": pd.to_datetime(df["timestamp"].iloc[-1]).isoformat(),
                    "rows": total,
                },
                "description": "Time coverage and number of data rows analyzed.",
                "timestamp": now_iso,
            },
            {
                "name": "last_observation",
                "value": {
                    "timestamp": pd.to_datetime(df["timestamp"].iloc[-1]).isoformat(),
                    "temperature_c": float(df["temperature_c"].iloc[-1]),
                    "humidity_percent": float(df["humidity_percent"].iloc[-1]),
                    "dew_point_c": round(float(df["dew_point_c"].iloc[-1]), 2),
                    "risk": bool(df["risk"].iloc[-1]),
                },
                "description": "Values from the most recent record including computed dew point and risk flag.",
                "timestamp": now_iso,
            },
        ],
        "result_generated_at": now_iso,
    }

    # Write result JSON
    try:
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error writing result JSON '{result_path}': {e}", file=sys.stderr)
        sys.exit(5)

    # Print a brief summary for console users
    print(f"Result written to: {result_path}")
    print(
        f"Dew point (°C) min/mean/max: {dp_min:.2f}/{dp_mean:.2f}/{dp_max:.2f} | "
        f"Risk points: {risk_count}/{total} ({risk_pct:.1f}%) | Threshold: {threshold:.2f}°C"
    )

if __name__ == "__main__":
    main()
