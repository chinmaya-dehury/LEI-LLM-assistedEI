"""
Task: HumidityVarianceTracker
Description: Calculate the short-term variance of humidity readings per mote to assess local environmental stability and sensor noise levels efficiently.
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
import math
import os
from pathlib import Path
from datetime import datetime

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
    exit(1)

output_dir = Path("/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_qwen_qwen3.7-flash_anthropic_claude-3-haiku_run1")
output_dir.mkdir(parents=True, exist_ok=True)

def safe_float(value):
    if value is None:
        return None
    value = str(value).strip()
    if value == '' or value.lower() in ('na', 'n/a', 'None'):
        return None
    try:
        return float(value)
    except ValueError:
        return None

mote_humidity = {}
mote_deltas = {}
rows_processed = 0
rows_skipped = 0

try:
    with open(data_file, 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            row = {k.lower(): v for k, v in row.items()}
            if 'moteid' not in row or 'humidity' not in row:
                rows_skipped += 1
                continue
            try:
                mote_id = int(row['moteid'])
            except (ValueError, TypeError):
                rows_skipped += 1
                continue
            humidity = safe_float(row.get('humidity'))
            if humidity is None:
                rows_skipped += 1
                continue
            rows_processed += 1
            if mote_id not in mote_humidity:
                mote_humidity[mote_id] = []
                mote_deltas[mote_id] = []
            mote_humidity[mote_id].append(humidity)
except Exception as e:
    print(f"Error reading data file: {e}")
    exit(1)

results = []
for mote_id in sorted(mote_humidity.keys()):
    humidities = mote_humidity[mote_id]
    deltas = []
    for i in range(1, len(humidities)):
        delta = humidities[i] - humidities[i-1]
        deltas.append(delta)
    if len(deltas) < 2:
        continue
    mean_delta = sum(deltas) / len(deltas)
    variance = sum((d - mean_delta) ** 2 for d in deltas) / len(deltas)
    mean_humidity = sum(humidities) / len(humidities)
    min_humidity = min(humidities)
    max_humidity = max(humidities)
    results.append({
        "moteid": mote_id,
        "num_readings": len(humidities),
        "mean_humidity": round(mean_humidity, 4),
        "min_humidity": round(min_humidity, 4),
        "max_humidity": round(max_humidity, 4),
        "short_term_variance": round(variance, 6),
        "std_dev_of_deltas": round(math.sqrt(variance), 6)
    })

result = {
    "task_name": "HumidityVarianceTracker",
    "description": "Calculate the short-term variance of humidity readings per mote to assess local environmental stability and sensor noise levels efficiently.",
    "result_summary": results,
    "result_generated_at": datetime.now().isoformat(),
    "metadata": {
        "total_rows_processed": rows_processed,
        "total_rows_skipped": rows_skipped,
        "unique_motes": len(mote_humidity)
    }
}

output_path = output_dir / "HumidityVarianceTracker_result.json"
with open(output_path, 'w') as f:
    json.dump(result, f, indent=2)

print(f"Results saved to {output_path}")
print(f"Processed {rows_processed} valid rows, skipped {rows_skipped} rows")
print(f"Analyzed {len(results)} motes")