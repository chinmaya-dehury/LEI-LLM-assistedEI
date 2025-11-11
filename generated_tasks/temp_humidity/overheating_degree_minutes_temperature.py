import os
import sys
import json
from pathlib import Path
from datetime import datetime
import argparse

try:
    import pandas as pd
    import numpy as np
except Exception as e:
    print(f"Error importing dependencies: {e}", file=sys.stderr)
    sys.exit(1)


def to_iso(ts):
    try:
        if pd.isna(ts):
            return None
        if hasattr(ts, 'to_pydatetime'):
            return ts.to_pydatetime().isoformat()
        if isinstance(ts, (datetime, )):
            return ts.isoformat()
        return str(ts)
    except Exception:
        return str(ts)


def main():
    TASK_NAME = "overheating_degree_minutes_temperature"
    DESCRIPTION = "Accumulate degree-minutes above a configurable comfort setpoint (default 26.0°C) using per-interval minutes to quantify overheating burden."
    DATA_TYPE = "temp_humidity"

    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument("--setpoint", type=float, default=float(os.environ.get("SETPOINT_C", 26.0)), help="Comfort temperature setpoint in °C (default from env SETPOINT_C or 26.0)")
    args = parser.parse_args()

    data_path = os.path.join("data", DATA_TYPE, "raw_data.csv")
    output_dir = Path("output") / DATA_TYPE
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{TASK_NAME}_result.json"

    now_iso = datetime.now().isoformat()

    try:
        df = pd.read_csv(data_path)
    except FileNotFoundError:
        print(f"Data file not found at {data_path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Failed to read CSV: {e}", file=sys.stderr)
        sys.exit(1)

    # Basic validation and preprocessing
    required_cols = ["timestamp", "temperature_c"]
    for c in required_cols:
        if c not in df.columns:
            print(f"Missing required column: {c}", file=sys.stderr)
            sys.exit(1)

    try:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    except Exception as e:
        print(f"Failed to parse timestamps: {e}", file=sys.stderr)
        sys.exit(1)

    df = df.dropna(subset=["timestamp"]).copy()
    df = df.sort_values("timestamp").reset_index(drop=True)

    # Ensure numeric
    df["temperature_c"] = pd.to_numeric(df["temperature_c"], errors="coerce")
    df = df.dropna(subset=["temperature_c"])  # drop rows with non-numeric temp

    if df.empty:
        print("No valid data rows after cleaning.", file=sys.stderr)
        sys.exit(1)

    # Compute minutes per row using timestamp diffs; fallback to 5 if not available
    df["delta_min"] = df["timestamp"].diff().dt.total_seconds().div(60)
    # If first diff is NaN, set to median or 5
    default_delta = 5.0
    if df["delta_min"].notna().any():
        med = df["delta_min"].median()
        if pd.notna(med) and med > 0:
            default_delta = float(med)
    df.loc[df.index[0], "delta_min"] = default_delta
    # Clip to reasonable bounds to avoid outliers
    df["delta_min"] = df["delta_min"].clip(lower=1, upper=120)

    setpoint = float(args.setpoint)

    # Degree-minutes calculation
    df["deg_above"] = np.maximum(0.0, df["temperature_c"] - setpoint)
    df["deg_min"] = df["deg_above"] * df["delta_min"]

    total_deg_min = float(df["deg_min"].sum())
    total_minutes_above = float(df.loc[df["deg_above"] > 0, "delta_min"].sum())
    max_deg_above = float(df["deg_above"].max()) if not df.empty else 0.0

    if (df["deg_min"].fillna(0).max()) > 0:
        peak_idx = int(df["deg_min"].idxmax())
        peak_time = df.loc[peak_idx, "timestamp"]
        peak_deg_min = float(df.loc[peak_idx, "deg_min"])
    else:
        peak_time = None
        peak_deg_min = 0.0

    end_time = df["timestamp"].max()

    results = {
        "task_name": TASK_NAME,
        "description": DESCRIPTION,
        "result_summary": [
            {
                "name": "total_overheating_degree_minutes",
                "value": round(total_deg_min, 3),
                "description": f"Sum of degrees above {setpoint:.1f}°C multiplied by minutes across intervals.",
                "timestamp": to_iso(end_time)
            },
            {
                "name": "total_minutes_above_setpoint",
                "value": round(total_minutes_above, 2),
                "description": f"Total minutes where temperature exceeded {setpoint:.1f}°C.",
                "timestamp": to_iso(end_time)
            },
            {
                "name": "max_instant_degrees_above_setpoint",
                "value": round(max_deg_above, 3),
                "description": f"Maximum single reading degrees above {setpoint:.1f}°C.",
                "timestamp": to_iso(end_time)
            },
            {
                "name": "peak_interval_overheating",
                "value": round(peak_deg_min, 3),
                "description": "Highest degree-minutes contribution from a single interval.",
                "timestamp": to_iso(peak_time)
            }
        ],
        "result_generated_at": now_iso
    }

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(json.dumps(results, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"Failed to write results: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()