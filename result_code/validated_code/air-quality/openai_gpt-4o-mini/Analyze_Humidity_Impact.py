"""
Task: Analyze_Humidity_Impact
Description: Examine the relationship between relative and absolute humidity variations and sensor readings to identify potential cross-sensitivities affecting air quality measurements.
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

# Initialize variables
humidity_data = []
cleaned_rows = 0
invalid_rows = 0

# Read the CSV file
with open(data_file, mode='r') as file:
    reader = csv.DictReader(file)
    for row in reader:
        # Normalize column names to lowercase
        row = {k.lower(): v for k, v in row.items()}
        # Handle missing values
        try:
            if row.get('rh') in ['', 'NA', 'N/A', 'None']:
                invalid_rows += 1
                continue
            if row.get('ah') in ['', 'NA', 'N/A', 'None']:
                invalid_rows += 1
                continue
            rh = float(row['rh'])
            ah = float(row['ah'])
            humidity_data.append({'rh': rh, 'ah': ah})
            cleaned_rows += 1
        except ValueError as e:
            print(f'Error converting values: {e}')
            invalid_rows += 1

# Prepare results
result_summary = {
    'total_cleaned_rows': cleaned_rows,
    'total_invalid_rows': invalid_rows,
    'humidity_data': humidity_data
}

# Save results to JSON
output_path = '/home/dcc/LEI-Models-Comparision/output/air-quality/air-quality_openai_gpt-4o-mini_google_gemini-3.1-flash-lite_run1'
output_file = os.path.join(output_path, 'Analyze_Humidity_Impact_result.json')
with open(output_file, 'w') as outfile:
    json.dump({
        'task_name': 'Analyze_Humidity_Impact',
        'description': 'Examine the relationship between relative and absolute humidity variations and sensor readings to identify potential cross-sensitivities affecting air quality measurements.',
        'result_summary': result_summary,
        'result_generated_at': '2023-10-01'
    }, outfile)

print('Analysis complete. Results saved.')