"""
Task: Light Level Anomaly Flagging
Description: Compare incoming light intensity values against a running median to automatically flag unexpected illumination spikes or drops indicative of equipment activity.
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
from datetime import datetime

def safe_float(value):
    if value is None:
        return None
    value = str(value).strip()
    if value in ('', 'NA', 'N/A', 'None', 'None'):
        return None
    try:
        return float(value)
    except ValueError:
        return None

class RunningMedian:
    def __init__(self, window_size=50):
        self.window_size = window_size
        self.values = []

    def add(self, value):
        self.values.append(value)
        if len(self.values) > self.window_size:
            self.values.pop(0)

    def get_median(self):
        if not self.values:
            return None
        sorted_vals = sorted(self.values)
        n = len(sorted_vals)
        if n % 2 == 1:
            return sorted_vals[n // 2]
        else:
            return (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2

    def get_iqr(self):
        if len(self.values) < 4:
            return None
        sorted_vals = sorted(self.values)
        n = len(sorted_vals)
        q1_idx = max(0, n // 4 - 1)
        q3_idx = min(n - 1, (3 * n) // 4)
        q1 = sorted_vals[q1_idx]
        q3 = sorted_vals[q3_idx]
        return q3 - q1

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
    print("Error: No data file found in data/lab-data/")
    sys.exit(1)

output_dir = Path("/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_qwen_qwen3.7-flash_nvidia_nemotron-3-ultra-550b-a55b_run2")
output_dir.mkdir(parents=True, exist_ok=True)

strict_mode = '--strict' in sys.argv

anomalies = []
total_rows = 0
valid_rows = 0
dropped_rows = 0
running_median = RunningMedian(window_size=50)
threshold_multiplier = 2.0
max_anomalies_to_store = 500

try:
    with open(data_file, 'r', newline='', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            normalized_row = {k.lower(): v for k, v in row.items()}

            if 'light' not in normalized_row:
                dropped_rows += 1
                continue

            light_val = safe_float(normalized_row.get('light'))

            if light_val is None:
                dropped_rows += 1
                continue

            valid_rows += 1

            current_median = running_median.get_median()

            if current_median is not None and valid_rows > 10:
                iqr = running_median.get_iqr()
                if iqr is not None and iqr > 0:
                    lower_bound = current_median - threshold_multiplier * iqr
                    upper_bound = current_median + threshold_multiplier * iqr

                    if light_val < lower_bound or light_val > upper_bound:
                        anomaly = {
                            "date": normalized_row.get('date', ''),
                            "time": normalized_row.get('time', ''),
                            "moteid": normalized_row.get('moteid', ''),
                            "epoch": normalized_row.get('epoch', ''),
                            "light_value": round(light_val, 4),
                            "expected_range": [round(lower_bound, 4), round(upper_bound, 4)],
                            "deviation_from_median": round(abs(light_val - current_median), 4)
                        }
                        if len(anomalies) < max_anomalies_to_store:
                            anomalies.append(anomaly)

            running_median.add(light_val)

except Exception as e:
    print(f"Error processing data: {e}", file=sys.stderr)
    sys.exit(1)

result = {
    "task_name": "Light Level Anomaly Flagging",
    "description": "Compare incoming light intensity values against a running median to automatically flag unexpected illumination spikes or drops indicative of equipment activity.",
    "result_summary": [
        f"Total rows processed: {total_rows}",
        f"Valid rows: {valid_rows}",
        f"Dropped rows (missing/invalid): {dropped_rows}",
        f"Anomalies detected: {len(anomalies)}",
        f"Sliding window size: 50 readings",
        f"Anomaly threshold: 2x IQR from running median"
    ],
    "anomalies": anomalies,
    "result_generated_at": datetime.now().isoformat()
}

output_path = output_dir / "light_level_anomaly_flagging_result.json"
with open(output_path, 'w') as f:
    json.dump(result, f, indent=2)

print(f"Results saved to {output_path}")
print(f"Processed {total_rows} rows, found {len(anomalies)} anomalies")