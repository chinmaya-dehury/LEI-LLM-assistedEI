"""
Task: Low Battery Voltage Warning
Description: For each mote, flag voltage readings below a configurable threshold (e.g., 2.2 V) to support battery health monitoring and proactive maintenance.
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

import os
import sys
import csv
import json
import argparse
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
        candidate = root_dir / "data" / "lab-data" / name
        if candidate.exists():
            return candidate
    return None


def is_missing(value):
    if value is None:
        return True
    s = str(value).strip()
    return s == "" or s.upper() in ("NA", "N/A", "NULL", "NONE")


def to_float(value, column):
    if is_missing(value):
        return None
    try:
        return float(value)
    except Exception:
        print(f"Warning: invalid numeric value in column {column}: {value!r}", file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser(description="Flag low battery voltage readings per mote.")
    parser.add_argument("--threshold", type=float, default=2.2, help="Voltage threshold in volts.")
    parser.add_argument("--max-samples", type=int, default=5, help="Max sample readings to keep per mote.")
    args = parser.parse_args()

    data_file = find_data_file()
    if not data_file:
        print("Error: raw_data.csv or raw_data.txt not found under data/lab-data/", file=sys.stderr)
        sys.exit(1)

    threshold = args.threshold
    mote_counts = {}
    mote_samples = {}
    total_rows = 0
    dropped = 0
    flagged_total = 0

    with open(data_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            row = {k.lower(): v for k, v in row.items()}
            moteid = row.get("moteid")
            voltage = to_float(row.get("voltage"), "voltage")

            if is_missing(moteid) or voltage is None:
                dropped += 1
                continue

            try:
                moteid = int(float(moteid))
            except Exception:
                dropped += 1
                continue

            if voltage < threshold:
                flagged_total += 1
                mote_counts.setdefault(moteid, 0)
                mote_samples.setdefault(moteid, [])
                mote_counts[moteid] += 1
                if len(mote_samples[moteid]) < args.max_samples:
                    mote_samples[moteid].append({
                        "voltage": voltage,
                        "epoch": row.get("epoch"),
                        "date": row.get("date"),
                        "time": row.get("time")
                    })

    summary = {
        "threshold_volts": threshold,
        "total_rows_processed": total_rows,
        "rows_dropped_missing": dropped,
        "total_flagged_readings": flagged_total,
        "motes_with_low_voltage": len(mote_counts)
    }

    mote_details = []
    for mote in sorted(mote_counts.keys()):
        mote_details.append({
            "moteid": mote,
            "low_voltage_count": mote_counts[mote],
            "sample_readings": mote_samples[mote]
        })
    summary["mote_details"] = mote_details

    result = {
        "task_name": "Low Battery Voltage Warning",
        "description": "Flag voltage readings below configurable threshold per mote for battery health monitoring.",
        "result_summary": [summary],
        "result_generated_at": datetime.now(timezone.utc).isoformat()
    }

    out_dir = Path("/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_moonshotai_kimi-k2.7-code_nvidia_nemotron-3-ultra-550b-a55b_run1")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "low_battery_voltage_warning_result.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"Saved results to {out_file}")
    print(f"Flagged {flagged_total} readings below {threshold} V across {len(mote_counts)} motes.")


if __name__ == "__main__":
    main()