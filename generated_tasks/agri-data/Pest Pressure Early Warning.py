from datetime import datetime
"""
Task: Pest Pressure Early Warning
Description: Detect early signs of pest pressure using a threshold-based alert system for the Pest_Pressure index.
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

def load_data(file_path):
    rows = []
    with open(file_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Normalize column names to lowercase
            row = {k.lower(): v for k, v in row.items()}
            rows.append(row)
    return rows

def detect_pest_pressure(rows, threshold=10):
    alerts = []
    dropped_rows = 0
    for i, row in enumerate(rows):
        try:
            pressure = float(row.get('pest_pressure', '').replace(',', ''))
        except (ValueError, TypeError):
            print(f'Row {i+1}: Invalid or missing Pest_Pressure value -> Skipping')
            dropped_rows += 1
            continue
        if pressure >= threshold:
            alerts.append({
                'row_index': i + 1,
                'pest_pressure': pressure,
                'timestamp': None  # Assuming timestamp is not provided in the sample data
            })
    return alerts, dropped_rows

if __name__ == '__main__':
    # Resolve project root to find the input file dynamically
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / 'data').exists():
        root_dir = root_dir.parent
    if root_dir == curr_dir:
        raise FileNotFoundError('Data directory not found under project root.')
    data_file_csv = root_dir / 'data' / 'agri-data' / 'raw_data.csv'
    data_file_txt = root_dir / 'data' / 'agri-data' / 'raw_data.txt'
    input_path = data_file_csv if data_file_csv.exists() else data_file_txt
    if not input_path.exists():
        raise FileNotFoundError('Input file does not exist.')
    rows = load_data(input_path)
    alerts, dropped_rows = detect_pest_pressure(rows)
    output_dir = Path('output') / 'agri-data'
    os.makedirs(output_dir, exist_ok=True)
    result_file = output_dir / f'Pest_Pressure_Early_Warning_result.json'
    import json
    result = {
        "task_name": "Pest Pressure Early Warning",
        "description": "Detect early signs of pest pressure using a threshold-based alert system for the Pest_Pressure index.",
        "result_summary": {
            "alerts": alerts,
            "dropped_rows_due_to_invalid_data": dropped_rows
        },
        "generated_at": f"{__import__('datetime').datetime.now():%Y-%m-%d %H:%M:%S}"
    }
    with open(result_file, 'w') as f:
        json.dump(result, f, indent=2)