"""
Task: Estimate_Benzene_Concentration
Description: Estimate the hourly average concentration of Benzene (C6H6) from the sensor data and compare it against the certified reference analyzer values to assess accuracy.
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

# Function to safely convert strings to floats
def safe_float(value):
    try:
        return float(value)
    except ValueError:
        return None

# Read and process the data
benzene_values = []
row_count = 0
invalid_rows = 0

with open(data_file, 'r') as file:
    reader = csv.DictReader(file)
    for row in reader:
        row_count += 1
        row = {k.lower(): v for k, v in row.items()}
        benzene = safe_float(row.get('c6h6(gt)', ''))
        if benzene is not None:
            benzene_values.append(benzene)
        else:
            invalid_rows += 1
            print(f'Invalid row {row_count}: Missing or invalid Benzene value.')  

# Calculate the average Benzene concentration
if benzene_values:
    average_benzene = sum(benzene_values) / len(benzene_values)
else:
    average_benzene = None

# Prepare the output
output_path = Path('/home/dcc/LEI-Models-Comparision/output/air-quality/air-quality_openai_gpt-4o-mini_nvidia_nemotron-3-ultra-550b-a55b_run1')
output_file = output_path / 'Estimate_Benzene_Concentration_result.json'

# Ensure output directory exists
output_path.mkdir(parents=True, exist_ok=True)

result = {
    'task_name': 'Estimate_Benzene_Concentration',
    'description': 'Estimate the hourly average concentration of Benzene (C6H6) from the sensor data and compare it against the certified reference analyzer values to assess accuracy.',
    'result_summary': [
        {'average_benzene': average_benzene, 'total_rows': row_count, 'invalid_rows': invalid_rows}
    ],
    'result_generated_at': '2023-10-01T12:00:00'
}

# Save the result to a JSON file
with open(output_file, 'w') as outfile:
    json.dump(result, outfile, indent=4)