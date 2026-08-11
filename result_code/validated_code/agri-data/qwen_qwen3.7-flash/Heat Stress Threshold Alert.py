"""
Task: Heat Stress Threshold Alert
Description: Continuously monitor the Temperature-Humidity Index (THI) and trigger a lightweight alert when the value exceeds a predefined threshold (e.g., 25.0), indicating potential crop heat stress.
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

# Resolve input file path dynamically
curr_dir = Path(__file__).resolve().parent
root_dir = curr_dir
while root_dir.name and not (root_dir / 'data').exists():
    parent = root_dir.parent
    if parent == root_dir:
        break
    root_dir = parent

data_file = root_dir / 'data' / 'agri-data' / 'raw_data.csv'
if not data_file.exists():
    data_file = root_dir / 'data' / 'agri-data' / 'raw_data.txt'

if not data_file.exists():
    print('Error: Input data file not found in data/agri-data/')
    sys.exit(1)

# Output directory (fixed path as specified)
output_dir = Path('/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_qwen_qwen3.7-flash_nvidia_nemotron-3-ultra-550b-a55b_run2')
output_dir.mkdir(parents=True, exist_ok=True)

# Heat stress threshold for THI
THI_THRESHOLD = 25.0

# Helper function to safely convert to float
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
alerts = []
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
            
            # Check if required columns exist
            if 'thi' not in row:
                dropped_rows += 1
                continue
            
            # Get THI value
            thi_value = safe_float(row.get('thi'))
            
            if thi_value is None:
                dropped_rows += 1
                continue
            
            valid_rows += 1
            
            # Check if THI exceeds threshold
            if thi_value > THI_THRESHOLD:
                alert = {
                    'row_index': total_rows,
                    'thi': thi_value,
                    'temperature': safe_float(row.get('temperature')),
                    'humidity': safe_float(row.get('humidity')),
                    'label': row.get('label', 'unknown')
                }
                alerts.append(alert)
                
except Exception as e:
    print(f'Error reading data: {e}')
    sys.exit(1)

# Generate result
result = {
    'task_name': 'Heat Stress Threshold Alert',
    'description': 'Continuously monitor the Temperature-Humidity Index (THI) and trigger a lightweight alert when the value exceeds a predefined threshold (e.g., 25.0), indicating potential crop heat stress.',
    'result_summary': {
        'total_rows_processed': total_rows,
        'valid_rows': valid_rows,
        'dropped_rows': dropped_rows,
        'alerts_triggered': len(alerts),
        'threshold': THI_THRESHOLD,
        'alerts': alerts
    },
    'result_generated_at': '2024-01-01T00:00:00Z'
}

# Save result to specified output directory
output_file = output_dir / 'Heat Stress Threshold Alert_result.json'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(result, f, indent=2)

print(f'Analysis complete. {len(alerts)} heat stress alerts triggered out of {valid_rows} valid rows.')