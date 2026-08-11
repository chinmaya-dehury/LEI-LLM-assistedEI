from datetime import datetime
"""
Task: Sensor Staleness Detector
Description: Measure the elapsed time since the last reading for each mote and report motes that have not reported within a configurable timeout window, supporting sensor health monitoring.
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

import argparse
import csv
import datetime
import json
import sys
from pathlib import Path

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
    for name in ('raw_data.csv', 'raw_data.txt'):
        candidate = root_dir / 'data' / 'lab-data' / name
        if candidate.exists():
            return candidate
    return None

def parse_datetime(date_str, time_str):
    try:
        d = date_str.strip()
        t = time_str.strip()
        if not d or not t:
            return None
        if '.' in t:
            base, frac = t.split('.', 1)
            frac = frac.ljust(6, '0')[:6]
            t = f'{base}.{frac}'
        dt_str = f'{d} {t}'
        return datetime.datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S.%f')
    except Exception:
        return None

def is_missing(value):
    if value is None:
        return True
    value = str(value).strip()
    return value == '' or value.upper() in ('NA', 'N/A', 'NULL', 'NONE', 'NAN')

def main():
    parser = argparse.ArgumentParser(description='Sensor staleness detector')
    parser.add_argument('--timeout', type=int, default=300, help='Stale threshold in seconds (default 300)')
    parser.add_argument('--strict', action='store_true', help='Exit on invalid rows')
    args = parser.parse_args()

    root_dir = find_project_root()
    data_file = resolve_input_file(root_dir)
    if not data_file:
        print('Error: raw_data.csv or raw_data.txt not found under data/lab-data/', file=sys.stderr)
        sys.exit(1)

    output_dir = Path('/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_moonshotai_kimi-k2.7-code_nvidia_nemotron-3-ultra-550b-a55b_run2')
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / 'sensor_staleness_detector_result.json'

    last_by_mote = {}
    invalid_rows = 0
    parsed_rows = 0

    required_cols = {'date', 'time', 'moteid'}
    with open(data_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            print('Error: input file has no header', file=sys.stderr)
            sys.exit(1)
        fieldnames_lower = {fn.lower() for fn in reader.fieldnames}
        missing_cols = required_cols - fieldnames_lower
        if missing_cols:
            print(f'Error: required columns missing: {missing_cols}', file=sys.stderr)
            sys.exit(1)

        for row_num, raw_row in enumerate(reader, start=2):
            row = {k.lower(): v for k, v in raw_row.items()}
            if any(is_missing(row.get(col)) for col in required_cols):
                invalid_rows += 1
                print(f'Row {row_num}: missing required value (date/time/moteid)', file=sys.stderr)
                if args.strict:
                    sys.exit(2)
                continue

            mote_val = row.get('moteid')
            try:
                mote_id = int(float(mote_val))
            except Exception:
                invalid_rows += 1
                print(f'Row {row_num}: invalid moteid {mote_val}', file=sys.stderr)
                if args.strict:
                    sys.exit(2)
                continue

            date_val = row.get('date')
            time_val = row.get('time')
            dt = parse_datetime(date_val, time_val)
            if dt is None:
                invalid_rows += 1
                print(f'Row {row_num}: invalid date/time {date_val} {time_val}', file=sys.stderr)
                if args.strict:
                    sys.exit(2)
                continue

            parsed_rows += 1
            if mote_id not in last_by_mote or dt > last_by_mote[mote_id]:
                last_by_mote[mote_id] = dt

    if not last_by_mote:
        print('Error: no valid rows parsed', file=sys.stderr)
        sys.exit(1)

    reference_time = max(last_by_mote.values())
    summary = []
    for mote_id in sorted(last_by_mote.keys()):
        last_ts = last_by_mote[mote_id]
        elapsed = (reference_time - last_ts).total_seconds()
        stale = elapsed > args.timeout
        summary.append({
            'moteid': mote_id,
            'last_reading': last_ts.isoformat(),
            'reference_time': reference_time.isoformat(),
            'elapsed_seconds': elapsed,
            'timeout_seconds': args.timeout,
            'stale': stale,
            'status': 'stale' if stale else 'active'
        })

    result = {
        'task_name': 'Sensor Staleness Detector',
        'description': 'Measure elapsed time since the last reading for each mote and flag motes exceeding a configurable timeout.',
        'result_summary': summary,
        'result_generated_at': datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00', 'Z')
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)

    print(f'Processed {parsed_rows} rows, dropped {invalid_rows} invalid rows.')
    print(f'Reference time: {reference_time.isoformat()}')
    print(f'Stale motes (>{args.timeout}s): {sum(1 for s in summary if s["stale"])}')
    print(f'Result saved to {output_file}')

if __name__ == '__main__':
    main()