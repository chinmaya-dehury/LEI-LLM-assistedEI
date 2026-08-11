"""
Task: Temperature Out-of-Range Alert
Description: For each mote, flag temperature readings that fall outside a configurable indoor laboratory range (e.g., 15–30 °C) to identify environmental anomalies or potential sensor faults.
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

import argparse
import csv
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

MISSING = {'', 'na', 'n/a', 'None', 'none'}


def is_missing(val):
    if val is None:
        return True
    return str(val).strip().lower() in MISSING


def safe_float(val, col):
    if is_missing(val):
        return None
    try:
        return float(val)
    except ValueError:
        print(f"Warning: invalid numeric value in column '{col}': {val!r}; skipping", file=sys.stderr)
        return None


def safe_int(val, col):
    if is_missing(val):
        return None
    try:
        return int(float(val))
    except ValueError:
        print(f"Warning: invalid integer value in column '{col}': {val!r}; skipping", file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser(description="Flag per-mote temperature readings outside a configurable range.")
    parser.add_argument("--low", type=float, default=15.0, help="Lower temperature threshold (Celsius)")
    parser.add_argument("--high", type=float, default=30.0, help="Upper temperature threshold (Celsius)")
    parser.add_argument("--strict", action="store_true", help="Exit if required fields are missing")
    parser.add_argument("--max-examples", type=int, default=5, help="Max flagged examples per mote in summary")
    args = parser.parse_args()

    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / "data").exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent

    data_file = root_dir / "data" / "lab-data" / "raw_data.csv"
    if not data_file.exists():
        data_file = root_dir / "data" / "lab-data" / "raw_data.txt"

    if not data_file.exists():
        print(f"Error: input file not found at {data_file}", file=sys.stderr)
        sys.exit(1)

    required = {"moteid", "temperature"}
    stats = defaultdict(lambda: {
        "readings": 0,
        "out_of_range": 0,
        "min_temp": float("inf"),
        "max_temp": float("-inf"),
        "examples": []
    })
    total_rows = 0
    dropped_rows = 0

    with open(data_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            print("Error: empty input file", file=sys.stderr)
            sys.exit(1)
        fieldnames = [c.lower() for c in reader.fieldnames]
        missing_cols = required - set(fieldnames)
        if missing_cols:
            print(f"Error: missing required columns: {sorted(missing_cols)}", file=sys.stderr)
            sys.exit(1)

        for raw_row in reader:
            total_rows += 1
            row = {k.lower(): v for k, v in raw_row.items()}
            mote = safe_int(row.get("moteid"), "moteid")
            temp = safe_float(row.get("temperature"), "temperature")
            if mote is None or temp is None:
                dropped_rows += 1
                if args.strict:
                    print("Error: strict mode requires complete moteid/temperature rows", file=sys.stderr)
                    sys.exit(1)
                continue

            s = stats[mote]
            s["readings"] += 1
            if temp < s["min_temp"]:
                s["min_temp"] = temp
            if temp > s["max_temp"]:
                s["max_temp"] = temp
            if temp < args.low or temp > args.high:
                s["out_of_range"] += 1
                if len(s["examples"]) < args.max_examples:
                    epoch = safe_int(row.get("epoch"), "epoch")
                    s["examples"].append({"epoch": epoch, "temperature": temp})

    summary = []
    for mote in sorted(stats.keys()):
        s = stats[mote]
        readings = s["readings"]
        oor = s["out_of_range"]
        pct = round((oor / readings) * 100, 4) if readings else 0.0
        summary.append({
            "moteid": mote,
            "readings_count": readings,
            "out_of_range_count": oor,
            "out_of_range_percent": pct,
            "min_temperature": round(s["min_temp"], 4) if s["min_temp"] != float("inf") else None,
            "max_temperature": round(s["max_temp"], 4) if s["max_temp"] != float("-inf") else None,
            "threshold_low": args.low,
            "threshold_high": args.high,
            "flagged_examples": s["examples"]
        })

    result = {
        "task_name": "Temperature Out-of-Range Alert",
        "description": "Per-mote temperature readings flagged outside the configured 15-30 °C range.",
        "result_summary": summary,
        "result_generated_at": datetime.now(timezone.utc).isoformat()
    }

    out_dir = Path("/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_moonshotai_kimi-k2.7-code_nvidia_nemotron-3-ultra-550b-a55b_run1")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "temperature_out_of_range_alert_result.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"Processed {total_rows} rows (dropped {dropped_rows}). Results saved to {out_file}")


if __name__ == "__main__":
    main()