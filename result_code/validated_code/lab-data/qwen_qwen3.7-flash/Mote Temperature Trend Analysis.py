from datetime import datetime
"""
Task: Mote Temperature Trend Analysis
Description: Calculate the rolling mean and first-order difference of temperature readings per mote over a fixed window to detect gradual environmental shifts or sensor drift.
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
    print('Error: Input data file not found.', file=sys.stderr)
    sys.exit(1)

output_dir = Path('/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_qwen_qwen3.7-flash_google_gemini-3.1-flash-lite_run1')
output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / 'Mote_Temperature_Trend_Analysis_result.json'

mote_temps = defaultdict(list)
dropped_rows = 0
total_rows = 0

try:
    with open(data_file, 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            row = {k.lower(): v for k, v in row.items()}
            
            mote_id = row.get('moteid')
            temp = safe_float(row.get('temperature'))
            epoch = safe_float(row.get('epoch'))
            
            if mote_id is None or temp is None or epoch is None:
                dropped_rows += 1
                continue
            
            mote_temps[int(mote_id)].append((int(epoch), temp))
except Exception as e:
    print(f'Error reading data: {e}', file=sys.stderr)
    sys.exit(1)

for mote_id in mote_temps:
    mote_temps[mote_id].sort(key=lambda x: x[0])

window_size = 5
results = []

for mote_id, readings in sorted(mote_temps.items()):
    if len(readings) < window_size:
        continue
    
    trend_samples = []
    for i in range(len(readings)):
        epoch, temp = readings[i]
        
        if i > 0:
            diff = temp - readings[i-1][1]
        else:
            diff = None
        
        start_idx = max(0, i - window_size + 1)
        window_temps = [readings[j][1] for j in range(start_idx, i + 1)]
        rolling_mean = sum(window_temps) / len(window_temps)
        
        trend_samples.append({
            'epoch': epoch,
            'temperature': round(temp, 4),
            'first_order_diff': round(diff, 4) if diff is not None else None,
            'rolling_mean': round(rolling_mean, 4)
        })
    
    temps = [r[1] for r in readings]
    diffs = []
    for i in range(1, len(readings)):
        diffs.append(readings[i][1] - readings[i-1][1])
    
    summary = {
        'mote_id': mote_id,
        'num_readings': len(readings),
        'mean_temperature': round(sum(temps) / len(temps), 4),
        'min_temperature': round(min(temps), 4),
        'max_temperature': round(max(temps), 4),
        'mean_diff': round(sum(diffs) / len(diffs), 4) if diffs else None,
        'std_diff': None,
        'trend_direction': 'stable'
    }
    
    if diffs:
        mean_diff = sum(diffs) / len(diffs)
        if abs(mean_diff) < 0.01:
            summary['trend_direction'] = 'stable'
        elif mean_diff > 0:
            summary['trend_direction'] = 'increasing'
        else:
            summary['trend_direction'] = 'decreasing'
        
        variance = sum((d - mean_diff) ** 2 for d in diffs) / len(diffs)
        summary['std_diff'] = round(variance ** 0.5, 4)
    
    results.append({
        'summary': summary,
        'trend_samples': trend_samples[:20]
    })

result = {
    'task_name': 'Mote Temperature Trend Analysis',
    'description': 'Calculate the rolling mean and first-order difference of temperature readings per mote over a fixed window to detect gradual environmental shifts or sensor drift.',
    'result_summary': results,
    'result_generated_at': __import__('datetime').datetime.now().isoformat(),
    'metadata': {
        'total_rows_processed': total_rows,
        'rows_dropped': dropped_rows,
        'motes_analyzed': len(results),
        'rolling_window_size': window_size
    }
}

with open(output_file, 'w') as f:
    json.dump(result, f, indent=2)

print(f'Results saved to {output_file}')
print(f'Motes analyzed: {len(results)}')
print(f'Rows processed: {total_rows}, Dropped: {dropped_rows}')