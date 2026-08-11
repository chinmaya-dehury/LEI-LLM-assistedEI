from datetime import datetime
"""
Task: Nutrient Balance Ratio Deviation Check
Description: Calculate the absolute deviation of the Nutrient Balance Ratio (NBR) from the ideal value of 1.0. Trigger a nutrient imbalance warning if the deviation exceeds 0.15, indicating potential over-fertilization or deficiency.
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
import datetime

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

# Output path (fixed per requirements)
output_dir = Path('/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_qwen_qwen3.7-flash_google_gemini-3.1-flash-lite_run1')
output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / 'Nutrient Balance Ratio Deviation Check_result.json'

# Safe float conversion helper
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

# Constants
IDEAL_NBR = 1.0
WARNING_THRESHOLD = 0.15

# Data collection
nbr_entries = []
total_rows = 0
dropped_rows = 0
warnings = []

try:
    with open(data_file, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            # Normalize column names to lowercase
            row = {k.lower(): v for k, v in row.items()}

            if 'nbr' not in row:
                dropped_rows += 1
                continue

            nbr = safe_float(row.get('nbr'))
            if nbr is None:
                dropped_rows += 1
                continue

            deviation = abs(nbr - IDEAL_NBR)
            is_warning = deviation > WARNING_THRESHOLD

            entry = {
                'nbr': nbr,
                'deviation': round(deviation, 4),
                'warning': is_warning
            }
            nbr_entries.append(entry)

            if is_warning:
                warnings.append(entry)

except Exception as e:
    print(f'Error reading data: {e}')
    sys.exit(1)

# Compute summary statistics
valid_count = len(nbr_entries)
warning_count = len(warnings)
avg_nbr = round(sum(e['nbr'] for e in nbr_entries) / valid_count, 4) if valid_count > 0 else None
avg_deviation = round(sum(e['deviation'] for e in nbr_entries) / valid_count, 4) if valid_count > 0 else None

# Build result
result = {
    'task_name': 'Nutrient Balance Ratio Deviation Check',
    'description': 'Calculate the absolute deviation of the Nutrient Balance Ratio (NBR) from the ideal value of 1.0. Trigger a nutrient imbalance warning if the deviation exceeds 0.15, indicating potential over-fertilization or deficiency.',
    'result_summary': [
        f'Total rows processed: {total_rows}',
        f'Valid NBR entries: {valid_count}',
        f'Dropped/invalid rows: {dropped_rows}',
        f'Warnings triggered: {warning_count}',
        f'Average NBR: {avg_nbr if avg_nbr is not None else "N/A"}',
        f'Average deviation: {avg_deviation if avg_deviation is not None else "N/A"}'
    ],
    'result_generated_at': datetime.datetime.now().isoformat(),
    'warnings': warnings[:10]
}

# Save result as JSON
with open(output_file, 'w') as f:
    json.dump(result, f, indent=2)

print(f'Result saved to {output_file}')
print(f'Processed {valid_count} valid entries, {warning_count} warnings triggered.')