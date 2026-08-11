"""
Task: Evaluate_Crop_Health_Classification
Description: Classify crop health based on soil conditions (NPK, moisture) and environmental parameters (temperature, humidity) to predict crop performance.
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

# Read and process the data
result_summary = []
cleaned_rows_count = 0
with open(data_file, 'r') as file:
    reader = csv.DictReader(file)
    for row in reader:
        row = {k.lower(): v for k, v in row.items()}
        # Handle missing values
        n = row.get('n')
        p = row.get('p')
        k = row.get('k')
        temperature = safe_float(row.get('temperature'))
        humidity = safe_float(row.get('humidity'))
        soil_moisture = safe_float(row.get('soil_moisture'))
        label = row.get('label')

        if n is None or p is None or k is None or temperature is None or humidity is None or soil_moisture is None:
            print(f'Dropped row due to missing values: {row}')
            continue

        # Simple classification logic (example)
        if temperature > 25 and humidity > 80 and soil_moisture > 40:
            health_status = 'Healthy'
        else:
            health_status = 'Unhealthy'

        result_summary.append({
            'n': n,
            'p': p,
            'k': k,
            'temperature': temperature,
            'humidity': humidity,
            'soil_moisture': soil_moisture,
            'label': label,
            'health_status': health_status
        })
        cleaned_rows_count += 1

# Prepare output
output_path = '/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_openai_gpt-4o-mini_nvidia_nemotron-3-ultra-550b-a55b_run1'
output_file = os.path.join(output_path, 'Evaluate_Crop_Health_Classification_result.json')
result = {
    'task_name': 'Evaluate_Crop_Health_Classification',
    'description': 'Classify crop health based on soil conditions and environmental parameters.',
    'result_summary': result_summary,
    'result_generated_at': '2023-10-01'
}

# Save results to JSON file
with open(output_file, 'w') as outfile:
    json.dump(result, outfile, indent=4)

print(f'Results saved to {output_file}. Total cleaned rows: {cleaned_rows_count}')