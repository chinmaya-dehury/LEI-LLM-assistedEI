"""
Task: Irrigation Necessity Trigger
Description: Compares current Soil_Moisture and recent Rainfall values to determine if supplemental irrigation is required for the current growth stage.
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
    print('Error: Input data file not found.')
    sys.exit(1)

# Output path
output_dir = Path('/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_qwen_qwen3.7-flash_anthropic_claude-3-haiku_run1')
output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / 'Irrigation Necessity Trigger_result.json'

# Helper function for safe numeric conversion
def safe_float(value):
    if value is None:
        return None
    value = str(value).strip()
    if value in ('', 'NA', 'N/A', 'None', 'None'):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

# Thresholds for irrigation necessity
SOIL_MOISTURE_THRESHOLD = 40.0  # %
RAINFALL_THRESHOLD = 50.0  # mm

# Growth stage water requirements (multiplier)
GROWTH_STAGE_REQUIREMENTS = {
    'seedling': 1.2,
    'vegetative': 1.0,
    'flowering': 1.3,
    'fruiting': 1.1,
    'harvest': 0.8
}

# Read and process data
records = []
dropped_rows = 0
total_rows = 0

try:
    with open(data_file, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            # Normalize keys to lowercase
            row = {k.lower(): v for k, v in row.items()}
            
            soil_moisture = safe_float(row.get('soil_moisture'))
            rainfall = safe_float(row.get('rainfall'))
            growth_stage = row.get('growth_stage', '').strip().lower() if row.get('growth_stage') else ''
            label = row.get('label', '').strip().lower() if row.get('label') else ''
            
            if soil_moisture is None or rainfall is None:
                dropped_rows += 1
                continue
            
            # Determine irrigation necessity
            # Adjust thresholds based on growth stage
            stage_multiplier = GROWTH_STAGE_REQUIREMENTS.get(growth_stage, 1.0)
            adjusted_moisture_threshold = SOIL_MOISTURE_THRESHOLD / stage_multiplier
            
            needs_irrigation = (soil_moisture < adjusted_moisture_threshold) and (rainfall < RAINFALL_THRESHOLD)
            
            # Calculate irrigation urgency
            if needs_irrigation:
                if soil_moisture < 25:
                    urgency = 'critical'
                elif soil_moisture < 35:
                    urgency = 'high'
                else:
                    urgency = 'moderate'
            else:
                urgency = 'none'
            
            records.append({
                'soil_moisture': soil_moisture,
                'rainfall': rainfall,
                'growth_stage': growth_stage,
                'label': label,
                'needs_irrigation': needs_irrigation,
                'urgency': urgency,
                'adjusted_threshold': adjusted_moisture_threshold
            })
except Exception as e:
    print(f'Error reading data: {e}')
    sys.exit(1)

# Generate summary statistics
if not records:
    print('No valid records found.')
    sys.exit(1)

total_records = len(records)
irrigation_needed_count = sum(1 for r in records if r['needs_irrigation'])
irrigation_rate = (irrigation_needed_count / total_records) * 100 if total_records > 0 else 0

urgency_counts = {'critical': 0, 'high': 0, 'moderate': 0, 'none': 0}
for r in records:
    urgency_counts[r['urgency']] += 1

# Average values
avg_soil_moisture = sum(r['soil_moisture'] for r in records) / total_records
avg_rainfall = sum(r['rainfall'] for r in records) / total_records

# Results
result = {
    'task_name': 'Irrigation Necessity Trigger',
    'description': 'Compares current Soil_Moisture and recent Rainfall values to determine if supplemental irrigation is required for the current growth stage.',
    'result_summary': [
        f'Total records analyzed: {total_records}',
        f'Dropped rows (missing data): {dropped_rows}',
        f'Irrigation needed: {irrigation_needed_count} ({irrigation_rate:.1f}%)',
        f'Urgency breakdown: Critical={urgency_counts["critical"]}, High={urgency_counts["high"]}, Moderate={urgency_counts["moderate"]}, None={urgency_counts["none"]}',
        f'Average Soil Moisture: {avg_soil_moisture:.2f}%',
        f'Average Rainfall: {avg_rainfall:.2f}mm',
        f'Base Soil Moisture Threshold: {SOIL_MOISTURE_THRESHOLD}%',
        f'Rainfall Threshold: {RAINFALL_THRESHOLD}mm'
    ],
    'result_generated_at': datetime.now().isoformat()
}

# Write output
with open(output_file, 'w') as f:
    json.dump(result, f, indent=2)

print(f'Results saved to {output_file}')
print(f'Irrigation needed in {irrigation_rate:.1f}% of records')