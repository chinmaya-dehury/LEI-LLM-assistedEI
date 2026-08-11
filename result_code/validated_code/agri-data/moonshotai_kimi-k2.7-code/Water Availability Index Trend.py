"""
Task: Water Availability Index Trend
Description: Compute the rolling trend of the Water Availability Index (WAI) derived from soil moisture and rainfall to highlight improving or worsening water conditions.
"""

# Programmatic path resolution pre-injected for reliability
import os
from pathlib import Path

_curr_dir = Path(__file__).resolve().parent
_root_dir = _curr_dir
while _root_dir.name and not (_root_dir / "data").exists():
    _parent = _root_dir.parent
    if _parent == _root_dir:
        break
    _root_dir = _parent

DATA_FILE_PATH = os.path.join(_root_dir, "data", "agri-data", "raw_data.csv")
if not os.path.exists(DATA_FILE_PATH):
    DATA_FILE_PATH = os.path.join(_root_dir, "data", "agri-data", "raw_data.txt")

METADATA_FILE_PATH = os.path.join(_root_dir, "data", "agri-data", "metadata.json")
OUTPUT_DIR = os.path.join(_root_dir, "output", "agri-data")
os.makedirs(OUTPUT_DIR, exist_ok=True)

import os
import csv
import json
import sys
from pathlib import Path
from datetime import datetime


def find_data_file():
    """Locate raw_data.csv or raw_data.txt under the project data directory."""
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / "data").exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent

    for name in ("raw_data.csv", "raw_data.txt"):
        candidate = root_dir / "data" / "agri-data" / name
        if candidate.exists():
            return candidate
    return None


def safe_float(value, column):
    """Convert a CSV value to float, treating missing/invalid as None."""
    if value is None:
        return None
    s = str(value).strip()
    if s == "" or s.upper() in ("NA", "N/A", "NULL"):
        return None
    try:
        return float(s)
    except ValueError:
        print(f"Warning: invalid numeric value in column '{column}': {value!r}", file=sys.stderr)
        return None


def compute_rolling_wai_trend(data_file, window=3):
    """Read WAI values and compute rolling-window trend."""
    wai_values = []
    dropped_rows = 0

    with open(data_file, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Normalize column names to lowercase for robust access
            row = {k.lower(): v for k, v in row.items()}

            # Prefer pre-computed WAI if available
            wai = safe_float(row.get("wai"), "wai")

            # Derive WAI from soil moisture and rainfall when not present
            if wai is None:
                soil_moisture = safe_float(row.get("soil_moisture"), "soil_moisture")
                rainfall = safe_float(row.get("rainfall"), "rainfall")
                if soil_moisture is None or rainfall is None:
                    dropped_rows += 1
                    continue
                # Normalized composite: equal contribution of moisture and rainfall
                wai = (soil_moisture * rainfall) / (soil_moisture + rainfall + 1e-6)

            wai_values.append(wai)

    if not wai_values:
        print("No valid WAI data found.", file=sys.stderr)
        return None

    summary = []
    n = len(wai_values)

    for i in range(window - 1, n):
        window_vals = wai_values[i - window + 1: i + 1]
        avg_wai = sum(window_vals) / window

        # Simple least-squares slope for the window
        x_mean = (window - 1) / 2.0
        y_mean = avg_wai
        numerator = sum((j - x_mean) * (window_vals[j] - y_mean) for j in range(window))
        denominator = sum((j - x_mean) ** 2 for j in range(window))
        slope = numerator / denominator if denominator != 0 else 0.0

        if slope > 0.001:
            trend = "improving"
        elif slope < -0.001:
            trend = "worsening"
        else:
            trend = "stable"

        summary.append({
            "window_end_index": i,
            "avg_wai": round(avg_wai, 4),
            "slope": round(slope, 6),
            "trend": trend
        })

    overall = "stable"
    if len(summary) >= 2:
        first_avg = summary[0]["avg_wai"]
        last_avg = summary[-1]["avg_wai"]
        if last_avg > first_avg:
            overall = "improving"
        elif last_avg < first_avg:
            overall = "worsening"

    return {
        "total_rows": n,
        "dropped_rows": dropped_rows,
        "window_size": window,
        "overall_trend": overall,
        "rolling_windows": summary
    }


def main():
    data_file = find_data_file()
    if not data_file:
        print("Error: raw_data.csv or raw_data.txt not found under data/agri-data/", file=sys.stderr)
        return

    result_summary = compute_rolling_wai_trend(data_file, window=3)
    if result_summary is None:
        return

    result = {
        "task_name": "Water Availability Index Trend",
        "description": "Rolling trend of the Water Availability Index (WAI) derived from soil moisture and rainfall to highlight improving or worsening water conditions.",
        "result_summary": result_summary,
        "result_generated_at": datetime.utcnow().isoformat() + "Z"
    }

    output_dir = Path("/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_moonshotai_kimi-k2.7-code_google_gemini-3.1-flash-lite_run2")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "water_availability_index_trend_result.json"

    with open(output_file, "w") as f:
        json.dump(result, f, indent=2)

    print(f"Saved WAI trend result to {output_file}")


if __name__ == "__main__":
    main()