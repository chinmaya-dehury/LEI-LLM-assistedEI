"""
Task: Analyze Photosynthesis Potential (PP)
Description: Estimate the Photosynthesis Potential (PP) based on sunlight exposure, CO2 concentration, and temperature to understand crop growth conditions.
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

result_summary = []
cleaned_rows_count = 0
missing_rows_count = 0

# Function to safely convert to float
def safe_float(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

# Read the data
with open(data_file, 'r') as file:
    reader = csv.DictReader(file)
    for row in reader:
        row = {k.lower(): v for k, v in row.items()}
        sunlight_exposure = safe_float(row.get('sunlight_exposure'))
        co2_concentration = safe_float(row.get('co2_concentration'))
        temperature = safe_float(row.get('temperature'))

        if sunlight_exposure is None or co2_concentration is None or temperature is None:
            missing_rows_count += 1
            continue

        # Calculate Photosynthesis Potential (PP)
        pp = (sunlight_exposure * co2_concentration * temperature) / 1000
        result_summary.append(pp)
        cleaned_rows_count += 1

# Prepare the result
result = {
    'task_name': 'Analyze Photosynthesis Potential (PP)',
    'description': 'Estimate the Photosynthesis Potential (PP) based on sunlight exposure, CO2 concentration, and temperature to understand crop growth conditions.',
    'result_summary': result_summary,
    'result_generated_at': '2023-10-01'
}

# Save the result
output_path = Path(OUTPUT_DIR)
output_path.mkdir(parents=True, exist_ok=True)
output_file = output_path / 'analyze_photosynthesis_potential_result.json'
with open(output_file, 'w') as outfile:
    json.dump(result, outfile)

print(f'Results saved to {output_file}')