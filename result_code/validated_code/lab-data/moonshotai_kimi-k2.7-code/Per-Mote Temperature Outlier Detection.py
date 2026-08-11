"""
Task: Per-Mote Temperature Outlier Detection
Description: Compute a running mean and standard deviation of temperature for each mote and flag readings that deviate beyond a configurable threshold (e.g., 2 sigma) as potential anomalies.
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

DATA_FILE_PATH = os.path.join(_root_dir, "data", "lab-data", "raw_data.csv")
if not os.path.exists(DATA_FILE_PATH):
    DATA_FILE_PATH = os.path.join(_root_dir, "data", "lab-data", "raw_data.txt")

METADATA_FILE_PATH = os.path.join(_root_dir, "data", "lab-data", "metadata.json")
OUTPUT_DIR = os.path.join(_root_dir, "output", "lab-data")
os.makedirs(OUTPUT_DIR, exist_ok=True)

import os
import csv
import json
import math
import argparse
from pathlib import Path
from datetime import datetime, timezone

TASK_NAME = "Per-Mote Temperature Outlier Detection"
DESCRIPTION = "Compute a running mean and standard deviation of temperature for each mote and flag readings that deviate beyond a configurable threshold (e.g., 2 sigma) as potential anomalies."


def find_project_root():
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / "data").exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent
    return root_dir


def safe_float(value, col_name):
    if value is None:
        return None
    s = str(value).strip()
    if s == "" or s.upper() in ("NA", "N/A", "NULL"):
        return None
    try:
        return float(s)
    except ValueError:
        print(f"Warning: invalid numeric value in column '{col_name}': '{value}'")
        return None


def parse_moteid(value):
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def compute_running_stats(data_file):
    """Compute running mean and variance per mote using Welford's algorithm."""
    mote_stats = {}
    total_rows = 0
    dropped_rows = 0

    with open(data_file, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            row = {k.lower(): v for k, v in row.items()}
            moteid = parse_moteid(row.get("moteid"))
            temp = safe_float(row.get("temperature"), "temperature")

            if moteid is None or temp is None:
                dropped_rows += 1
                continue

            if moteid not in mote_stats:
                mote_stats[moteid] = {"count": 0, "mean": 0.0, "m2": 0.0}

            stats = mote_stats[moteid]
            stats["count"] += 1
            delta = temp - stats["mean"]
            stats["mean"] += delta / stats["count"]
            delta2 = temp - stats["mean"]
            stats["m2"] += delta * delta2

    # Convert M2 to population standard deviation
    for stats in mote_stats.values():
        if stats["count"] < 2:
            stats["std"] = 0.0
        else:
            stats["std"] = math.sqrt(stats["m2"] / stats["count"])

    return mote_stats, total_rows, dropped_rows


def count_outliers(data_file, mote_stats, threshold):
    """Second pass: count readings beyond threshold * std from the mean."""
    outlier_counts = {moteid: 0 for moteid in mote_stats}

    with open(data_file, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row = {k.lower(): v for k, v in row.items()}
            moteid = parse_moteid(row.get("moteid"))
            temp = safe_float(row.get("temperature"), "temperature")

            if moteid is None or temp is None or moteid not in mote_stats:
                continue

            mean = mote_stats[moteid]["mean"]
            std = mote_stats[moteid]["std"]
            if std > 0 and abs(temp - mean) > threshold * std:
                outlier_counts[moteid] += 1

    return outlier_counts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true", help="Require complete rows")
    parser.add_argument("--threshold", type=float, default=2.0, help="Sigma threshold for outlier detection")
    args = parser.parse_args()

    root_dir = find_project_root()
    data_file = root_dir / "data" / "lab-data" / "raw_data.csv"
    if not data_file.exists():
        data_file = root_dir / "data" / "lab-data" / "raw_data.txt"

    if not data_file.exists():
        print(f"Error: input file not found at {data_file}")
        return

    mote_stats, total_rows, dropped_rows = compute_running_stats(data_file)

    if args.strict and dropped_rows > 0:
        print(f"Strict mode enabled; {dropped_rows} rows were dropped. Exiting.")
        return

    outlier_counts = count_outliers(data_file, mote_stats, args.threshold)

    results = []
    for moteid in sorted(mote_stats.keys()):
        stats = mote_stats[moteid]
        results.append({
            "moteid": moteid,
            "readings_count": stats["count"],
            "mean_temperature": round(stats["mean"], 4),
            "std_temperature": round(stats["std"], 4),
            "outlier_count": outlier_counts[moteid],
            "outlier_threshold_sigma": args.threshold
        })

    output_dir = Path("/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_moonshotai_kimi-k2.7-code_google_gemini-3.1-flash-lite_run1")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{TASK_NAME.replace(' ', '_')}_result.json"

    result = {
        "task_name": TASK_NAME,
        "description": DESCRIPTION,
        "result_summary": [
            {
                "total_rows_processed": total_rows,
                "dropped_rows": dropped_rows,
                "motes_analyzed": len(results),
                "sigma_threshold": args.threshold,
                "mote_statistics": results
            }
        ],
        "result_generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"Results saved to {output_file}")


if __name__ == "__main__":
    main()