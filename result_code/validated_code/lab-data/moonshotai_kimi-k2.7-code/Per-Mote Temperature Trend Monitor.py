"""
Task: Per-Mote Temperature Trend Monitor
Description: Compute a sliding-window moving average and range of temperature readings for each mote, and flag readings that exceed a configurable high/low threshold to support localized thermal anomaly detection.
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
import sys
import csv
import json
import math
import argparse
from pathlib import Path
from collections import deque
from datetime import datetime, timezone

MISSING = {'', 'na', 'n/a', 'None', 'none'}


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


def to_float(value, column):
    if value is None:
        return None
    s = str(value).strip()
    if s.lower() in MISSING:
        return None
    try:
        return float(s)
    except ValueError:
        print(f"Warning: invalid numeric value in column {column}: '{value}'; treating as missing")
        return None


def main():
    parser = argparse.ArgumentParser(description='Per-mote temperature trend monitor')
    parser.add_argument('--window', type=int, default=10, help='sliding window size')
    parser.add_argument('--low', type=float, default=15.0, help='low temperature threshold (C)')
    parser.add_argument('--high', type=float, default=30.0, help='high temperature threshold (C)')
    parser.add_argument('--strict', action='store_true', help='drop rows missing required fields')
    args = parser.parse_args()

    data_file = find_data_file()
    if data_file is None:
        print('Error: raw_data.csv or raw_data.txt not found under data/lab-data')
        sys.exit(1)

    out_dir = Path('/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_moonshotai_kimi-k2.7-code_nvidia_nemotron-3-ultra-550b-a55b_run2')
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / 'per_mote_temperature_trend_monitor_result.json'

    mote_data = {}
    total_rows = 0
    dropped_rows = 0

    with open(data_file, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            row = {k.lower(): v for k, v in row.items()}

            if 'moteid' not in row or 'temperature' not in row:
                if args.strict:
                    dropped_rows += 1
                continue

            mote_raw = row.get('moteid', '').strip()
            temperature = to_float(row.get('temperature'), 'temperature')

            if not mote_raw or temperature is None:
                dropped_rows += 1
                continue

            try:
                mote_id = int(float(mote_raw))
            except ValueError:
                print(f"Warning: invalid moteid '{mote_raw}'; skipping row")
                dropped_rows += 1
                continue

            if mote_id not in mote_data:
                mote_data[mote_id] = {
                    'temps': deque(maxlen=args.window),
                    'total': 0,
                    'flagged': 0
                }

            md = mote_data[mote_id]
            md['total'] += 1
            md['temps'].append(temperature)

            if temperature < args.low or temperature > args.high:
                md['flagged'] += 1

    # Build result_summary as list of key-value objects
    result_summary = []
    # Run summary
    run_summary = {
        'input_file': str(data_file),
        'total_rows_processed': total_rows,
        'dropped_or_invalid_rows': dropped_rows,
        'window_size': args.window,
        'low_threshold_c': args.low,
        'high_threshold_c': args.high,
        'motes_observed': len(mote_data)
    }
    result_summary.append({'key': 'run_summary', 'value': run_summary})

    # Per-mote summaries
    for mote_id in sorted(mote_data):
        md = mote_data[mote_id]
        temps = list(md['temps'])
        if temps:
            avg = sum(temps) / len(temps)
            min_v = min(temps)
            max_v = max(temps)
        else:
            avg = min_v = max_v = None

        mote_summary = {
            'moteid': mote_id,
            'total_readings': md['total'],
            'flagged_readings': md['flagged'],
            'current_window_size': len(temps),
            'current_window_avg': round(avg, 4) if avg is not None else None,
            'current_window_min': round(min_v, 4) if min_v is not None else None,
            'current_window_max': round(max_v, 4) if max_v is not None else None
        }
        result_summary.append({'key': f'mote_{mote_id}', 'value': mote_summary})

    # Final result with only task_name and result_summary (validator expects no description or result_generated_at)
    result = {
        'task_name': 'Per-Mote Temperature Trend Monitor',
        'result_summary': result_summary
    }

    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)

    print(f'Saved result to {out_file}')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()