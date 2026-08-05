"""
Task: Soil_Nutrient_Drift_Detection
Description: Calculate the moving average of the Nutrient Balance Ratio (NBR) over a 7-day window to detect significant shifts in soil nutrient composition that may require fertilizer adjustment.
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

import csv
import os
import json
from pathlib import Path
from collections import deque

def get_data_file():
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / "data").exists():
        parent = root_dir.parent
        if parent == root_dir: break
        root_dir = parent
    
    for ext in ['.csv', '.txt']:
        f = root_dir / "data" / "agri-data" / f"raw_data{ext}"
        if f.exists(): return f
    return None

def safe_float(val):
    try:
        return float(val)
    except (ValueError, TypeError):
        return None

def run_task():
    data_file = get_data_file()
    if not data_file:
        print("Error: Data file not found.")
        return

    output_dir = Path(OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    nbr_values = []
    with open(data_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            row = {k.lower(): v for k, v in row.items()}
            nbr = safe_float(row.get('nbr'))
            if nbr is not None:
                nbr_values.append(nbr)

    window_size = 7
    moving_averages = []
    for i in range(len(nbr_values) - window_size + 1):
        window = nbr_values[i:i + window_size]
        moving_averages.append(sum(window) / window_size)

    result = {
        "task_name": "Soil_Nutrient_Drift_Detection",
        "description": "7-day moving average of NBR",
        "result_summary": moving_averages,
        "result_generated_at": "2023-10-27T10:00:00Z"
    }

    with open(output_dir / "Soil_Nutrient_Drift_Detection_result.json", 'w') as f:
        json.dump(result, f)

if __name__ == "__main__":
    run_task()