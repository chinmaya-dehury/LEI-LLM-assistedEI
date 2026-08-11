"""
Task: NO2-to-NOx Ratio Tracker
Description: Compute the ratio of NO2(GT) to NOx(GT) whenever both reference values are valid, and flag readings where the ratio falls outside an expected range to highlight chemical or measurement anomalies.
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
from datetime import datetime, timezone
from pathlib import Path


def find_project_root():
    curr = Path(__file__).resolve().parent
    root = curr
    while root.name and not (root / "data").exists():
        parent = root.parent
        if parent == root:
            break
        root = parent
    return root


def parse_float(value, col):
    if value is None:
        return None
    v = value.strip()
    if v == "" or v.upper() in {"NA", "N/A", "NULL", "NONE"}:
        return None
    try:
        f = float(v)
        # Common sentinel for missing/invalid sensor readings in this dataset
        if f == -200.0:
            return None
        return f
    except ValueError:
        print(f"Warning: invalid numeric value '{value}' in column {col}; skipping.", file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser(description="NO2-to-NOx Ratio Tracker")
    parser.add_argument("--strict", action="store_true", help="Require complete rows")
    args = parser.parse_args()

    root = find_project_root()
    data_file = root / "data" / "air-quality" / "raw_data.csv"
    if not data_file.exists():
        data_file = root / "data" / "air-quality" / "raw_data.txt"
    if not data_file.exists():
        print(f"Error: input file not found at {data_file}", file=sys.stderr)
        sys.exit(1)

    no2_col = "no2(gt)"
    nox_col = "nox(gt)"
    date_col = "date"
    time_col = "time"

    ratios = []
    flagged = []
    total_rows = 0
    missing_cols = 0
    invalid_numeric = 0

    lower_bound = 0.0
    upper_bound = 1.2

    with open(data_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            row = {k.lower(): v for k, v in row.items()}

            if no2_col not in row or nox_col not in row:
                missing_cols += 1
                continue

            no2 = parse_float(row.get(no2_col), no2_col)
            nox = parse_float(row.get(nox_col), nox_col)

            if no2 is None or nox is None:
                invalid_numeric += 1
                continue
            if nox == 0:
                invalid_numeric += 1
                continue

            ratio = no2 / nox
            ratios.append(ratio)

            if ratio < lower_bound or ratio > upper_bound:
                flagged.append({
                    "date": row.get(date_col, ""),
                    "time": row.get(time_col, ""),
                    "no2_gt": no2,
                    "nox_gt": nox,
                    "ratio": round(ratio, 4)
                })

    valid_count = len(ratios)
    mean_ratio = sum(ratios) / valid_count if valid_count else math.nan

    summary = {
        "input_file": str(data_file),
        "total_rows": total_rows,
        "valid_pairs": valid_count,
        "missing_or_invalid_pairs": invalid_numeric,
        "missing_columns_count": missing_cols,
        "mean_no2_nox_ratio": round(mean_ratio, 4) if not math.isnan(mean_ratio) else None,
        "expected_ratio_range": [lower_bound, upper_bound],
        "flagged_count": len(flagged),
        "flagged_sample": flagged[:50]
    }

    out_dir = Path("/home/dcc/LEI-Models-Comparision/output/air-quality/air-quality_moonshotai_kimi-k2.7-code_nvidia_nemotron-3-ultra-550b-a55b_run2")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "no2_to_nox_ratio_tracker_result.json"

    result = {
        "task_name": "NO2-to-NOx Ratio Tracker",
        "description": "Compute the ratio of NO2(GT) to NOx(GT) whenever both reference values are valid, and flag readings where the ratio falls outside an expected range to highlight chemical or measurement anomalies.",
        "result_summary": [summary],
        "result_generated_at": datetime.now(timezone.utc).isoformat()
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"Result saved to {out_file}")


if __name__ == "__main__":
    main()