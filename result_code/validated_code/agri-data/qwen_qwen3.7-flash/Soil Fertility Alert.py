"""
Task: Soil Fertility Alert
Description: Monitor the Soil Fertility Index (SFI) in real-time and trigger a low-fertility alert when the value drops below a predefined threshold (e.g., 0.65), indicating a need for organic matter or nutrient supplementation.
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
import sys
from pathlib import Path
from datetime import datetime

# Resolve data file path dynamically
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
    print('Error: Data file not found in data/agri-data/')
    sys.exit(1)

# Output path (CRITICAL: use specified directory)
output_dir = Path('/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_qwen_qwen3.7-flash_anthropic_claude-3-haiku_run2')
output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / 'Soil Fertility Alert_result.json'

# Threshold for low fertility alert
THRESHOLD = 0.65

def safe_float(value):
    """Safely convert a value to float, returning None if conversion fails."""
    if value is None:
        return None
    value = str(value).strip()
    if value == '' or value.lower() in ('na', 'n/a', 'None'):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

# Read and process data
low_fertility_records = []
total_rows = 0
valid_sfi_rows = 0
dropped_rows = 0

try:
    with open(data_file, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            # Normalize keys to lowercase
            row = {k.lower(): v for k, v in row.items()}

            # Check if SFI column exists
            if 'sfi' not in row:
                dropped_rows += 1
                continue

            sfi_value = safe_float(row.get('sfi'))
            if sfi_value is None:
                dropped_rows += 1
                continue

            valid_sfi_rows += 1

            # Check if SFI is below threshold
            if sfi_value < THRESHOLD:
                record = {
                    'sfi': sfi_value,
                    'label': row.get('label', 'unknown'),
                    'temperature': row.get('temperature', ''),
                    'humidity': row.get('humidity', ''),
                    'soil_moisture': row.get('soil_moisture', ''),
                    'organic_matter': row.get('organic_matter', '')
                }
                low_fertility_records.append(record)

except Exception as e:
    print(f'Error reading data file: {e}')
    sys.exit(1)

# Prepare result
result = {
    'task_name': 'Soil Fertility Alert',
    'description': 'Monitor the Soil Fertility Index (SFI) in real-time and trigger a low-fertility alert when the value drops below a predefined threshold (e.g., 0.65), indicating a need for organic matter or nutrient supplementation.',
    'result_summary': [
        {'metric': 'total_rows_processed', 'value': total_rows},
        {'metric': 'valid_sfi_records', 'value': valid_sfi_rows},
        {'metric': 'dropped_rows', 'value': dropped_rows},
        {'metric': 'low_fertility_alerts', 'value': len(low_fertility_records)},
        {'metric': 'threshold', 'value': THRESHOLD}
    ],
    'low_fertility_records': low_fertility_records,
    'result_generated_at': datetime.now().isoformat()
}

# Save result
try:
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
    print(f'Results saved to {output_file}')
    print(f'Low fertility alerts: {len(low_fertility_records)} out of {valid_sfi_rows} valid records')
except Exception as e:
    print(f'Error saving results: {e}')
    sys.exit(1)