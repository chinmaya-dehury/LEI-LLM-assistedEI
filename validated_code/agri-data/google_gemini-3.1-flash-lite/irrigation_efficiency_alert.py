"""
Task: Irrigation_Efficiency_Alert
Description: Monitor Water_Usage_Efficiency against a threshold to trigger an alert if water consumption per kg of crop yield exceeds optimal levels, indicating potential irrigation system leaks or inefficiencies.
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
import json
import os
from pathlib import Path
from datetime import datetime

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
    
    threshold = 0.75
    alerts = []
    dropped = 0

    with open(data_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            row = {k.lower(): v for k, v in row.items()}
            wue = safe_float(row.get('water_usage_efficiency'))
            if wue is None:
                dropped += 1
                continue
            
            if wue > threshold:
                alerts.append({"efficiency": wue, "status": "Inefficient"})

    result = {
        "task_name": "Irrigation_Efficiency_Alert",
        "description": "Identifies records where water usage efficiency exceeds the threshold of 0.75.",
        "result_summary": {
            "alerts_count": len(alerts),
            "dropped_rows": dropped,
            "threshold": threshold
        },
        "result_generated_at": datetime.now().isoformat()
    }

    with open(output_dir / "Irrigation_Efficiency_Alert_result.json", 'w') as f:
        json.dump(result, f, indent=2)

if __name__ == "__main__":
    run_task()