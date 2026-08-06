"""
Task: Epoch Synchronization Check
Description: Check for missing or delayed readings by analyzing the epoch sequences from different motes to ensure data integrity.
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
from pathlib import Path
import csv
import json

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
    print("Data file not found.")
    exit(1)

missing_epochs = []

try:
    with open(data_file, 'r') as file:
        reader = csv.DictReader(file)
        epochs = {}
        for row in reader:
            row = {k.lower(): v for k, v in row.items()}
            moteid = row.get('moteid')
            epoch = row.get('epoch')
            if moteid and epoch:
                try:
                    moteid = int(moteid)
                    epoch = int(epoch)
                    if moteid not in epochs:
                        epochs[moteid] = set()
                    epochs[moteid].add(epoch)
                except ValueError:
                    print(f"Invalid moteid or epoch: {moteid}, {epoch}")
            else:
                print("Missing moteid or epoch in row.")

    for moteid, epoch_set in epochs.items():
        expected_epochs = set(range(1, max(epoch_set) + 1))
        missing = expected_epochs - epoch_set
        if missing:
            missing_epochs.append({"moteid": moteid, "missing_epochs": list(missing)})

except Exception as e:
    print(f"Error processing file: {e}")

output_path = Path(OUTPUT_DIR)
output_path.mkdir(parents=True, exist_ok=True)
result = {
    "task_name": "Epoch Synchronization Check",
    "description": "Check for missing or delayed readings by analyzing the epoch sequences from different motes to ensure data integrity.",
    "result_summary": missing_epochs,
    "result_generated_at": "2023-10-01T00:00:00Z"
}

with open(output_path / "epoch_synchronization_check_result.json", 'w') as outfile:
    json.dump(result, outfile, indent=4)