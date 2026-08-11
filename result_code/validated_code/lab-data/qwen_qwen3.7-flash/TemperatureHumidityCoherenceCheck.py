from datetime import datetime
"""
Task: TemperatureHumidityCoherenceCheck
Description: Compute the moving average difference between temperature and humidity readings per mote to detect environmental anomalies or sensor calibration drift.
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
import math
from pathlib import Path
from collections import defaultdict

# Resolve input file path dynamically
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
    print('ERROR: No raw_data.csv or raw_data.txt found in data/lab-data/')
    sys.exit(1)

# Output path
output_dir = Path('/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_qwen_qwen3.7-flash_google_gemini-3.1-flash-lite_run2')
output_dir.mkdir(parents=True, exist_ok=True)
output_path = output_dir / 'TemperatureHumidityCoherenceCheck_result.json'

# Helper: safe float conversion
def safe_float(val):
    if val is None:
        return None
    val = str(val).strip()
    if val in ('', 'NA', 'N/A', 'None', 'None'):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None

# Read and parse data
print(f'Reading data from: {data_file}')
mote_readings = defaultdict(list)  # moteid -> list of (temp, humidity)
dropped_rows = 0
total_rows = 0

try:
    with open(data_file, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            # Normalize keys to lowercase
            row = {k.lower(): v for k, v in row.items()}
            
            mote_id = row.get('moteid', '').strip()
            if not mote_id:
                dropped_rows += 1
                continue
            
            temp = safe_float(row.get('temperature'))
            hum = safe_float(row.get('humidity'))
            
            if temp is None or hum is None:
                dropped_rows += 1
                continue
            
            mote_readings[mote_id].append((temp, hum))
except Exception as e:
    print(f'ERROR reading file: {e}')
    sys.exit(1)

print(f'Total rows processed: {total_rows}, Dropped: {dropped_rows}, Valid motes: {len(mote_readings)}')

# Compute moving average difference per mote
window_size = 5  # Moving average window
anomalies = []
mote_stats = {}

for mote_id, readings in mote_readings.items():
    if len(readings) < window_size:
        mote_stats[mote_id] = {
            'status': 'insufficient_data',
            'readings_count': len(readings),
            'mean_diff': None,
            'std_diff': None,
            'max_anomaly_score': None
        }
        continue
    
    diffs = []
    anomaly_scores = []
    
    for i in range(len(readings)):
        temp_val, hum_val = readings[i]
        
        # Compute moving average over window
        start_idx = max(0, i - window_size + 1)
        window_temps = [readings[j][0] for j in range(start_idx, i + 1)]
        window_hums = [readings[j][1] for j in range(start_idx, i + 1)]
        
        ma_temp = sum(window_temps) / len(window_temps)
        ma_hum = sum(window_hums) / len(window_hums)
        
        diff = abs(ma_temp - ma_hum)
        diffs.append(diff)
        
        # Anomaly score: deviation from running mean of differences
        if len(diffs) >= 3:
            mean_d = sum(diffs[-window_size:]) / min(window_size, len(diffs))
            var_d = sum((d - mean_d) ** 2 for d in diffs[-window_size:]) / min(window_size, len(diffs))
            std_d = math.sqrt(var_d) if var_d > 0 else 0.001
            score = (diff - mean_d) / std_d
            anomaly_scores.append(score)
    
    mean_diff = sum(diffs) / len(diffs)
    std_diff = math.sqrt(sum((d - mean_diff) ** 2 for d in diffs) / len(diffs)) if len(diffs) > 1 else 0
    max_anomaly = max(anomaly_scores) if anomaly_scores else None
    
    mote_stats[mote_id] = {
        'status': 'ok' if max_anomaly is None or max_anomaly < 2.0 else 'anomaly_detected',
        'readings_count': len(readings),
        'mean_diff': round(mean_diff, 4),
        'std_diff': round(std_diff, 4),
        'max_anomaly_score': round(max_anomaly, 4) if max_anomaly is not None else None
    }
    
    if mote_stats[mote_id]['status'] == 'anomaly_detected':
        anomalies.append({
            'mote_id': int(mote_id),
            'mean_diff': round(mean_diff, 4),
            'max_anomaly_score': round(max_anomaly, 4),
            'readings_count': len(readings)
        })

# Summary
result_summary = [
    f'Total motes analyzed: {len(mote_stats)}',
    f'Motes with anomalies: {len(anomalies)}',
    f'Dropped rows (missing/invalid): {dropped_rows}',
    f'Total valid readings: {sum(s["readings_count"] for s in mote_stats.values())}'
]

if anomalies:
    result_summary.append(f'Top 5 anomalous motes:')
    sorted_anomalies = sorted(anomalies, key=lambda x: x['max_anomaly_score'], reverse=True)[:5]
    for a in sorted_anomalies:
        result_summary.append(f'  Mote {a["mote_id"]}: mean_diff={a["mean_diff"]}, max_anomaly_score={a["max_anomaly_score"]}')

result = {
    'task_name': 'TemperatureHumidityCoherenceCheck',
    'description': 'Moving average difference between temperature and humidity per mote for anomaly detection.',
    'result_summary': result_summary,
    'result_generated_at': __import__('datetime').datetime.now().isoformat(),
    'mote_statistics': mote_stats,
    'anomalies': anomalies
}

with open(output_path, 'w') as f:
    json.dump(result, f, indent=2)

print(f'Result saved to: {output_path}')
for line in result_summary:
    print(line)