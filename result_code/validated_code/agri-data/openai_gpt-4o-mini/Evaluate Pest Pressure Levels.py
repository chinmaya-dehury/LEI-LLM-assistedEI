import re
"""
Task: Evaluate Pest Pressure Levels
Description: Assess the level of pest pressure and its potential impact on crop yield.
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
pest_pressure_levels = []
dropped_rows = 0

# Read the data
with open(data_file, mode='r') as file:
    reader = csv.DictReader(file)
    for row in reader:
        # Normalize column names
        row = {k.lower(): v for k, v in row.items()}
        # Check for required columns
        if 'pest_pressure' not in row:
            print('Missing column: pest_pressure. Skipping row.'); dropped_rows += 1; continue
        # Handle missing or invalid data
        try:
            pest_pressure = float(row['pest_pressure']) if row['pest_pressure'] not in ['', 'NA', 'N/A', 'None'] else None
            if pest_pressure is not None:
                pest_pressure_levels.append(pest_pressure)
        except ValueError:
            print(f'Invalid pest pressure value: {row.get('pest_pressure')}. Skipping row.'); dropped_rows += 1

# Prepare results
result_summary = {
    'average_pest_pressure': sum(pest_pressure_levels) / len(pest_pressure_levels) if pest_pressure_levels else None,
    'total_dropped_rows': dropped_rows
}

# Output results
output_path = Path('/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_openai_gpt-4o-mini_google_gemini-3.1-flash-lite_run2') / 'Evaluate_Pest_Pressure_Levels_result.json'
result = {
    'task_name': 'Evaluate Pest Pressure Levels',
    'description': 'Assess the level of pest pressure and its potential impact on crop yield.',
    'result_summary': result_summary,
    'result_generated_at': '2023-10-01'
}
with open(output_path, 'w') as outfile:
    json.dump(result, outfile)
print(f'Results saved to {output_path}')