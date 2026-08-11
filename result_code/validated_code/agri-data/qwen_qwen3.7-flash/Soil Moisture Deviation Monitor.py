"""
Task: Soil Moisture Deviation Monitor
Description: Calculate the rolling average of Soil_Moisture over the last 7 daily samples and flag any current reading that deviates by more than 15% from the average to detect irrigation anomalies or sensor drift.
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

DATA_FILE_PATH = os.path.join(_root_dir, "data", "agri-data", "raw_data.csv")
if not os.path.exists(DATA_FILE_PATH):
    DATA_FILE_PATH = os.path.join(_root_dir, "data", "agri-data", "raw_data.txt")

METADATA_FILE_PATH = os.path.join(_root_dir, "data", "agri-data", "metadata.json")
OUTPUT_DIR = os.path.join(_root_dir, "output", "agri-data")
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
while root_dir.name and not (root_dir / 'data').exists():
    parent = root_dir.parent
    if parent == root_dir:
        break
    root_dir = parent

data_file = root_dir / 'data' / 'agri-data' / 'raw_data.csv'
if not data_file.exists():
    data_file = root_dir / 'data' / 'agri-data' / 'raw_data.txt'

if not data_file.exists():
    print('Error: Input data file not found under data/agri-data/')
    sys.exit(1)

# Output path (CRITICAL: use specified directory)
output_dir = Path('/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_qwen_qwen3.7-flash_nvidia_nemotron-3-ultra-550b-a55b_run2')
output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / 'Soil_Moisture_Deviation_Monitor_result.json'

# Helper: safe float conversion
def safe_float(value):
    if value is None:
        return None
    value = str(value).strip()
    if value == '' or value.lower() in ('na', 'n/a', 'None', 'none'):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

# Read and parse data
rows = []
dropped = 0
with open(data_file, 'r', newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        # Normalize keys to lowercase
        row = {k.lower(): v for k, v in row.items()}
        if 'soil_moisture' not in row:
            dropped += 1
            continue
        moisture = safe_float(row.get('soil_moisture'))
        if moisture is None:
            dropped += 1
            continue
        rows.append(moisture)

if not rows:
    print('Error: No valid soil moisture data found.')
    sys.exit(1)

# Rolling average and deviation detection
window_size = 7
threshold = 0.15  # 15%
flags = []

for i in range(len(rows)):
    if i < window_size - 1:
        continue  # Not enough data for full window

    window = rows[i - window_size + 1:i + 1]
    avg = sum(window) / len(window)

    current = rows[i]
    if avg == 0:
        deviation = 0
    else:
        deviation = abs(current - avg) / avg

    if deviation > threshold:
        flags.append({
            'index': i,
            'current_value': round(current, 2),
            'rolling_avg': round(avg, 2),
            'deviation_percent': round(deviation * 100, 2),
            'flagged': True
        })

# Build result
result = {
    'task_name': 'Soil_Moisture_Deviation_Monitor',
    'description': 'Calculate the rolling average of Soil_Moisture over the last 7 daily samples and flag any current reading that deviates by more than 15% from the average to detect irrigation anomalies or sensor drift.',
    'result_summary': {
        'total_samples': len(rows),
        'dropped_samples': dropped,
        'window_size': window_size,
        'threshold_percent': 15,
        'flags_count': len(flags),
        'flags': flags
    },
    'result_generated_at': datetime.now().isoformat()
}

# Save result
with open(output_file, 'w') as f:
    json.dump(result, f, indent=2)

print(f'Result saved to {output_file}')
print(f'Total samples: {len(rows)}, Dropped: {dropped}, Flags: {len(flags)}')