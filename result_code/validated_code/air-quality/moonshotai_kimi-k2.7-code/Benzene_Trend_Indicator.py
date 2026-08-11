"""
Task: Benzene_Trend_Indicator
Description: Estimate the short-term trend of C6H6(GT) over the last N hours using a lightweight endpoint-difference or incremental slope calculation.
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

import sys
import csv
import math
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta

MISSING_STRINGS = {'', 'NA', 'N/A', 'None', 'NULL', 'None'}
GT_SENTINEL = -200.0


def find_project_root():
    curr = Path(__file__).resolve().parent
    while curr.name and not (curr / 'data').exists():
        parent = curr.parent
        if parent == curr:
            break
        curr = parent
    return curr


def is_missing(raw):
    if raw is None:
        return True
    return str(raw).strip() in MISSING_STRINGS


def to_float(raw, col):
    if is_missing(raw):
        return None
    try:
        v = float(str(raw).strip())
    except ValueError:
        print(f'Warning: non-numeric value in {col}: {raw!r}', file=sys.stderr)
        return None
    if col == 'c6h6(gt)' and v <= -199.0:
        return None
    return v


def parse_datetime(row):
    d = row.get('date', '').strip()
    t = row.get('time', '').strip()
    if not d or not t:
        return None
    for fmt in ('%d-%m-%Y %H:%M:%S', '%Y-%m-%d %H:%M:%S'):
        try:
            return datetime.strptime(f'{d} {t}', fmt)
        except ValueError:
            continue
    return None


def main():
    parser = argparse.ArgumentParser(description='Benzene short-term trend indicator')
    parser.add_argument('--hours', type=int, default=24, help='Number of recent hours to analyse')
    parser.add_argument('--strict', action='store_true', help='Skip rows with missing benzene values')
    args = parser.parse_args()

    root = find_project_root()
    data_dir = root / 'data' / 'air-quality'
    data_file = data_dir / 'raw_data.csv'
    if not data_file.exists():
        data_file = data_dir / 'raw_data.txt'

    if not data_file.exists():
        print(f'Input file not found in {data_dir}', file=sys.stderr)
        sys.exit(1)

    records = []
    dropped = 0
    with open(data_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            row = {k.lower(): v for k, v in row.items()}
            if 'c6h6(gt)' not in row:
                dropped += 1
                continue
            dt = parse_datetime(row)
            val = to_float(row.get('c6h6(gt)'), 'c6h6(gt)')
            if dt is None or val is None:
                dropped += 1
                continue
            records.append((dt, val))

    if dropped:
        print(f'Note: {dropped} rows dropped due to missing/invalid datetime or C6H6(GT).')

    if len(records) < 2:
        print('Insufficient valid records to compute trend.', file=sys.stderr)
        sys.exit(1)

    records.sort(key=lambda x: x[0])
    latest = records[-1][0]
    cutoff = latest - timedelta(hours=args.hours)
    window = [r for r in records if r[0] >= cutoff]

    if len(window) < 2:
        window = records[-args.hours:] if len(records) >= args.hours else records

    start_dt, start_val = window[0]
    end_dt, end_val = window[-1]
    hours = (end_dt - start_dt).total_seconds() / 3600.0

    if hours <= 0:
        slope = math.nan
        direction = 'insufficient_time_span'
    else:
        slope = (end_val - start_val) / hours
        if slope > 0.05:
            direction = 'increasing'
        elif slope < -0.05:
            direction = 'decreasing'
        else:
            direction = 'stable'

    result = {
        'task_name': 'Benzene_Trend_Indicator',
        'description': 'Short-term trend of C6H6(GT) over the last N hours using endpoint-difference slope.',
        'result_summary': [
            {
                'requested_window_hours': args.hours,
                'records_used': len(window),
                'start_datetime': start_dt.strftime('%d-%m-%Y %H:%M:%S'),
                'end_datetime': end_dt.strftime('%d-%m-%Y %H:%M:%S'),
                'start_c6h6_gt': start_val,
                'end_c6h6_gt': end_val,
                'delta_c6h6_gt': round(end_val - start_val, 4),
                'hours_span': round(hours, 2),
                'slope_per_hour': round(slope, 6) if not math.isnan(slope) else None,
                'trend_direction': direction
            }
        ],
        'result_generated_at': datetime.now().astimezone().strftime('%Y-%m-%dT%H:%M:%S%z')
    }

    out_dir = Path('/home/dcc/LEI-Models-Comparision/output/air-quality/air-quality_moonshotai_kimi-k2.7-code_anthropic_claude-3-haiku_run1')
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / 'Benzene_Trend_Indicator_result.json'
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
    print(f'Result saved to {out_file}')


if __name__ == '__main__':
    main()