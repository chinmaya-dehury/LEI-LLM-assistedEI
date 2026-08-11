"""
Task: Frost Risk Monitor
Description: Monitor the Frost_Risk index and trigger a protective alert when the value exceeds 0.5, enabling preemptive measures like covering crops or activating heaters.
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
import sys
from pathlib import Path
from datetime import datetime

# Resolve input file path dynamically
curr_dir = Path(__file__).resolve().parent
root_dir = curr_dir
while root_dir.name and not (root_dir / "data").exists():
    parent = root_dir.parent
    if parent == root_dir:
        break
    root_dir = parent

data_file = root_dir / "data" / "agri-data" / "raw_data.csv"
if not data_file.exists():
    data_file = root_dir / "data" / "agri-data" / "raw_data.txt"

if not data_file.exists():
    print("ERROR: Input data file not found.")
    sys.exit(1)

# Output path
output_dir = Path("/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_qwen_qwen3.7-flash_google_gemini-3.1-flash-lite_run2")
output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / "Frost Risk Monitor_result.json"

# Helper function for safe float conversion
def safe_float(value):
    if value is None:
        return None
    value = str(value).strip()
    if value in ('', 'NA', 'N/A', 'None', 'None'):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

# Read and process data
frost_alerts = []
total_rows = 0
valid_rows = 0
dropped_rows = 0

try:
    with open(data_file, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            # Normalize keys to lowercase
            row = {k.lower(): v for k, v in row.items()}
            
            # Check if frost_risk column exists
            if 'frost_risk' not in row:
                dropped_rows += 1
                continue
            
            frost_risk = safe_float(row.get('frost_risk'))
            
            if frost_risk is None:
                dropped_rows += 1
                continue
            
            valid_rows += 1
            
            # Check if frost risk exceeds threshold
            if frost_risk > 0.5:
                frost_alerts.append({
                    "frost_risk": frost_risk,
                    "alert": True
                })
except Exception as e:
    print(f"ERROR: Failed to read data file: {e}")
    sys.exit(1)

# Generate result
result = {
    "task_name": "Frost Risk Monitor",
    "description": "Monitor the Frost_Risk index and trigger a protective alert when the value exceeds 0.5, enabling preemptive measures like covering crops or activating heaters.",
    "result_summary": {
        "total_rows_processed": total_rows,
        "valid_rows": valid_rows,
        "dropped_rows": dropped_rows,
        "alerts_triggered": len(frost_alerts),
        "alerts": frost_alerts
    },
    "result_generated_at": datetime.now().isoformat()
}

# Save result
with open(output_file, 'w') as f:
    json.dump(result, f, indent=2)

print(f"Frost Risk Monitor complete. {len(frost_alerts)} alerts triggered out of {valid_rows} valid readings.")