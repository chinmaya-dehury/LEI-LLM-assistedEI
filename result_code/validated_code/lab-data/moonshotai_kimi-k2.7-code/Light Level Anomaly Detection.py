"""
Task: Light Level Anomaly Detection
Description: For each mote, flag light readings that are unexpectedly near zero for an extended period or exceed a bright-light threshold, indicating lighting faults or sensor issues.
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
import os
import sys
import csv
import json
import math
import argparse
from pathlib import Path
from datetime import datetime, timezone

def find_data_file():
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / 'data').exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent
    for name in ('raw_data.csv', 'raw_data.txt'):
        p = root_dir / 'data' / 'lab-data' / name
        if p.exists():
            return p
    return None

def to_float(value, col):
    if value is None:
        return None
    s = value.strip()
    if s == '' or s.upper() in ('NA', 'N/A', 'NULL'):
        return None
    try:
        return float(s)
    except ValueError:
        raise ValueError(f'Invalid numeric value in column {col}: {value!r}')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--strict', action='store_true', help='Exit on invalid rows')
    parser.add_argument('--near-zero', type=float, default=1.0)
    parser.add_argument('--bright', type=float, default=10000.0)
    parser.add_argument('--streak', type=int, default=5)
    args = parser.parse_args()

    data_file = find_data_file()
    if data_file is None:
        print('Input data file not found under data/lab-data/', file=sys.stderr)
        sys.exit(1)

    near_zero_threshold = args.near_zero
    bright_threshold = args.bright
    min_streak = args.streak

    motes = {}
    invalid = 0
    total = 0

    with open(data_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            row = {k.lower(): v for k, v in row.items()}
            try:
                moteid_raw = row.get('moteid')
                if moteid_raw is None:
                    invalid += 1
                    continue
                moteid = int(moteid_raw.strip())
                light = to_float(row.get('light'), 'light')
                epoch_raw = row.get('epoch')
                if light is None or epoch_raw is None:
                    invalid += 1
                    if args.strict:
                        print('Strict mode: missing light or epoch', file=sys.stderr)
                        sys.exit(2)
                    continue
                epoch = int(epoch_raw.strip())
            except Exception as e:
                invalid += 1
                if args.strict:
                    print(f'Strict mode error: {e}', file=sys.stderr)
                    sys.exit(2)
                continue
            motes.setdefault(moteid, []).append((epoch, light))

    summaries = []
    for moteid in sorted(motes):
        readings = motes[moteid]
        readings.sort(key=lambda x: x[0])
        total_r = len(readings)
        near_zero_count = 0
        bright_count = 0
        max_streak = 0
        current_streak = 0
        streak_examples = []
        bright_examples = []

        for epoch, light in readings:
            if light <= near_zero_threshold:
                near_zero_count += 1
                current_streak += 1
                if current_streak == min_streak:
                    streak_examples.append({'epoch': epoch, 'light': light})
            else:
                current_streak = 0
            if light > bright_threshold:
                bright_count += 1
                if len(bright_examples) < 5:
                    bright_examples.append({'epoch': epoch, 'light': light})
            if current_streak > max_streak:
                max_streak = current_streak

        anomaly_flag = near_zero_count > 0 or bright_count > 0 or max_streak >= min_streak
        summaries.append({
            'moteid': moteid,
            'total_readings': total_r,
            'near_zero_count': near_zero_count,
            'max_consecutive_near_zero': max_streak,
            'bright_count': bright_count,
            'anomaly_flag': anomaly_flag,
            'sample_near_zero_streaks': streak_examples[:5],
            'sample_bright_anomalies': bright_examples[:5]
        })

    result = {
        'task_name': 'Light Level Anomaly Detection',
        'description': 'For each mote, flag light readings that are unexpectedly near zero for an extended period or exceed a bright-light threshold, indicating lighting faults or sensor issues.',
        'result_summary': summaries,
        'result_generated_at': datetime.now(timezone.utc).isoformat()
    }

    out_dir = Path('/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_moonshotai_kimi-k2.7-code_nvidia_nemotron-3-ultra-550b-a55b_run1')
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / 'Light_Level_Anomaly_Detection_result.json'
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
    print(f'Saved results to {out_file}')
    print(f'Processed {total} rows, dropped/invalid {invalid}')

if __name__ == '__main__':
    main()