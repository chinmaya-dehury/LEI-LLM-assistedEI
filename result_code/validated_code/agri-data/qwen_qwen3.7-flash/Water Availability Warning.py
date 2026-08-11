"""
Task: Water Availability Warning
Description: Assess combined soil moisture and rainfall conditions using the Water Availability Index (WAI). Flag a water stress warning when WAI falls below a threshold (e.g., 0.75) to prompt timely irrigation adjustments.
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

# Output path
output_dir = Path('/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_qwen_qwen3.7-flash_anthropic_claude-3-haiku_run2')
output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / 'Water Availability Warning_result.json'

# Threshold for water stress
WAI_THRESHOLD = 0.75

# Safe numeric conversion
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

# Read and process data
rows = []
warnings = []
dropped_count = 0
total_count = 0

try:
    with open(data_file, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Normalize keys to lowercase
            row = {k.lower(): v for k, v in row.items()}
            total_count += 1

            # Check if WAI column exists
            if 'wai' not in row:
                dropped_count += 1
                continue

            wai_value = safe_float(row.get('wai'))
            if wai_value is None:
                dropped_count += 1
                continue

            # Check for water stress
            if wai_value < WAI_THRESHOLD:
                warning_entry = {
                    'row_index': total_count,
                    'wai': wai_value,
                    'threshold': WAI_THRESHOLD,
                    'status': 'WATER_STRESS'
                }
                # Include additional context if available
                if 'label' in row:
                    warning_entry['crop_label'] = row.get('label', '').strip()
                if 'soil_moisture' in row:
                    warning_entry['soil_moisture'] = safe_float(row.get('soil_moisture'))
                if 'rainfall' in row:
                    warning_entry['rainfall'] = safe_float(row.get('rainfall'))
                warnings.append(warning_entry)

except Exception as e:
    print(f'ERROR: Failed to read data file: {e}', file=sys.stderr)
    sys.exit(1)

# Build result
result = {
    'task_name': 'Water Availability Warning',
    'description': 'Assess combined soil moisture and rainfall conditions using the Water Availability Index (WAI). Flag a water stress warning when WAI falls below a threshold (e.g., 0.75) to prompt timely irrigation adjustments.',
    'result_summary': [
        f'Total rows processed: {total_count}',
        f'Rows dropped (missing/invalid WAI): {dropped_count}',
        f'Water stress warnings (WAI < {WAI_THRESHOLD}): {len(warnings)}',
        f'Warning rate: {len(warnings)/total_count*100:.1f}%' if total_count > 0 else 'N/A'
    ],
    'warnings': warnings,
    'result_generated_at': datetime.utcnow().isoformat() + 'Z'
}

# Save result
try:
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, default=str)
    print(f'Result saved to: {output_file}')
except Exception as e:
    print(f'ERROR: Failed to save result: {e}', file=sys.stderr)
    sys.exit(1)

# Print summary
print(f'Total rows: {total_count}')
print(f'Dropped rows: {dropped_count}')
print(f'Water stress warnings: {len(warnings)}')
if warnings:
    print(f'Average WAI in warning rows: {sum(w["wai"] for w in warnings)/len(warnings):.3f}')