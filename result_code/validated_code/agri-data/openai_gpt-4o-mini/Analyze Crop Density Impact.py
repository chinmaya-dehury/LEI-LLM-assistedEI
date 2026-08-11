"""
Task: Analyze Crop Density Impact
Description: Analyze the impact of crop density on growth stage and overall crop health.
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
results = []
cleaned_rows_count = 0
missing_rows_count = 0

# Read the data
with open(data_file, mode='r') as file:
    reader = csv.DictReader(file)
    for row in reader:
        # Normalize column names
        row = {k.lower(): v for k, v in row.items()}
        # Check for required columns
        if 'crop_density' not in row or 'growth_stage' not in row:
            print('Missing required columns in row. Skipping.');
            missing_rows_count += 1
            continue
        # Process crop density
        crop_density = safe_float(row.get('crop_density'))
        growth_stage = row.get('growth_stage')
        if crop_density is None or growth_stage is None:
            print(f'Invalid data in row: {row}. Skipping.');
            missing_rows_count += 1
            continue
        # Append result
        results.append({'crop_density': crop_density, 'growth_stage': growth_stage})
        cleaned_rows_count += 1

# Prepare output
output_path = Path('/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_openai_gpt-4o-mini_google_gemini-3.1-flash-lite_run2')
output_file = output_path / 'analyze_crop_density_impact_result.json'

# Create output directory if it doesn't exist
output_path.mkdir(parents=True, exist_ok=True)

# Save results
output_data = {
    'task_name': 'Analyze Crop Density Impact',
    'description': 'Analyze the impact of crop density on growth stage and overall crop health.',
    'result_summary': results,
    'result_generated_at': '2023-10-01'
}

with open(output_file, 'w') as json_file:
    json.dump(output_data, json_file, indent=4)

print(f'Results saved to {output_file}')