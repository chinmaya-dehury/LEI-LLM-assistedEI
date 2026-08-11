"""
Task: Evaluate Crop Growth Stage
Description: Classify the current growth stage of the crop based on environmental parameters to inform management decisions.
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
with open(data_file, 'r') as file:
    reader = csv.DictReader(file)
    for row in reader:
        row = {k.lower(): v for k, v in row.items()}
        # Check for required columns
        if 'temperature' in row and 'humidity' in row and 'soil_moisture' in row:
            temperature = safe_float(row.get('temperature'))
            humidity = safe_float(row.get('humidity'))
            soil_moisture = safe_float(row.get('soil_moisture'))
            if temperature is not None and humidity is not None and soil_moisture is not None:
                # Simple classification logic based on thresholds
                if temperature > 25 and humidity > 80 and soil_moisture > 40:
                    growth_stage = 'Flowering'
                elif temperature > 20 and humidity > 70:
                    growth_stage = 'Vegetative'
                else:
                    growth_stage = 'Seedling'
                results.append({'temperature': temperature, 'humidity': humidity, 'soil_moisture': soil_moisture, 'growth_stage': growth_stage})
                cleaned_rows_count += 1
            else:
                missing_rows_count += 1
                print(f'Missing or invalid data in row: {row}')
        else:
            missing_rows_count += 1
            print(f'Missing required columns in row: {row}')

# Prepare output
output_path = Path('/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_openai_gpt-4o-mini_nvidia_nemotron-3-ultra-550b-a55b_run2')
output_file = output_path / 'evaluate_crop_growth_stage_result.json'
output_data = {
    'task_name': 'Evaluate Crop Growth Stage',
    'description': 'Classify the current growth stage of the crop based on environmental parameters to inform management decisions.',
    'result_summary': results,
    'result_generated_at': '2023-10-01'
}

# Save results to JSON file
with open(output_file, 'w') as outfile:
    json.dump(output_data, outfile, indent=4)

print(f'Results saved to {output_file}')