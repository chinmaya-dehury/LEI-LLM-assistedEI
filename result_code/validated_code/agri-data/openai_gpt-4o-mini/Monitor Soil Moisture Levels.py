"""
Task: Monitor Soil Moisture Levels
Description: Continuously monitor soil moisture levels to ensure optimal irrigation practices.
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
soil_moisture_levels = []
dropped_rows = 0

# Read the data file
with open(data_file, 'r') as file:
    reader = csv.DictReader(file)
    for row in reader:
        row = {k.lower(): v for k, v in row.items()}
        soil_moisture = safe_float(row.get('soil_moisture'))
        if soil_moisture is not None:
            soil_moisture_levels.append(soil_moisture)
        else:
            dropped_rows += 1
            print(f'Dropped row due to missing soil moisture: {row}')  

# Prepare the result
result_summary = {
    'average_soil_moisture': sum(soil_moisture_levels) / len(soil_moisture_levels) if soil_moisture_levels else None,
    'total_dropped_rows': dropped_rows
}

# Output path
output_path = '/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_openai_gpt-4o-mini_google_gemini-3.1-flash-lite_run2'
output_file = os.path.join(output_path, 'monitor_soil_moisture_levels_result.json')

# Save the results
result = {
    'task_name': 'Monitor Soil Moisture Levels',
    'description': 'Continuously monitor soil moisture levels to ensure optimal irrigation practices.',
    'result_summary': result_summary,
    'result_generated_at': '2023-10-01'
}

with open(output_file, 'w') as outfile:
    json.dump(result, outfile)
print(f'Results saved to {output_file}')