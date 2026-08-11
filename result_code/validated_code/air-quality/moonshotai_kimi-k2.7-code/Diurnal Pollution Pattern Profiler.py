"""
Task: Diurnal Pollution Pattern Profiler
Description: Aggregate valid CO(GT), NMHC(GT), C6H6(GT), NOx(GT), and NO2(GT) readings by hour-of-day using lightweight counters and sums. Output average concentrations per hour to reveal daily road-level pollution cycles.
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

import argparse
import csv
import json
import math
import sys
from datetime import datetime
from pathlib import Path

POLLUTANTS = ["co(gt)", "nmhc(gt)", "c6h6(gt)", "nox(gt)", "no2(gt)"]


def is_missing(raw):
    if raw is None:
        return True
    s = str(raw).strip()
    return s == "" or s.lower() in {"na", "n/a", "None", "none"}


def to_float(raw, col):
    if is_missing(raw):
        return None
    s = str(raw).strip()
    try:
        v = float(s)
    except ValueError:
        print(f"Warning: non-numeric value in {col}: {raw!r}", file=sys.stderr)
        return None
    # The dataset uses -200 as a missing sentinel; concentrations cannot be negative
    if v <= -200 or math.isnan(v):
        return None
    return v


def parse_hour(time_val):
    if is_missing(time_val):
        return None
    s = str(time_val).strip()
    try:
        return datetime.strptime(s, "%H:%M:%S").hour
    except ValueError:
        try:
            return int(s.split(":")[0])
        except Exception:
            return None


def resolve_data_file():
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / "data").exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent
    for name in ["raw_data.csv", "raw_data.txt"]:
        candidate = root_dir / "data" / "air-quality" / name
        if candidate.exists():
            return candidate
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true", help="Skip rows with any missing pollutant value")
    args = parser.parse_args()

    data_file = resolve_data_file()
    if data_file is None:
        print("Error: raw_data.csv or raw_data.txt not found under data/air-quality/", file=sys.stderr)
        sys.exit(1)

    out_dir = Path("/home/dcc/LEI-Models-Comparision/output/air-quality/air-quality_moonshotai_kimi-k2.7-code_google_gemini-3.1-flash-lite_run1")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "diurnal_pollution_pattern_profiler_result.json"

    sums = {p: [0.0] * 24 for p in POLLUTANTS}
    counts = {p: [0] * 24 for p in POLLUTANTS}
    total_rows = 0
    dropped_rows = 0

    with open(data_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            row = {k.lower().strip(): v for k, v in row.items()}

            hour = parse_hour(row.get("time"))
            if hour is None:
                dropped_rows += 1
                continue

            values = {}
            row_valid = True
            for p in POLLUTANTS:
                v = to_float(row.get(p), p)
                if v is None and args.strict:
                    row_valid = False
                    break
                values[p] = v

            if not row_valid:
                dropped_rows += 1
                continue

            for p, v in values.items():
                if v is not None:
                    sums[p][hour] += v
                    counts[p][hour] += 1

    result_summary = []
    for hour in range(24):
        entry = {"hour": hour}
        has_any = False
        for p in POLLUTANTS:
            c = counts[p][hour]
            if c > 0:
                entry[p] = round(sums[p][hour] / c, 4)
                has_any = True
            else:
                entry[p] = None
        if has_any:
            result_summary.append(entry)

    output = {
        "task_name": "Diurnal Pollution Pattern Profiler",
        "description": "Average hourly ground-truth pollutant concentrations (CO, NMHC, C6H6, NOx, NO2) by hour-of-day.",
        "result_summary": result_summary,
        "result_generated_at": datetime.now().isoformat()
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"Processed {total_rows} rows, dropped {dropped_rows} rows.")
    print(f"Result saved to {out_file}")
    print(f"Hours with data: {len(result_summary)}")


if __name__ == "__main__":
    main()