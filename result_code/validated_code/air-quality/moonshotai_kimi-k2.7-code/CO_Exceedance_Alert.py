"""
Task: CO_Exceedance_Alert
Description: Compare the latest hourly averaged CO(GT) concentration against a configurable safe threshold and emit an alert when the threshold is exceeded.
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
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

TASK_NAME = 'CO_Exceedance_Alert'
OUTPUT_DIR = Path('/home/dcc/LEI-Models-Comparision/output/air-quality/air-quality_moonshotai_kimi-k2.7-code_anthropic_claude-3-haiku_run1')
MISSING = {'', 'na', 'n/a', 'None', 'none', '-200'}

def find_data_file():
    curr = Path(__file__).resolve().parent
    root = curr
    while root.name and not (root / 'data').exists():
        parent = root.parent
        if parent == root:
            break
        root = parent
    for name in ('raw_data.csv', 'raw_data.txt'):
        candidate = root / 'data' / 'air-quality' / name
        if candidate.exists():
            return candidate
    return None

def is_missing(value):
    if value is None:
        return True
    return str(value).strip().lower() in MISSING

def to_float(value, col):
    if is_missing(value):
        return None
    try:
        return float(value)
    except Exception:
        print(f'Warning: invalid numeric value in {col}: {value!r}', file=sys.stderr)
        return None

def parse_dt(date_str, time_str):
    try:
        return datetime.strptime(f'{date_str.strip()} {time_str.strip()}', '%d-%m-%Y %H:%M:%S')
    except Exception:
        return None

def main():
    parser = argparse.ArgumentParser(description='CO exceedance alert')
    parser.add_argument('--threshold', type=float, default=10.0, help='CO safe threshold in mg/m^3')
    parser.add_argument('--strict', action='store_true', help='require valid CO for latest row')
    args = parser.parse_args()

    data_file = find_data_file()
    if not data_file:
        print('Error: raw_data.csv/txt not found under data/air-quality/', file=sys.stderr)
        sys.exit(1)

    latest_dt = None
    latest_co = None
    latest_row_num = None
    dropped = 0
    total = 0

    with open(data_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=2):
            total += 1
            row = {k.lower().strip(): v for k, v in row.items()}
            date_str = row.get('date')
            time_str = row.get('time')
            if not date_str or not time_str:
                dropped += 1
                print(f'Warning: row {i} missing date/time', file=sys.stderr)
                continue
            dt = parse_dt(date_str, time_str)
            if dt is None:
                dropped += 1
                print(f'Warning: row {i} bad date/time: {date_str} {time_str}', file=sys.stderr)
                continue
            co = to_float(row.get('co(gt)'), 'CO(GT)')
            if co is None:
                dropped += 1
                if args.strict:
                    print(f'Warning: row {i} missing/invalid CO', file=sys.stderr)
                continue
            if latest_dt is None or dt > latest_dt:
                latest_dt = dt
                latest_co = co
                latest_row_num = i

    if latest_co is None:
        print('Error: no valid CO measurement found', file=sys.stderr)
        sys.exit(1)

    alert = latest_co > args.threshold
    status = 'ALERT' if alert else 'OK'
    message = f'Latest CO at {latest_dt.isoformat()} is {latest_co:.4f} mg/m^3 ({status}, threshold {args.threshold:.2f})'
    print(message)

    result = {
        'task_name': TASK_NAME,
        'description': 'Compare the latest hourly averaged CO(GT) concentration against a configurable safe threshold and emit an alert when the threshold is exceeded.',
        'result_summary': [
            {
                'latest_timestamp': latest_dt.isoformat(),
                'latest_row': latest_row_num,
                'co_mg_m3': round(latest_co, 4),
                'threshold_mg_m3': round(args.threshold, 2),
                'alert': alert,
                'status': status,
                'total_rows_read': total,
                'rows_with_valid_co': total - dropped
            }
        ],
        'result_generated_at': datetime.now(timezone.utc).isoformat()
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f'{TASK_NAME}_result.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
    print(f'Result saved to {out_path}')

if __name__ == '__main__':
    main()