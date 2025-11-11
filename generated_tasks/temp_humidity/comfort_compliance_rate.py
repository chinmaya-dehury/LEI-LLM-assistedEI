import os
import sys
import json
from pathlib import Path
from datetime import datetime

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
        from datetime import datetime as _dt
        if isinstance(ts, _dt):
            return ts.isoformat()
        return str(ts)
    except Exception:
        return str(ts)


def main():
    TASK_NAME = "comfort_compliance_rate"
    DESCRIPTION = "Compute percent of time within a simplified comfort box (temperature_c in [22, 26] and humidity_percent in [30, 60]); report compliance %, compliant minutes, and longest continuous non-compliance streak."
    DATA_TYPE = "temp_humidity"

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

    # Validate
    required_cols = ["timestamp", "temperature_c", "humidity_percent"]
    for c in required_cols:
        if c not in df.columns:
            print(f"Missing required column: {c}", file=sys.stderr)
            sys.exit(1)

    # Parse and clean
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"]).copy()
    df = df.sort_values("timestamp").reset_index(drop=True)

    df["temperature_c"] = pd.to_numeric(df["temperature_c"], errors="coerce")
    df["humidity_percent"] = pd.to_numeric(df["humidity_percent"], errors="coerce")
    df = df.dropna(subset=["temperature_c", "humidity_percent"])  # ensure numeric

    if df.empty:
        print("No valid data rows after cleaning.", file=sys.stderr)
        sys.exit(1)

    # Compute per-interval minutes
    df["delta_min"] = df["timestamp"].diff().dt.total_seconds().div(60)
    default_delta = 5.0
    if df["delta_min"].notna().any():
        med = df["delta_min"].median()
        if pd.notna(med) and med > 0:
            default_delta = float(med)
    df.loc[df.index[0], "delta_min"] = default_delta
    df["delta_min"] = df["delta_min"].clip(lower=1, upper=120)

    # Comfort box
    temp_ok = (df["temperature_c"] >= 22.0) & (df["temperature_c"] <= 26.0)
    rh_ok = (df["humidity_percent"] >= 30.0) & (df["humidity_percent"] <= 60.0)
    compliant = temp_ok & rh_ok

    total_minutes = float(df["delta_min"].sum()) if not df.empty else 0.0
    compliant_minutes = float(df.loc[compliant, "delta_min"].sum()) if total_minutes > 0 else 0.0
    compliance_percent = float((compliant_minutes / total_minutes) * 100.0) if total_minutes > 0 else 0.0

    # Longest continuous non-compliance streak (sum of consecutive non-compliant intervals)
    longest_streak = 0.0
    current_streak = 0.0
    for is_ok, minutes in zip(compliant.tolist(), df["delta_min"].tolist()):
        if not is_ok:
            current_streak += float(minutes)
            if current_streak > longest_streak:
                longest_streak = current_streak
        else:
            current_streak = 0.0

    end_time = df["timestamp"].max()

    results = {
        "task_name": TASK_NAME,
        "description": DESCRIPTION,
        "result_summary": [
            {
                "name": "compliance_percent",
                "value": round(compliance_percent, 2),
                "description": "Percent of time within comfort box [22-26]°C and [30-60]% RH (time-weighted).",
                "timestamp": to_iso(end_time)
            },
            {
                "name": "compliant_minutes",
                "value": round(compliant_minutes, 2),
                "description": "Total minutes meeting both temperature and humidity comfort thresholds.",
                "timestamp": to_iso(end_time)
            },
            {
                "name": "longest_non_compliance_streak_minutes",
                "value": round(longest_streak, 2),
                "description": "Longest continuous duration of non-compliance (sum of consecutive non-compliant intervals).",
                "timestamp": to_iso(end_time)
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