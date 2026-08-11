"""
Task: Heat Stress Detection via THI
Description: Evaluate the Temperature-Humidity Index (THI) to identify heat stress conditions. Flag records where THI exceeds 25 to prompt irrigation or shading adjustments.
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
    print('Error: Input data file not found under data/agri-data/')
    sys.exit(1)

# Output path (CRITICAL: use specified path)
output_dir = Path('/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_qwen_qwen3.7-flash_google_gemini-3.1-flash-lite_run2')
output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / 'heat_stress_detection_result.json'

# Helper: safe numeric conversion
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
records = []
heat_stress_records = []
dropped_rows = 0
total_rows = 0

try:
    with open(data_file, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            # Normalize keys to lowercase
            row = {k.lower(): v for k, v in row.items()}

            # Check required columns
            if 'temperature' not in row or 'humidity' not in row or 'thi' not in row:
                dropped_rows += 1
                continue

            # Extract and validate values
            temperature = safe_float(row.get('temperature'))
            humidity = safe_float(row.get('humidity'))
            thi = safe_float(row.get('thi'))

            if temperature is None or humidity is None or thi is None:
                dropped_rows += 1
                continue

            # Check for heat stress (THI > 25)
            is_heat_stress = thi > 25.0

            record = {
                'temperature': temperature,
                'humidity': humidity,
                'thi': thi,
                'heat_stress': is_heat_stress
            }

            records.append(record)

            if is_heat_stress:
                heat_stress_records.append(record)

except Exception as e:
    print(f'Error reading data: {e}')
    sys.exit(1)

# Compute summary statistics
if records:
    avg_thi = sum(r['thi'] for r in records) / len(records)
    max_thi = max(r['thi'] for r in records)
    min_thi = min(r['thi'] for r in records)
    heat_stress_pct = (len(heat_stress_records) / len(records)) * 100
else:
    avg_thi = max_thi = min_thi = 0.0
    heat_stress_pct = 0.0

# Build result
result = {
    'task_name': 'Heat Stress Detection via THI',
    'description': 'Evaluate the Temperature-Humidity Index (THI) to identify heat stress conditions. Flag records where THI exceeds 25 to prompt irrigation or shading adjustments.',
    'result_summary': [
        f'Total valid records analyzed: {len(records)}',
        f'Records with heat stress (THI > 25): {len(heat_stress_records)}',
        f'Heat stress percentage: {heat_stress_pct:.2f}%',
        f'Average THI: {avg_thi:.2f}',
        f'Max THI: {max_thi:.2f}',
        f'Min THI: {min_thi:.2f}',
        f'Dropped/invalid rows: {dropped_rows}',
        f'Total rows processed: {total_rows}'
    ],
    'result_generated_at': datetime.now().isoformat(),
    'heat_stress_records': heat_stress_records
}

# Save result
try:
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, default=str)
    print(f'Result saved to: {output_file}')
except Exception as e:
    print(f'Error saving result: {e}')
    sys.exit(1)

# Print concise summary
print(f'Heat stress detection complete: {len(heat_stress_records)}/{len(records)} records flagged (THI > 25)')