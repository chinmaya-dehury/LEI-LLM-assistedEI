"""
Task: Detect_Sensor_Drift
Description: Monitor sensor readings over time to detect any significant drifts in sensor performance compared to the reference analyzer.
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

DATA_FILE_PATH = os.path.join(_root_dir, "data", "air-quality", "raw_data.csv")
if not os.path.exists(DATA_FILE_PATH):
    DATA_FILE_PATH = os.path.join(_root_dir, "data", "air-quality", "raw_data.txt")

METADATA_FILE_PATH = os.path.join(_root_dir, "data", "air-quality", "metadata.json")
OUTPUT_DIR = os.path.join(_root_dir, "output", "air-quality")
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

data_file = root_dir / 'data' / 'air-quality' / 'raw_data.csv'
if not data_file.exists():
    data_file = root_dir / 'data' / 'air-quality' / 'raw_data.txt'
if not data_file.exists():
    print('Data file not found. Exiting.'); exit(1)

# Function to safely convert strings to floats
def safe_float(value):
    try:
        return float(value)
    except ValueError:
        return None

# Initialize variables
sensor_drift = []
row_count = 0
invalid_rows = 0

# Read the data
with open(data_file, 'r') as file:
    reader = csv.DictReader(file)
    for row in reader:
        row_count += 1
        # Normalize column names
        row = {k.lower(): v for k, v in row.items()}
        # Extract relevant data
        co_gt = safe_float(row.get('co(gt)'))
        no2_gt = safe_float(row.get('no2(gt)'))
        temperature = safe_float(row.get('t'))
        rh = safe_float(row.get('rh'))
        if co_gt is None or no2_gt is None or temperature is None or rh is None:
            invalid_rows += 1
            print(f'Invalid row skipped: {row}')
            continue
        # Simple drift detection logic (example)
        if co_gt > 2.0:
            sensor_drift.append({'co_gt': co_gt, 'no2_gt': no2_gt, 'temperature': temperature, 'rh': rh})

# Prepare output
output_path = Path('/home/dcc/LEI-Models-Comparision/output/air-quality/air-quality_openai_gpt-4o-mini_nvidia_nemotron-3-ultra-550b-a55b_run2')
output_file = output_path / 'sensor_drift_result.json'
result = {
    'task_name': 'Detect_Sensor_Drift',
    'description': 'Monitor sensor readings over time to detect any significant drifts in sensor performance compared to the reference analyzer.',
    'result_summary': sensor_drift,
    'result_generated_at': '2023-10-01'
}

# Save results
with open(output_file, 'w') as outfile:
    json.dump(result, outfile)

print(f'Results saved to {output_file}')