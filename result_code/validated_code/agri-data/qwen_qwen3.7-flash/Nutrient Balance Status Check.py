import re
from datetime import datetime
"""
Task: Nutrient Balance Status Check
Description: Evaluate the Nutrient Balance Ratio (NBR) against an optimal range (0.8 to 1.2) and output a simple categorical status (Optimal, Imbalanced) to guide fertilizer adjustments without heavy computation.
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
import sys
from pathlib import Path
import datetime

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

# Output directory (fixed path per requirements)
output_dir = Path('/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_qwen_qwen3.7-flash_nvidia_nemotron-3-ultra-550b-a55b_run2')
output_dir.mkdir(parents=True, exist_ok=True)

# Optimal NBR range
NBR_MIN = 0.8
NBR_MAX = 1.2

def safe_float(value):
    """Safely convert a value to float, returning None on failure."""
    if value is None:
        return None
    value = str(value).strip()
    if value in ('', 'NA', 'N/A', 'None', 'None'):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

# Data collection
nbr_values = []
crop_stats = {}
total_rows = 0
valid_rows = 0
dropped_rows = 0

try:
    with open(data_file, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            # Normalize keys to lowercase
            row = {k.lower(): v for k, v in row.items()}

            # Get NBR value
            nbr = safe_float(row.get('nbr'))
            crop = row.get('label', 'unknown').strip().lower() if row.get('label') else 'unknown'

            if nbr is None:
                dropped_rows += 1
                continue

            valid_rows += 1
            nbr_values.append(nbr)

            # Categorize based on optimal range
            if NBR_MIN <= nbr <= NBR_MAX:
                status = 'Optimal'
            else:
                status = 'Imbalanced'

            # Track per crop
            if crop not in crop_stats:
                crop_stats[crop] = {'Optimal': 0, 'Imbalanced': 0}
            crop_stats[crop][status] += 1

except Exception as e:
    print(f'Error reading data: {e}')
    sys.exit(1)

# Calculate summary statistics
if nbr_values:
    optimal_count = sum(1 for v in nbr_values if NBR_MIN <= v <= NBR_MAX)
    imbalanced_count = len(nbr_values) - optimal_count
    avg_nbr = sum(nbr_values) / len(nbr_values)
    min_nbr = min(nbr_values)
    max_nbr = max(nbr_values)
else:
    optimal_count = 0
    imbalanced_count = 0
    avg_nbr = 0.0
    min_nbr = 0.0
    max_nbr = 0.0

# Build result
result = {
    'task_name': 'Nutrient Balance Status Check',
    'description': 'Evaluate the Nutrient Balance Ratio (NBR) against an optimal range (0.8 to 1.2) and output a simple categorical status (Optimal, Imbalanced) to guide fertilizer adjustments without heavy computation.',
    'result_summary': [
        {'metric': 'total_rows_processed', 'value': total_rows},
        {'metric': 'valid_nbr_records', 'value': valid_rows},
        {'metric': 'dropped_records', 'value': dropped_rows},
        {'metric': 'optimal_count', 'value': optimal_count},
        {'metric': 'imbalanced_count', 'value': imbalanced_count},
        {'metric': 'optimal_percentage', 'value': round(optimal_count / valid_rows * 100, 2) if valid_rows > 0 else 0},
        {'metric': 'imbalanced_percentage', 'value': round(imbalanced_count / valid_rows * 100, 2) if valid_rows > 0 else 0},
        {'metric': 'avg_nbr', 'value': round(avg_nbr, 4)},
        {'metric': 'min_nbr', 'value': round(min_nbr, 4)},
        {'metric': 'max_nbr', 'value': round(max_nbr, 4)},
        {'metric': 'optimal_range', 'value': [NBR_MIN, NBR_MAX]}
    ],
    'crop_breakdown': crop_stats,
    'result_generated_at': datetime.datetime.now().isoformat()
}

# Save result
output_file = output_dir / 'nutrient_balance_status_check_result.json'
with open(output_file, 'w') as f:
    json.dump(result, f, indent=2)

print(f'Results saved to {output_file}')
print(f'Total rows: {total_rows}, Valid: {valid_rows}, Dropped: {dropped_rows}')
if valid_rows > 0:
    print(f'Optimal: {optimal_count} ({optimal_count/valid_rows*100:.1f}%), Imbalanced: {imbalanced_count} ({imbalanced_count/valid_rows*100:.1f}%)')
    print(f'Average NBR: {avg_nbr:.4f}, Range: [{min_nbr:.4f}, {max_nbr:.4f}]')
else:
    print('No valid NBR records found.')