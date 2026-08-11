import re
"""
Task: Water Availability Status Check
Description: Evaluates the Water Availability Index (WAI) against growth-stage-specific thresholds to determine if current soil moisture and rainfall levels are sufficient or if irrigation adjustments are needed.
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
output_dir = Path('/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_qwen_qwen3.7-flash_nvidia_nemotron-3-ultra-550b-a55b_run1')
output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / 'Water_Availability_Status_Check_result.json'

# Growth stage thresholds for WAI evaluation
# WAI ranges from 0 to 1; higher is better for water availability
GROWTH_STAGE_THRESHOLDS = {
    'seedling': {'min_wai': 0.80, 'optimal_wai': 0.90, 'label': 'Seedling'},
    'vegetative': {'min_wai': 0.70, 'optimal_wai': 0.85, 'label': 'Vegetative'},
    'flowering': {'min_wai': 0.75, 'optimal_wai': 0.90, 'label': 'Flowering'},
    'mature': {'min_wai': 0.60, 'optimal_wai': 0.80, 'label': 'Mature'},
    'harvest': {'min_wai': 0.55, 'optimal_wai': 0.75, 'label': 'Harvest'},
}

MISSING_VALUES = {'', 'na', 'n/a', 'None', 'none', '-'}


def safe_float(value):
    """Safely convert a value to float, returning None on failure."""
    if value is None:
        return None
    val_str = str(value).strip().lower()
    if val_str in MISSING_VALUES:
        return None
    try:
        return float(val_str)
    except (ValueError, TypeError):
        return None


def evaluate_water_availability(wai, growth_stage):
    """Evaluate water availability based on WAI and growth stage thresholds."""
    stage_key = growth_stage.lower().strip() if growth_stage else ''

    if stage_key not in GROWTH_STAGE_THRESHOLDS:
        return {
            'status': 'unknown_stage',
            'message': f'Unknown growth stage: {growth_stage}',
            'action': 'Verify growth stage classification',
        }

    thresholds = GROWTH_STAGE_THRESHOLDS[stage_key]
    min_wai = thresholds['min_wai']
    optimal_wai = thresholds['optimal_wai']

    if wai is None:
        return {
            'status': 'missing_data',
            'message': 'WAI data missing or invalid',
            'action': 'Check sensor readings for WAI',
        }

    if wai >= optimal_wai:
        return {
            'status': 'optimal',
            'message': 'Water availability is optimal for this growth stage',
            'action': 'Continue current irrigation practices',
        }
    elif wai >= min_wai:
        return {
            'status': 'adequate',
            'message': 'Water availability is adequate but could be improved',
            'action': 'Consider minor irrigation adjustments for optimal growth',
        }
    else:
        return {
            'status': 'insufficient',
            'message': 'Irrigation adjustment needed - water availability is insufficient',
            'action': 'Increase irrigation frequency or amount immediately',
        }


# Read and process data
rows = []
dropped_rows = 0
missing_data_rows = 0

try:
    with open(data_file, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Normalize keys to lowercase
            row = {k.lower(): v for k, v in row.items()}

            # Extract relevant fields
            wai = safe_float(row.get('wai'))
            growth_stage = row.get('growth_stage', '').strip().lower()
            soil_moisture = safe_float(row.get('soil_moisture'))
            rainfall = safe_float(row.get('rainfall'))
            irrigation_frequency = safe_float(row.get('irrigation_frequency'))

            # Track missing data
            if wai is None or not growth_stage:
                dropped_rows += 1
                continue

            # Evaluate water availability
            evaluation = evaluate_water_availability(wai, growth_stage)

            rows.append({
                'wai': wai,
                'growth_stage': growth_stage,
                'soil_moisture': soil_moisture,
                'rainfall': rainfall,
                'irrigation_frequency': irrigation_frequency,
                'water_availability_status': evaluation['status'],
                'message': evaluation['message'],
                'action': evaluation['action'],
            })

except Exception as e:
    print(f'Error reading data: {e}')
    sys.exit(1)

# Generate summary statistics
status_counts = {}
for row in rows:
    status = row['water_availability_status']
    status_counts[status] = status_counts.get(status, 0) + 1

# Calculate average WAI by growth stage
stage_wai_sums = {}
stage_wai_counts = {}
for row in rows:
    stage = row['growth_stage']
    wai = row['wai']
    if stage not in stage_wai_sums:
        stage_wai_sums[stage] = 0.0
        stage_wai_counts[stage] = 0
    stage_wai_sums[stage] += wai
    stage_wai_counts[stage] += 1

avg_wai_by_stage = {}
for stage in stage_wai_sums:
    avg_wai_by_stage[stage] = round(stage_wai_sums[stage] / stage_wai_counts[stage], 4)

# Generate result
result = {
    'task_name': 'Water Availability Status Check',
    'description': 'Evaluates the Water Availability Index (WAI) against growth-stage-specific thresholds to determine if current soil moisture and rainfall levels are sufficient or if irrigation adjustments are needed.',
    'result_summary': [
        {
            'total_rows_processed': len(rows),
            'dropped_rows': dropped_rows,
            'status_distribution': status_counts,
            'average_wai_by_growth_stage': avg_wai_by_stage,
            'recommendations': {
                'optimal': 'Continue current irrigation practices',
                'adequate': 'Consider minor irrigation adjustments for optimal growth',
                'insufficient': 'Increase irrigation frequency or amount immediately',
                'missing_data': 'Check sensor readings and data collection systems',
                'unknown_stage': 'Verify growth stage classification',
            },
        }
    ],
    'result_generated_at': datetime.now().isoformat(),
}

# Save result
with open(output_file, 'w') as f:
    json.dump(result, f, indent=2)

print(f'Results saved to {output_file}')
print(f'Processed {len(rows)} rows, dropped {dropped_rows} rows')
print(f'Status distribution: {status_counts}')
print(f'Average WAI by growth stage: {avg_wai_by_stage}')