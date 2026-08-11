from datetime import datetime
"""
Task: Heat Stress Detection
Description: Evaluate the Temperature-Humidity Index (THI) to identify crop heat stress conditions. Trigger an alert when THI exceeds a critical threshold (e.g., 25.0), suggesting potential yield reduction and the need for cooling or shading measures.
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
import math
from pathlib import Path

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
    exit(1)

# Output path
output_dir = Path('/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_qwen_qwen3.7-flash_anthropic_claude-3-haiku_run2')
output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / 'Heat Stress Detection_result.json'

# Safe numeric conversion
def safe_float(value):
    if value is None:
        return None
    value = str(value).strip()
    if value in ('', 'NA', 'N/A', 'None', 'NaN', 'nan'):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

# Calculate THI: THI = T - 0.55 * (1 - RH/100) * (T - 14.5)
def calculate_thi(temperature, humidity):
    if temperature is None or humidity is None:
        return None
    return temperature - 0.55 * (1 - humidity / 100.0) * (temperature - 14.5)

# Read and process data
rows = []
heat_stress_rows = []
dropped_count = 0
total_count = 0

try:
    with open(data_file, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Normalize keys to lowercase
            row = {k.lower(): v for k, v in row.items()}
            total_count += 1

            # Extract and convert numeric fields
            temperature = safe_float(row.get('temperature'))
            humidity = safe_float(row.get('humidity'))
            label = row.get('label', '').strip() if row.get('label') else ''
            soil_moisture = safe_float(row.get('soil_moisture'))
            rainfall = safe_float(row.get('rainfall'))

            # Calculate THI
            thi = calculate_thi(temperature, humidity)

            if thi is None:
                dropped_count += 1
                continue

            record = {
                'temperature': temperature,
                'humidity': humidity,
                'thi': round(thi, 2),
                'label': label,
                'soil_moisture': soil_moisture,
                'rainfall': rainfall
            }
            rows.append(record)

            # Check heat stress condition
            if thi > 25.0:
                heat_stress_rows.append(record)

except Exception as e:
    print(f'ERROR: Failed to read data file: {e}')
    exit(1)

# Summary statistics
if rows:
    thi_values = [r['thi'] for r in rows if r['thi'] is not None]
    avg_thi = sum(thi_values) / len(thi_values) if thi_values else 0
    max_thi = max(thi_values) if thi_values else 0
    min_thi = min(thi_values) if thi_values else 0
else:
    avg_thi = 0
    max_thi = 0
    min_thi = 0

# Crop-specific heat stress counts
crop_stress = {}
for r in heat_stress_rows:
    crop = r['label'] if r['label'] else 'unknown'
    crop_stress[crop] = crop_stress.get(crop, 0) + 1

# Build result
result = {
    'task_name': 'Heat Stress Detection',
    'description': 'Evaluate the Temperature-Humidity Index (THI) to identify crop heat stress conditions. Trigger an alert when THI exceeds a critical threshold (e.g., 25.0), suggesting potential yield reduction and the need for cooling or shading measures.',
    'result_summary': [
        f'Total valid records analyzed: {len(rows)}',
        f'Total rows processed: {total_count}',
        f'Dropped rows (missing data): {dropped_count}',
        f'Average THI: {round(avg_thi, 2)}',
        f'Maximum THI: {round(max_thi, 2)}',
        f'Minimum THI: {round(min_thi, 2)}',
        f'Heat stress events (THI > 25.0): {len(heat_stress_rows)}',
        f'Heat stress percentage: {round(len(heat_stress_rows) / len(rows) * 100, 2) if rows else 0}%',
        f'Crop-specific heat stress counts: {json.dumps(crop_stress)}'
    ],
    'result_generated_at': __import__('datetime').datetime.now().isoformat(),
    'heat_stress_details': heat_stress_rows[:50] if len(heat_stress_rows) > 50 else heat_stress_rows
}

# Write output
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(result, f, indent=2, default=str)

print(f'Heat Stress Detection complete. Results saved to {output_file}')
print(f'Heat stress events: {len(heat_stress_rows)} / {len(rows)} records ({round(len(heat_stress_rows) / len(rows) * 100, 2) if rows else 0}%)')