"""
Task: NOx Concentration Estimator
Description: Estimate NOx(GT) concentration from PT08.S3(NOx) using a lightweight incremental linear mapping derived from recent valid samples. Report the estimate and a running mean absolute error against the reference analyzer.
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

import os
import sys
import csv
import json
import math
from pathlib import Path
from datetime import datetime

WINDOW_SIZE = 168  # recent ~1 week of hourly samples

def find_project_root():
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / "data").exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent
    return root_dir

def is_missing(value):
    if value is None:
        return True
    s = str(value).strip()
    return s == "" or s.upper() in ("NA", "N/A", "NULL") or s == "-200"

def safe_float(value, col_name=None):
    if is_missing(value):
        return None
    try:
        v = float(value)
        if v == -200.0:
            return None
        return v
    except (ValueError, TypeError):
        label = f"column '{col_name}'" if col_name else "value"
        print(f"Warning: Could not convert {label}: '{value}'", file=sys.stderr)
        return None

def main():
    root_dir = find_project_root()
    data_dir = root_dir / "data" / "air-quality"
    data_file = data_dir / "raw_data.csv"
    if not data_file.exists():
        data_file = data_dir / "raw_data.txt"
    if not data_file.exists():
        print(f"Error: No raw_data.csv or raw_data.txt found in {data_dir}", file=sys.stderr)
        sys.exit(1)

    nox_col = "nox(gt)"
    sensor_col = "pt08.s3(nox)"

    window = []
    results = []
    dropped = 0
    total = 0
    mae_accum = 0.0
    mae_n = 0

    with open(data_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            row = {k.lower(): v for k, v in row.items()}
            x = safe_float(row.get(sensor_col), sensor_col)
            y = safe_float(row.get(nox_col), nox_col)
            if x is None or y is None:
                dropped += 1
                continue

            pred = None
            wlen = len(window)
            if wlen >= 2:
                n_w = float(wlen)
                sum_x = sum(p[0] for p in window)
                sum_y = sum(p[1] for p in window)
                sum_xx = sum(p[0] * p[0] for p in window)
                sum_xy = sum(p[0] * p[1] for p in window)
                denom = sum_xx - (sum_x * sum_x / n_w)
                if abs(denom) > 1e-12:
                    a = (sum_xy - (sum_x * sum_y / n_w)) / denom
                    b = (sum_y - a * sum_x) / n_w
                    pred = a * x + b
            elif wlen == 1:
                pred = window[0][1]

            if pred is not None:
                err = abs(pred - y)
                mae_accum += err
                mae_n += 1
                results.append({
                    "estimated_nox_gt": round(pred, 4),
                    "reference_nox_gt": y,
                    "absolute_error": round(err, 4),
                    "running_mae": round(mae_accum / mae_n, 4)
                })

            window.append((x, y))
            if len(window) > WINDOW_SIZE:
                window.pop(0)

    final_mae = round(mae_accum / mae_n, 4) if mae_n > 0 else None

    output_dir = Path("/home/dcc/LEI-Models-Comparision/output/air-quality/air-quality_moonshotai_kimi-k2.7-code_google_gemini-3.1-flash-lite_run1")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "NOx_Concentration_Estimator_result.json"

    result = {
        "task_name": "NOx Concentration Estimator",
        "description": "Estimate NOx(GT) concentration from PT08.S3(NOx) using a lightweight incremental linear mapping derived from recent valid samples. Report the estimate and a running mean absolute error against the reference analyzer.",
        "result_summary": [
            f"Total rows read: {total}",
            f"Rows dropped due to missing/invalid values (including -200 sentinel): {dropped}",
            f"Valid samples used for estimation: {total - dropped}",
            f"Predictions made: {mae_n}",
            f"Window size: {WINDOW_SIZE}",
            f"Final running mean absolute error (MAE): {final_mae if final_mae is not None else 'N/A'}"
        ],
        "sample_results": results[:10],
        "result_generated_at": datetime.utcnow().isoformat() + "Z"
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"Results saved to {output_file}")
    print(f"Final running MAE: {final_mae if final_mae is not None else 'N/A'}")

if __name__ == "__main__":
    main()