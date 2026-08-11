"""
Task: Roadside Air Quality Classifier
Description: Classify current hourly readings of CO, NO2, and Benzene into low, moderate, or high bands using simple threshold comparisons for immediate on-field status reporting.
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
from pathlib import Path
from datetime import datetime
from collections import Counter

def find_data_file():
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

def to_float(value, col):
    if value is None:
        return None
    v = value.strip()
    if v == "" or v.upper() in ("NA", "N/A", "NULL", "NONE", "-"):
        return None
    try:
        return float(v)
    except ValueError:
        print(f"Warning: invalid numeric value in {col}: '{value}'", file=sys.stderr)
        return None

def classify(value, low, high):
    if value is None:
        return "missing"
    if value < low:
        return "low"
    if value <= high:
        return "moderate"
    return "high"

def main():
    data_file = find_data_file()
    if not data_file:
        print("Error: raw_data.csv or raw_data.txt not found under data/air-quality/", file=sys.stderr)
        sys.exit(1)

    co_counts = Counter()
    no2_counts = Counter()
    benz_counts = Counter()
    total = 0
    missing = 0

    with open(data_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            row = {k.lower().strip(): v for k, v in row.items()}
            co = to_float(row.get("co(gt)"), "CO(GT)")
            no2 = to_float(row.get("no2(gt)"), "NO2(GT)")
            benz = to_float(row.get("c6h6(gt)"), "C6H6(GT)")
            if co is None or no2 is None or benz is None:
                missing += 1
                continue
            co_counts[classify(co, 2.0, 5.0)] += 1
            no2_counts[classify(no2, 40.0, 100.0)] += 1
            benz_counts[classify(benz, 5.0, 10.0)] += 1

    classified = sum(co_counts.values())
    result = {
        "task_name": "Roadside Air Quality Classifier",
        "description": "Classify current hourly readings of CO, NO2, and Benzene into low, moderate, or high bands using simple threshold comparisons for immediate on-field status reporting.",
        "result_summary": [
            {"metric": "total_rows_read", "value": total},
            {"metric": "rows_with_any_missing_pollutant", "value": missing},
            {"metric": "rows_classified", "value": classified},
            {"metric": "co_band_counts_mg_m3", "value": dict(co_counts)},
            {"metric": "no2_band_counts_ug_m3", "value": dict(no2_counts)},
            {"metric": "benzene_band_counts_ug_m3", "value": dict(benz_counts)}
        ],
        "result_generated_at": datetime.utcnow().isoformat() + "Z"
    }

    out_dir = Path("/home/dcc/LEI-Models-Comparision/output/air-quality/air-quality_moonshotai_kimi-k2.7-code_google_gemini-3.1-flash-lite_run2")
    os.makedirs(out_dir, exist_ok=True)
    out_file = out_dir / "Roadside_Air_Quality_Classifier_result.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"Result saved to {out_file}")

if __name__ == "__main__":
    main()