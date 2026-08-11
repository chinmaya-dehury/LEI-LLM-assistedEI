"""
Task: Assess Pest Pressure Levels
Description: Monitor and report pest pressure levels to inform pest management strategies and protect crop health.
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

# Resolve the input file path dynamically
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

result_summary = []
cleaned_rows_count = 0
missing_rows_count = 0

# Function to safely convert to float
def safe_float(value):
    try:
        return float(value)
    except ValueError:
        return None

# Read the data
with open(data_file, 'r') as file:
    reader = csv.DictReader(file)
    for row in reader:
        row = {k.lower(): v for k, v in row.items()}
        # Check for pest pressure
        if 'pest_pressure' in row:
            pest_pressure = safe_float(row.get('pest_pressure'))
            if pest_pressure is not None:
                result_summary.append(pest_pressure)
                cleaned_rows_count += 1
            else:
                missing_rows_count += 1
                print(f'Missing or invalid pest pressure value in row: {row}')
        else:
            missing_rows_count += 1
            print('Missing pest_pressure column in row:', row)

# Prepare output
output_path = Path('/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_openai_gpt-4o-mini_nvidia_nemotron-3-ultra-550b-a55b_run2')
output_file = output_path / 'assess_pest_pressure_levels_result.json'

# Create output directory if it doesn't exist
output_path.mkdir(parents=True, exist_ok=True)

result = {
    'task_name': 'Assess Pest Pressure Levels',
    'description': 'Monitor and report pest pressure levels to inform pest management strategies and protect crop health.',
    'result_summary': result_summary,
    'result_generated_at': '2023-10-01'
}

# Save the result to a JSON file
with open(output_file, 'w') as f:
    json.dump(result, f)

print(f'Results saved to {output_file}')