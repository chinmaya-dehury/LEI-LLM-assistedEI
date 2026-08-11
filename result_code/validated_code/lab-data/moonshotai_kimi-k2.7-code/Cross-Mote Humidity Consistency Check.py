"""
Task: Cross-Mote Humidity Consistency Check
Description: For each epoch, compare each mote's humidity reading to the median humidity across all motes in that epoch and flag motes with large deviations for calibration validation.
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
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

MISSING = {'', 'na', 'n/a', 'None', 'none'}

def resolve_root(start):
    root = start
    while root.name and not (root / 'data').exists():
        parent = root.parent
        if parent == root:
            break
        root = parent
    return root

def to_float(value, col, bad_counter):
    if value is None:
        return None
    s = str(value).strip()
    if s.lower() in MISSING:
        return None
    try:
        return float(s)
    except ValueError:
        bad_counter[0] += 1
        print(f'Warning: invalid numeric value in column {col}: {value!r}', file=sys.stderr)
        return None

def to_int(value, col, bad_counter):
    f = to_float(value, col, bad_counter)
    if f is None:
        return None
    return int(f)

def median(vals):
    if not vals:
        return None
    s = sorted(vals)
    n = len(s)
    m = n // 2
    if n % 2:
        return s[m]
    return (s[m - 1] + s[m]) / 2.0

def main():
    parser = argparse.ArgumentParser(description='Cross-mote humidity consistency check.')
    parser.add_argument('--threshold', type=float, default=5.0, help='Absolute humidity deviation threshold in percent.')
    parser.add_argument('--strict', action='store_true', help='Exit if required columns are missing from header.')
    parser.add_argument('--output-dir', type=str, default='/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_moonshotai_kimi-k2.7-code_nvidia_nemotron-3-ultra-550b-a55b_run1')
    args = parser.parse_args()

    curr_dir = Path(__file__).resolve().parent
    root_dir = resolve_root(curr_dir)

    data_file = root_dir / 'data' / 'lab-data' / 'raw_data.csv'
    if not data_file.exists():
        data_file = root_dir / 'data' / 'lab-data' / 'raw_data.txt'
    if not data_file.exists():
        print('Input file not found. Searched under', root_dir / 'data' / 'lab-data', file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    required = ['epoch', 'moteid', 'humidity']
    epochs = defaultdict(list)
    total = 0
    dropped = 0
    bad = [0]

    with open(data_file, newline='') as f:
        reader = csv.DictReader(f)
        header = [h.lower() for h in reader.fieldnames] if reader.fieldnames else []
        if args.strict:
            missing_cols = [c for c in required if c not in header]
            if missing_cols:
                print('Strict mode: required columns missing:', missing_cols, file=sys.stderr)
                sys.exit(2)

        for raw in reader:
            row = {k.lower(): v for k, v in raw.items()}
            total += 1

            epoch = to_int(row.get('epoch'), 'epoch', bad)
            moteid = to_int(row.get('moteid'), 'moteid', bad)
            humidity = to_float(row.get('humidity'), 'humidity', bad)

            if epoch is None or moteid is None or humidity is None:
                dropped += 1
                continue

            epochs[epoch].append((moteid, humidity))

    flagged = []
    flagged_by_mote = defaultdict(int)
    epoch_count = 0

    for ep, readings in epochs.items():
        values = [h for _, h in readings]
        med = median(values)
        if med is None:
            continue
        epoch_count += 1
        for mote, h in readings:
            dev = h - med
            if abs(dev) > args.threshold:
                flagged.append({
                    'epoch': ep,
                    'moteid': mote,
                    'humidity': round(h, 4),
                    'epoch_median': round(med, 4),
                    'deviation': round(dev, 4)
                })
                flagged_by_mote[mote] += 1

    top_motes = dict(sorted(flagged_by_mote.items(), key=lambda kv: kv[1], reverse=True)[:10])

    result = {
        'task_name': 'Cross-Mote Humidity Consistency Check',
        'description': 'For each epoch, compare each mote humidity reading to the median humidity across all motes in that epoch and flag deviations exceeding the threshold.',
        'result_summary': [
            {'total_rows_read': total},
            {'rows_dropped_invalid': dropped},
            {'numeric_conversion_errors': bad[0]},
            {'epochs_analyzed': epoch_count},
            {'deviation_threshold_percent': args.threshold},
            {'flagged_deviation_count': len(flagged)},
            {'top_flagged_motes': top_motes},
            {'sample_flags': flagged[:10]}
        ],
        'result_generated_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    }

    out_path = out_dir / 'cross_mote_humidity_consistency_check_result.json'
    with open(out_path, 'w') as f:
        json.dump(result, f, indent=2)
    print('Result written to', out_path)

if __name__ == '__main__':
    main()