"""
Task: Analyze Sunlight Exposure
Description: Evaluate the average daily sunlight exposure to determine its impact on photosynthesis potential and crop yield.
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
sunlight_exposure_sum = 0.0
count = 0
invalid_rows = 0

# Read the CSV file
with open(data_file, mode='r') as file:
    reader = csv.DictReader(file)
    for row in reader:
        row = {k.lower(): v for k, v in row.items()}
        sunlight_exposure = row.get('sunlight_exposure')
        if sunlight_exposure:
            sunlight_exposure = safe_float(sunlight_exposure)
            if sunlight_exposure is not None:
                sunlight_exposure_sum += sunlight_exposure
                count += 1
            else:
                invalid_rows += 1
        else:
            invalid_rows += 1

# Calculate average sunlight exposure
average_sunlight_exposure = sunlight_exposure_sum / count if count > 0 else None

# Prepare result
result = {
    'task_name': 'Analyze Sunlight Exposure',
    'description': 'Evaluate the average daily sunlight exposure to determine its impact on photosynthesis potential and crop yield.',
    'result_summary': [
        {'average_sunlight_exposure': average_sunlight_exposure},
        {'total_invalid_rows': invalid_rows}
    ],
    'result_generated_at': '2023-10-01'
}

# Save result to JSON file
output_path = Path(OUTPUT_DIR)
output_path.mkdir(parents=True, exist_ok=True)
output_file = output_path / 'analyze_sunlight_exposure_result.json'
with open(output_file, 'w') as json_file:
    json.dump(result, json_file, indent=4)

print(f'Results saved to {output_file}')