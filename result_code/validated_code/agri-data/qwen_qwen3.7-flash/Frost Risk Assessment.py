"""
Task: Frost Risk Assessment
Description: Checks the Frost_Risk index against a predefined safety margin to trigger early warning alerts for potential crop damage.
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

# Define output path
output_dir = Path('/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_qwen_qwen3.7-flash_anthropic_claude-3-haiku_run1')
output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / 'frost_risk_assessment_result.json'

# Safety margin threshold for Frost_Risk (values above this trigger alerts)
FROST_RISK_THRESHOLD = 1

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

# Read and process data
rows = []
dropped_rows = 0
frost_alerts = []

try:
    with open(data_file, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Normalize keys to lowercase
            row = {k.lower(): v for k, v in row.items()}

            if 'frost_risk' not in row:
                dropped_rows += 1
                continue

            frost_risk = safe_float(row.get('frost_risk'))
            if frost_risk is None:
                dropped_rows += 1
                continue

            rows.append({
                'frost_risk': frost_risk,
                'label': row.get('label', 'unknown')
            })

            if frost_risk > FROST_RISK_THRESHOLD:
                frost_alerts.append({
                    'frost_risk': frost_risk,
                    'label': row.get('label', 'unknown')
                })

except Exception as e:
    print(f'Error reading data: {e}', file=sys.stderr)
    sys.exit(1)

# Calculate statistics
total_rows = len(rows)
alert_count = len(frost_alerts)
alert_percentage = (alert_count / total_rows * 100) if total_rows > 0 else 0.0

# Build result
result = {
    'task_name': 'Frost Risk Assessment',
    'description': 'Checks the Frost_Risk index against a predefined safety margin to trigger early warning alerts for potential crop damage.',
    'result_summary': [
        f'Total valid rows analyzed: {total_rows}',
        f'Rows dropped (missing/invalid frost_risk): {dropped_rows}',
        f'Frost risk alerts triggered: {alert_count}',
        f'Alert percentage: {alert_percentage:.2f}%',
        f'Safety margin threshold: {FROST_RISK_THRESHOLD}'
    ],
    'result_generated_at': datetime.now().isoformat()
}

# Save result
with open(output_file, 'w') as f:
    json.dump(result, f, indent=2)

print(f'Results saved to {output_file}')
print(f'Frost risk alerts: {alert_count}/{total_rows} ({alert_percentage:.2f}%)')