import json
import sys
import math
import csv
"""
Task: Water Usage Efficiency Trend Alert
Description: Flag records where Water_Usage_Efficiency exceeds a target threshold, signaling inefficient water consumption per unit of crop output.
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

import os, sys, csv, json, math, argparse
from pathlib import Path
from datetime import datetime, timezone

def find_data_file():
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / "data").exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent
    for name in ("raw_data.csv", "raw_data.txt"):
        p = root_dir / "data" / "agri-data" / name
        if p.exists():
            return p
    return None

def to_float(v, col):
    if v is None:
        return None
    s = str(v).strip()
    if s == "" or s.upper() in ("NA", "N/A", "NULL"):
        return None
    try:
        return float(s)
    except ValueError:
        print(f"Warning: invalid numeric value in {col}: {v!r}", file=sys.stderr)
        return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", type=float, default=15.0, help="Water usage efficiency threshold (L/kg)")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    data_file = find_data_file()
    if data_file is None:
        print("Error: raw_data.csv/txt not found under data/agri-data", file=sys.stderr)
        sys.exit(1)

    out_dir = Path("/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_moonshotai_kimi-k2.7-code_nvidia_nemotron-3-ultra-550b-a55b_run1")
    out_dir.mkdir(parents=True, exist_ok=True)

    flagged = []
    total = 0
    missing = 0
    invalid = 0
    with open(data_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=1):
            total += 1
            row = {k.lower(): v for k, v in row.items()}
            if "water_usage_efficiency" not in row:
                if i == 1:
                    print("Error: required column Water_Usage_Efficiency missing", file=sys.stderr)
                    if args.strict:
                        sys.exit(1)
                missing += 1
                continue
            wue = to_float(row["water_usage_efficiency"], "Water_Usage_Efficiency")
            if wue is None:
                missing += 1
                continue
            if math.isnan(wue):
                invalid += 1
                continue
            if wue > args.threshold:
                flagged.append({"row_index": i, "water_usage_efficiency": round(wue, 3)})

    summary = {
        "task_name": "water_usage_efficiency_trend_alert",
        "description": f"Flag records where Water_Usage_Efficiency exceeds threshold {args.threshold} L/kg.",
        "result_summary": [
            {"total_rows": total, "flagged_rows": len(flagged), "missing_or_invalid": missing + invalid, "threshold": args.threshold},
            {"flagged_records": flagged}
        ],
        "result_generated_at": datetime.now(timezone.utc).isoformat()
    }

    out_path = out_dir / "water_usage_efficiency_trend_alert_result.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"Saved {out_path}; flagged {len(flagged)} of {total} rows.")

if __name__ == "__main__":
    main()