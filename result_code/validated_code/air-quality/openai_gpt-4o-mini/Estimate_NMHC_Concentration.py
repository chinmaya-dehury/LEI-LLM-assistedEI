"""
Task: Estimate_NMHC_Concentration
Description: Estimate the hourly average concentration of Non Metanic Hydrocarbons (NMHC) from the sensor data and compare it against the certified reference analyzer values to assess accuracy.
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

nmc_values = []

with data_file.open('r') as file:
    reader = csv.DictReader(file)
    dropped_rows = 0
    for row in reader:
        row = {k.lower(): v for k, v in row.items()}
        try:
            nmc = row.get('nmhc(gt)')
            if nmc in ['', 'NA', 'N/A', 'None']:
                dropped_rows += 1
                continue
            nmc_values.append(float(nmc))
        except ValueError:
            print(f'Invalid NMHC value: {nmc}. Dropping row.');
            dropped_rows += 1

result_summary = {
    'average_nmhc': sum(nmc_values) / len(nmc_values) if nmc_values else None,
    'dropped_rows': dropped_rows
}

output_path = '/home/dcc/LEI-Models-Comparision/output/air-quality/air-quality_openai_gpt-4o-mini_nvidia_nemotron-3-ultra-550b-a55b_run1'
output_file = os.path.join(output_path, 'Estimate_NMHC_Concentration_result.json')

result = {
    'task_name': 'Estimate_NMHC_Concentration',
    'description': 'Estimate the hourly average concentration of Non Metanic Hydrocarbons (NMHC) from the sensor data and compare it against the certified reference analyzer values to assess accuracy.',
    'result_summary': result_summary,
    'result_generated_at': '2023-10-01'
}

with open(output_file, 'w') as f:
    json.dump(result, f)
print(f'Results saved to {output_file}')