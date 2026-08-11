import re
"""
Task: Soil Fertility Index Threshold Alert
Description: Monitor the Soil Fertility Index (SFI) and trigger a low-fertility alert when the value drops below 0.70, indicating insufficient organic matter or NPK levels for optimal crop growth.
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
    print("ERROR: Input data file not found under data/agri-data/")
    sys.exit(1)

# Output path
output_dir = Path("/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_qwen_qwen3.7-flash_google_gemini-3.1-flash-lite_run1")
output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / "Soil_Fertility_Index_Threshold_Alert_result.json"

# Threshold for low fertility
SFI_THRESHOLD = 0.70

def safe_float(value):
    """Safely convert a value to float, returning None on failure."""
    if value is None:
        return None
    value = str(value).strip()
    if value == '' or value.upper() in ('NA', 'N/A', 'NULL', 'NONE', ''):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

# Read and process data
rows = []
alert_rows = []
dropped_count = 0

try:
    with open(data_file, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Normalize keys to lowercase
            row = {k.lower(): v for k, v in row.items()}
            
            # Check if SFI column exists
            if 'sfi' not in row:
                print("WARNING: 'sfi' column not found in data.")
                dropped_count += 1
                continue
            
            sfi_value = safe_float(row.get('sfi'))
            
            if sfi_value is None:
                dropped_count += 1
                continue
            
            rows.append({
                'sfi': sfi_value,
                'label': row.get('label', 'unknown'),
                'temperature': safe_float(row.get('temperature')),
                'humidity': safe_float(row.get('humidity')),
                'soil_moisture': safe_float(row.get('soil_moisture')),
                'organic_matter': safe_float(row.get('organic_matter')),
                'n': safe_float(row.get('n')),
                'p': safe_float(row.get('p')),
                'k': safe_float(row.get('k'))
            })
            
            # Check threshold alert
            if sfi_value < SFI_THRESHOLD:
                alert_rows.append({
                    'sfi': sfi_value,
                    'label': row.get('label', 'unknown'),
                    'temperature': safe_float(row.get('temperature')),
                    'humidity': safe_float(row.get('humidity')),
                    'soil_moisture': safe_float(row.get('soil_moisture')),
                    'organic_matter': safe_float(row.get('organic_matter')),
                    'n': safe_float(row.get('n')),
                    'p': safe_float(row.get('p')),
                    'k': safe_float(row.get('k'))
                })

except Exception as e:
    print(f"ERROR: Failed to read data file: {e}")
    sys.exit(1)

# Compute summary statistics
if rows:
    sfi_values = [r['sfi'] for r in rows]
    min_sfi = min(sfi_values)
    max_sfi = max(sfi_values)
    avg_sfi = sum(sfi_values) / len(sfi_values)
    
    # Count alerts by crop label
    alert_by_label = {}
    for ar in alert_rows:
        label = ar['label']
        alert_by_label[label] = alert_by_label.get(label, 0) + 1
else:
    min_sfi = max_sfi = avg_sfi = 0.0
    alert_by_label = {}

# Build result
result = {
    "task_name": "Soil Fertility Index Threshold Alert",
    "description": "Monitor the Soil Fertility Index (SFI) and trigger a low-fertility alert when the value drops below 0.70, indicating insufficient organic matter or NPK levels for optimal crop growth.",
    "result_summary": [
        {
            "metric": "total_valid_rows",
            "value": len(rows)
        },
        {
            "metric": "dropped_rows",
            "value": dropped_count
        },
        {
            "metric": "alert_threshold",
            "value": SFI_THRESHOLD
        },
        {
            "metric": "total_alerts",
            "value": len(alert_rows)
        },
        {
            "metric": "min_sfi",
            "value": round(min_sfi, 4)
        },
        {
            "metric": "max_sfi",
            "value": round(max_sfi, 4)
        },
        {
            "metric": "avg_sfi",
            "value": round(avg_sfi, 4)
        },
        {
            "metric": "alert_percentage",
            "value": round((len(alert_rows) / len(rows) * 100) if rows else 0, 2)
        },
        {
            "metric": "alerts_by_crop_label",
            "value": alert_by_label
        }
    ],
    "result_generated_at": datetime.now().isoformat(),
    "alert_details": alert_rows
}

# Write output
try:
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, default=str)
    print(f"Output saved to: {output_file}")
    print(f"Total valid rows: {len(rows)}, Alerts triggered: {len(alert_rows)}")
except Exception as e:
    print(f"ERROR: Failed to write output file: {e}")
    sys.exit(1)