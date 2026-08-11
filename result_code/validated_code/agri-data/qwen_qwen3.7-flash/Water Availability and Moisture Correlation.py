"""
Task: Water Availability and Moisture Correlation
Description: Cross-reference the Water Availability Index (WAI) with real-time Soil_Moisture readings. Flag instances where WAI is below 0.80 but Soil_Moisture remains above 45%, suggesting drainage issues or irrigation inefficiency.
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

# Resolve output directory
output_dir = Path('/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_qwen_qwen3.7-flash_google_gemini-3.1-flash-lite_run1')
output_dir.mkdir(parents=True, exist_ok=True)

# Helper: safe float conversion
def safe_float(value):
    if value is None:
        return None
    value = str(value).strip()
    if value == '' or value.upper() in ('NA', 'N/A', 'NULL', 'NONE', ''):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

# Read and parse data
flagged_records = []
total_rows = 0
skipped_rows = 0

try:
    with open(data_file, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            # Normalize keys to lowercase
            row = {k.lower(): v for k, v in row.items()}

            # Check required columns exist
            if 'wai' not in row or 'soil_moisture' not in row:
                skipped_rows += 1
                continue

            wai = safe_float(row.get('wai'))
            soil_moisture = safe_float(row.get('soil_moisture'))

            if wai is None or soil_moisture is None:
                skipped_rows += 1
                continue

            # Flag: WAI < 0.80 AND Soil_Moisture > 45%
            if wai < 0.80 and soil_moisture > 45.0:
                flagged_records.append({
                    'wai': round(wai, 4),
                    'soil_moisture': round(soil_moisture, 2),
                    'label': row.get('label', 'unknown'),
                    'soil_type': row.get('soil_type', 'unknown'),
                    'rainfall': safe_float(row.get('rainfall')),
                    'irrigation_frequency': safe_float(row.get('irrigation_frequency')),
                    'issue': 'Possible drainage issue or irrigation inefficiency'
                })

except Exception as e:
    print(f'ERROR: Failed to read data file: {e}')
    sys.exit(1)

# Build result
result = {
    'task_name': 'Water Availability and Moisture Correlation',
    'description': 'Cross-reference WAI with Soil_Moisture to flag drainage/irrigation inefficiency',
    'result_summary': [
        f'Total rows processed: {total_rows}',
        f'Rows skipped (missing data): {skipped_rows}',
        f'Flagged instances (WAI < 0.80 AND Soil_Moisture > 45%): {len(flagged_records)}'
    ],
    'flagged_records': flagged_records,
    'result_generated_at': datetime.utcnow().isoformat() + 'Z'
}

# Save output
output_path = output_dir / 'Water_Availability_and_Moisture_Correlation_result.json'
try:
    with open(output_path, 'w', encoding='utf-8') as out_f:
        json.dump(result, out_f, indent=2, ensure_ascii=False)
    print(f'Result saved to: {output_path}')
    print(f'Flagged {len(flagged_records)} records with potential drainage/irrigation issues.')
except Exception as e:
    print(f'ERROR: Failed to write output: {e}')
    sys.exit(1)