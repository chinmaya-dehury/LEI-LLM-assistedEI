"""
Task: Analyze_Temperature_Impact_on_Sensors
Description: Evaluate the impact of temperature variations on the sensor readings to identify potential cross-sensitivities.
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

DATA_FILE_PATH = os.path.join(_root_dir, "data", "air-quality", "raw_data.csv")
if not os.path.exists(DATA_FILE_PATH):
    DATA_FILE_PATH = os.path.join(_root_dir, "data", "air-quality", "raw_data.txt")

METADATA_FILE_PATH = os.path.join(_root_dir, "data", "air-quality", "metadata.json")
OUTPUT_DIR = os.path.join(_root_dir, "output", "air-quality")
os.makedirs(OUTPUT_DIR, exist_ok=True)

import os
import csv
import json
from pathlib import Path

# Resolve the input file path
curr_dir = Path(__file__).resolve().parent
root_dir = curr_dir
while root_dir.name and not (root_dir / 'data').exists():
    parent = root_dir.parent
    if parent == root_dir:
        break
    root_dir = parent

data_file = root_dir / 'data' / 'air-quality' / 'raw_data.csv'
if not data_file.exists():
    data_file = root_dir / 'data' / 'air-quality' / 'raw_data.txt'
if not data_file.exists():
    print('Data file not found. Exiting.'); exit(1)

results = []
row_count = 0
invalid_count = 0

with data_file.open('r') as file:
    reader = csv.DictReader(file)
    for row in reader:
        row_count += 1
        row = {k.lower(): v for k, v in row.items()}
        try:
            temperature = float(row.get('t', '')) if row.get('t', '') not in ['', 'NA', 'N/A', 'None'] else None
            co = float(row.get('co(gt)', '')) if row.get('co(gt)', '') not in ['', 'NA', 'N/A', 'None'] else None
            if temperature is None or co is None:
                invalid_count += 1
                continue
            results.append({'temperature': temperature, 'co': co})
        except ValueError as e:
            print(f'Error converting row {row_count}: {e}')
            invalid_count += 1

result_summary = {'total_rows': row_count, 'valid_rows': row_count - invalid_count, 'invalid_rows': invalid_count}

output_path = Path('/home/dcc/LEI-Models-Comparision/output/air-quality/air-quality_openai_gpt-4o-mini_nvidia_nemotron-3-ultra-550b-a55b_run2')
output_file = output_path / 'Analyze_Temperature_Impact_on_Sensors_result.json'

if not output_path.exists():
    os.makedirs(output_path)

with output_file.open('w') as outfile:
    json.dump({'task_name': 'Analyze_Temperature_Impact_on_Sensors', 'description': 'Evaluate the impact of temperature variations on the sensor readings to identify potential cross-sensitivities.', 'result_summary': result_summary, 'result_generated_at': '2023-10-01T00:00:00'}, outfile)

print(f'Results saved to {output_file}')