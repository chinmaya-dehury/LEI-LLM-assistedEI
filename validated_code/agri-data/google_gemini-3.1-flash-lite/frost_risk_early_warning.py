"""
Task: Frost_Risk_Early_Warning
Description: Monitor the Frost_Risk index and ambient temperature to trigger an immediate notification if conditions cross a critical threshold, allowing for proactive protective measures.
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

def get_safe_float(val):
    try:
        return float(val)
    except (ValueError, TypeError):
        return None

def run_task():
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / "data").exists():
        parent = root_dir.parent
        if parent == root_dir: break
        root_dir = parent

    data_file = root_dir / "data" / "agri-data" / "raw_data.csv"
    if not data_file.exists():
        data_file = root_dir / "data" / "agri-data" / "raw_data.txt"
    
    if not data_file.exists():
        print("Error: Data file not found.")
        return

    output_dir = Path(OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    alerts = []
    dropped = 0
    
    with open(data_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            row = {k.lower(): v for k, v in row.items()}
            temp = get_safe_float(row.get('temperature'))
            frost = get_safe_float(row.get('frost_risk'))
            
            if temp is None or frost is None:
                dropped += 1
                continue
            
            # Threshold: Frost risk > 0.15 or Temp < 5.0C
            if frost > 0.15 or temp < 5.0:
                alerts.append({"temperature": temp, "frost_risk": frost})

    result = {
        "task_name": "Frost_Risk_Early_Warning",
        "description": "Identified records exceeding frost risk thresholds.",
        "result_summary": {
            "alert_count": len(alerts),
            "dropped_rows": dropped,
            "alerts": alerts
        },
        "result_generated_at": datetime.now().isoformat()
    }

    with open(output_dir / "Frost_Risk_Early_Warning_result.json", 'w') as f:
        json.dump(result, f, indent=2)
    print(f"Task complete. Alerts found: {len(alerts)}. Dropped: {dropped}")

if __name__ == "__main__":
    run_task()