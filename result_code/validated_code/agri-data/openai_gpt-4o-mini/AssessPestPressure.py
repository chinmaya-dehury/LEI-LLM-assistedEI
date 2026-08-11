"""
Task: AssessPestPressure
Description: Monitor pest pressure levels to evaluate their impact on crop health and yield.
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

# Function to safely convert strings to floats
def safe_float(value):
    try:
        return float(value)
    except ValueError:
        return None

# Initialize variables
pest_pressure_data = []
dropped_rows = 0

# Read the data
with open(data_file, 'r') as file:
    reader = csv.DictReader(file)
    for row in reader:
        row = {k.lower(): v for k, v in row.items()}
        # Check for required columns
        if 'pest_pressure' in row:
            pest_pressure = safe_float(row.get('pest_pressure'))
            if pest_pressure is not None:
                pest_pressure_data.append(pest_pressure)
            else:
                dropped_rows += 1
                print(f'Dropped row due to invalid pest pressure: {row}')
        else:
            dropped_rows += 1
            print('Dropped row due to missing pest pressure column.')

# Prepare results
result_summary = {
    'average_pest_pressure': sum(pest_pressure_data) / len(pest_pressure_data) if pest_pressure_data else None,
    'total_dropped_rows': dropped_rows
}

# Output path
output_path = '/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_openai_gpt-4o-mini_google_gemini-3.1-flash-lite_run1'
output_file = os.path.join(output_path, 'AssessPestPressure_result.json')

# Save results
result = {
    'task_name': 'AssessPestPressure',
    'description': 'Monitor pest pressure levels to evaluate their impact on crop health and yield.',
    'result_summary': result_summary,
    'result_generated_at': '2023-10-01'
}

with open(output_file, 'w') as outfile:
    json.dump(result, outfile)
print(f'Results saved to {output_file}')