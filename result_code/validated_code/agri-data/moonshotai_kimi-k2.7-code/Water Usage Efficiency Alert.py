"""
Task: Water Usage Efficiency Alert
Description: Flag records where Water_Usage_Efficiency exceeds a defined threshold, indicating poor water use performance.
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

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

TASK_NAME = 'water_usage_efficiency_alert'


def find_project_root():
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / 'data').exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent
    return root_dir


def resolve_input_file(root_dir):
    for fname in ('raw_data.csv', 'raw_data.txt'):
        p = root_dir / 'data' / 'agri-data' / fname
        if p.exists():
            return p
    return None


MISSING = {'', 'NA', 'N/A', 'None', 'NULL', 'None', 'nan'}


def is_missing(value):
    if value is None:
        return True
    s = str(value).strip()
    return s in MISSING


def to_float(value, col_name):
    if is_missing(value):
        return None
    try:
        return float(value)
    except Exception:
        print(f'Warning: cannot parse {col_name} value {value!r}; treating as missing', file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser(description='Water Usage Efficiency Alert')
    parser.add_argument('--threshold', type=float, default=12.5, help='Poor water use threshold (default 12.5)')
    parser.add_argument('--strict', action='store_true', help='Drop rows with missing Water_Usage_Efficiency')
    args = parser.parse_args()

    root_dir = find_project_root()
    data_file = resolve_input_file(root_dir)
    if data_file is None:
        print('Error: raw_data.csv or raw_data.txt not found under data/agri-data/', file=sys.stderr)
        sys.exit(1)

    col = 'water_usage_efficiency'
    records_total = 0
    dropped = 0
    values = []
    flagged = []

    try:
        with open(data_file, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                print('Error: input file has no header', file=sys.stderr)
                sys.exit(1)
            fieldnames_lower = [fn.lower().strip() for fn in reader.fieldnames]
            if col not in fieldnames_lower:
                print(f'Error: required column {col} not found. Available: {fieldnames_lower}', file=sys.stderr)
                sys.exit(1)
            for idx, row in enumerate(reader, start=2):
                records_total += 1
                row = {k.lower().strip(): v for k, v in row.items()}
                wue = to_float(row.get(col), 'Water_Usage_Efficiency')
                if wue is None:
                    dropped += 1
                    if args.strict:
                        continue
                    continue
                values.append(wue)
                if wue > args.threshold:
                    flagged.append({
                        'row': idx,
                        'label': row.get('label'),
                        'water_usage_efficiency': wue
                    })
    except Exception as e:
        print(f'Error reading input file: {e}', file=sys.stderr)
        sys.exit(1)

    out_dir = Path('/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_moonshotai_kimi-k2.7-code_anthropic_claude-3-haiku_run2')
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f'{TASK_NAME}_result.json'

    summary = {
        'task_name': 'Water Usage Efficiency Alert',
        'description': 'Flag records where Water_Usage_Efficiency exceeds a defined threshold, indicating poor water use performance.',
        'result_summary': [
            {
                'input_file': str(data_file),
                'threshold': args.threshold,
                'total_rows': records_total,
                'missing_water_usage_efficiency': dropped,
                'valid_rows': len(values),
                'alert_count': len(flagged),
                'mean_water_usage_efficiency': round(sum(values) / len(values), 4) if values else None,
                'max_water_usage_efficiency': round(max(values), 4) if values else None,
                'flagged_records': flagged[:100]
            }
        ],
        'result_generated_at': datetime.now(timezone.utc).isoformat()
    }

    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    print(f'Result saved to {out_file}')
    print(f'Alerts: {len(flagged)} of {len(values)} valid rows exceed threshold {args.threshold}')


if __name__ == '__main__':
    main()