"""
Task: Sensor Reading Staleness Monitor
Description: Measure the elapsed time since the last reading for each mote and flag stale motes that have not reported within an expected interval, supporting sensor health monitoring.
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
import random
import argparse
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

TASK_NAME = 'sensor_reading_staleness_monitor'
OUTPUT_DIR = Path('/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_moonshotai_kimi-k2.7-code_anthropic_claude-3-haiku_run2')
MISSING = {'', 'NA', 'N/A', 'None', 'NULL', 'None'}
MAX_GAP_SAMPLE = 1000

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

def is_missing(value):
    return value is None or (isinstance(value, str) and value.strip() in MISSING)

def to_int(value):
    try:
        return int(float(value))
    except Exception:
        return None

def parse_dt(date_str, time_str):
    if is_missing(date_str) or is_missing(time_str):
        return None
    try:
        t = time_str.strip()
        if '.' in t:
            base, frac = t.rsplit('.', 1)
            frac = (frac + '000000')[:6]
            t = f'{base}.{frac}'
        return datetime.strptime(f'{date_str.strip()} {t}', '%Y-%m-%d %H:%M:%S.%f')
    except Exception:
        return None

def median(values):
    if not values:
        return None
    s = sorted(values)
    n = len(s)
    if n % 2 == 1:
        return s[n // 2]
    return (s[n // 2 - 1] + s[n // 2]) / 2.0

def main():
    parser = argparse.ArgumentParser(description='Sensor reading staleness monitor')
    parser.add_argument('--strict', action='store_true', help='Exit with error if any row is dropped')
    args = parser.parse_args()

    data_file = find_data_file()
    if not data_file:
        print('Data file not found under data/lab-data/', file=sys.stderr)
        sys.exit(1)

    required = {'moteid', 'date', 'time'}
    latest = {}
    mote_gaps = defaultdict(list)
    mote_gap_count = defaultdict(int)
    dropped = 0
    total_rows = 0

    with open(data_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            print('Empty CSV header', file=sys.stderr)
            sys.exit(1)
        fields = [c.lower() for c in reader.fieldnames]
        if not required.issubset(set(fields)):
            print(f'Missing required columns: {required - set(fields)}', file=sys.stderr)
            sys.exit(1)

        for raw in reader:
            total_rows += 1
            row = {k.lower(): v for k, v in raw.items()}
            mote = to_int(row.get('moteid'))
            dt = parse_dt(row.get('date'), row.get('time'))
            if mote is None or dt is None:
                dropped += 1
                continue
            prev = latest.get(mote)
            if prev is not None:
                gap = (dt - prev).total_seconds()
                if gap > 0:
                    mote_gap_count[mote] += 1
                    g = mote_gaps[mote]
                    if len(g) < MAX_GAP_SAMPLE:
                        g.append(gap)
                    else:
                        j = random.randrange(mote_gap_count[mote])
                        if j < MAX_GAP_SAMPLE:
                            g[j] = gap
            if prev is None or dt > prev:
                latest[mote] = dt

    if args.strict and dropped:
        print(f'Strict mode: dropped {dropped} rows', file=sys.stderr)
        sys.exit(2)

    if not latest:
        print('No valid readings found', file=sys.stderr)
        sys.exit(1)

    reference = max(latest.values())
    per_mote_medians = [median(g) for g in mote_gaps.values() if g]
    expected = median(per_mote_medians) or 60.0
    threshold = max(expected * 3.0, 300.0)

    motes = []
    stale_count = 0
    for mote in sorted(latest):
        last = latest[mote]
        elapsed = (reference - last).total_seconds()
        stale = elapsed > threshold
        if stale:
            stale_count += 1
        motes.append({
            'type': 'mote',
            'moteid': mote,
            'last_reading': last.isoformat(),
            'elapsed_seconds': round(elapsed, 2),
            'stale': stale
        })

    result = {
        'task_name': TASK_NAME,
        'description': 'Measures elapsed time since the last reading for each mote and flags stale motes exceeding the expected reporting interval.',
        'result_summary': [
            {
                'type': 'overall',
                'reference_time': reference.isoformat(),
                'expected_interval_seconds': round(expected, 2),
                'threshold_seconds': round(threshold, 2),
                'total_motes': len(latest),
                'stale_mote_count': stale_count,
                'dropped_rows': dropped,
                'total_rows': total_rows
            }
        ] + motes,
        'result_generated_at': datetime.now(timezone.utc).isoformat()
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f'{TASK_NAME}_result.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
    print(f'Saved {out_path}')
    print(f'Motes: {len(latest)}, stale: {stale_count}, threshold: {threshold:.1f}s')

if __name__ == '__main__':
    main()