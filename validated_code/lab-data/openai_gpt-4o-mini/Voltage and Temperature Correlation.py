"""
Task: Voltage and Temperature Correlation
Description: Examine the correlation between battery voltage levels and temperature readings to assess sensor health and performance.
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
import statistics

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

voltage_readings = []
temperature_readings = []
dropped_rows = 0

with open(data_file, 'r') as file:
    reader = csv.DictReader(file)
    for row in reader:
        row = {k.lower(): v for k, v in row.items()}
        try:
            voltage = float(row.get('voltage', ''))
            temperature = float(row.get('temperature', ''))
            if voltage is not None and temperature is not None:
                voltage_readings.append(voltage)
                temperature_readings.append(temperature)
            else:
                dropped_rows += 1
        except ValueError as e:
            print(f"Invalid data encountered: {e}")
            dropped_rows += 1

if len(voltage_readings) == 0 or len(temperature_readings) == 0:
    print("No valid readings to analyze.")
    exit(1)

correlation = statistics.correlation(voltage_readings, temperature_readings)

output_path = Path(OUTPUT_DIR)
output_path.mkdir(parents=True, exist_ok=True)
result = {
    "task_name": "Voltage and Temperature Correlation",
    "description": "Examine the correlation between battery voltage levels and temperature readings to assess sensor health and performance.",
    "result_summary": [
        {"correlation": correlation, "dropped_rows": dropped_rows}
    ],
    "result_generated_at": "2023-10-01T12:00:00Z"
}

with open(output_path / "voltage_and_temperature_correlation_result.json", 'w') as outfile:
    json.dump(result, outfile)