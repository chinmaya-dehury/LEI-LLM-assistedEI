"""
Task: Nutrient Imbalance Check
Description: Monitor the Nutrient Balance Ratio (NBR) to detect deviations in soil nitrogen, phosphorus, and potassium levels. Trigger an alert if NBR falls outside the optimal range (e.g., < 0.85 or > 1.15) to guide precise fertilizer application.
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
    print('Error: Input data file not found in data/agri-data/')
    sys.exit(1)

# Output path (fixed as specified)
output_dir = Path('/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_qwen_qwen3.7-flash_anthropic_claude-3-haiku_run2')
output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / 'nutrient_imbalance_check_result.json'

# Optimal NBR range thresholds
NBR_MIN = 0.85
NBR_MAX = 1.15

# Helper: safely convert value to float
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

# Read and process data
alerts = []
total_rows = 0
valid_nbr_count = 0
nbr_values = []
dropped_rows = 0

try:
    with open(data_file, 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            # Normalize keys to lowercase
            row = {k.lower(): v for k, v in row.items()}

            # Get NBR value
            nbr = safe_float(row.get('nbr'))
            if nbr is None:
                dropped_rows += 1
                continue

            valid_nbr_count += 1
            nbr_values.append(nbr)

            # Check if NBR is outside optimal range
            if nbr < NBR_MIN or nbr > NBR_MAX:
                alerts.append({
                    'row_index': total_rows,
                    'nbr': round(nbr, 4),
                    'status': 'IMBALANCED',
                    'message': f'NBR {nbr:.2f} is outside optimal range ({NBR_MIN}-{NBR_MAX})'
                })
except Exception as e:
    print(f'Error reading data file: {e}')
    sys.exit(1)

# Calculate summary statistics
if nbr_values:
    nbr_min = min(nbr_values)
    nbr_max = max(nbr_values)
    nbr_mean = sum(nbr_values) / len(nbr_values)
    nbr_std = (sum((x - nbr_mean) ** 2 for x in nbr_values) / len(nbr_values)) ** 0.5
else:
    nbr_min = nbr_max = nbr_mean = nbr_std = None

# Count imbalance types
low_nbr_count = sum(1 for v in nbr_values if v < NBR_MIN)
high_nbr_count = sum(1 for v in nbr_values if v > NBR_MAX)

summary_items = [
    f'Total rows processed: {total_rows}',
    f'Valid NBR values: {valid_nbr_count}',
    f'Dropped/invalid rows: {dropped_rows}',
    f'Alerts triggered: {len(alerts)}',
    f'Low NBR alerts (< {NBR_MIN}): {low_nbr_count}',
    f'High NBR alerts (> {NBR_MAX}): {high_nbr_count}',
    f'NBR min: {nbr_min:.4f}' if nbr_min is not None else 'NBR min: N/A',
    f'NBR max: {nbr_max:.4f}' if nbr_max is not None else 'NBR max: N/A',
    f'NBR mean: {nbr_mean:.4f}' if nbr_mean is not None else 'NBR mean: N/A',
    f'NBR std dev: {nbr_std:.4f}' if nbr_std is not None else 'NBR std dev: N/A',
    f'Optimal NBR range: {NBR_MIN} - {NBR_MAX}'
]

# Prepare result
result = {
    'task_name': 'Nutrient Imbalance Check',
    'description': 'Monitor the Nutrient Balance Ratio (NBR) to detect deviations in soil nitrogen, phosphorus, and potassium levels. Trigger an alert if NBR falls outside the optimal range (e.g., < 0.85 or > 1.15) to guide precise fertilizer application.',
    'result_summary': summary_items,
    'alerts': alerts,
    'result_generated_at': datetime.now().isoformat()
}

# Save result
try:
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    print(f'Nutrient Imbalance Check completed. {len(alerts)} alerts generated.')
    print(f'Results saved to: {output_file}')
except Exception as e:
    print(f'Error saving results: {e}')
    sys.exit(1)