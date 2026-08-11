from datetime import datetime
"""
Task: Per-Mote Temperature Anomaly Detection
Description: Compute a rolling mean and standard deviation for temperature readings per mote to flag outliers exceeding a defined threshold, enabling early detection of sensor drift or environmental spikes without heavy computation.
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
import sys
from pathlib import Path
from collections import defaultdict

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
    print('Error: No data file found in data/lab-data/')
    sys.exit(1)

OUTPUT_DIR = Path('/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_qwen_qwen3.7-flash_nvidia_nemotron-3-ultra-550b-a55b_run1')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

WINDOW_SIZE = 10
Z_THRESHOLD = 2.0

mote_temps = defaultdict(list)
dropped_rows = 0
total_rows = 0

try:
    with open(data_file, 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            row = {k.lower(): v for k, v in row.items()}
            moteid = row.get('moteid')
            epoch = row.get('epoch')
            temp = safe_float(row.get('temperature'))
            if moteid is None or epoch is None or temp is None:
                dropped_rows += 1
                continue
            try:
                moteid = int(moteid)
                epoch = int(epoch)
            except (ValueError, TypeError):
                dropped_rows += 1
                continue
            mote_temps[moteid].append((epoch, temp))
except Exception as e:
    print(f'Error reading data file: {e}')
    sys.exit(1)

for moteid in mote_temps:
    mote_temps[moteid].sort(key=lambda x: x[0])

anomalies = []
stats_per_mote = {}

for moteid, readings in mote_temps.items():
    mote_anomalies = []
    valid_readings = []
    for i, (epoch, temp) in enumerate(readings):
        start_idx = max(0, i - WINDOW_SIZE)
        window = [t for _, t in readings[start_idx:i]]
        if len(window) < 3:
            valid_readings.append(temp)
            continue
        mean = sum(window) / len(window)
        variance = sum((t - mean) ** 2 for t in window) / len(window)
        std = math.sqrt(variance) if variance > 0 else 0.001
        z_score = abs(temp - mean) / std if std > 0 else 0
        if z_score > Z_THRESHOLD:
            mote_anomalies.append({
                'epoch': epoch,
                'temperature': round(temp, 4),
                'rolling_mean': round(mean, 4),
                'rolling_std': round(std, 4),
                'z_score': round(z_score, 4)
            })
        valid_readings.append(temp)
    if valid_readings:
        overall_mean = sum(valid_readings) / len(valid_readings)
        overall_var = sum((t - overall_mean) ** 2 for t in valid_readings) / len(valid_readings)
        overall_std = math.sqrt(overall_var)
    else:
        overall_mean = 0
        overall_std = 0
    stats_per_mote[moteid] = {
        'num_readings': len(readings),
        'mean_temperature': round(overall_mean, 4),
        'std_temperature': round(overall_std, 4),
        'anomaly_count': len(mote_anomalies)
    }
    anomalies.extend([{'moteid': moteid, **a} for a in mote_anomalies])

top_anomalous = sorted(
    [{'moteid': m, 'count': s['anomaly_count']} for m, s in stats_per_mote.items()],
    key=lambda x: x['count'], reverse=True
)[:10]

result = {
    'task_name': 'Per-Mote Temperature Anomaly Detection',
    'description': 'Compute a rolling mean and standard deviation for temperature readings per mote to flag outliers exceeding a defined threshold, enabling early detection of sensor drift or environmental spikes without heavy computation.',
    'result_summary': [
        {
            'total_rows_processed': total_rows,
            'rows_dropped': dropped_rows,
            'motes_analyzed': len(stats_per_mote),
            'total_anomalies_detected': len(anomalies),
            'window_size': WINDOW_SIZE,
            'z_threshold': Z_THRESHOLD,
            'per_mote_stats': stats_per_mote,
            'top_anomalous_motives': top_anomalous
        }
    ],
    'result_generated_at': __import__('datetime').datetime.now().isoformat()
}

output_path = OUTPUT_DIR / 'Per-Mote_Temperature_Anomaly_Detection_result.json'
with open(output_path, 'w') as f:
    json.dump(result, f, indent=2)

print(f'Anomaly detection complete. Processed {total_rows} rows, detected {len(anomalies)} anomalies across {len(stats_per_mote)} motes.')
print(f'Results saved to: {output_path}')