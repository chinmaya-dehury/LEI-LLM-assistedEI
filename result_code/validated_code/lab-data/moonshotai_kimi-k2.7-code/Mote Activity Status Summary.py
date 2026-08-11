"""
Task: Mote Activity Status Summary
Description: Count the number of readings per mote within a configurable time window and flag motes with zero or unusually low activity to support sensor health monitoring.
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
from datetime import datetime

TASK_NAME = 'Mote Activity Status Summary'
OUTPUT_DIR = Path('/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_moonshotai_kimi-k2.7-code_nvidia_nemotron-3-ultra-550b-a55b_run1')
DEFAULT_MAX_MOTES = 54
MISSING_TOKENS = {'', 'NA', 'N/A', 'None', 'NULL', 'None'}


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
    data_dir = root_dir / 'data' / 'lab-data'
    for name in ['raw_data.csv', 'raw_data.txt']:
        candidate = data_dir / name
        if candidate.exists():
            return candidate
    return None


def to_float(value, column):
    if value is None:
        return None
    if str(value).strip() in MISSING_TOKENS:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        print(f'Warning: invalid numeric value in column {column}: {value!r}', file=sys.stderr)
        return None


def parse_datetime(date_str, time_str):
    if not date_str or not time_str:
        return None
    if str(date_str).strip() in MISSING_TOKENS or str(time_str).strip() in MISSING_TOKENS:
        return None
    try:
        return datetime.strptime(f'{date_str.strip()} {time_str.strip()}', '%Y-%m-%d %H:%M:%S.%f')
    except ValueError:
        try:
            return datetime.strptime(f'{date_str.strip()} {time_str.strip()}', '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return None


def main():
    parser = argparse.ArgumentParser(description='Mote Activity Status Summary')
    parser.add_argument('--window-start', type=str, default=None, help='Start datetime in ISO format (e.g., 2004-02-28T00:00:00)')
    parser.add_argument('--window-end', type=str, default=None, help='End datetime in ISO format')
    parser.add_argument('--low-threshold', type=int, default=None, help='Absolute threshold below which a mote is flagged as low activity')
    parser.add_argument('--max-motes', type=int, default=DEFAULT_MAX_MOTES, help='Total number of motes expected in the network')
    parser.add_argument('--strict', action='store_true', help='Exit on missing required columns instead of continuing')
    args = parser.parse_args()

    window_start = datetime.fromisoformat(args.window_start) if args.window_start else None
    window_end = datetime.fromisoformat(args.window_end) if args.window_end else None

    root_dir = find_project_root()
    data_file = resolve_input_file(root_dir)
    if data_file is None:
        print('Error: input file raw_data.csv or raw_data.txt not found under data/lab-data/', file=sys.stderr)
        sys.exit(1)

    counts = {}
    total_rows = 0
    dropped_rows = 0
    required_columns = {'date', 'time', 'moteid'}

    with open(data_file, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            print('Error: input file has no headers', file=sys.stderr)
            sys.exit(1)

        fieldnames = [name.lower().strip() for name in reader.fieldnames]
        if not required_columns.issubset(fieldnames):
            missing = required_columns - set(fieldnames)
            msg = f'Error: missing required columns: {missing}'
            if args.strict:
                print(msg, file=sys.stderr)
                sys.exit(1)
            else:
                print(msg, file=sys.stderr)

        for row in reader:
            total_rows += 1
            row = {k.lower().strip(): v for k, v in row.items()}

            if not required_columns.issubset(row.keys()):
                dropped_rows += 1
                continue

            dt = parse_datetime(row.get('date'), row.get('time'))
            if dt is None:
                dropped_rows += 1
                continue

            if window_start and dt < window_start:
                continue
            if window_end and dt > window_end:
                continue

            mote_val = row.get('moteid')
            if str(mote_val).strip() in MISSING_TOKENS:
                dropped_rows += 1
                continue
            try:
                mote_id = int(mote_val)
            except (ValueError, TypeError):
                dropped_rows += 1
                continue

            counts[mote_id] = counts.get(mote_id, 0) + 1

    max_mote = args.max_motes
    total_readings = sum(counts.values())
    active_motes = set(counts.keys())

    if args.low_threshold is not None:
        low_threshold = args.low_threshold
    else:
        if counts:
            mean_count = total_readings / max_mote
            low_threshold = max(1, int(math.floor(mean_count * 0.25)))
        else:
            low_threshold = 1

    result_summary = []
    zero_motes = 0
    low_motes = 0
    active_count = 0

    for mote_id in range(1, max_mote + 1):
        count = counts.get(mote_id, 0)
        is_active = count > 0
        is_zero = count == 0
        is_low = is_active and count < low_threshold
        if is_active:
            active_count += 1
        if is_zero:
            zero_motes += 1
        if is_low:
            low_motes += 1
        result_summary.append({
            'mote_id': mote_id,
            'reading_count': count,
            'active': is_active,
            'zero_activity': is_zero,
            'low_activity': is_low
        })

    summary = {
        'total_motes': max_mote,
        'active_motes': active_count,
        'zero_activity_motes': zero_motes,
        'low_activity_motes': low_motes,
        'total_readings_in_window': total_readings,
        'window_start': args.window_start,
        'window_end': args.window_end,
        'low_activity_threshold': low_threshold,
        'input_file': str(data_file),
        'total_rows_parsed': total_rows,
        'dropped_or_invalid_rows': dropped_rows
    }

    result_summary.insert(0, summary)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / 'mote_activity_status_summary_result.json'
    result = {
        'task_name': TASK_NAME,
        'description': 'Count the number of readings per mote within a configurable time window and flag motes with zero or unusually low activity to support sensor health monitoring.',
        'result_summary': result_summary,
        'result_generated_at': datetime.utcnow().isoformat() + 'Z'
    }
    with open(output_file, 'w', encoding='utf-8') as out:
        json.dump(result, out, indent=2)

    print(f'Results saved to {output_file}')
    print(f'Total motes: {max_mote}, Active: {active_count}, Zero activity: {zero_motes}, Low activity: {low_motes}')


if __name__ == '__main__':
    main()