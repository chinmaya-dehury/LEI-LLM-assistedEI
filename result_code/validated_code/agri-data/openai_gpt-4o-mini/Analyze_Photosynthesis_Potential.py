"""
Task: Analyze_Photosynthesis_Potential
Description: Estimate the Photosynthesis Potential (PP) based on sunlight exposure, CO2 concentration, and temperature to understand crop growth potential.
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

with open(data_file, mode='r') as file:
    reader = csv.DictReader(file)
    for row in reader:
        row = {k.lower(): v for k, v in row.items()}
        try:
            sunlight_exposure = float(row.get('sunlight_exposure', ''))
            co2_concentration = float(row.get('co2_concentration', ''))
            temperature = float(row.get('temperature', ''))
            if sunlight_exposure is None or co2_concentration is None or temperature is None:
                raise ValueError('Missing values')
            pp = (sunlight_exposure * co2_concentration * temperature) / 1000  # Example formula
            result_summary.append(pp)
            cleaned_rows_count += 1
        except (ValueError, TypeError) as e:
            print(f'Row skipped due to error: {e}')
            missing_rows_count += 1

output_path = '/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_openai_gpt-4o-mini_nvidia_nemotron-3-ultra-550b-a55b_run1'
output_file = os.path.join(output_path, 'Analyze_Photosynthesis_Potential_result.json')

result = {
    'task_name': 'Analyze_Photosynthesis_Potential',
    'description': 'Estimate the Photosynthesis Potential (PP) based on sunlight exposure, CO2 concentration, and temperature to understand crop growth potential.',
    'result_summary': result_summary,
    'result_generated_at': '2023-10-01'
}

with open(output_file, 'w') as outfile:
    json.dump(result, outfile)

print(f'Results saved to {output_file}')