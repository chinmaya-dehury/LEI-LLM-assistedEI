"""
Task: Humidity Variation Detection
Description: Monitor and detect variations in humidity levels across different motes to assess environmental stability and identify potential anomalies.
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

DATA_FILE_PATH = os.path.join(_root_dir, "data", "lab-data", "raw_data.csv")
if not os.path.exists(DATA_FILE_PATH):
    DATA_FILE_PATH = os.path.join(_root_dir, "data", "lab-data", "raw_data.txt")

METADATA_FILE_PATH = os.path.join(_root_dir, "data", "lab-data", "metadata.json")
OUTPUT_DIR = os.path.join(_root_dir, "output", "lab-data")
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

data_file = root_dir / 'data' / 'lab-data' / 'raw_data.csv'
if not data_file.exists():
    data_file = root_dir / 'data' / 'lab-data' / 'raw_data.txt'
if not data_file.exists():
    print('Data file not found. Exiting.'); exit(1)

# Initialize variables
humidity_data = {}
cleaned_rows = 0
invalid_rows = 0

# Read the CSV file
with open(data_file, mode='r') as file:
    reader = csv.DictReader(file)
    for row in reader:
        # Normalize column names
        row = {k.lower(): v for k, v in row.items()}
        # Handle missing humidity values
        humidity = row.get('humidity', '').strip()
        if humidity in ['', 'na', 'n/a', 'None']:
            invalid_rows += 1
            continue
        try:
            humidity = float(humidity)
        except ValueError:
            print(f'Invalid humidity value: {humidity}');
            invalid_rows += 1
            continue
        moteid = row.get('moteid')
        if moteid:
            if moteid not in humidity_data:
                humidity_data[moteid] = []
            humidity_data[moteid].append(humidity)
            cleaned_rows += 1

# Analyze humidity variations
humidity_variations = {moteid: {'mean': sum(values) / len(values), 'count': len(values)} for moteid, values in humidity_data.items()}

# Prepare output
output_path = Path(OUTPUT_DIR)
output_path.mkdir(parents=True, exist_ok=True)
result = {
    'task_name': 'Humidity Variation Detection',
    'description': 'Monitor and detect variations in humidity levels across different motes to assess environmental stability and identify potential anomalies.',
    'result_summary': humidity_variations,
    'result_generated_at': '2023-10-01'
}

# Save results to JSON
output_file = output_path / 'humidity_variation_detection_result.json'
with open(output_file, 'w') as outfile:
    json.dump(result, outfile, indent=4)

print(f'Results saved to {output_file}')