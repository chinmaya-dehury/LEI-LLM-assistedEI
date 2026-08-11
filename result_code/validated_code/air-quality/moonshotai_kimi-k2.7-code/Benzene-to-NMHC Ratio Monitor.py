"""
Task: Benzene-to-NMHC Ratio Monitor
Description: Calculate the ratio of C6H6(GT) to NMHC(GT) for valid samples and detect abnormal hydrocarbon composition that may indicate sensor cross-sensitivity or pollution source changes.
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

import csv
import json
import os
import sys
import math
from datetime import datetime, timezone
from pathlib import Path

TASK_NAME = "Benzene-to-NMHC Ratio Monitor"
OUTPUT_DIR = Path("/home/dcc/LEI-Models-Comparision/output/air-quality/air-quality_moonshotai_kimi-k2.7-code_nvidia_nemotron-3-ultra-550b-a55b_run2")

MISSING_VALUES = {'', 'NA', 'N/A', 'None', 'NULL', 'None', 'none', '-200'}


def find_data_file():
    """Locate raw_data.csv or raw_data.txt under the project-root data/air-quality folder."""
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / "data").exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent

    candidates = [
        root_dir / "data" / "air-quality" / "raw_data.csv",
        root_dir / "data" / "air-quality" / "raw_data.txt",
    ]
    for cand in candidates:
        if cand.exists():
            return cand
    return None


def to_float(value, column_name):
    """Safely convert a raw value to float, treating sentinel/empty values as missing."""
    if value is None:
        return None
    s = str(value).strip()
    if s in MISSING_VALUES:
        return None
    try:
        return float(s)
    except ValueError:
        print(f"Warning: cannot parse {column_name} value '{value}'; treating as missing", file=sys.stderr)
        return None


def main():
    data_file = find_data_file()
    if data_file is None:
        print("Error: raw_data.csv or raw_data.txt not found under data/air-quality/", file=sys.stderr)
        sys.exit(1)

    ratios = []
    abnormal_count = 0
    total_rows = 0
    skipped_rows = 0

    benzene_col = "c6h6(gt)"
    nmhc_col = "nmhc(gt)"

    try:
        with data_file.open(newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                total_rows += 1
                row = {k.lower(): v for k, v in row.items()}

                if benzene_col not in row or nmhc_col not in row:
                    skipped_rows += 1
                    continue

                c6h6 = to_float(row.get(benzene_col), benzene_col)
                nmhc = to_float(row.get(nmhc_col), nmhc_col)

                if c6h6 is None or nmhc is None:
                    skipped_rows += 1
                    continue

                if nmhc == 0:
                    print(f"Warning: NMHC zero at row {total_rows}; skipping ratio", file=sys.stderr)
                    skipped_rows += 1
                    continue

                ratio = c6h6 / nmhc
                ratios.append(ratio)

                # Flag abnormal composition: benzene proportion > 30%
                if ratio > 0.30:
                    abnormal_count += 1
    except Exception as e:
        print(f"Error reading {data_file}: {e}", file=sys.stderr)
        sys.exit(1)

    if not ratios:
        print("No valid C6H6/NMHC ratio samples found.", file=sys.stderr)
        sys.exit(1)

    ratios.sort()
    n = len(ratios)
    mean_ratio = sum(ratios) / n
    median_ratio = ratios[n // 2] if n % 2 else (ratios[n // 2 - 1] + ratios[n // 2]) / 2
    min_ratio = ratios[0]
    max_ratio = ratios[-1]
    p95 = ratios[int(math.floor(0.95 * (n - 1)))]

    result = {
        "task_name": TASK_NAME,
        "result_summary": [
            {"key": "total_rows_read", "value": total_rows},
            {"key": "valid_ratio_samples", "value": n},
            {"key": "skipped_rows", "value": skipped_rows},
            {"key": "abnormal_high_benzene_count", "value": abnormal_count},
            {"key": "mean_c6h6_nmhc_ratio", "value": round(mean_ratio, 6)},
            {"key": "median_c6h6_nmhc_ratio", "value": round(median_ratio, 6)},
            {"key": "min_c6h6_nmhc_ratio", "value": round(min_ratio, 6)},
            {"key": "max_c6h6_nmhc_ratio", "value": round(max_ratio, 6)},
            {"key": "p95_c6h6_nmhc_ratio", "value": round(p95, 6)},
        ]
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{TASK_NAME.replace(' ', '_').replace('-', '_').lower()}_result.json"
    with out_path.open('w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)

    print(json.dumps(result, indent=2))
    print(f"Result saved to {out_path}")


if __name__ == "__main__":
    main()