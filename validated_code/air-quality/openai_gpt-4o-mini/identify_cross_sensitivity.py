"""
Task: Identify_Cross_Sensitivity
Description: Analyze the relationship between different gas concentrations (e.g., CO and NOx) to identify potential cross-sensitivity of sensors.
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

results = []
cleaned_rows = 0
invalid_rows = 0

with open(data_file, 'r') as file:
    reader = csv.DictReader(file)
    for row in reader:
        row = {k.lower(): v for k, v in row.items()}
        co = safe_float(row.get('co(gt)', ''))
        nox = safe_float(row.get('nox(gt)', ''))
        if co is None or nox is None:
            invalid_rows += 1
            continue
        results.append({'co': co, 'nox': nox})
        cleaned_rows += 1

# Analyze cross-sensitivity
if results:
    co_values = [r['co'] for r in results]
    nox_values = [r['nox'] for r in results]
    correlation = sum((x - sum(co_values)/len(co_values)) * (y - sum(nox_values)/len(nox_values)) for x, y in zip(co_values, nox_values)) / (len(co_values) - 1)
    output = {
        'task_name': 'Identify_Cross_Sensitivity',
        'description': 'Analyze the relationship between different gas concentrations (e.g., CO and NOx) to identify potential cross-sensitivity of sensors.',
        'result_summary': [{'correlation': correlation}],
        'result_generated_at': '2023-10-01'
    }
else:
    output = {
        'task_name': 'Identify_Cross_Sensitivity',
        'description': 'Analyze the relationship between different gas concentrations (e.g., CO and NOx) to identify potential cross-sensitivity of sensors.',
        'result_summary': [],
        'result_generated_at': '2023-10-01'
    }

# Save results
output_path = Path(OUTPUT_DIR) / 'Identify_Cross_Sensitivity_result.json'
output_path.parent.mkdir(parents=True, exist_ok=True)
with open(output_path, 'w') as outfile:
    json.dump(output, outfile)

print(f'Results saved to {output_path}')