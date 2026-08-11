"""
Task: Pest Pressure Spike Detection
Description: Detect sudden increases in the Pest_Pressure index relative to recent local readings to enable timely pest management intervention.
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

import argparse
import csv
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

WINDOW_SIZE = 10
Z_THRESHOLD = 2.0
ABSOLUTE_INCREASE_THRESHOLD = 0.5

def find_project_root(start):
    root = start
    while root.name:
        if (root / "data").exists():
            return root
        parent = root.parent
        if parent == root:
            break
        root = parent
    return start

def safe_float(value, col_name):
    if value is None:
        return None
    s = str(value).strip()
    if s == "" or s.upper() in {"NA", "N/A", "NULL"}:
        return None
    try:
        return float(s)
    except ValueError:
        print("Warning: invalid numeric value '%s' in column '%s', skipping." % (value, col_name), file=sys.stderr)
        return None

def main():
    parser = argparse.ArgumentParser(description="Detect pest pressure spikes from agricultural sensor data.")
    parser.add_argument("--strict", action="store_true", help="Fail if any rows are dropped due to missing or invalid data.")
    args = parser.parse_args()

    try:
        script_dir = Path(__file__).resolve().parent
    except NameError:
        script_dir = Path.cwd()
    root_dir = find_project_root(script_dir)
    data_file = root_dir / "data" / "agri-data" / "raw_data.csv"
    if not data_file.exists():
        data_file = root_dir / "data" / "agri-data" / "raw_data.txt"
    if not data_file.exists():
        print("Error: input file not found at %s" % data_file, file=sys.stderr)
        sys.exit(1)

    output_dir = Path("/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_moonshotai_kimi-k2.7-code_nvidia_nemotron-3-ultra-550b-a55b_run1")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "Pest Pressure Spike Detection_result.json"

    required_cols = {"pest_pressure", "label"}
    rows = []
    dropped = 0
    try:
        with open(data_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                print("Error: CSV has no header row.", file=sys.stderr)
                sys.exit(1)
            for idx, row in enumerate(reader):
                row = {k.lower().strip(): v for k, v in row.items()}
                if not required_cols.issubset(row.keys()):
                    print("Warning: row %d missing required columns, skipping." % idx, file=sys.stderr)
                    dropped += 1
                    continue
                pp = safe_float(row.get("pest_pressure"), "pest_pressure")
                if pp is None:
                    dropped += 1
                    continue
                rows.append({"row_index": idx, "label": row.get("label", "").strip(), "pest_pressure": pp})
    except Exception as e:
        print("Error reading input file: %s" % e, file=sys.stderr)
        sys.exit(1)

    if args.strict and dropped > 0:
        print("Error: strict mode enabled but %d rows were dropped." % dropped, file=sys.stderr)
        sys.exit(1)

    total_rows = len(rows)
    spikes = []
    for i in range(total_rows):
        if i < WINDOW_SIZE:
            continue
        window = [rows[j]["pest_pressure"] for j in range(i - WINDOW_SIZE, i)]
        current = rows[i]["pest_pressure"]
        local_mean = sum(window) / len(window)
        variance = sum((x - local_mean) ** 2 for x in window) / len(window)
        local_std = math.sqrt(variance) if variance > 0 else 0.0
        deviation = current - local_mean
        if local_std == 0:
            is_spike = deviation > ABSOLUTE_INCREASE_THRESHOLD
            z_score = float("inf") if deviation > 0 else 0.0
        else:
            z_score = deviation / local_std
            is_spike = z_score > Z_THRESHOLD and deviation > 0
        if is_spike:
            if z_score == float("inf") or deviation > local_mean * 0.5:
                severity = "high"
            else:
                severity = "moderate"
            spikes.append({
                "row_index": rows[i]["row_index"],
                "label": rows[i]["label"],
                "pest_pressure": round(current, 4),
                "local_mean": round(local_mean, 4),
                "local_std": round(local_std, 4),
                "deviation_from_mean": round(deviation, 4),
                "z_score": round(z_score, 4) if z_score != float("inf") else "inf",
                "severity": severity,
            })

    summary = {
        "input_file": str(data_file),
        "total_valid_rows": total_rows,
        "dropped_rows": dropped,
        "window_size": WINDOW_SIZE,
        "z_threshold": Z_THRESHOLD,
        "absolute_increase_threshold": ABSOLUTE_INCREASE_THRESHOLD,
        "spike_count": len(spikes),
        "spikes": spikes,
    }

    result = {
        "task_name": "Pest Pressure Spike Detection",
        "description": "Detect sudden increases in the Pest_Pressure index relative to recent local readings to enable timely pest management intervention.",
        "result_summary": [summary],
        "result_generated_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print("Saved results to %s" % output_file)
    except Exception as e:
        print("Error writing output file: %s" % e, file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()