"""
Task: CO Sensor Calibration Drift Tracker
Description: Compare hourly PT08.S1(CO) sensor resistance with the co-located CO(GT) reference in non-overlapping weekly windows. Compute the median ratio and median absolute difference between sensor and reference to detect slow calibration drift or sensor degradation over the deployment period.
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
from datetime import datetime, timedelta
from pathlib import Path

OUTPUT_DIR = Path('/home/dcc/LEI-Models-Comparision/output/air-quality/air-quality_moonshotai_kimi-k2.7-code_google_gemini-3.1-flash-lite_run1')
MISSING = {'', 'na', 'n/a', 'None', 'none'}


def find_data_file():
    curr = Path(__file__).resolve().parent
    root = curr
    while root.name and not (root / 'data').exists():
        parent = root.parent
        if parent == root:
            break
        root = parent
    for name in ('raw_data.csv', 'raw_data.txt'):
        p = root / 'data' / 'air-quality' / name
        if p.exists():
            return p
    return None


def to_float(value, col):
    if value is None:
        return None
    s = str(value).strip()
    if s.lower() in MISSING:
        return None
    try:
        v = float(s)
    except ValueError:
        print(f'Warning: invalid numeric value in {col}: {value!r}', file=sys.stderr)
        return None
    # Treat common sentinel -200 as missing
    if v <= -199.0:
        return None
    return v


def parse_dt(row):
    d = row.get('date', '').strip()
    t = row.get('time', '').strip()
    if not d or not t:
        return None
    try:
        return datetime.strptime(f'{d} {t}', '%d-%m-%Y %H:%M:%S')
    except ValueError:
        try:
            return datetime.strptime(f'{d} {t}', '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return None


def median(vals):
    if not vals:
        return None
    s = sorted(vals)
    n = len(s)
    mid = n // 2
    if n % 2:
        return s[mid]
    return (s[mid - 1] + s[mid]) / 2.0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--strict', action='store_true', help='require complete rows')
    args = parser.parse_args()

    data_file = find_data_file()
    if not data_file:
        print('Error: raw_data.csv/txt not found under data/air-quality', file=sys.stderr)
        sys.exit(1)

    rows_read = 0
    dropped = 0
    groups = {}

    with open(data_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows_read += 1
            row = {k.lower(): v for k, v in row.items()}
            dt = parse_dt(row)
            if dt is None:
                dropped += 1
                continue
            co = to_float(row.get('co(gt)'), 'co(gt)')
            s1 = to_float(row.get('pt08.s1(co)'), 'pt08.s1(co)')
            if co is None or s1 is None:
                dropped += 1
                continue
            week_start = (dt.date() - timedelta(days=dt.weekday())).isoformat()
            groups.setdefault(week_start, []).append((s1, co))

    if not groups:
        print('Error: no valid CO/S1 pairs found', file=sys.stderr)
        sys.exit(1)

    summary = []
    for week in sorted(groups):
        pairs = groups[week]
        ratios = []
        diffs = []
        for s, c in pairs:
            if c != 0:
                ratios.append(s / c)
            diffs.append(abs(s - c))
        summary.append({
            'week_start': week,
            'n_pairs': len(pairs),
            'median_ratio': median(ratios),
            'median_absolute_difference': median(diffs)
        })

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result = {
        'task_name': 'CO Sensor Calibration Drift Tracker',
        'description': 'Weekly median ratio and median absolute difference between PT08.S1(CO) sensor resistance and CO(GT) reference to detect calibration drift.',
        'result_summary': summary,
        'result_generated_at': datetime.utcnow().isoformat() + 'Z'
    }
    out_path = OUTPUT_DIR / 'CO_Sensor_Calibration_Drift_Tracker_result.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
    print(f'Saved {out_path} with {len(summary)} weekly windows ({rows_read} rows read, {dropped} dropped).')


if __name__ == '__main__':
    main()