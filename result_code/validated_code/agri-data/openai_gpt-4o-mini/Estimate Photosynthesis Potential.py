import re
"""
Task: Estimate Photosynthesis Potential
Description: Estimate the Photosynthesis Potential (PP) based on sunlight exposure, CO2 concentration, and temperature.
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
from pathlib import Path
import csv
import json
import math

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
        sunlight_exposure = safe_float(row.get('sunlight_exposure'))
        co2_concentration = safe_float(row.get('co2_concentration'))
        temperature = safe_float(row.get('temperature'))

        if sunlight_exposure is not None and co2_concentration is not None and temperature is not None:
            # Estimate Photosynthesis Potential (PP)
            pp = (sunlight_exposure * co2_concentration) / (temperature + 1)
            result_summary.append(pp)
            cleaned_rows_count += 1
        else:
            print(f'Invalid row encountered, skipping: {row}')  # Log invalid rows

# Prepare the result
output_path = Path('/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_openai_gpt-4o-mini_google_gemini-3.1-flash-lite_run2')
output_file = output_path / 'Estimate_Photosynthesis_Potential_result.json'

# Ensure output directory exists
output_path.mkdir(parents=True, exist_ok=True)

result = {
    'task_name': 'Estimate Photosynthesis Potential',
    'description': 'Estimate the Photosynthesis Potential (PP) based on sunlight exposure, CO2 concentration, and temperature.',
    'result_summary': result_summary,
    'result_generated_at': '2023-10-01'
}

# Save the result to a JSON file
with open(output_file, 'w') as f:
    json.dump(result, f)

print(f'Results saved to {output_file}')