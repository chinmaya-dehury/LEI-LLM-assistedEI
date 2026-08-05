"""
Task: Irrigation_Efficiency_Alert
Description: Monitor the Water Usage Efficiency (WAI) and trigger a flag if the current value deviates significantly from the historical mean, indicating potential irrigation system leaks or over-watering.
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
from datetime import datetime

def safe_float(val):
    try:
        return float(val)
    except (ValueError, TypeError):
        return None

def get_root():
    curr = Path(__file__).resolve().parent
    while curr.name and not (curr / "data").exists():
        if curr.parent == curr: break
        curr = curr.parent
    return curr

def run():
    root = get_root()
    data_file = root / "data" / "agri-data" / "raw_data.csv"
    if not data_file.exists():
        data_file = root / "data" / "agri-data" / "raw_data.txt"
    
    if not data_file.exists():
        print("Error: Data file not found.")
        return

    output_dir = Path(OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    wai_values = []
    rows = []
    
    with open(data_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            row = {k.lower(): v for k, v in row.items()}
            wai = safe_float(row.get('wai'))
            if wai is not None:
                wai_values.append(wai)
                rows.append(row)
    
    if not wai_values:
        return

    mean_wai = sum(wai_values) / len(wai_values)
    threshold = mean_wai * 0.2
    alerts = []
    
    for row in rows:
        val = safe_float(row.get('wai'))
        if abs(val - mean_wai) > threshold:
            alerts.append({"wai": val, "deviation": val - mean_wai})

    result = {
        "task_name": "Irrigation_Efficiency_Alert",
        "description": "Detected deviations from mean WAI",
        "result_summary": {
            "mean_wai": mean_wai,
            "alert_count": len(alerts),
            "alerts": alerts[:5]
        },
        "result_generated_at": datetime.now().isoformat()
    }
    
    with open(output_dir / "Irrigation_Efficiency_Alert_result.json", 'w') as f:
        json.dump(result, f, indent=2)

if __name__ == '__main__':
    run()