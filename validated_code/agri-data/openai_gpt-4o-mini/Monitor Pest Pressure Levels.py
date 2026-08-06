"""
Task: Monitor Pest Pressure Levels
Description: Track the level of pest infestation pressure to inform pest management strategies and protect crop health.
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

# Initialize variables
result_summary = []
cleaned_rows_count = 0
missing_rows_count = 0

# Read and process the data
with open(data_file, mode='r') as file:
    reader = csv.DictReader(file)
    for row in reader:
        # Normalize column names to lowercase
        row = {k.lower(): v for k, v in row.items()}
        try:
            # Check for pest pressure column and convert to float
            pest_pressure = row.get('pest_pressure')
            if pest_pressure in (None, '', 'NA', 'N/A', 'None'):
                missing_rows_count += 1
                continue
            pest_pressure = float(pest_pressure)
            result_summary.append(pest_pressure)
            cleaned_rows_count += 1
        except ValueError:
            print(f'Invalid pest pressure value: {pest_pressure}. Skipping row.');
            missing_rows_count += 1

# Prepare the result
result = {
    'task_name': 'Monitor Pest Pressure Levels',
    'description': 'Track the level of pest infestation pressure to inform pest management strategies and protect crop health.',
    'result_summary': result_summary,
    'result_generated_at': '2023-10-01'
}

# Save the result
output_path = Path(OUTPUT_DIR)
output_path.mkdir(parents=True, exist_ok=True)
output_file = output_path / 'monitor_pest_pressure_levels_result.json'
with open(output_file, 'w') as outfile:
    json.dump(result, outfile)

print(f'Results saved to {output_file}')