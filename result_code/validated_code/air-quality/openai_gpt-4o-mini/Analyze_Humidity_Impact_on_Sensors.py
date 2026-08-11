"""
Task: Analyze_Humidity_Impact_on_Sensors
Description: Evaluate the impact of relative and absolute humidity variations on the sensor readings to identify potential cross-sensitivities.
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
cleaned_rows_count = 0
missing_rows_count = 0

with open(data_file, 'r') as file:
    reader = csv.DictReader(file)
    for row in reader:
        row = {k.lower(): v for k, v in row.items()}
        try:
            temperature = float(row.get('t', 'nan')) if row.get('t') not in ['', 'NA', 'N/A', 'None'] else None
            rh = float(row.get('rh', 'nan')) if row.get('rh') not in ['', 'NA', 'N/A', 'None'] else None
            ah = float(row.get('ah', 'nan')) if row.get('ah') not in ['', 'NA', 'N/A', 'None'] else None
            co_gt = float(row.get('co(gt)', 'nan')) if row.get('co(gt)') not in ['', 'NA', 'N/A', 'None'] else None
            if temperature is not None and rh is not None and ah is not None and co_gt is not None:
                results.append({'temperature': temperature, 'rh': rh, 'ah': ah, 'co_gt': co_gt})
                cleaned_rows_count += 1
            else:
                missing_rows_count += 1
                print(f'Missing or invalid data in row: {row}')
        except ValueError as e:
            missing_rows_count += 1
            print(f'ValueError: {e} in row: {row}')

output_path = Path('/home/dcc/LEI-Models-Comparision/output/air-quality/air-quality_openai_gpt-4o-mini_nvidia_nemotron-3-ultra-550b-a55b_run2')
output_file = output_path / 'Analyze_Humidity_Impact_on_Sensors_result.json'

if not output_path.exists():
    os.makedirs(output_path)

result_summary = {
    'task_name': 'Analyze_Humidity_Impact_on_Sensors',
    'description': 'Evaluate the impact of relative and absolute humidity variations on the sensor readings to identify potential cross-sensitivities.',
    'result_summary': results,
    'cleaned_rows_count': cleaned_rows_count,
    'missing_rows_count': missing_rows_count,
    'result_generated_at': '2023-10-01'
}

with open(output_file, 'w') as outfile:
    json.dump(result_summary, outfile, indent=4)
print(f'Results saved to {output_file}')