import re
from datetime import datetime
"""
Task: Epoch Synchronization Gaps Identification
Description: Detect missing epochs in the sequence across different motes to identify synchronization issues or sensor failures.
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

import csv
from pathlib import Path
import os

def resolve_data_path():
    # Resolve project root containing 'data' directory
    script_dir = Path(__file__).resolve().parent
    root_dir = script_dir
    while True:
        if (root_dir / "data").exists():
            break
        parent = root_dir.parent
        if parent == root_dir:
            raise FileNotFoundError("Data directory not found in project structure.")
        root_dir = parent
    # Determine correct file name based on extension
    csv_path = root_dir / "data" / "lab-data" / "raw_data.csv"
    txt_path = root_dir / "data" / "lab-data" / "raw_data.txt"
    if csv_path.exists():
        return csv_path
    elif txt_path.exists():
        return txt_path
    else:
        raise FileNotFoundError("Neither raw_data.csv nor raw_data.txt found under data/lab-data.")

def parse_sensor_data(file_path):
    rows = []
    with open(file_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Normalize column names to lowercase
            normalized_row = {k.lower(): v for k, v in row.items()}
            rows.append(normalized_row)
    return rows

def identify_epoch_gaps(data_rows):
    mote_ids = set()
    epochs_per_mote = {}
    for row in data_rows:
        mote_id = row.get('moteid')
        epoch = row.get('epoch')
        if mote_id is None or epoch is None:
            continue
        mote_ids.add(mote_id)
        if mote_id not in epochs_per_mote:
            epochs_per_mote[mote_id] = []
        try:
            epochs_per_mote[mote_id].append(int(epoch))
        except ValueError:
            # Skip invalid epoch values
            continue
    gaps_report = {}
    for mote_id in sorted(mote_ids):
        epochs_list = sorted(epochs_per_mote[mote_id])
        expected_epochs = list(range(min(epochs_list), max(epochs_list) + 1))
        missing_epochs = set(expected_epochs) - set(epochs_list)
        gaps_report[mote_id] = {
            "total_readings": len(epochs_list),
            "missing_epochs": sorted(missing_epochs),
        }
    return gaps_report

def main():
    try:
        data_file = resolve_data_path()
        print(f"Reading data from {data_file}")
        rows = parse_sensor_data(data_file)
        gaps = identify_epoch_gaps(rows)
        import json
        result = {
            "task_name": "Epoch Synchronization Gaps Identification",
            "description": "Detect missing epochs in the sequence across different motes to identify synchronization issues or sensor failures.",
            "result_summary": gaps,
            "result_generated_at": f"{__import__('datetime').datetime.now():%Y-%m-%d %H:%M:%S}"
        }
        output_dir = Path("output") / "lab-data"
        os.makedirs(output_dir, exist_ok=True)
        output_path = output_dir / f"epoch_gaps_result.json"
        with open(output_path, 'w') as outfile:
            json.dump(result, outfile, indent=2)
        print(f"Result written to {output_path}")
    except Exception as e:
        import sys
        print(f"Error during execution: {e}", file=sys.stderr)
        raise

if __name__ == "__main__":
    main()