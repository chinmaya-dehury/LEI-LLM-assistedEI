from datetime import datetime
"""
Task: Temperature-Humidity Comfort Index Calculation
Description: Compute a lightweight thermal comfort score for each mote by applying a fixed-weight combination of normalized temperature and humidity values within a sliding window.
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
import json
import os
import sys
from pathlib import Path
from collections import defaultdict
import math

def safe_float(value):
    if value is None:
        return None
    value = str(value).strip()
    if value in ('', 'NA', 'N/A', 'None', 'None'):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

def normalize_value(val, min_val, max_val):
    if val is None or min_val == max_val:
        return None
    return (val - min_val) / (max_val - min_val)

def compute_comfort_index(temp_norm, humid_norm, w_temp=0.6, w_humid=0.4):
    if temp_norm is None or humid_norm is None:
        return None
    raw = w_temp * temp_norm + w_humid * humid_norm
    return round(raw, 4)

def main():
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
        print("ERROR: No input data file found.")
        sys.exit(1)

    output_dir = Path("/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_qwen_qwen3.7-flash_google_gemini-3.1-flash-lite_run1")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "Temperature-Humidity Comfort Index Calculation_result.json"

    WINDOW_SIZE = 10
    W_TEMP = 0.6
    W_HUMID = 0.4
    TEMP_MIN, TEMP_MAX = 0.0, 50.0
    HUMID_MIN, HUMID_MAX = 0.0, 100.0

    mote_readings = defaultdict(list)
    dropped_rows = 0
    total_rows = 0

    try:
        with open(data_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                total_rows += 1
                row_lower = {k.lower(): v for k, v in row.items()}

                mote_id = row_lower.get('moteid', '').strip()
                if not mote_id:
                    dropped_rows += 1
                    continue

                temp = safe_float(row_lower.get('temperature'))
                humid = safe_float(row_lower.get('humidity'))

                if temp is None or humid is None:
                    dropped_rows += 1
                    continue

                mote_readings[mote_id].append({'temp': temp, 'humid': humid})
    except Exception as e:
        print(f"ERROR reading data: {e}")
        sys.exit(1)

    print(f"Loaded {total_rows} rows, kept {sum(len(v) for v in mote_readings.values())}, dropped {dropped_rows}")
    print(f"Unique motes: {len(mote_readings)}")

    results = []
    for mote_id, readings in sorted(mote_readings.items()):
        n = len(readings)
        comfort_scores = []

        for i in range(n):
            start_idx = max(0, i - WINDOW_SIZE + 1)
            window = readings[start_idx:i + 1]

            temps = [r['temp'] for r in window]
            humids = [r['humid'] for r in window]

            avg_temp = sum(temps) / len(temps)
            avg_humid = sum(humids) / len(humids)

            t_norm = normalize_value(avg_temp, TEMP_MIN, TEMP_MAX)
            h_norm = normalize_value(avg_humid, HUMID_MIN, HUMID_MAX)

            comfort = compute_comfort_index(t_norm, h_norm, W_TEMP, W_HUMID)
            comfort_scores.append(comfort)

        valid_scores = [s for s in comfort_scores if s is not None]
        if valid_scores:
            mean_comfort = round(sum(valid_scores) / len(valid_scores), 4)
            min_comfort = round(min(valid_scores), 4)
            max_comfort = round(max(valid_scores), 4)
            std_dev = round((sum((s - mean_comfort) ** 2 for s in valid_scores) / len(valid_scores)) ** 0.5, 4)
        else:
            mean_comfort = min_comfort = max_comfort = std_dev = None

        results.append({
            'mote_id': int(mote_id),
            'num_readings': n,
            'mean_comfort_index': mean_comfort,
            'min_comfort_index': min_comfort,
            'max_comfort_index': max_comfort,
            'std_dev_comfort': std_dev
        })

    result_output = {
        'task_name': 'Temperature-Humidity Comfort Index Calculation',
        'description': 'Compute a lightweight thermal comfort score for each mote by applying a fixed-weight combination of normalized temperature and humidity values within a sliding window.',
        'result_summary': results,
        'result_generated_at': __import__('datetime').datetime.now().isoformat(),
        'parameters': {
            'window_size': WINDOW_SIZE,
            'weight_temperature': W_TEMP,
            'weight_humidity': W_HUMID,
            'temp_range': [TEMP_MIN, TEMP_MAX],
            'humidity_range': [HUMID_MIN, HUMID_MAX],
            'rows_dropped': dropped_rows,
            'total_rows_processed': total_rows
        }
    }

    with open(output_path, 'w') as f:
        json.dump(result_output, f, indent=2)

    print(f"Results saved to {output_path}")
    print(f"Processed {len(results)} motes successfully.")

if __name__ == '__main__':
    main()