"""
Task: Daily_Solar_Radiation_Average
Description: Calculate the daily average solar radiation to assess exposure cycles and potential cloud cover impact.
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
from pathlib import Path
import csv
import json
from collections import defaultdict

# Resolve the input file path
curr_dir = Path(__file__).resolve().parent
root_dir = curr_dir
while root_dir.name and not (root_dir / "data").exists():
    parent = root_dir.parent
    if parent == root_dir:
        break
    root_dir = parent

data_file = root_dir / "data" / "meteo-data" / "raw_data.csv"
if not data_file.exists():
    data_file = root_dir / "data" / "meteo-data" / "raw_data.txt"
if not data_file.exists():
    print("Data file not found.")
    exit(1)

# Function to safely convert strings to floats
def safe_float(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

# Read the data and calculate daily average solar radiation
solar_radiation = defaultdict(list)
cleaned_rows = 0
invalid_rows = 0

with open(data_file, 'r') as file:
    reader = csv.DictReader(file)
    for row in reader:
        row = {k.lower(): v for k, v in row.items()}
        try:
            date_key = f"{row.get('year')}-{row.get('month')}-{row.get('day')}"
            solar_value = safe_float(row.get('solar_radiation'))
            if solar_value is not None:
                solar_radiation[date_key].append(solar_value)
                cleaned_rows += 1
            else:
                invalid_rows += 1
        except Exception as e:
            print(f"Error processing row: {e}")
            invalid_rows += 1

# Calculate daily averages
daily_averages = {date: sum(values) / len(values) for date, values in solar_radiation.items() if values}

# Prepare the result
result = {
    "task_name": "Daily_Solar_Radiation_Average",
    "description": "Calculate the daily average solar radiation to assess exposure cycles and potential cloud cover impact.",
    "result_summary": daily_averages,
    "result_generated_at": "2023-10-01T00:00:00Z"
}

# Save the result
output_path = Path(OUTPUT_DIR)
output_path.mkdir(parents=True, exist_ok=True)
output_file = output_path / "daily_solar_radiation_average_result.json"
with open(output_file, 'w') as outfile:
    json.dump(result, outfile)

print(f"Processed {cleaned_rows} rows, dropped {invalid_rows} invalid rows.")