"""
Task: MonitorIrrigationFrequency
Description: Track the frequency of irrigation to optimize water usage and assess its impact on crop growth.
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

# Initialize variables
irrigation_frequency = []
cleaned_rows_count = 0
missing_rows_count = 0

# Read the CSV file
with open(data_file, mode='r') as file:
    reader = csv.DictReader(file)
    for row in reader:
        row = {k.lower(): v for k, v in row.items()}
        try:
            if 'irrigation_frequency' in row:
                freq = int(row['irrigation_frequency'])
                irrigation_frequency.append(freq)
                cleaned_rows_count += 1
            else:
                print('Missing column: irrigation_frequency. Skipping row.')
                missing_rows_count += 1
        except ValueError as e:
            print(f'Invalid value for irrigation_frequency: {row.get("irrigation_frequency", "N/A")} - {e}')
            missing_rows_count += 1

# Prepare results
result_summary = {
    'total_rows': cleaned_rows_count + missing_rows_count,
    'cleaned_rows': cleaned_rows_count,
    'missing_rows': missing_rows_count,
    'irrigation_frequency_data': irrigation_frequency
}

# Output path
output_path = '/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_openai_gpt-4o-mini_google_gemini-3.1-flash-lite_run1'
output_file = os.path.join(output_path, 'MonitorIrrigationFrequency_result.json')

# Save results to JSON
with open(output_file, 'w') as json_file:
    json.dump({
        'task_name': 'MonitorIrrigationFrequency',
        'description': 'Track the frequency of irrigation to optimize water usage and assess its impact on crop growth.',
        'result_summary': result_summary,
        'result_generated_at': '2023-10-01'
    }, json_file, indent=4)

print(f'Results saved to {output_file}')