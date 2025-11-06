import os
import sys
import json
import argparse
from datetime import datetime, timezone

try:
    import pandas as pd
except ImportError:
    print("This task requires pandas. Please install it with: pip install pandas")
    sys.exit(1)


def load_data(input_path):
    if not os.path.exists(input_path):
        print(f"Input file not found: {input_path}")
        sys.exit(1)
    try:
        df = pd.read_csv(input_path)
    except Exception as e:
        print(f"Failed to read CSV: {e}")
        sys.exit(1)

    required_cols = {"timestamp", "temperature_c", "humidity_percent"}
    missing = required_cols - set(df.columns)
    if missing:
        print(f"Missing required columns in input CSV: {missing}")
        sys.exit(1)

    # Parse and clean
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["temperature_c"] = pd.to_numeric(df["temperature_c"], errors="coerce")
    df["humidity_percent"] = pd.to_numeric(df["humidity_percent"], errors="coerce")

    # Drop rows with invalid timestamps
    df = df.dropna(subset=["timestamp"]).copy()

    # Sort by time and set index
    df = df.sort_values("timestamp").set_index("timestamp")

    # If completely empty after cleaning
    if df.empty:
        print("No valid data rows after cleaning.")
    return df


def compute_hourly_stats(df):
    if df.empty:
        return pd.DataFrame()
    # Resample hourly and compute mean/min/max for both metrics
    agg = df.resample('1H').agg({
        'temperature_c': ['mean', 'min', 'max'],
        'humidity_percent': ['mean', 'min', 'max']
    })
    # Flatten multiindex columns
    agg.columns = [f"{a}_{b}" for a, b in agg.columns]
    # Drop hours where everything is NaN
    agg = agg.dropna(how='all')
    return agg


def build_result_json(task_name, task_description, hourly_df):
    now_iso = datetime.now(timezone.utc).isoformat()
    result_summary = []

    descriptions = {
        'temperature_c_mean': 'Hourly mean temperature in °C',
        'temperature_c_min': 'Hourly minimum temperature in °C',
        'temperature_c_max': 'Hourly maximum temperature in °C',
        'humidity_percent_mean': 'Hourly mean relative humidity in %',
        'humidity_percent_min': 'Hourly minimum relative humidity in %',
        'humidity_percent_max': 'Hourly maximum relative humidity in %',
    }

    if not hourly_df.empty:
        for ts, row in hourly_df.iterrows():
            ts_iso = ts.isoformat()
            for col in hourly_df.columns:
                val = row[col]
                if pd.notna(val):
                    result_summary.append({
                        "name": col,
                        "value": float(val),
                        "description": descriptions.get(col, col),
                        "timestamp": ts_iso
                    })

    result = {
        "task_name": task_name,
        "description": task_description,
        "result_summary": result_summary,
        "result_generated_at": now_iso
    }
    return result


def main():
    parser = argparse.ArgumentParser(description="Hourly summary stats for environmental sensor data")
    parser.add_argument("--data_type", type=str, default="environment", help="Data type folder name (used to locate data and output directories)")
    parser.add_argument("--input", type=str, default=None, help="Optional explicit input CSV path. If not provided, uses data/{DATA_TYPE}/raw_data.csv")
    args = parser.parse_args()

    data_type = args.data_type
    input_path = args.input if args.input else os.path.join("data", data_type, "raw_data.csv")

    # Prepare output directory and result path
    output_dir = os.path.join("output", data_type)
    os.makedirs(output_dir, exist_ok=True)
    result_path = os.path.join(output_dir, "hourly_summary_stats_result.json")

    # Load and process data
    df = load_data(input_path)
    hourly_df = compute_hourly_stats(df)

    # Print human-readable summary to console
    if hourly_df.empty:
        print("No hourly statistics could be computed (no data).")
    else:
        # Format display to 2 decimals
        with pd.option_context('display.float_format', lambda x: f"{x:.2f}"):
            print("Hourly summary statistics (mean/min/max):")
            print(hourly_df)

    # Build and write result JSON
    task_name = "hourly_summary_stats"
    task_description = "Resample 5-minute readings to hourly and compute mean, min, and max for temperature_c and humidity_percent."
    result = build_result_json(task_name, task_description, hourly_df)

    try:
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"Results saved to: {result_path}")
    except Exception as e:
        print(f"Failed to write result JSON: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
