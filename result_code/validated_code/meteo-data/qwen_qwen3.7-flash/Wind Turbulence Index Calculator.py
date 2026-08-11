from datetime import datetime
"""
Task: Wind Turbulence Index Calculator
Description: Analyze short-term fluctuations in wind speed to compute a simple turbulence metric, helping identify sudden gusts or unstable atmospheric conditions without complex vector math.
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

DATA_FILE_PATH = os.path.join(_root_dir, "data", "meteo-data", "raw_data.csv")
if not os.path.exists(DATA_FILE_PATH):
    DATA_FILE_PATH = os.path.join(_root_dir, "data", "meteo-data", "raw_data.txt")

METADATA_FILE_PATH = os.path.join(_root_dir, "data", "meteo-data", "metadata.json")
OUTPUT_DIR = os.path.join(_root_dir, "output", "meteo-data")
os.makedirs(OUTPUT_DIR, exist_ok=True)

import csv
import json
import os
import sys
import math
from pathlib import Path

def safe_float(value):
    if value is None:
        return None
    val = str(value).strip()
    if val == '' or val.lower() in ('na', 'n/a', 'None', 'nan'):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None

def calc_mean(values):
    valid = [v for v in values if v is not None]
    if not valid:
        return None
    return sum(valid) / len(valid)

def calc_std(values, mean=None):
    valid = [v for v in values if v is not None]
    if len(valid) < 2:
        return None
    if mean is None:
        mean = sum(valid) / len(valid)
    variance = sum((x - mean) ** 2 for x in valid) / (len(valid) - 1)
    return math.sqrt(variance)

def main():
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / "data").exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent

    data_file = root_dir / "data" / "meteo-data" / "raw_data.csv"
    if not data_file.exists():
        data_file = root_dir / "data" / "meteo-data" / "raw_data.txt"
    if not data_file.exists():
        print("ERROR: Input data file not found.")
        sys.exit(1)

    output_dir = Path("/home/dcc/LEI-Models-Comparision/output/meteo-data/meteo-data_qwen_qwen3.7-flash_majority_vote_3x_run1")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "wind_turbulence_index_calculator_result.json"

    WINDOW_SIZE = 5
    HIGH_TURBULENCE_THRESHOLD = 0.25

    wind_speeds = []
    timestamps = []
    dropped_rows = 0
    total_rows = 0

    try:
        with open(data_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                total_rows += 1
                normalized_row = {k.lower(): v for k, v in row.items()}
                ws = safe_float(normalized_row.get('wind_speed'))
                ts = safe_float(normalized_row.get('time_since_epoch'))
                if ws is None:
                    dropped_rows += 1
                    continue
                wind_speeds.append(ws)
                timestamps.append(ts)
    except Exception as e:
        print(f"ERROR reading file: {e}")
        sys.exit(1)

    if not wind_speeds:
        print("No valid wind speed data found.")
        result = {
            "task_name": "Wind Turbulence Index Calculator",
            "description": "Analyze short-term fluctuations in wind speed to compute a simple turbulence metric.",
            "result_summary": [{"error": "No valid wind speed data available"}],
            "result_generated_at": __import__('datetime').datetime.now().isoformat()
        }
        with open(output_path, 'w') as out:
            json.dump(result, out, indent=2)
        return

    turbulence_indices = []
    high_turbulence_count = 0
    turbulence_values = []

    for i in range(len(wind_speeds)):
        start_idx = max(0, i - WINDOW_SIZE + 1)
        window = wind_speeds[start_idx:i + 1]
        mean_val = calc_mean(window)
        std_val = calc_std(window, mean_val)
        if mean_val and mean_val > 0 and std_val is not None:
            ti = std_val / mean_val
        else:
            ti = None
        turbulence_indices.append(ti)
        if ti is not None:
            turbulence_values.append(ti)
            if ti >= HIGH_TURBULENCE_THRESHOLD:
                high_turbulence_count += 1

    valid_ti = [v for v in turbulence_values if v is not None]
    avg_ti = calc_mean(valid_ti) if valid_ti else None
    max_ti = max(valid_ti) if valid_ti else None
    min_ti = min(valid_ti) if valid_ti else None
    overall_std = calc_std(wind_speeds) if len(wind_speeds) >= 2 else None
    overall_mean = calc_mean(wind_speeds)

    result_summary = [
        {"metric": "total_records", "value": len(wind_speeds)},
        {"metric": "dropped_rows", "value": dropped_rows},
        {"metric": "overall_mean_wind_speed_ms", "value": round(overall_mean, 4) if overall_mean else None},
        {"metric": "overall_std_wind_speed_ms", "value": round(overall_std, 4) if overall_std else None},
        {"metric": "avg_turbulence_intensity", "value": round(avg_ti, 4) if avg_ti else None},
        {"metric": "max_turbulence_intensity", "value": round(max_ti, 4) if max_ti else None},
        {"metric": "min_turbulence_intensity", "value": round(min_ti, 4) if min_ti else None},
        {"metric": "high_turbulence_events_count", "value": high_turbulence_count},
        {"metric": "high_turbulence_threshold", "value": HIGH_TURBULENCE_THRESHOLD},
        {"metric": "rolling_window_size", "value": WINDOW_SIZE}
    ]

    result = {
        "task_name": "Wind Turbulence Index Calculator",
        "description": "Analyze short-term fluctuations in wind speed to compute a simple turbulence metric, helping identify sudden gusts or unstable atmospheric conditions without complex vector math.",
        "result_summary": result_summary,
        "result_generated_at": __import__('datetime').datetime.now().isoformat()
    }

    with open(output_path, 'w') as out:
        json.dump(result, out, indent=2)
    print(f"Result saved to {output_path}")

if __name__ == '__main__':
    main()