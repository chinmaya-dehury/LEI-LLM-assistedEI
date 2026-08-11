"""
Task: Multi-Pollutant Peak Event Detector
Description: Identify peak pollution events by checking whether CO(GT), NOx(GT), and C6H6(GT) simultaneously exceed their respective configurable thresholds within the same hour.
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
import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

TASK_NAME = "Multi-Pollutant Peak Event Detector"
DESCRIPTION = "Identify peak pollution events by checking whether CO(GT), NOx(GT), and C6H6(GT) simultaneously exceed their respective configurable thresholds within the same hour."

MISSING = {"", "NA", "N/A", "None", "NULL", "None", "-200"}
OUTPUT_DIR = Path("/home/dcc/LEI-Models-Comparision/output/air-quality/air-quality_moonshotai_kimi-k2.7-code_nvidia_nemotron-3-ultra-550b-a55b_run2")


def find_data_file():
    curr = Path(__file__).resolve().parent
    root = curr
    while root.name and not (root / "data").exists():
        parent = root.parent
        if parent == root:
            break
        root = parent
    for name in ["raw_data.csv", "raw_data.txt"]:
        f = root / "data" / "air-quality" / name
        if f.exists():
            return f
    return None


def to_float(value, col):
    if value is None:
        return None
    s = str(value).strip()
    if s in MISSING:
        return None
    try:
        v = float(s)
        if v <= -199:
            return None
        return v
    except ValueError:
        print(f"Warning: invalid numeric value '{value}' in column '{col}', skipping value.", file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument("--co-threshold", type=float, default=5.0, help="CO(GT) threshold (mg/m^3)")
    parser.add_argument("--nox-threshold", type=float, default=200.0, help="NOx(GT) threshold (ppb)")
    parser.add_argument("--c6h6-threshold", type=float, default=20.0, help="C6H6(GT) threshold (microg/m^3)")
    parser.add_argument("--max-peaks", type=int, default=100, help="Maximum number of peak events to include in result")
    parser.add_argument("--strict", action="store_true", help="Exit if required columns are missing")
    args = parser.parse_args()

    data_file = find_data_file()
    if data_file is None:
        print("Error: raw_data.csv or raw_data.txt not found under data/air-quality/.", file=sys.stderr)
        sys.exit(1)

    required = ["date", "time", "co(gt)", "nox(gt)", "c6h6(gt)"]
    total_rows = 0
    valid_rows = 0
    dropped = 0
    peaks = []

    try:
        with open(data_file, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                total_rows += 1
                row = {k.lower().strip(): v for k, v in row.items()}
                if not all(col in row for col in required):
                    if args.strict:
                        print(f"Error: missing required columns in row {total_rows}.", file=sys.stderr)
                        sys.exit(1)
                    dropped += 1
                    continue
                co = to_float(row.get("co(gt)"), "CO(GT)")
                nox = to_float(row.get("nox(gt)"), "NOx(GT)")
                c6h6 = to_float(row.get("c6h6(gt)"), "C6H6(GT)")
                if co is None or nox is None or c6h6 is None:
                    dropped += 1
                    continue
                valid_rows += 1
                if co > args.co_threshold and nox > args.nox_threshold and c6h6 > args.c6h6_threshold:
                    peaks.append({
                        "timestamp": f"{row.get('date')} {row.get('time')}",
                        "co_gt_mg_m3": co,
                        "nox_gt_ppb": nox,
                        "c6h6_gt_ug_m3": c6h6
                    })
    except Exception as e:
        print(f"Error reading {data_file}: {e}", file=sys.stderr)
        sys.exit(1)

    peaks.sort(
        key=lambda p: (p["co_gt_mg_m3"] / args.co_threshold +
                       p["nox_gt_ppb"] / args.nox_threshold +
                       p["c6h6_gt_ug_m3"] / args.c6h6_threshold),
        reverse=True
    )
    retained = peaks[:args.max_peaks]

    summary = {
        "thresholds": {
            "co_gt_mg_m3": args.co_threshold,
            "nox_gt_ppb": args.nox_threshold,
            "c6h6_gt_ug_m3": args.c6h6_threshold
        },
        "total_rows": total_rows,
        "valid_rows": valid_rows,
        "dropped_rows": dropped,
        "peak_count": len(peaks),
        "peak_events": retained
    }

    result = {
        "task_name": TASK_NAME,
        "description": DESCRIPTION,
        "result_summary": [summary],
        "result_generated_at": datetime.now(timezone.utc).isoformat()
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{TASK_NAME.replace(' ', '_').lower()}_result.json"
    with open(out_path, "w", encoding="utf-8") as out:
        json.dump(result, out, indent=2)
    print(f"Saved {len(peaks)} peak event(s) to {out_path}")


if __name__ == "__main__":
    main()