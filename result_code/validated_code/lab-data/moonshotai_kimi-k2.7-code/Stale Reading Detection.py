import re
"""
Task: Stale Reading Detection
Description: Monitor the elapsed time since the last reported reading for each mote and raise an alert when a mote has not reported within an expected interval, indicating communication or sensor failure.
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

DATA_FILE_PATH = os.path.join(_root_dir, "data", "lab-data", "raw_data.csv")
if not os.path.exists(DATA_FILE_PATH):
    DATA_FILE_PATH = os.path.join(_root_dir, "data", "lab-data", "raw_data.txt")

METADATA_FILE_PATH = os.path.join(_root_dir, "data", "lab-data", "metadata.json")
OUTPUT_DIR = os.path.join(_root_dir, "output", "lab-data")
os.makedirs(OUTPUT_DIR, exist_ok=True)

#!/usr/bin/env python3
import argparse
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path

MISSING = {'', 'na', 'n/a', 'None', 'none'}


def find_data_file(root_dir):
    for name in ('raw_data.csv', 'raw_data.txt'):
        p = root_dir / 'data' / 'lab-data' / name
        if p.exists():
            return p
    return None


def safe_float(value, col):
    if value is None:
        return None
    s = str(value).strip()
    if s.lower() in MISSING:
        return None
    try:
        return float(s)
    except ValueError:
        print(f'Warning: invalid numeric value in {col}: {value!r}', file=sys.stderr)
        return None


def parse_ts(row):
    d = row.get('date', '').strip()
    t = row.get('time', '').strip()
    if not d or not t:
        return None
    try:
        return datetime.fromisoformat(f'{d}T{t}')
    except ValueError as e:
        print(f'Warning: invalid timestamp date={d!r} time={t!r}: {e}', file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser(description='Detect stale sensor readings.')
    parser.add_argument('--threshold', type=float, default=300.0,
                        help='Stale threshold in seconds (default: 300)')
    parser.add_argument('--strict', action='store_true',
                        help='Skip rows missing required fields')
    args = parser.parse_args()

    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / 'data').exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent

    data_file = find_data_file(root_dir)
    if not data_file:
        print(f'Error: raw_data.csv/txt not found under {root_dir / "data" / "lab-data"}', file=sys.stderr)
        sys.exit(1)

    out_dir = Path('/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_moonshotai_kimi-k2.7-code_anthropic_claude-3-haiku_run1')
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / 'stale_reading_detection_result.json'

    required = {'date', 'time', 'moteid'}
    last_by_mote = {}
    global_latest = None
    total_rows = 0
    dropped = 0

    with open(data_file, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for raw_row in reader:
            total_rows += 1
            row = {k.lower(): (v.strip() if v else '') for k, v in raw_row.items()}

            missing_cols = required - set(row.keys())
            if missing_cols:
                print(f'Warning: missing columns {missing_cols} at row {total_rows}', file=sys.stderr)
                dropped += 1
                continue

            mote = row.get('moteid', '').strip()
            if not mote or mote.lower() in MISSING:
                dropped += 1
                continue

            ts = parse_ts(row)
            if ts is None:
                dropped += 1
                continue

            prev = last_by_mote.get(mote)
            if prev is None or ts > prev['ts']:
                epoch = row.get('epoch', '').strip()
                last_by_mote[mote] = {'ts': ts, 'epoch': epoch}

            if global_latest is None or ts > global_latest:
                global_latest = ts

    if global_latest is None:
        print('Error: no valid timestamps found', file=sys.stderr)
        sys.exit(1)

    alerts = []
    for mote in sorted(last_by_mote, key=lambda x: int(x) if x.isdigit() else x):
        info = last_by_mote[mote]
        gap = (global_latest - info['ts']).total_seconds()
        if gap > args.threshold:
            alerts.append({
                'moteid': mote,
                'last_reading_timestamp': info['ts'].isoformat(),
                'last_epoch': info['epoch'],
                'seconds_since_last_reading': round(gap, 3),
                'status': 'STALE'
            })

    summary = {
        'task_name': 'Stale Reading Detection',
        'description': 'Detect motes that have not reported within the expected interval based on the latest dataset timestamp.',
        'result_summary': [
            {'total_rows_processed': total_rows},
            {'dropped_invalid_rows': dropped},
            {'latest_dataset_timestamp': global_latest.isoformat()},
            {'stale_threshold_seconds': args.threshold},
            {'mote_count': len(last_by_mote)},
            {'stale_mote_count': len(alerts)},
            {'stale_motes': alerts}
        ],
        'result_generated_at': datetime.utcnow().isoformat() + 'Z'
    }

    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)

    print(f'Result saved to {out_file}')
    print(f'Stale motes: {len(alerts)} / {len(last_by_mote)}')


if __name__ == '__main__':
    main()