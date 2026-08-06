"""
Task: Monitor Soil Moisture Levels
Description: Track the percentage of soil moisture to ensure optimal irrigation practices and prevent over or under-watering.
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

# Function to safely convert strings to float
def safe_float(value):
    try:
        return float(value)
    except ValueError:
        return None

# Initialize variables
soil_moisture_levels = []
dropped_rows = 0

# Read the CSV file
with open(data_file, mode='r') as file:
    reader = csv.DictReader(file)
    for row in reader:
        row = {k.lower(): v for k, v in row.items()}
        soil_moisture = row.get('soil_moisture', '')
        if soil_moisture in ['', 'NA', 'N/A', 'None']:
            dropped_rows += 1
            continue
        soil_moisture_value = safe_float(soil_moisture)
        if soil_moisture_value is not None:
            soil_moisture_levels.append(soil_moisture_value)
        else:
            dropped_rows += 1

# Prepare results
result_summary = {
    'average_soil_moisture': sum(soil_moisture_levels) / len(soil_moisture_levels) if soil_moisture_levels else None,
    'total_dropped_rows': dropped_rows
}

# Save results to JSON
output_path = Path(OUTPUT_DIR)
output_path.mkdir(parents=True, exist_ok=True)
result = {
    'task_name': 'Monitor Soil Moisture Levels',
    'description': 'Track the percentage of soil moisture to ensure optimal irrigation practices and prevent over or under-watering.',
    'result_summary': result_summary,
    'result_generated_at': '2023-10-01T00:00:00Z'
}
with open(output_path / 'monitor_soil_moisture_levels_result.json', 'w') as json_file:
    json.dump(result, json_file, indent=4)
print('Results saved successfully.')