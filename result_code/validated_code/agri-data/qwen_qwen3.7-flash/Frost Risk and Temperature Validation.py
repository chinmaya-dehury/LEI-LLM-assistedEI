import re
"""
Task: Frost Risk and Temperature Validation
Description: Assess the Frost_Risk index in conjunction with ambient Temperature. Trigger a frost protection alert when Frost_Risk exceeds 0.6 and Temperature falls below 4.0°C.
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
while root_dir.name and not (root_dir / 'data').exists():
    parent = root_dir.parent
    if parent == root_dir:
        break
    root_dir = parent

data_file = root_dir / 'data' / 'agri-data' / 'raw_data.csv'
if not data_file.exists():
    data_file = root_dir / 'data' / 'agri-data' / 'raw_data.txt'

if not data_file.exists():
    print('ERROR: Input data file not found under data/agri-data/')
    sys.exit(1)

# Output path (strictly specified)
output_dir = Path('/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_qwen_qwen3.7-flash_google_gemini-3.1-flash-lite_run1')
output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / 'Frost Risk and Temperature Validation_result.json'

# Safe numeric conversion
def safe_float(value):
    if value is None:
        return None
    value = str(value).strip()
    if value == '' or value.upper() in ('NA', 'N/A', 'NULL', 'NONE'):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

# Read and parse data
rows = []
missing_count = 0
total_count = 0

try:
    with open(data_file, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_count += 1
            # Normalize keys to lowercase
            row = {k.lower(): v for k, v in row.items()}
            
            # Check required columns
            if 'frost_risk' not in row or 'temperature' not in row:
                missing_count += 1
                continue
            
            frost_risk = safe_float(row.get('frost_risk'))
            temperature = safe_float(row.get('temperature'))
            
            if frost_risk is None or temperature is None:
                missing_count += 1
                continue
            
            rows.append({
                'frost_risk': frost_risk,
                'temperature': temperature
            })
except Exception as e:
    print(f'ERROR: Failed to read data file: {e}')
    sys.exit(1)

# Filter frost alerts: Frost_Risk > 0.6 AND Temperature < 4.0
alerts = []
for r in rows:
    if r['frost_risk'] > 0.6 and r['temperature'] < 4.0:
        alerts.append({
            'frost_risk': r['frost_risk'],
            'temperature': r['temperature']
        })

# Build result
result = {
    'task_name': 'Frost Risk and Temperature Validation',
    'description': 'Assess the Frost_Risk index in conjunction with ambient Temperature. Trigger a frost protection alert when Frost_Risk exceeds 0.6 and Temperature falls below 4.0°C.',
    'result_summary': [
        f'Total rows processed: {total_count}',
        f'Rows with valid frost_risk and temperature: {len(rows)}',
        f'Rows dropped (missing/invalid): {missing_count}',
        f'Frost alerts triggered: {len(alerts)}',
        f'Alert threshold: Frost_Risk > 0.6 AND Temperature < 4.0°C'
    ],
    'alerts': alerts,
    'result_generated_at': datetime.utcnow().isoformat() + 'Z'
}

# Write output
try:
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
    print(f'Result saved to {output_file}')
except Exception as e:
    print(f'ERROR: Failed to write output: {e}')
    sys.exit(1)