"""
Task: CO_Sensor_Reference_Deviation_Tracker
Description: Calculate the hourly absolute percentage deviation between the PT08.S1(CO) sensor response and the certified CO(GT) ground truth to detect calibration drift or sensor degradation.
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
import os
import sys
import csv
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone

def find_project_root(start):
    root = start
    while root.name and not (root / 'data').exists():
        parent = root.parent
        if parent == root:
            break
        root = parent
    return root

def is_missing(raw):
    if raw is None:
        return True
    s = str(raw).strip()
    if s == '':
        return True
    if s.upper() in ('NA', 'N/A', 'NULL', 'NONE'):
        return True
    return False

def to_float(raw, col):
    if is_missing(raw):
        return None
    s = str(raw).strip()
    try:
        v = float(s)
    except ValueError:
        print(f'Warning: non-numeric value in {col}: {raw!r}', file=sys.stderr)
        return None
    # -200 is a common sentinel for missing values in this dataset
    if v == -200.0:
        return None
    return v

def main():
    parser = argparse.ArgumentParser(description='Track CO sensor/reference deviation.')
    parser.add_argument('--strict', action='store_true', help='Fail if any rows have missing or invalid values.')
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    root = find_project_root(script_dir)
    data_dir = root / 'data' / 'air-quality'
    data_file = data_dir / 'raw_data.csv'
    if not data_file.exists():
        data_file = data_dir / 'raw_data.txt'
    if not data_file.exists():
        print(f'Error: raw_data.csv/txt not found in {data_dir}', file=sys.stderr)
        sys.exit(1)
    print(f'Reading {data_file}')

    deviations = []
    total_rows = 0
    skipped_missing = 0
    skipped_gt_zero = 0

    try:
        with data_file.open(newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                total_rows += 1
                row = {(k.lower() if k else ''): v for k, v in row.items()}
                gt = to_float(row.get('co(gt)'), 'CO(GT)')
                sensor = to_float(row.get('pt08.s1(co)'), 'PT08.S1(CO)')
                if gt is None or sensor is None:
                    skipped_missing += 1
                    continue
                if gt == 0.0:
                    skipped_gt_zero += 1
                    continue
                dev = abs(sensor - gt) / abs(gt) * 100.0
                deviations.append(dev)
    except Exception as e:
        print(f'Error reading file: {e}', file=sys.stderr)
        sys.exit(1)

    if args.strict and skipped_missing > 0:
        print(f'Error: strict mode enabled but {skipped_missing} rows had missing/invalid data.', file=sys.stderr)
        sys.exit(2)

    if not deviations:
        summary = ['No valid CO sensor/reference pairs found.']
    else:
        mean_dev = sum(deviations) / len(deviations)
        max_dev = max(deviations)
        min_dev = min(deviations)
        summary = [
            f'Valid pairs: {len(deviations)} / {total_rows}',
            f'Mean absolute percentage deviation: {mean_dev:.4f}%',
            f'Max absolute percentage deviation: {max_dev:.4f}%',
            f'Min absolute percentage deviation: {min_dev:.4f}%',
            f'Skipped due to missing/invalid/sentinel: {skipped_missing}',
            f'Skipped due to zero ground truth: {skipped_gt_zero}'
        ]

    result = {
        'task_name': 'CO_Sensor_Reference_Deviation_Tracker',
        'description': 'Hourly absolute percentage deviation between PT08.S1(CO) sensor response and certified CO(GT) ground truth.',
        'result_summary': summary,
        'result_generated_at': datetime.now(timezone.utc).isoformat()
    }

    out_dir = Path('/home/dcc/LEI-Models-Comparision/output/air-quality/air-quality_moonshotai_kimi-k2.7-code_anthropic_claude-3-haiku_run2')
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / 'CO_Sensor_Reference_Deviation_Tracker_result.json'
    with out_file.open('w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
    print(f'Saved result to {out_file}')
    for line in summary:
        print(line)

if __name__ == '__main__':
    main()