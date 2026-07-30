from datetime import datetime
"""
Task: Environmental Stress Index Calculation
Description: Compute the Temperature-Humidity Index (THI) from ambient temperature and humidity to assess crop stress conditions.
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

import csv
from pathlib import Path
import os

def compute_thi(input_file):
    thi_values = []
    dropped_rows = 0
    with open(input_file, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Normalize column names to lowercase
            row = {k.lower(): v for k, v in row.items()}
            temp = row.get('temperature')
            hum = row.get('humidity')
            if temp is None or hum is None:
                dropped_rows += 1
                continue
            try:
                temperature = float(temp)
                humidity = float(hum)
            except ValueError:
                dropped_rows += 1
                continue
            thi = temperature + 0.55 * (5.29 * humidity - 158.67)
            thi_values.append(thi)
    return thi_values, dropped_rows

def resolve_data_path():
    # Find the project root containing 'data'
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while True:
        if (root_dir / "data").exists():
            break
        parent = root_dir.parent
        if parent == root_dir:
            raise FileNotFoundError('Data directory not found in project hierarchy.')
        root_dir = parent
    # Determine the correct raw data file
    csv_path = root_dir / "data" / "agri-data" / "raw_data.csv"
    txt_path = root_dir / "data" / "agri-data" / "raw_data.txt"
    if not csv_path.exists() and not txt_path.exists():
        raise FileNotFoundError('Neither raw_data.csv nor raw_data.txt found under data/agri-data.')
    return csv_path if csv_path.exists() else txt_path

if __name__ == "__main__":
    input_file = resolve_data_path()
    thi_values, dropped_rows = compute_thi(input_file)
    # Prepare JSON output
    result_summary = {
        "THI_values": thi_values,
        "dropped_rows_count": dropped_rows,
        "generated_at": f"{__import__('datetime').datetime.now():%Y-%m-%d %H:%M:%S}"
    }
    # Construct output path
    output_dir = Path("output") / "agri-data"
    os.makedirs(output_dir, exist_ok=True)
    output_path = output_dir / f"environmental_stress_index_result.json"
    with open(output_path, 'w') as outfile:
        import json
        json.dump(result_summary, outfile, indent=2)