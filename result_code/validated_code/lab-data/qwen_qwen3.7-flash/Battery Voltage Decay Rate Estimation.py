from datetime import datetime
"""
Task: Battery Voltage Decay Rate Estimation
Description: Compute the linear decay rate of battery voltage over a sliding window of recent readings per mote to forecast remaining operational life.
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
import datetime

# Resolve input file path
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
    print("Error: Input data file not found.")
    sys.exit(1)

# Output directory
output_dir = Path("/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_qwen_qwen3.7-flash_nvidia_nemotron-3-ultra-550b-a55b_run2")
output_dir.mkdir(parents=True, exist_ok=True)

# Configuration
WINDOW_SIZE = 50
MIN_VOLTAGE_THRESHOLD = 2.0
STABLE_THRESHOLD = 0.001

def safe_float(value):
    """Safely convert value to float."""
    if value is None:
        return None
    value = str(value).strip()
    if value in ('', 'NA', 'N/A', 'None', 'None'):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

def safe_int(value):
    """Safely convert value to int."""
    f = safe_float(value)
    if f is None:
        return None
    return int(f)

# Read and parse data
mote_readings = defaultdict(list)
dropped_rows = 0
total_rows = 0

try:
    with open(data_file, 'r', newline='', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            row = {k.lower(): v for k, v in row.items()}

            moteid_raw = row.get('moteid')
            epoch_raw = row.get('epoch')
            voltage_raw = row.get('voltage')

            if moteid_raw is None or epoch_raw is None or voltage_raw is None:
                dropped_rows += 1
                continue

            moteid = safe_int(moteid_raw)
            epoch = safe_int(epoch_raw)
            voltage = safe_float(voltage_raw)

            if moteid is None or epoch is None or voltage is None:
                dropped_rows += 1
                continue

            mote_readings[moteid].append((epoch, voltage))
except Exception as e:
    print(f"Error reading data file: {e}")
    sys.exit(1)

# Sort readings by epoch for each mote
for moteid in mote_readings:
    mote_readings[moteid].sort(key=lambda x: x[0])

# Compute decay rates using sliding window (linear regression)
results = []

for moteid, readings in sorted(mote_readings.items()):
    if len(readings) < WINDOW_SIZE:
        continue

    window = readings[-WINDOW_SIZE:]
    epochs = [r[0] for r in window]
    voltages = [r[1] for r in window]

    n = len(epochs)
    sum_x = sum(epochs)
    sum_y = sum(voltages)
    sum_xy = sum(e * v for e, v in zip(epochs, voltages))
    sum_x2 = sum(e * e for e in epochs)

    denominator = n * sum_x2 - sum_x * sum_x
    if denominator == 0:
        continue

    slope = (n * sum_xy - sum_x * sum_y) / denominator
    intercept = (sum_y - slope * sum_x) / n

    # Forecast remaining life: when voltage drops below MIN_VOLTAGE_THRESHOLD
    if slope >= 0:
        remaining_epochs = None
    else:
        remaining_epochs = (MIN_VOLTAGE_THRESHOLD - intercept) / slope if slope != 0 else None

    status = "degrading" if slope < -STABLE_THRESHOLD else ("stable" if abs(slope) <= STABLE_THRESHOLD else "increasing")

    result = {
        "mote_id": moteid,
        "num_readings": len(readings),
        "window_size": WINDOW_SIZE,
        "decay_rate_per_epoch": round(slope, 8),
        "current_voltage": round(voltages[-1], 4),
        "intercept": round(intercept, 4),
        "forecasted_min_voltage_epoch": round(remaining_epochs, 2) if remaining_epochs is not None else None,
        "status": status
    }
    results.append(result)

# Build output
output = {
    "task_name": "Battery Voltage Decay Rate Estimation",
    "description": "Compute the linear decay rate of battery voltage over a sliding window of recent readings per mote to forecast remaining operational life.",
    "result_summary": results,
    "result_generated_at": datetime.datetime.now().isoformat(),
    "metadata": {
        "total_rows_processed": total_rows,
        "rows_dropped": dropped_rows,
        "mot_analyzed": len(results),
        "window_size": WINDOW_SIZE,
        "min_voltage_threshold": MIN_VOLTAGE_THRESHOLD
    }
}

# Save output
output_path = output_dir / "battery_voltage_decay_result.json"
try:
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"Results saved to {output_path}")
    print(f"Analyzed {len(results)} motes out of {len(mote_readings)} total.")
    print(f"Dropped {dropped_rows} rows due to missing/invalid data.")
except Exception as e:
    print(f"Error saving results: {e}")
    sys.exit(1)