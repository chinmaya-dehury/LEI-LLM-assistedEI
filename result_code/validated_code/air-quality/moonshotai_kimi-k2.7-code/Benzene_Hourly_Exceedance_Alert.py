"""
Task: Benzene_Hourly_Exceedance_Alert
Description: Compare each hourly C6H6(GT) measurement against a configurable regulatory limit and emit an alert when an exceedance is detected.
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

#!/usr/bin/env python3
import argparse
import csv
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

TASK_NAME = 'Benzene_Hourly_Exceedance_Alert'
DESCRIPTION = 'Compare each hourly C6H6(GT) measurement against a configurable regulatory limit and emit an alert when an exceedance is detected.'
OUTPUT_DIR = Path('/home/dcc/LEI-Models-Comparision/output/air-quality/air-quality_moonshotai_kimi-k2.7-code_anthropic_claude-3-haiku_run2')
MISSING = {'', 'NA', 'N/A', 'None', 'NULL', 'None', 'nan', '-200'}

def find_data_file():
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / 'data').exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent
    for name in ('raw_data.csv', 'raw_data.txt'):
        candidate = root_dir / 'data' / 'air-quality' / name
        if candidate.exists():
            return candidate
    return None

def to_float(value, col):
    if value is None:
        return None
    s = str(value).strip()
    if s in MISSING:
        return None
    try:
        v = float(s)
    except ValueError:
        print(f'Warning: invalid numeric value in {col}: {value!r}', file=sys.stderr)
        return None
    if math.isnan(v):
        return None
    return v

def parse_timestamp(date_str, time_str):
    try:
        return datetime.strptime(f'{date_str.strip()} {time_str.strip()}', '%d-%m-%Y %H:%M:%S').replace(tzinfo=timezone.utc).isoformat()
    except Exception as e:
        return f'{date_str} {time_str}'

def main():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument('--limit', type=float, default=5.0, help='Benzene regulatory limit in microg/m^3')
    parser.add_argument('--strict', action='store_true', help='Exit if required columns are missing')
    args = parser.parse_args()

    data_file = find_data_file()
    if not data_file:
        print('Error: raw_data.csv or raw_data.txt not found under data/air-quality/', file=sys.stderr)
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / f'{TASK_NAME}_result.json'

    total_rows = 0
    valid_rows = 0
    missing_rows = 0
    exceedances = []
    alerts = []

    target_col = 'c6h6(gt)'
    date_col = 'date'
    time_col = 'time'

    with open(data_file, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            row = {k.lower(): v for k, v in row.items() if isinstance(k, str)}
            if target_col not in row:
                msg = f'Required column {target_col!r} missing at row {total_rows}'
                if args.strict:
                    print('Error:', msg, file=sys.stderr)
                    sys.exit(2)
                else:
                    print('Warning:', msg, file=sys.stderr)
                    missing_rows += 1
                    continue
            val = to_float(row.get(target_col), target_col)
            if val is None:
                missing_rows += 1
                continue
            valid_rows += 1
            if val > args.limit:
                ts = parse_timestamp(row.get(date_col, ''), row.get(time_col, ''))
                alert = {
                    'timestamp': ts,
                    'c6h6_gt_microg_m3': val,
                    'limit_microg_m3': args.limit,
                    'alert': True
                }
                alerts.append(alert)
                if len(exceedances) < 20:
                    exceedances.append(alert)

    summary = {
        'limit_microg_m3': args.limit,
        'total_rows_read': total_rows,
        'valid_benzene_readings': valid_rows,
        'missing_or_invalid_rows': missing_rows,
        'exceedance_count': len(alerts),
        'exceedance_rate': round(len(alerts) / valid_rows, 6) if valid_rows else None,
        'sample_exceedances': exceedances
    }

    result = {
        'task_name': TASK_NAME,
        'description': DESCRIPTION,
        'result_summary': [summary],
        'result_generated_at': datetime.now(timezone.utc).isoformat()
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
    print(f'{TASK_NAME}: {len(alerts)} exceedances out of {valid_rows} valid readings. Result saved to {output_file}')

if __name__ == '__main__':
    main()