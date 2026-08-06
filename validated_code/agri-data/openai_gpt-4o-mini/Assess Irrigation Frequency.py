"""
Task: Assess Irrigation Frequency
Description: Monitor the frequency of irrigation to optimize water usage and ensure adequate moisture for crop growth.
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

# Initialize variables
irrigation_frequency_count = 0
cleaned_rows_count = 0

# Read the CSV file
with open(data_file, mode='r') as file:
    reader = csv.DictReader(file)
    for row in reader:
        row = {k.lower(): v for k, v in row.items()}
        try:
            irrigation_frequency = int(row.get('irrigation_frequency', None))
            if irrigation_frequency is not None:
                irrigation_frequency_count += irrigation_frequency
                cleaned_rows_count += 1
            else:
                print(f'Row skipped due to missing irrigation_frequency: {row}')  
        except ValueError:
            print(f'Invalid irrigation_frequency value: {row.get('irrigation_frequency')} in row {row}')

# Prepare results
result_summary = {
    'total_irrigation_frequency': irrigation_frequency_count,
    'cleaned_rows_count': cleaned_rows_count
}

# Save results
output_path = Path(OUTPUT_DIR)
output_path.mkdir(parents=True, exist_ok=True)
result = {
    'task_name': 'Assess Irrigation Frequency',
    'description': 'Monitor the frequency of irrigation to optimize water usage and ensure adequate moisture for crop growth.',
    'result_summary': result_summary,
    'result_generated_at': '2023-10-01'
}
with open(output_path / 'assess_irrigation_frequency_result.json', 'w') as outfile:
    json.dump(result, outfile)
print('Results saved successfully.')