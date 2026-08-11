"""
Task: Per-Mote Temperature Drift Detection
Description: Calculate the difference between the current temperature reading and a rolling average for each active mote to identify potential sensor calibration drift.
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
from datetime import datetime

# Resolve input file path dynamically
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
    print("Error: No raw_data.csv or raw_data.txt found in data/lab-data/")
    sys.exit(1)

# Output path
output_dir = Path("/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_qwen_qwen3.7-flash_nvidia_nemotron-3-ultra-550b-a55b_run2")
output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / "per_mote_temperature_drift_result.json"

# Helper function for safe float conversion
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

# Read and parse data
mote_temps = defaultdict(list)
dropped_rows = 0
total_rows = 0

try:
    with open(data_file, 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            row = {k.lower(): v for k, v in row.items()}
            
            if 'moteid' not in row or 'temperature' not in row:
                dropped_rows += 1
                continue
            
            mote_id = row.get('moteid', '').strip()
            temp = safe_float(row.get('temperature'))
            timestamp = row.get('date', '') + ' ' + row.get('time', '')
            
            if not mote_id or temp is None:
                dropped_rows += 1
                continue
            
            mote_temps[mote_id].append((timestamp, temp))
except Exception as e:
    print(f"Error reading data: {e}")
    sys.exit(1)

print(f"Loaded {len(mote_temps)} motes, processed {total_rows} rows ({dropped_rows} dropped)")

# Calculate drift detection
window_size = 10
drift_threshold = 2.0

drift_results = []

for mote_id, readings in mote_temps.items():
    temps = [t for _, t in readings]
    
    if len(temps) < window_size:
        continue
    
    mean_temp = sum(temps) / len(temps)
    variance = sum((t - mean_temp) ** 2 for t in temps) / len(temps)
    std_dev = math.sqrt(variance) if variance > 0 else 0.001
    
    drift_points = []
    for i in range(window_size, len(temps)):
        window = temps[i-window_size:i]
        window_mean = sum(window) / len(window)
        
        diff = abs(temps[i] - window_mean)
        
        if diff > drift_threshold * std_dev:
            drift_points.append({
                "index": i,
                "current_temp": round(temps[i], 4),
                "rolling_avg": round(window_mean, 4),
                "difference": round(diff, 4),
                "z_score": round(diff / std_dev, 4)
            })
    
    if drift_points:
        drift_results.append({
            "mote_id": int(mote_id),
            "total_readings": len(readings),
            "mean_temperature": round(mean_temp, 4),
            "std_deviation": round(std_dev, 4),
            "drift_count": len(drift_points),
            "max_drift": max(dp["difference"] for dp in drift_points),
            "recent_drifts": drift_points[-5:]
        })

drift_results.sort(key=lambda x: x["drift_count"], reverse=True)

result = {
    "task_name": "Per-Mote Temperature Drift Detection",
    "description": "Calculate the difference between the current temperature reading and a rolling average for each active mote to identify potential sensor calibration drift.",
    "result_summary": [
        f"Analyzed {len(mote_temps)} motes",
        f"Found temperature drift in {len(drift_results)} motes",
        f"Total drift events detected: {sum(r['drift_count'] for r in drift_results)}",
        f"Top drifting mote: Mote {drift_results[0]['mote_id']} with {drift_results[0]['drift_count']} drift events" if drift_results else "No significant drift detected"
    ],
    "detailed_results": drift_results[:20],
    "result_generated_at": datetime.now().isoformat(),
    "parameters": {
        "window_size": window_size,
        "drift_threshold_std": drift_threshold,
        "dropped_rows": dropped_rows,
        "total_rows_processed": total_rows
    }
}

with open(output_file, 'w') as f:
    json.dump(result, f, indent=2)

print(f"Results saved to {output_file}")
print(f"Drift detected in {len(drift_results)} out of {len(mote_temps)} motes")
if drift_results:
    print(f"Most drifted: Mote {drift_results[0]['mote_id']} ({drift_results[0]['drift_count']} events)")