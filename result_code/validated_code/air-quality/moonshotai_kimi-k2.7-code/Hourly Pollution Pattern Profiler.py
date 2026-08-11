"""
Task: Hourly Pollution Pattern Profiler
Description: Aggregate each pollutant concentration by hour-of-day over a recent period to reveal recurring traffic-related pollution peaks.
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
import os
import sys
import csv
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta

TASK_NAME = "Hourly Pollution Pattern Profiler"
DESCRIPTION = "Aggregate each pollutant concentration by hour-of-day over the most recent 30 days of data to reveal recurring traffic-related pollution peaks."

OUTPUT_DIR = Path("/home/dcc/LEI-Models-Comparision/output/air-quality/air-quality_moonshotai_kimi-k2.7-code_google_gemini-3.1-flash-lite_run2")

MISSING_TOKENS = {"", "NA", "N/A", "None", "NULL", "None", "-200"}

POLLUTANTS = {
    "co(gt)": "CO",
    "nmhc(gt)": "NMHC",
    "c6h6(gt)": "C6H6",
    "nox(gt)": "NOx",
    "no2(gt)": "NO2",
}


def is_missing(value):
    if value is None:
        return True
    return str(value).strip() in MISSING_TOKENS


def to_float(value, col):
    if is_missing(value):
        return None
    try:
        v = float(value)
        # Negative sentinel values are treated as missing for concentrations.
        if v <= -200:
            return None
        return v
    except ValueError:
        print(f"Warning: invalid numeric value '{value}' in column '{col}', skipping.", file=sys.stderr)
        return None


def resolve_project_root():
    curr = Path(__file__).resolve().parent
    root = curr
    while root.name and not (root / "data").exists():
        parent = root.parent
        if parent == root:
            break
        root = parent
    return root


def find_data_file(root_dir):
    for ext in (".csv", ".txt"):
        candidate = root_dir / "data" / "air-quality" / f"raw_data{ext}"
        if candidate.exists():
            return candidate
    return None


def parse_datetime(date_str, time_str):
    if not date_str or not time_str:
        return None
    try:
        return datetime.strptime(f"{date_str.strip()} {time_str.strip()}", "%d-%m-%Y %H:%M:%S")
    except ValueError:
        return None


def main():
    parser = argparse.ArgumentParser(description=TASK_NAME)
    parser.add_argument("--strict", action="store_true", help="Skip rows with any missing pollutant value")
    args = parser.parse_args()

    root_dir = resolve_project_root()
    data_file = find_data_file(root_dir)
    if data_file is None:
        print("Error: raw_data.csv or raw_data.txt not found under data/air-quality/.", file=sys.stderr)
        sys.exit(1)

    print(f"Reading {data_file}")

    rows = []
    dropped = 0
    with data_file.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for lineno, row in enumerate(reader, start=2):
            if not row:
                continue
            row = {k.lower().strip(): v for k, v in row.items()}

            dt = parse_datetime(row.get("date"), row.get("time"))
            if dt is None:
                print(f"Warning: row {lineno} has invalid date/time, skipping.")
                dropped += 1
                continue

            record = {"dt": dt}
            valid_count = 0
            for col in POLLUTANTS:
                val = to_float(row.get(col), col)
                record[col] = val
                if val is not None:
                    valid_count += 1

            if args.strict and valid_count != len(POLLUTANTS):
                dropped += 1
                continue
            if valid_count == 0:
                dropped += 1
                continue

            rows.append(record)

    print(f"Loaded {len(rows)} rows, dropped {dropped} rows.")

    if not rows:
        print("Error: no valid rows to analyze.", file=sys.stderr)
        sys.exit(1)

    # Focus on the most recent 30 days of available data.
    max_dt = max(r["dt"] for r in rows)
    cutoff = max_dt - timedelta(days=30)
    recent_rows = [r for r in rows if r["dt"] >= cutoff]
    if not recent_rows:
        recent_rows = rows
        print("Warning: no data in last 30 days; using all data.")
    else:
        print(f"Analyzing {len(recent_rows)} rows from {cutoff} to {max_dt}.")

    # Aggregate by hour of day.
    hours = {h: {col: [] for col in POLLUTANTS} for h in range(24)}
    for r in recent_rows:
        h = r["dt"].hour
        for col in POLLUTANTS:
            v = r[col]
            if v is not None:
                hours[h][col].append(v)

    result_summary = []
    for h in range(24):
        entry = {"hour": h}
        counts = {}
        means = {}
        for col, label in POLLUTANTS.items():
            vals = hours[h][col]
            counts[label] = len(vals)
            means[label] = round(sum(vals) / len(vals), 4) if vals else None
        entry["sample_counts"] = counts
        entry["mean_concentrations"] = means
        result_summary.append(entry)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result = {
        "task_name": TASK_NAME,
        "description": DESCRIPTION,
        "result_summary": result_summary,
        "result_generated_at": datetime.now().isoformat(),
    }
    out_path = OUTPUT_DIR / "hourly_pollution_pattern_profiler_result.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"Result saved to {out_path}")


if __name__ == "__main__":
    main()