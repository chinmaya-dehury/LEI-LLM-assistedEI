"""
Task: Mote Activity Count
Description: Count the number of readings received per mote within a fixed time window to identify inactive or failing nodes.
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

import os
import csv
import json
import sys
import math
from pathlib import Path
from collections import defaultdict
from datetime import datetime

TASK_NAME = 'Mote Activity Count'


def find_data_file():
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / 'data').exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent
    for name in ('raw_data.csv', 'raw_data.txt'):
        candidate = root_dir / 'data' / 'lab-data' / name
        if candidate.exists():
            return candidate
    return None


def to_int(value, column):
    if value is None or value == '':
        return None
    try:
        return int(float(value))
    except Exception:
        print(f'Warning: invalid integer in column {column}: {value!r}')
        return None


def parse_datetime(row):
    date_part = row.get('date', '').strip()
    time_part = row.get('time', '').strip()
    if not date_part or not time_part:
        return None
    time_whole = time_part.split('.')[0]
    try:
        return datetime.strptime(f'{date_part} {time_whole}', '%Y-%m-%d %H:%M:%S')
    except Exception:
        return None


def main():
    data_file = find_data_file()
    if not data_file:
        print('Error: data/lab-data/raw_data.csv or raw_data.txt not found')
        sys.exit(1)

    print(f'Reading {data_file}')

    missing_placeholders = {'', 'NA', 'N/A', 'None', 'None'}
    counts = defaultdict(int)
    total_rows = 0
    dropped_rows = 0
    window_start = None
    window_end = None

    with open(data_file, newline='') as f:
        reader = csv.DictReader(f)
        for raw_row in reader:
            row = {k.lower(): (v if v not in missing_placeholders else '') for k, v in raw_row.items()}
            total_rows += 1

            mote_id = to_int(row.get('moteid'), 'moteid')
            if mote_id is None:
                dropped_rows += 1
                continue

            counts[mote_id] += 1

            dt = parse_datetime(row)
            if dt:
                if window_start is None or dt < window_start:
                    window_start = dt
                if window_end is None or dt > window_end:
                    window_end = dt

    all_motes = set(range(1, 55))
    active_motes = set(counts.keys())
    inactive_motes = sorted(all_motes - active_motes)

    mote_summary = []
    for mote in sorted(active_motes):
        mote_summary.append({'moteid': mote, 'reading_count': counts[mote], 'active': True})
    for mote in inactive_motes:
        mote_summary.append({'moteid': mote, 'reading_count': 0, 'active': False})

    result = {
        'task_name': TASK_NAME,
        'description': 'Count the number of readings received per mote within the observed time window to identify inactive or failing nodes.',
        'result_summary': [
            {
                'total_rows_read': total_rows,
                'dropped_rows': dropped_rows,
                'time_window': {
                    'start': window_start.isoformat() if window_start else None,
                    'end': window_end.isoformat() if window_end else None
                },
                'active_mote_count': len(active_motes),
                'inactive_mote_count': len(inactive_motes),
                'mote_counts': mote_summary
            }
        ],
        'result_generated_at': datetime.utcnow().isoformat() + 'Z'
    }

    out_dir = Path('/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_moonshotai_kimi-k2.7-code_google_gemini-3.1-flash-lite_run1')
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f'{TASK_NAME}_result.json'

    with open(out_file, 'w') as f:
        json.dump(result, f, indent=2)

    print(f'Saved result to {out_file}')
    print(f'Active motes: {len(active_motes)}, Inactive motes: {len(inactive_motes)}, Dropped rows: {dropped_rows}')


if __name__ == '__main__':
    main()