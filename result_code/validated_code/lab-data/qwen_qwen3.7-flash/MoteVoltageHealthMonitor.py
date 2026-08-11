"""
Task: MoteVoltageHealthMonitor
Description: Monitor the rate of battery voltage decline per sensor mote using a sliding window to identify nodes approaching critical power levels without heavy historical analysis.
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
    print("Error: No data file found in data/lab-data/")
    sys.exit(1)

# Output path
output_dir = Path("/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_qwen_qwen3.7-flash_anthropic_claude-3-haiku_run1")
output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / "MoteVoltageHealthMonitor_result.json"

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
mote_data = {}
dropped_rows = 0
total_rows = 0

try:
    with open(data_file, 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            row = {k.lower(): v for k, v in row.items()}
            
            if 'moteid' not in row or 'voltage' not in row:
                dropped_rows += 1
                continue
            
            mote_id = row.get('moteid', '').strip()
            voltage = safe_float(row.get('voltage'))
            timestamp = row.get('date', '') + ' ' + row.get('time', '')
            
            if not mote_id or voltage is None:
                dropped_rows += 1
                continue
            
            if mote_id not in mote_data:
                mote_data[mote_id] = []
            mote_data[mote_id].append((timestamp, voltage))
except Exception as e:
    print(f"Error reading data: {e}")
    sys.exit(1)

print(f"Loaded {len(mote_data)} motes from {total_rows} rows ({dropped_rows} dropped)")

# Analyze voltage health using sliding window
WINDOW_SIZE = 10
CRITICAL_THRESHOLD = 2.2
DECLINE_RATE_THRESHOLD = 0.01

results = []

for mote_id, readings in mote_data.items():
    readings.sort(key=lambda x: x[0])
    
    if len(readings) < WINDOW_SIZE:
        continue
    
    recent_readings = readings[-WINDOW_SIZE:]
    avg_recent_voltage = sum(r[1] for r in recent_readings) / len(recent_readings)
    
    all_voltages = [r[1] for r in readings]
    avg_overall_voltage = sum(all_voltages) / len(all_voltages)
    
    mid = len(readings) // 2
    first_half = readings[:mid]
    second_half = readings[mid:]
    
    avg_first = sum(r[1] for r in first_half) / len(first_half)
    avg_second = sum(r[1] for r in second_half) / len(second_half)
    
    decline_rate = (avg_first - avg_second) / max(len(readings), 1)
    
    if avg_recent_voltage < CRITICAL_THRESHOLD:
        status = "critical"
    elif decline_rate > DECLINE_RATE_THRESHOLD:
        status = "warning"
    else:
        status = "healthy"
    
    result_entry = {
        "mote_id": int(mote_id),
        "status": status,
        "avg_voltage_recent": round(avg_recent_voltage, 4),
        "avg_voltage_overall": round(avg_overall_voltage, 4),
        "decline_rate_per_reading": round(decline_rate, 6),
        "total_readings": len(readings)
    }
    
    results.append(result_entry)

results.sort(key=lambda x: x['decline_rate_per_reading'], reverse=True)

critical_count = sum(1 for r in results if r['status'] == 'critical')
warning_count = sum(1 for r in results if r['status'] == 'warning')
healthy_count = sum(1 for r in results if r['status'] == 'healthy')

summary = {
    "total_motes_analyzed": len(results),
    "critical_nodes": critical_count,
    "warning_nodes": warning_count,
    "healthy_nodes": healthy_count,
    "top_declining_motes": results[:5] if len(results) >= 5 else results
}

final_result = {
    "task_name": "MoteVoltageHealthMonitor",
    "description": "Monitor the rate of battery voltage decline per sensor mote using a sliding window to identify nodes approaching critical power levels without heavy historical analysis.",
    "result_summary": summary,
    "result_generated_at": datetime.now().isoformat(),
    "detailed_results": results
}

with open(output_file, 'w') as f:
    json.dump(final_result, f, indent=2)

print(f"Results saved to {output_file}")
print(f"Analysis complete: {critical_count} critical, {warning_count} warning, {healthy_count} healthy motes")