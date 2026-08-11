"""
Task: Water Efficiency Tracker
Description: Track Water_Usage_Efficiency (L/kg) and compare it against a baseline target. Flag deviations to optimize irrigation scheduling and reduce water waste.
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
import math
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
    print('ERROR: Input data file not found under data/agri-data/')
    sys.exit(1)

# Output path
output_dir = Path('/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_qwen_qwen3.7-flash_google_gemini-3.1-flash-lite_run2')
output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / 'Water Efficiency Tracker_result.json'

# Helper: safe float conversion
def safe_float(val):
    if val is None:
        return None
    val = str(val).strip()
    if val == '' or val.upper() in ('NA', 'N/A', 'NULL', 'NONE', ''):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None

# Read and parse data
rows = []
missing_count = 0
total_count = 0

try:
    with open(data_file, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_count += 1
            # Normalize keys to lowercase
            row = {k.lower(): v for k, v in row.items()}
            rows.append(row)
except Exception as e:
    print(f'ERROR reading file: {e}')
    sys.exit(1)

print(f'Read {total_count} rows from {data_file}')

# Extract water usage efficiency values grouped by crop label
water_efficiency_by_crop = {}
flagged_records = []
all_efficiency = []

for row in rows:
    label = row.get('label', 'unknown').strip().lower() if row.get('label') else 'unknown'
    wue = safe_float(row.get('water_usage_efficiency'))
    
    if wue is None:
        missing_count += 1
        continue
    
    all_efficiency.append(wue)
    
    if label not in water_efficiency_by_crop:
        water_efficiency_by_crop[label] = []
    water_efficiency_by_crop[label].append(wue)

if missing_count > 0:
    print(f'Skipped {missing_count} rows with missing Water_Usage_Efficiency')

if not all_efficiency:
    print('No valid Water_Usage_Efficiency data found')
    result = {
        'task_name': 'Water Efficiency Tracker',
        'description': 'Track Water_Usage_Efficiency (L/kg) and compare it against a baseline target. Flag deviations to optimize irrigation scheduling and reduce water waste.',
        'result_summary': [{'error': 'No valid data available'}],
        'result_generated_at': datetime.now().isoformat()
    }
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    print(f'Result saved to {output_file}')
    sys.exit(0)

# Calculate baseline statistics (global)
mean_wue = sum(all_efficiency) / len(all_efficiency)
variance = sum((x - mean_wue) ** 2 for x in all_efficiency) / len(all_efficiency)
std_wue = math.sqrt(variance)

# Baseline target: mean efficiency
baseline_target = round(mean_wue, 4)
threshold_low = round(mean_wue - std_wue, 4)
threshold_high = round(mean_wue + std_wue, 4)

print(f'Global Water Usage Efficiency - Mean: {mean_wue:.4f} L/kg, StdDev: {std_wue:.4f}')
print(f'Baseline Target: {baseline_target} L/kg')
print(f'Warning Thresholds: Low < {threshold_low}, High > {threshold_high}')

# Calculate per-crop statistics
crop_stats = {}
for crop, values in water_efficiency_by_crop.items():
    crop_mean = sum(values) / len(values)
    crop_var = sum((x - crop_mean) ** 2 for x in values) / len(values)
    crop_std = math.sqrt(crop_var)
    crop_stats[crop] = {
        'count': len(values),
        'mean': round(crop_mean, 4),
        'std': round(crop_std, 4),
        'min': round(min(values), 4),
        'max': round(max(values), 4)
    }

# Flag deviations from baseline
for row in rows:
    wue = safe_float(row.get('water_usage_efficiency'))
    if wue is None:
        continue
    
    label = row.get('label', 'unknown').strip().lower() if row.get('label') else 'unknown'
    deviation = wue - baseline_target
    deviation_pct = round((deviation / baseline_target) * 100, 2) if baseline_target != 0 else 0
    
    flag = None
    if wue < threshold_low:
        flag = 'LOW_EFFICIENCY'
    elif wue > threshold_high:
        flag = 'HIGH_EFFICIENCY'
    
    if flag:
        flagged_records.append({
            'crop': label,
            'water_usage_efficiency': round(wue, 4),
            'deviation_from_baseline': round(deviation, 4),
            'deviation_pct': deviation_pct,
            'flag': flag
        })

# Build result summary
result_summary = [
    {
        'metric': 'Global Water Usage Efficiency',
        'mean': round(mean_wue, 4),
        'std_dev': round(std_wue, 4),
        'min': round(min(all_efficiency), 4),
        'max': round(max(all_efficiency), 4),
        'baseline_target': baseline_target,
        'threshold_low': threshold_low,
        'threshold_high': threshold_high,
        'total_records': len(all_efficiency),
        'flagged_count': len(flagged_records)
    },
    {
        'metric': 'Per-Crop Statistics',
        'crops': crop_stats
    },
    {
        'metric': 'Flagged Records',
        'count': len(flagged_records),
        'records': flagged_records[:20]  # Limit to first 20 for brevity
    }
]

result = {
    'task_name': 'Water Efficiency Tracker',
    'description': 'Track Water_Usage_Efficiency (L/kg) and compare it against a baseline target. Flag deviations to optimize irrigation scheduling and reduce water waste.',
    'result_summary': result_summary,
    'result_generated_at': datetime.now().isoformat()
}

with open(output_file, 'w') as f:
    json.dump(result, f, indent=2)

print(f'Result saved to {output_file}')
print(f'Flagged {len(flagged_records)} records with efficiency deviations')