"""
Task: Comparative Mote Calibration
Description: Perform a comparative analysis of temperature and humidity readings across multiple motes to validate sensor calibration.
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
while root_dir.name and not (root_dir / "data").exists():
    parent = root_dir.parent
    if parent == root_dir:
        break
    root_dir = parent

data_file = root_dir / "data" / "lab-data" / "raw_data.csv"
if not data_file.exists():
    data_file = root_dir / "data" / "lab-data" / "raw_data.txt"
if not data_file.exists():
    print("Data file not found.")
    exit(1)

# Initialize variables for analysis
mote_data = {}
rows_dropped = 0

# Read the data
with open(data_file, mode='r') as file:
    reader = csv.DictReader(file)
    for row in reader:
        # Normalize column names
        row = {k.lower(): v for k, v in row.items()}
        # Handle missing values
        if row.get('temperature') in ['', 'NA', 'N/A', 'None']:
            rows_dropped += 1
            continue
        if row.get('humidity') in ['', 'NA', 'N/A', 'None']:
            rows_dropped += 1
            continue
        try:
            mote_id = int(row['moteid'])
            temperature = float(row['temperature'])
            humidity = float(row['humidity'])
        except ValueError as e:
            print(f"Error converting data for mote {row.get('moteid')}: {e}")
            rows_dropped += 1
            continue
        # Store data by mote
        if mote_id not in mote_data:
            mote_data[mote_id] = {'temperature': [], 'humidity': []}
        mote_data[mote_id]['temperature'].append(temperature)
        mote_data[mote_id]['humidity'].append(humidity)

# Prepare results
result_summary = []
for mote_id, data in mote_data.items():
    avg_temp = sum(data['temperature']) / len(data['temperature']) if data['temperature'] else None
    avg_hum = sum(data['humidity']) / len(data['humidity']) if data['humidity'] else None
    result_summary.append({"mote_id": mote_id, "avg_temperature": avg_temp, "avg_humidity": avg_hum})

# Output results
output_path = "/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_openai_gpt-4o-mini_nvidia_nemotron-3-ultra-550b-a55b_run1"
output_file = os.path.join(output_path, "comparative_mote_calibration_result.json")
result = {
    "task_name": "Comparative Mote Calibration",
    "description": "Perform a comparative analysis of temperature and humidity readings across multiple motes to validate sensor calibration.",
    "result_summary": result_summary,
    "result_generated_at": "2023-10-01"
}

with open(output_file, 'w') as f:
    json.dump(result, f, indent=4)

print(f"Analysis complete. Rows dropped: {rows_dropped}. Results saved to {output_file}.")