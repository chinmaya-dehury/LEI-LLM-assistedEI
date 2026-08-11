"""
Task: Missing_Sensor_Data_Quality_Flag
Description: Count the number of -200 sentinel missing values per sensor per hour and report a lightweight data-quality summary for each hourly record.
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

DATA_FILE_PATH = os.path.join(_root_dir, "data", "air-quality", "raw_data.csv")
if not os.path.exists(DATA_FILE_PATH):
    DATA_FILE_PATH = os.path.join(_root_dir, "data", "air-quality", "raw_data.txt")

METADATA_FILE_PATH = os.path.join(_root_dir, "data", "air-quality", "metadata.json")
OUTPUT_DIR = os.path.join(_root_dir, "output", "air-quality")
os.makedirs(OUTPUT_DIR, exist_ok=True)

import os
import sys
import csv
import json
from pathlib import Path
from datetime import datetime

def find_project_root(start):
    root = start
    while root.name:
        if (root / 'data').exists():
            return root
        parent = root.parent
        if parent == root:
            break
        root = parent
    return start

def is_missing(val):
    if val is None:
        return True
    s = str(val).strip()
    if s == '':
        return True
    if s.upper() in ('NA', 'N/A', 'NULL'):
        return True
    if s == '-200':
        return True
    return False

def to_float(val):
    if is_missing(val):
        return None
    try:
        return float(val)
    except Exception:
        return None

curr_dir = Path(__file__).resolve().parent
root_dir = find_project_root(curr_dir)

data_file = root_dir / 'data' / 'air-quality' / 'raw_data.csv'
if not data_file.exists():
    data_file = root_dir / 'data' / 'air-quality' / 'raw_data.txt'

if not data_file.exists():
    print(f'Input file not found: {data_file}', file=sys.stderr)
    sys.exit(1)

out_dir = Path('/home/dcc/LEI-Models-Comparision/output/air-quality/air-quality_moonshotai_kimi-k2.7-code_anthropic_claude-3-haiku_run2')
out_dir.mkdir(parents=True, exist_ok=True)
out_file = out_dir / 'Missing_Sensor_Data_Quality_Flag_result.json'

numeric_cols = []
per_sensor_counts = {}
records = []
dropped_rows = 0
total_rows = 0

with open(data_file, 'r', newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    if reader.fieldnames is None:
        print('Empty input file.', file=sys.stderr)
        sys.exit(1)
    fieldnames = [fn.lower().strip() for fn in reader.fieldnames if fn.strip() != '']
    numeric_cols = [c for c in fieldnames if c not in ('date', 'time')]
    for c in numeric_cols:
        per_sensor_counts[c] = 0

    for idx, raw_row in enumerate(reader, start=2):
        total_rows += 1
        try:
            row = {k.lower().strip(): v for k, v in raw_row.items() if k is not None and k.strip() != ''}
        except Exception as e:
            dropped_rows += 1
            print(f'Row {idx}: failed to normalize keys: {e}')
            continue

        date_str = row.get('date', '').strip()
        time_str = row.get('time', '').strip()
        dt_str = ''
        if date_str and time_str:
            try:
                dt = datetime.strptime(f'{date_str} {time_str}', '%d-%m-%Y %H:%M:%S')
                dt_str = dt.isoformat()
            except Exception:
                dt_str = f'{date_str} {time_str}'

        missing_sensors = []
        row_missing_count = 0
        for col in numeric_cols:
            val = row.get(col, '')
            if is_missing(val):
                row_missing_count += 1
                missing_sensors.append(col)
                per_sensor_counts[col] = per_sensor_counts.get(col, 0) + 1
            else:
                fv = to_float(val)
                if fv is None:
                    print(f'Row {idx}, col {col}: invalid numeric value "{val}"')
                    row_missing_count += 1
                    missing_sensors.append(col)
                    per_sensor_counts[col] = per_sensor_counts.get(col, 0) + 1

        records.append({
            'timestamp': dt_str,
            'date': date_str,
            'time': time_str,
            'missing_sensor_count': row_missing_count,
            'missing_sensors': missing_sensors
        })

overall = {
    'total_rows': total_rows,
    'rows_parsed': total_rows - dropped_rows,
    'dropped_rows': dropped_rows,
    'sentinel_missing_per_sensor': per_sensor_counts,
    'total_sentinel_missing': sum(per_sensor_counts.values())
}

result = {
    'task_name': 'Missing_Sensor_Data_Quality_Flag',
    'description': 'Count the number of -200 sentinel missing values per sensor per hour and report a lightweight data-quality summary for each hourly record.',
    'result_summary': [overall, {'hourly_records': records}],
    'result_generated_at': datetime.utcnow().isoformat() + 'Z'
}

with open(out_file, 'w', encoding='utf-8') as f:
    json.dump(result, f, indent=2)

print(f'Result saved to {out_file}')
print(f'Total rows: {total_rows}, dropped: {dropped_rows}, sentinel missing values: {overall["total_sentinel_missing"]}')