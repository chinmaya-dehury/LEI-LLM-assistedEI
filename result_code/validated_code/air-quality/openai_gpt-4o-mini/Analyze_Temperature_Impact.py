"""
Task: Analyze_Temperature_Impact
Description: Analyze the impact of temperature variations on the sensor readings to identify potential cross-sensitivities affecting air quality measurements.
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

results = []
cleaned_rows_count = 0
missing_rows_count = 0

# Function to safely convert to float
def safe_float(value):
    try:
        return float(value)
    except ValueError:
        return None

with open(data_file, 'r') as file:
    reader = csv.DictReader(file)
    for row in reader:
        row = {k.lower(): v for k, v in row.items()}
        temperature = safe_float(row.get('t'))
        co = safe_float(row.get('co(gt)'))
        if temperature is None or co is None:
            missing_rows_count += 1
            continue
        results.append({'temperature': temperature, 'co': co})
        cleaned_rows_count += 1

# Analyze the impact of temperature on CO readings
if results:
    avg_temp = sum(r['temperature'] for r in results) / len(results)
    avg_co = sum(r['co'] for r in results) / len(results)
    result_summary = {'average_temperature': avg_temp, 'average_co': avg_co, 'cleaned_rows': cleaned_rows_count, 'missing_rows': missing_rows_count}
else:
    result_summary = {'error': 'No valid data to analyze', 'missing_rows': missing_rows_count}

# Save results
output_path = '/home/dcc/LEI-Models-Comparision/output/air-quality/air-quality_openai_gpt-4o-mini_nvidia_nemotron-3-ultra-550b-a55b_run1'
output_file = os.path.join(output_path, 'Analyze_Temperature_Impact_result.json')
with open(output_file, 'w') as outfile:
    json.dump({'task_name': 'Analyze_Temperature_Impact', 'description': 'Analyze the impact of temperature variations on the sensor readings to identify potential cross-sensitivities affecting air quality measurements.', 'result_summary': result_summary, 'result_generated_at': '2023-10-01T00:00:00'}, outfile)
print(f'Results saved to {output_file}')