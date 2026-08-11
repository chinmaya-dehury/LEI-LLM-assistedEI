"""
Task: Sensor_Drift_Indicator
Description: Compare the current rolling average of a sensor response to its deployment baseline average and report the percentage deviation as a drift indicator.
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

DATA_FILE_PATH = os.path.join(_root_dir, "data", "air-quality", "raw_data.csv")
if not os.path.exists(DATA_FILE_PATH):
    DATA_FILE_PATH = os.path.join(_root_dir, "data", "air-quality", "raw_data.txt")

METADATA_FILE_PATH = os.path.join(_root_dir, "data", "air-quality", "metadata.json")
OUTPUT_DIR = os.path.join(_root_dir, "output", "air-quality")
os.makedirs(OUTPUT_DIR, exist_ok=True)

#!/usr/bin/env python3
"""Sensor drift indicator for air-quality sensor array."""
import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SENSORS = [
    "pt08.s1(co)",
    "pt08.s2(nmhc)",
    "pt08.s3(nox)",
    "pt08.s4(no2)",
    "pt08.s5(o3)",
]

MISSING_STRINGS = {"", "na", "n/a", "None", "none"}

def is_missing(value):
    if value is None:
        return True
    s = str(value).strip()
    return s == "" or s.lower() in MISSING_STRINGS

def to_float(value, column):
    if is_missing(value):
        return None
    s = str(value).strip()
    try:
        f = float(s)
    except ValueError:
        print(f"Warning: cannot parse {column} value {value!r}", file=sys.stderr)
        return None
    if f <= -200.0:
        return None
    return f

def find_data_file():
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / "data").exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent
    for fname in ("raw_data.csv", "raw_data.txt"):
        candidate = root_dir / "data" / "air-quality" / fname
        if candidate.exists():
            return candidate
    return None

def load_rows(path, strict):
    rows = []
    dropped = 0
    with open(path, "r", newline="") as fh:
        reader = csv.DictReader(fh)
        for idx, raw_row in enumerate(reader):
            try:
                row = {k.lower().strip(): v for k, v in raw_row.items() if k and str(k).strip()}
                record = {}
                for sensor in SENSORS:
                    record[sensor] = to_float(row.get(sensor), sensor)
                if strict and any(v is None for v in record.values()):
                    dropped += 1
                    continue
                rows.append(record)
            except Exception as exc:
                print(f"Warning: row {idx} skipped: {exc}", file=sys.stderr)
                dropped += 1
    return rows, dropped

def mean(values):
    if not values:
        return None
    return sum(values) / len(values)

def compute_drift(rows, baseline_count=720, current_count=168):
    n = len(rows)
    if n == 0:
        return []
    current_count = min(current_count, n)
    baseline_count = min(baseline_count, n - current_count)
    if baseline_count <= 0:
        baseline_count = max(1, n // 2)
        current_count = n - baseline_count
    baseline_rows = rows[:baseline_count]
    current_rows = rows[-current_count:]
    results = []
    for sensor in SENSORS:
        base_vals = [r[sensor] for r in baseline_rows if r.get(sensor) is not None]
        cur_vals = [r[sensor] for r in current_rows if r.get(sensor) is not None]
        base_avg = mean(base_vals)
        cur_avg = mean(cur_vals)
        if base_avg is None or cur_avg is None or base_avg == 0:
            deviation = None
        else:
            deviation = (cur_avg - base_avg) / base_avg * 100.0
        results.append({
            "sensor": sensor,
            "baseline_window_rows": len(baseline_rows),
            "baseline_valid_readings": len(base_vals),
            "baseline_average": round(base_avg, 6) if base_avg is not None else None,
            "current_window_rows": len(current_rows),
            "current_valid_readings": len(cur_vals),
            "current_average": round(cur_avg, 6) if cur_avg is not None else None,
            "drift_percent": round(deviation, 4) if deviation is not None else None,
        })
    return results

def main():
    parser = argparse.ArgumentParser(description="Compute sensor drift indicator.")
    parser.add_argument("--strict", action="store_true", help="Drop rows with any missing sensor value.")
    args = parser.parse_args()

    data_file = find_data_file()
    if not data_file:
        print("Error: raw_data.csv or raw_data.txt not found under data/air-quality/", file=sys.stderr)
        sys.exit(1)

    rows, dropped = load_rows(data_file, args.strict)
    print(f"Loaded {len(rows)} rows from {data_file} (dropped {dropped}).")

    summary = compute_drift(rows)

    out_dir = Path("/home/dcc/LEI-Models-Comparision/output/air-quality/air-quality_moonshotai_kimi-k2.7-code_anthropic_claude-3-haiku_run1")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "Sensor_Drift_Indicator_result.json"

    result = {
        "task_name": "Sensor_Drift_Indicator",
        "description": "Compare the current rolling average of a sensor response to its deployment baseline average and report the percentage deviation as a drift indicator.",
        "result_summary": summary,
        "result_generated_at": datetime.now(timezone.utc).isoformat(),
    }

    with open(out_file, "w") as fh:
        json.dump(result, fh, indent=2)

    print(f"Saved drift indicator to {out_file}")
    for item in summary:
        print(f"{item['sensor']}: baseline={item['baseline_average']}, current={item['current_average']}, drift={item['drift_percent']}%")

if __name__ == "__main__":
    main()