import re
"""
Task: Analyze Irrigation Frequency
Description: Evaluate the frequency of irrigation to optimize water usage based on crop needs and soil moisture.
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
irrigation_frequency = []
soil_moisture = []
cleaned_rows = 0
invalid_rows = 0

# Read the CSV file
with data_file.open('r') as file:
    reader = csv.DictReader(file)
    for row in reader:
        # Normalize column names
        row = {k.lower(): v for k, v in row.items()}
        try:
            # Handle missing or invalid data
            if 'irrigation_frequency' in row and 'soil_moisture' in row:
                irrigation_freq = int(row['irrigation_frequency']) if row['irrigation_frequency'] not in ['', 'NA', 'N/A', 'None'] else None
                soil_moist = float(row['soil_moisture']) if row['soil_moisture'] not in ['', 'NA', 'N/A', 'None'] else None
                if irrigation_freq is not None and soil_moist is not None:
                    irrigation_frequency.append(irrigation_freq)
                    soil_moisture.append(soil_moist)
                    cleaned_rows += 1
                else:
                    invalid_rows += 1
            else:
                print('Missing required columns in row. Skipping.'); invalid_rows += 1
        except ValueError as e:
            print(f'Value error: {e}. Skipping row.'); invalid_rows += 1

# Prepare results
result_summary = {
    'average_irrigation_frequency': sum(irrigation_frequency) / len(irrigation_frequency) if irrigation_frequency else None,
    'average_soil_moisture': sum(soil_moisture) / len(soil_moisture) if soil_moisture else None,
    'cleaned_rows': cleaned_rows,
    'invalid_rows': invalid_rows
}

# Save results
output_path = Path(OUTPUT_DIR)
output_path.mkdir(parents=True, exist_ok=True)
result = {
    'task_name': 'Analyze Irrigation Frequency',
    'description': 'Evaluate the frequency of irrigation to optimize water usage based on crop needs and soil moisture.',
    'result_summary': result_summary,
    'result_generated_at': '2023-10-01'
}
with open(output_path / 'analyze_irrigation_frequency_result.json', 'w') as outfile:
    json.dump(result, outfile, indent=4)
print('Results saved successfully.')