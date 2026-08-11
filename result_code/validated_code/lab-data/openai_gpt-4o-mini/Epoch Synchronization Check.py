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
import csv
import json
from pathlib import Path

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

with open(data_file, 'r') as file:
    reader = csv.DictReader(file)
    epoch_set = set()
    for row in reader:
        row = {k.lower(): v for k, v in row.items()}
        if 'epoch' in row and row['epoch']:
            try:
                epoch = int(row['epoch'])
                epoch_set.add(epoch)
            except ValueError:
                print(f"Invalid epoch value: {row['epoch']}")
                continue
        else:
            print("Missing epoch in row.")
            continue

max_epoch = max(epoch_set) if epoch_set else 0
expected_epochs = set(range(1, max_epoch + 1))
missing_epochs = sorted(expected_epochs - epoch_set)

output_path = Path("/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_openai_gpt-4o-mini_nvidia_nemotron-3-ultra-550b-a55b_run1") / "epoch_synchronization_check_result.json"
result = {
    "task_name": "Epoch Synchronization Check",
    "description": "Check for missing or delayed readings by analyzing the epoch sequences from different motes to ensure data integrity.",
    "result_summary": missing_epochs,
    "result_generated_at": "2023-10-01T00:00:00Z"
}

with open(output_path, 'w') as outfile:
    json.dump(result, outfile)
    print(f"Results saved to {output_path}")