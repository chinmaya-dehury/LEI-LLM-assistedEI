import json
import sys
import csv
"""
Task: Frost Risk Alert
Description: Trigger an alert when the Frost_Risk index exceeds a safety threshold, indicating possible frost damage risk.
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

import os, sys, csv, json, argparse
from pathlib import Path
from datetime import datetime, timezone

def find_data_file():
    curr = Path(__file__).resolve().parent
    root = curr
    while root.name and not (root / 'data').exists():
        parent = root.parent
        if parent == root:
            break
        root = parent
    for name in ('raw_data.csv', 'raw_data.txt'):
        p = root / 'data' / 'agri-data' / name
        if p.exists():
            return p
    return None

def is_missing(v):
    if v is None:
        return True
    s = str(v).strip()
    return s == '' or s.lower() in {'na', 'n/a', 'None', 'none'}

def to_float(v, col):
    if is_missing(v):
        return None
    try:
        return float(v)
    except ValueError:
        print('Warning: invalid numeric value in column %r: %r' % (col, v), file=sys.stderr)
        return None

def main():
    parser = argparse.ArgumentParser(description='Frost Risk Alert')
    parser.add_argument('--threshold', type=float, default=0.15, help='Frost risk alert threshold')
    parser.add_argument('--strict', action='store_true', help='Skip rows with missing Frost_Risk')
    args = parser.parse_args()

    data_file = find_data_file()
    if not data_file:
        print('Error: raw_data.csv or raw_data.txt not found under data/agri-data/', file=sys.stderr)
        sys.exit(1)

    out_dir = Path('/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_moonshotai_kimi-k2.7-code_nvidia_nemotron-3-ultra-550b-a55b_run1')
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / 'Frost Risk Alert_result.json'

    alerts = []
    values = []
    dropped = 0
    total = 0
    with open(data_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            total += 1
            row = {k.lower(): v for k, v in row.items()}
            if 'frost_risk' not in row:
                dropped += 1
                continue
            fr = to_float(row.get('frost_risk'), 'frost_risk')
            if fr is None:
                dropped += 1
                continue
            values.append(fr)
            if fr > args.threshold:
                alerts.append({'row': idx, 'frost_risk': fr})

    if not values:
        print('No valid Frost_Risk values found.')
        summary = {
            'threshold': args.threshold,
            'total_rows': total,
            'valid_rows': 0,
            'dropped_rows': dropped,
            'alert_count': 0,
            'alert_triggered': False,
            'max_frost_risk': None,
            'mean_frost_risk': None,
            'alerts': []
        }
    else:
        summary = {
            'threshold': args.threshold,
            'total_rows': total,
            'valid_rows': len(values),
            'dropped_rows': dropped,
            'alert_count': len(alerts),
            'alert_triggered': len(alerts) > 0,
            'max_frost_risk': max(values),
            'mean_frost_risk': round(sum(values) / len(values), 6),
            'alerts': alerts
        }
        print('Frost risk threshold: %s' % args.threshold)
        print('Rows processed: %s, valid: %s, dropped: %s' % (total, len(values), dropped))
        print('Alerts triggered: %s (max risk %.3f)' % (len(alerts), summary['max_frost_risk']))

    result = {
        'task_name': 'Frost Risk Alert',
        'description': 'Trigger an alert when the Frost_Risk index exceeds a safety threshold, indicating possible frost damage risk.',
        'result_summary': [summary],
        'result_generated_at': datetime.now(timezone.utc).isoformat()
    }

    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
    print('Result saved to %s' % out_file)

if __name__ == '__main__':
    main()