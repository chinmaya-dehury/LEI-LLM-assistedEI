"""
Task: Estimate_CO_Concentration
Description: Estimate the hourly average carbon monoxide concentration (CO) from the sensor data and compare it against the certified reference analyzer values to assess accuracy.
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

# Function to safely convert strings to float
def safe_float(value):
    try:
        return float(value)
    except ValueError:
        return None

results = []
cleaned_rows = 0
invalid_rows = 0

with open(data_file, 'r') as file:
    reader = csv.DictReader(file)
    for row in reader:
        row = {k.lower(): v for k, v in row.items()}
        co_value = safe_float(row.get('co(gt)', ''))
        if co_value is not None:
            results.append(co_value)
            cleaned_rows += 1
        else:
            print(f'Invalid CO value at row: {row}')
            invalid_rows += 1

# Prepare output
output_path = '/home/dcc/LEI-Models-Comparision/output/air-quality/air-quality_openai_gpt-4o-mini_nvidia_nemotron-3-ultra-550b-a55b_run1'
output_file = os.path.join(output_path, 'Estimate_CO_Concentration_result.json')
result_summary = {
    'task_name': 'Estimate_CO_Concentration',
    'description': 'Estimate the hourly average carbon monoxide concentration (CO) from the sensor data and compare it against the certified reference analyzer values to assess accuracy.',
    'result_summary': results,
    'result_generated_at': '2023-10-01'
}

# Save results to JSON file
with open(output_file, 'w') as outfile:
    json.dump(result_summary, outfile)

print(f'Results saved to {output_file}. Cleaned rows: {cleaned_rows}, Invalid rows: {invalid_rows}')