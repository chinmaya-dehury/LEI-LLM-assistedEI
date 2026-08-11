"""
Task: Missing Value Flagging
Description: Scan each incoming record for the -200 sentinel value used for missing or invalid measurements, and emit a per-column flag plus a count of missing values in the current window.
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

import argparse
import csv
import json
import sys
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

MISSING_SENTINELS = {'-200', '-200.0', '', 'na', 'n/a', 'None', 'none'}

def find_data_file():
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / 'data').exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent
    for fname in ('raw_data.csv', 'raw_data.txt'):
        candidate = root_dir / 'data' / 'air-quality' / fname
        if candidate.exists():
            return candidate
    return None

def numeric_is_missing(value, col=None, row_idx=None):
    if value is None:
        return True
    s = str(value).strip().lower()
    if s in MISSING_SENTINELS:
        return True
    try:
        num = float(s)
    except Exception as exc:
        if col is not None and row_idx is not None:
            print(f'WARNING: row {row_idx}, column {col}: cannot convert {value!r} to float ({exc}); treating as missing', file=sys.stderr)
        return True
    return num == -200.0

def parse_row(raw_row):
    clean = {}
    for k, v in raw_row.items():
        key = k.lower().strip() if k else ''
        if not key:
            continue
        clean[key] = v.strip() if v else ''
    return clean

def main():
    parser = argparse.ArgumentParser(description='Flag -200 sentinel missing values in air quality sensor records.')
    parser.add_argument('--window', type=int, default=24, help='Sliding window size in records')
    parser.add_argument('--strict', action='store_true', help='Exit if required Date/Time columns are missing')
    args = parser.parse_args()

    data_file = find_data_file()
    if not data_file:
        print('ERROR: raw_data.csv or raw_data.txt not found under data/air-quality/', file=sys.stderr)
        sys.exit(1)

    output_dir = Path('/home/dcc/LEI-Models-Comparision/output/air-quality/air-quality_moonshotai_kimi-k2.7-code_nvidia_nemotron-3-ultra-550b-a55b_run2')
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / 'missing_value_flagging_result.json'

    required = {'date', 'time'}
    numeric_cols = []
    window = deque(maxlen=args.window)
    total_missing = {}
    record_summaries = []
    dropped = 0
    row_count = 0

    try:
        with open(data_file, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                print('ERROR: input file has no header', file=sys.stderr)
                sys.exit(1)
            header = [h.strip().lower() for h in reader.fieldnames if h]
            missing_required = required - set(header)
            if missing_required:
                msg = f'ERROR: missing required columns: {sorted(missing_required)}'
                print(msg, file=sys.stderr)
                if args.strict:
                    sys.exit(1)
            numeric_cols = [h for h in header if h not in required]
            for col in numeric_cols:
                total_missing[col] = 0

            for idx, raw_row in enumerate(reader, start=1):
                try:
                    row = parse_row(raw_row)
                    if not row:
                        dropped += 1
                        continue
                    date_str = row.get('date', '')
                    time_str = row.get('time', '')
                    dt_str = f'{date_str} {time_str}'.strip()
                    flags = {}
                    for col in numeric_cols:
                        missing = numeric_is_missing(row.get(col, ''), col, idx)
                        flags[col] = missing
                        if missing:
                            total_missing[col] += 1
                    window.append(flags)
                    window_counts = {col: sum(1 for rec in window if rec.get(col)) for col in numeric_cols}
                    record_summaries.append({
                        'row': idx,
                        'timestamp': dt_str,
                        'missing_flags': flags,
                        'window_missing_count': window_counts
                    })
                    row_count += 1
                except Exception as exc:
                    print(f'WARNING: skipping row {idx}: {exc}', file=sys.stderr)
                    dropped += 1
    except Exception as exc:
        print(f'ERROR reading {data_file}: {exc}', file=sys.stderr)
        sys.exit(1)

    result = {
        'task_name': 'Missing Value Flagging',
        'description': 'Scan each incoming record for the -200 sentinel value used for missing or invalid measurements, and emit a per-column flag plus a count of missing values in the current window.',
        'result_summary': [{
            'window_size': args.window,
            'total_rows_processed': row_count,
            'rows_dropped': dropped,
            'total_missing_per_column': total_missing,
            'records': record_summaries
        }],
        'result_generated_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)

    print(f'Processed {row_count} records, dropped {dropped}. Results written to {output_file}')

if __name__ == '__main__':
    main()