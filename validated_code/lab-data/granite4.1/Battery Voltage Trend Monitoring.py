from datetime import datetime
"""
Task: Battery Voltage Trend Monitoring
Description: Track voltage changes over time and flag motes where voltage drops below a predefined threshold indicating potential battery depletion.
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

import csv
from pathlib import Path
import os

def safe_float(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

def resolve_data_path():
    script_dir = Path(__file__).resolve().parent
    root_dir = script_dir
    while root_dir.name and not (root_dir / "data").exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent
    data_file_csv = root_dir / "data" / "lab-data" / "raw_data.csv"
    data_file_txt = root_dir / "data" / "lab-data" / "raw_data.txt"
    if data_file_csv.exists():
        return data_file_csv
    elif data_file_txt.exists():
        return data_file_txt
    else:
        raise FileNotFoundError("Data file not found under data/lab-data/.")

def process_voltage_data(threshold=2.1):
    data_path = resolve_data_path()
    dropped_rows = 0
    voltage_readings = []
    with open(data_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Normalize column names to lowercase
            row_lower = {k.lower(): v for k, v in row.items()}
            if 'voltage' not in row_lower:
                continue  # Skip rows missing voltage column
            voltage = safe_float(row_lower['voltage'])
            if voltage is None:
                dropped_rows += 1
                continue
            mote_id = int(row_lower.get('moteid', -1))
            timestamp = row_lower.get('time')
            date = row_lower.get('date')
            epoch = int(row_lower.get('epoch', -1))
            voltage_readings.append({
                'mote_id': mote_id,
                'timestamp': timestamp,
                'date': date,
                'epoch': epoch,
                'voltage': voltage
            })
    print(f"Total rows dropped due to missing/invalid voltage: {dropped_rows}")
    return voltage_readings

def flag_low_voltage(voltage_readings, threshold=2.1):
    flagged = []
    for reading in voltage_readings:
        if reading['voltage'] < threshold:
            flagged.append({
                'mote_id': reading['mote_id'],
                'timestamp': reading['timestamp'],
                'date': reading['date'],
                'epoch': reading['epoch'],
                'voltage': reading['voltage']
            })
    return flagged

if __name__ == "__main__":
    voltage_data = process_voltage_data()
    low_voltage_flags = flag_low_voltage(voltage_data, threshold=2.1)
    import json
    output_path = Path("output") / "lab-data" / f"battery_voltage_trend_{int(2.1*100)}.json"
    os.makedirs(output_path.parent, exist_ok=True)
    with open(output_path, 'w') as outfile:
        json.dump({
            "task_name": "Battery Voltage Trend Monitoring",
            "description": "Track voltage changes over time and flag motes where voltage drops below a predefined threshold indicating potential battery depletion.",
            "result_summary": low_voltage_flags,
            "result_generated_at": f"{__import__('datetime').datetime.now():%Y-%m-%d %H:%M:%S}"
        }, outfile, indent=2)