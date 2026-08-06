"""
Task: Monitor CO2 Concentration Levels
Description: Track carbon dioxide concentration in the air to assess its impact on crop growth and photosynthesis.
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

data_file = root_dir / 'data' / 'agri-data' / 'raw_data.csv'
if not data_file.exists():
    data_file = root_dir / 'data' / 'agri-data' / 'raw_data.txt'
if not data_file.exists():
    print('Data file not found. Exiting.'); exit(1)

co2_levels = []
invalid_rows = 0

with open(data_file, 'r') as file:
    reader = csv.DictReader(file)
    for row in reader:
        row = {k.lower(): v for k, v in row.items()}
        co2_value = row.get('co2_concentration', '').strip()
        if co2_value in ['', 'na', 'n/a', 'None']:
            invalid_rows += 1
            continue
        try:
            co2_value = float(co2_value)
            co2_levels.append(co2_value)
        except ValueError:
            print(f'Invalid CO2 concentration value: {co2_value}');
            invalid_rows += 1

result_summary = {
    'average_co2': sum(co2_levels) / len(co2_levels) if co2_levels else None,
    'total_invalid_rows': invalid_rows
}

output_path = Path(OUTPUT_DIR)
output_path.mkdir(parents=True, exist_ok=True)
result = {
    'task_name': 'Monitor CO2 Concentration Levels',
    'description': 'Track carbon dioxide concentration in the air to assess its impact on crop growth and photosynthesis.',
    'result_summary': result_summary,
    'result_generated_at': '2023-10-01T12:00:00Z'
}

with open(output_path / 'monitor_co2_concentration_levels_result.json', 'w') as outfile:
    json.dump(result, outfile, indent=4)