"""
Task: Analyze Irrigation Frequency
Description: Evaluate the frequency of irrigation and its correlation with soil moisture and crop health.
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

# Helper function to safely convert to float
def safe_float(value):
    try:
        return float(value)
    except ValueError:
        return None

with open(data_file, 'r') as file:
    reader = csv.DictReader(file)
    for row in reader:
        row = {k.lower(): v for k, v in row.items()}
        irrigation_frequency = row.get('irrigation_frequency')
        soil_moisture = row.get('soil_moisture')
        label = row.get('label')

        # Handle missing values
        if irrigation_frequency in ['', 'NA', 'N/A', 'None']:
            missing_rows_count += 1
            continue
        if soil_moisture in ['', 'NA', 'N/A', 'None']:
            missing_rows_count += 1
            continue

        # Convert to float
        irrigation_frequency = safe_float(irrigation_frequency)
        soil_moisture = safe_float(soil_moisture)

        if irrigation_frequency is None or soil_moisture is None:
            missing_rows_count += 1
            continue

        # Collect results
        result_summary.append({
            'irrigation_frequency': irrigation_frequency,
            'soil_moisture': soil_moisture,
            'label': label
        })
        cleaned_rows_count += 1

# Prepare output
output_path = Path('/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_openai_gpt-4o-mini_google_gemini-3.1-flash-lite_run2')
output_file = output_path / 'analyze_irrigation_frequency_result.json'

# Ensure output directory exists
output_path.mkdir(parents=True, exist_ok=True)

result = {
    'task_name': 'Analyze Irrigation Frequency',
    'description': 'Evaluate the frequency of irrigation and its correlation with soil moisture and crop health.',
    'result_summary': result_summary,
    'result_generated_at': '2023-10-01'
}

# Save results to JSON file
with open(output_file, 'w') as f:
    json.dump(result, f, indent=4)

print(f'Results saved to {output_file}')