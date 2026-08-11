"""
Task: LightIntensitySpikeDetector
Description: Monitor light sensor readings per mote and trigger alerts when instantaneous values exceed a defined threshold or show a sharp step-change from the previous sample.
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

curr_dir = Path(__file__).resolve().parent
root_dir = curr_dir
while root_dir.name and not (root_dir / 'data').exists():
    parent = root_dir.parent
    if parent == root_dir:
        break
    root_dir = parent

data_file = root_dir / 'data' / 'lab-data' / 'raw_data.csv'
if not data_file.exists():
    data_file = root_dir / 'data' / 'lab-data' / 'raw_data.txt'

if not data_file.exists():
    print('Error: Input data file not found.')
    sys.exit(1)

output_dir = Path('/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_qwen_qwen3.7-flash_google_gemini-3.1-flash-lite_run2')
output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / 'LightIntensitySpikeDetector_result.json'

ABSOLUTE_THRESHOLD_LUX = 50000
STEP_CHANGE_FACTOR = 2.0

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

mote_readings = {}
spike_alerts = []
dropped_rows = 0
total_rows = 0

try:
    with open(data_file, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            row = {k.lower(): v for k, v in row.items()}
            if 'light' not in row or 'moteid' not in row:
                dropped_rows += 1
                continue
            mote_id = row.get('moteid', '').strip()
            light_val = safe_float(row.get('light'))
            epoch = row.get('epoch', '').strip()
            date_str = row.get('date', '').strip()
            time_str = row.get('time', '').strip()
            if not mote_id or light_val is None:
                dropped_rows += 1
                continue
            if mote_id not in mote_readings:
                mote_readings[mote_id] = []
            mote_readings[mote_id].append({
                'epoch': epoch,
                'timestamp': f'{date_str} {time_str}' if date_str and time_str else '',
                'light': light_val
            })
except Exception as e:
    print(f'Error reading data: {e}')
    sys.exit(1)

for mote_id, readings in mote_readings.items():
    for i, reading in enumerate(readings):
        light = reading['light']
        alert_reasons = []
        if light > ABSOLUTE_THRESHOLD_LUX:
            alert_reasons.append(f'absolute_threshold_exceeded ({light:.2f} > {ABSOLUTE_THRESHOLD_LUX})')
        if i > 0:
            prev_light = readings[i-1]['light']
            if prev_light > 0 and light > prev_light * STEP_CHANGE_FACTOR:
                change_pct = ((light - prev_light) / prev_light) * 100
                alert_reasons.append(f'step_change_detected ({prev_light:.2f} -> {light:.2f}, +{change_pct:.1f}%)')
        if alert_reasons:
            spike_alerts.append({
                'moteid': int(mote_id),
                'epoch': reading['epoch'],
                'timestamp': reading['timestamp'],
                'light_value': round(light, 4),
                'alert_reasons': alert_reasons
            })

result = {
    'task_name': 'LightIntensitySpikeDetector',
    'description': 'Monitor light sensor readings per mote and trigger alerts when instantaneous values exceed a defined threshold or show a sharp step-change from the previous sample.',
    'result_summary': [
        f'Total rows processed: {total_rows}',
        f'Dropped rows (missing/invalid): {dropped_rows}',
        f'Motes analyzed: {len(mote_readings)}',
        f'Spike alerts detected: {len(spike_alerts)}',
        f'Absolute threshold: {ABSOLUTE_THRESHOLD_LUX} Lux',
        f'Step-change factor: {STEP_CHANGE_FACTOR}x'
    ],
    'result_generated_at': datetime.now().isoformat(),
    'spike_alerts': spike_alerts[:100]
}

with open(output_file, 'w') as f:
    json.dump(result, f, indent=2)

print(f'Results saved to {output_file}')
print(f'Spike alerts detected: {len(spike_alerts)}')