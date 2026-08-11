"""
Task: Inter-Mote Temperature Consistency Check
Description: Compare temperature readings across motes sharing the same epoch using a simple median-deviation rule to flag motes that report values inconsistent with their neighbors.
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

#!/usr/bin/env python3
import os
import sys
import csv
import json
from pathlib import Path
from datetime import datetime

TASK_NAME = "inter_mote_temperature_consistency_check"


def find_project_root():
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / "data").exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent
    return root_dir


def resolve_data_file(root_dir):
    data_file = root_dir / "data" / "lab-data" / "raw_data.csv"
    if not data_file.exists():
        data_file = root_dir / "data" / "lab-data" / "raw_data.txt"
    return data_file


def to_float(value, col_name):
    if value is None:
        return None
    v = str(value).strip()
    if v == "" or v.upper() in {"NA", "N/A", "NULL"}:
        return None
    try:
        return float(v)
    except ValueError:
        print(f"Warning: invalid numeric value in column '{col_name}': '{value}'", file=sys.stderr)
        return None


def median(values):
    n = len(values)
    if n == 0:
        return None
    s = sorted(values)
    mid = n // 2
    if n % 2 == 1:
        return s[mid]
    return (s[mid - 1] + s[mid]) / 2.0


def main():
    root_dir = find_project_root()
    data_file = resolve_data_file(root_dir)

    if not data_file.exists():
        print(f"Error: data file not found at {data_file}", file=sys.stderr)
        sys.exit(1)

    output_dir = Path("/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_moonshotai_kimi-k2.7-code_anthropic_claude-3-haiku_run2")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{TASK_NAME}_result.json"

    required_cols = {"epoch", "moteid", "temperature"}
    epochs = {}
    total_rows = 0
    dropped_rows = 0

    with open(data_file, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            print("Error: empty data file", file=sys.stderr)
            sys.exit(1)
        fieldnames = {fn.lower() for fn in reader.fieldnames}
        missing = required_cols - fieldnames
        if missing:
            print(f"Error: missing required columns: {missing}", file=sys.stderr)
            sys.exit(1)

        for row in reader:
            total_rows += 1
            row = {k.lower(): v for k, v in row.items()}
            epoch = to_float(row.get("epoch"), "epoch")
            moteid = to_float(row.get("moteid"), "moteid")
            temp = to_float(row.get("temperature"), "temperature")
            if epoch is None or moteid is None or temp is None:
                dropped_rows += 1
                continue
            epoch_int = int(epoch)
            epochs.setdefault(epoch_int, []).append({"moteid": int(moteid), "temperature": temp})

    threshold_c = 3.0
    inconsistent_count = 0
    epoch_summaries = []

    for epoch_int, readings in epochs.items():
        if len(readings) < 2:
            continue
        temps = [r["temperature"] for r in readings]
        med = median(temps)
        if med is None:
            continue
        flagged = []
        for r in readings:
            dev = abs(r["temperature"] - med)
            if dev > threshold_c:
                flagged.append({
                    "moteid": r["moteid"],
                    "temperature": round(r["temperature"], 4),
                    "deviation_from_median_c": round(dev, 4)
                })
        if flagged:
            inconsistent_count += len(flagged)
            epoch_summaries.append({
                "epoch": epoch_int,
                "median_temperature_c": round(med, 4),
                "mote_count": len(readings),
                "flagged_motes": flagged
            })

    epoch_summaries.sort(key=lambda x: x["epoch"])

    result = {
        "task_name": TASK_NAME,
        "description": "Compare temperature readings across motes sharing the same epoch using a simple median-deviation rule to flag motes that report values inconsistent with their neighbors.",
        "result_summary": [
            f"Total rows read: {total_rows}",
            f"Dropped/invalid rows: {dropped_rows}",
            f"Epochs with multiple mote readings: {sum(1 for r in epochs.values() if len(r) >= 2)}",
            f"Epochs with flagged motes: {len(epoch_summaries)}",
            f"Total flagged mote readings: {inconsistent_count}",
            f"Temperature deviation threshold: {threshold_c} C",
            f"Flagged epochs (first 20 shown): {epoch_summaries[:20]}"
        ],
        "result_generated_at": datetime.utcnow().isoformat() + "Z"
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"Result saved to {output_file}")


if __name__ == "__main__":
    main()