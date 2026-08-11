"""
Task: NMHC Concentration Estimator
Description: Estimate NMHC(GT) concentration from PT08.S2(NMHC) using a lightweight incremental linear mapping derived from recent valid samples. Output the estimated concentration and the current mapping error for ground-truth validation.
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
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

MISSING_TOKENS = {'', 'na', 'n/a', 'None', 'none'}


def find_data_file():
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / "data").exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent
    for name in ("raw_data.csv", "raw_data.txt"):
        candidate = root_dir / "data" / "air-quality" / name
        if candidate.exists():
            return candidate
    return None


def is_missing(value):
    if value is None:
        return True
    return str(value).strip().lower() in MISSING_TOKENS


def to_float(value, column):
    if is_missing(value):
        return None
    text = str(value).strip()
    try:
        num = float(text)
    except ValueError:
        print(f"WARN: non-numeric value in {column}: {value!r}", file=sys.stderr)
        return None
    # Sensor/device missing-value placeholder used in this dataset
    if num <= -200.0:
        return None
    return num


def fit_linear(pairs):
    n = len(pairs)
    if n < 2:
        return None
    sum_x = sum_y = sum_xy = sum_x2 = 0.0
    for x, y in pairs:
        sum_x += x
        sum_y += y
        sum_xy += x * y
        sum_x2 += x * x
    denom = n * sum_x2 - sum_x * sum_x
    if abs(denom) < 1e-12:
        return None
    slope = (n * sum_xy - sum_x * sum_y) / denom
    intercept = (sum_y - slope * sum_x) / n
    return slope, intercept


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--window", type=int, default=100,
                        help="Number of recent valid samples for the linear mapping")
    parser.add_argument("--strict", action="store_true",
                        help="Skip rows with missing required fields")
    args = parser.parse_args()

    data_file = find_data_file()
    if not data_file:
        print("ERROR: raw_data.csv/txt not found under data/air-quality/", file=sys.stderr)
        sys.exit(1)

    x_col = "pt08.s2(nmhc)"
    y_col = "nmhc(gt)"
    window = deque(maxlen=args.window)
    total = 0
    dropped = 0
    recent = []
    latest_estimate = None
    latest_error = None
    latest_params = None

    with open(data_file, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            total += 1
            row = {k.lower().strip(): v for k, v in row.items()}

            if x_col not in row or y_col not in row:
                dropped += 1
                if args.strict:
                    continue
                continue

            x = to_float(row.get(x_col), x_col)
            y = to_float(row.get(y_col), y_col)

            if x is None:
                dropped += 1
                continue

            if y is not None:
                window.append((x, y))

            params = fit_linear(window)
            if params is None:
                continue

            slope, intercept = params
            estimate = slope * x + intercept
            error = None if y is None else estimate - y

            latest_estimate = estimate
            latest_error = error
            latest_params = {"slope": slope, "intercept": intercept}

            record = {"pt08_s2_nmhc": x, "estimated_nmhc": estimate}
            if y is not None:
                record["actual_nmhc"] = y
                record["error"] = error
            recent.append(record)
            if len(recent) > 10:
                recent.pop(0)

    out_dir = Path("/home/dcc/LEI-Models-Comparision/output/air-quality/air-quality_moonshotai_kimi-k2.7-code_google_gemini-3.1-flash-lite_run1")
    out_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "task_name": "NMHC Concentration Estimator",
        "description": "Estimate NMHC(GT) concentration from PT08.S2(NMHC) using a lightweight incremental linear mapping derived from recent valid samples.",
        "result_summary": [
            {
                "input_file": str(data_file),
                "total_rows_read": total,
                "dropped_rows": dropped,
                "window_size": args.window,
                "valid_training_pairs": len(window),
                "latest_mapping": latest_params,
                "latest_estimate_nmhc": latest_estimate,
                "latest_error_vs_ground_truth": latest_error,
                "recent_estimates": recent
            }
        ],
        "result_generated_at": datetime.now(timezone.utc).isoformat()
    }

    out_file = out_dir / "nmhc_concentration_estimator_result.json"
    with open(out_file, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, allow_nan=False)
    print(f"Saved result to {out_file}")


if __name__ == "__main__":
    main()