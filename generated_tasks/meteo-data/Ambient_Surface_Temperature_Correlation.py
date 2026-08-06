"""
Task: Ambient_Surface_Temperature_Correlation
Description: Analyze the correlation between ambient temperature and surface temperature to understand diurnal heating and cooling patterns.
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

DATA_FILE_PATH = os.path.join(_root_dir, "data", "meteo-data", "raw_data.csv")
if not os.path.exists(DATA_FILE_PATH):
    DATA_FILE_PATH = os.path.join(_root_dir, "data", "meteo-data", "raw_data.txt")

METADATA_FILE_PATH = os.path.join(_root_dir, "data", "meteo-data", "metadata.json")
OUTPUT_DIR = os.path.join(_root_dir, "output", "meteo-data")
os.makedirs(OUTPUT_DIR, exist_ok=True)

import os
import csv
import json
from pathlib import Path
import numpy as np

# Resolve the input file path
curr_dir = Path(__file__).resolve().parent
root_dir = curr_dir
while root_dir.name and not (root_dir / 'data').exists():
    parent = root_dir.parent
    if parent == root_dir:
        break
    root_dir = parent

data_file = root_dir / 'data' / 'meteo-data' / 'raw_data.csv'
if not data_file.exists():
    data_file = root_dir / 'data' / 'meteo-data' / 'raw_data.txt'
if not data_file.exists():
    print('Data file not found. Exiting.'); exit(1)

# Initialize lists to hold temperature data
ambient_temps = []
surface_temps = []
dropped_rows = 0

# Read the CSV file
with open(data_file, mode='r') as file:
    reader = csv.DictReader(file)
    for row in reader:
        # Normalize column names
        row = {k.lower(): v for k, v in row.items()}
        # Extract temperatures safely
        try:
            ambient_temp = float(row.get('ambient_temperature', ''))
            surface_temp = float(row.get('surface_temperature', ''))
            if ambient_temp is not None and surface_temp is not None:
                ambient_temps.append(ambient_temp)
                surface_temps.append(surface_temp)
            else:
                dropped_rows += 1
        except ValueError as e:
            print(f'Error converting temperatures: {e}'); dropped_rows += 1

# Calculate correlation if enough data is available
if len(ambient_temps) > 1 and len(surface_temps) > 1:
    correlation = np.corrcoef(ambient_temps, surface_temps)[0, 1]
else:
    correlation = None

# Prepare the result
result = {
    'task_name': 'Ambient_Surface_Temperature_Correlation',
    'description': 'Analyze the correlation between ambient temperature and surface temperature to understand diurnal heating and cooling patterns.',
    'result_summary': [
        {'correlation': correlation},
        {'dropped_rows': dropped_rows}
    ],
    'result_generated_at': '2023-10-01T00:00:00Z'
}

# Save the result
output_path = Path(OUTPUT_DIR)
output_path.mkdir(parents=True, exist_ok=True)
output_file = output_path / 'Ambient_Surface_Temperature_Correlation_result.json'
with open(output_file, 'w') as outfile:
    json.dump(result, outfile, indent=4)
print(f'Results saved to {output_file}')