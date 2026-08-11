"""
Task: Cross-Mote Temperature Consistency Check
Description: For each epoch, compare a mote's temperature reading against the median temperature of all motes reporting in the same epoch, and flag motes whose deviation exceeds a configurable threshold for calibration validation.
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
import heapq
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

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

def safe_float(value, col):
    if value is None:
        return None
    v = value.strip()
    if v.lower() in MISSING:
        return None
    try:
        return float(v)
    except ValueError:
        print('Warning: invalid numeric value in', col, ':', repr(value), file=sys.stderr)
        return None

def main():
    parser = argparse.ArgumentParser(description='Cross-mote temperature consistency check')
    parser.add_argument('--threshold', type=float, default=5.0, help='Temperature deviation threshold (Celsius)')
    parser.add_argument('--strict', action='store_true', help='Abort if any required row is incomplete')
    parser.add_argument('--top-flags', type=int, default=20, help='Number of top flags to include in result')
    args = parser.parse_args()

    data_file = find_data_file()
    if not data_file:
        print('Error: raw_data.csv or raw_data.txt not found under data/lab-data/', file=sys.stderr)
        sys.exit(1)

    epoch_temps = defaultdict(list)
    total_rows = 0
    dropped_rows = 0

    with open(data_file, 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            row = {k.lower(): v for k, v in row.items()}
            epoch_val = row.get('epoch')
            mote_val = row.get('moteid')
            temp_val = row.get('temperature')
            epoch = None
            mote = None
            try:
                if epoch_val and epoch_val.strip().lower() not in MISSING:
                    epoch = int(float(epoch_val.strip()))
            except ValueError:
                pass
            try:
                if mote_val and mote_val.strip().lower() not in MISSING:
                    mote = int(float(mote_val.strip()))
            except ValueError:
                pass
            temp = safe_float(temp_val, 'temperature')
            if epoch is None or mote is None or temp is None:
                dropped_rows += 1
                continue
            epoch_temps[epoch].append((mote, temp))

    if args.strict and dropped_rows:
        print('Error: strict mode requires complete rows; dropped', dropped_rows, 'rows.', file=sys.stderr)
        sys.exit(1)

    total_epochs = len(epoch_temps)
    total_readings = sum(len(v) for v in epoch_temps.values())
    flagged_readings = 0
    flagged_motes = set()
    per_mote_flags = defaultdict(int)
    top_heap = []
    counter = 0

    for epoch, readings in epoch_temps.items():
        if not readings:
            continue
        temps = [t for _, t in readings]
        temps.sort()
        n = len(temps)
        median = temps[n // 2] if n % 2 else (temps[n // 2 - 1] + temps[n // 2]) / 2.0
        for mote, temp in readings:
            deviation = abs(temp - median)
            if deviation > args.threshold:
                flagged_readings += 1
                flagged_motes.add(mote)
                per_mote_flags[mote] += 1
                flag = {'epoch': epoch, 'moteid': mote, 'temperature': round(temp, 4), 'median_temperature': round(median, 4), 'deviation': round(deviation, 4)}
                if len(top_heap) < args.top_flags:
                    heapq.heappush(top_heap, (deviation, counter, flag))
                elif deviation > top_heap[0][0]:
                    heapq.heapreplace(top_heap, (deviation, counter, flag))
                counter += 1

    top_flags = [item[2] for item in sorted(top_heap, key=lambda x: x[0], reverse=True)]

    result = {
        'task_name': 'Cross-Mote Temperature Consistency Check',
        'description': 'For each epoch, compare a mote temperature reading against the median temperature of all motes reporting in the same epoch, and flag motes whose deviation exceeds a configurable threshold for calibration validation.',
        'result_summary': [
            {
                'threshold_celsius': args.threshold,
                'total_epochs': total_epochs,
                'total_readings': total_readings,
                'flagged_readings': flagged_readings,
                'flagged_mote_count': len(flagged_motes),
                'dropped_rows': dropped_rows,
                'total_rows': total_rows
            },
            {
                'per_mote_flag_counts': {str(k): v for k, v in sorted(per_mote_flags.items(), key=lambda x: x[1], reverse=True)}
            },
            {
                'top_flags': top_flags
            }
        ],
        'result_generated_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    }

    out_dir = Path('/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_moonshotai_kimi-k2.7-code_nvidia_nemotron-3-ultra-550b-a55b_run2')
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / 'cross_mote_temperature_consistency_check_result.json'
    with open(out_file, 'w') as f:
        json.dump(result, f, indent=2)
    print('Result saved to', out_file)
    print('Epochs:', total_epochs, 'Readings:', total_readings, 'Flagged:', flagged_readings, 'Motes flagged:', len(flagged_motes))

if __name__ == '__main__':
    main()