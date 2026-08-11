from datetime import datetime
"""
Task: Sensor Synchronization Gap Detection
Description: Analyze epoch sequences per mote to detect missing or delayed readings by flagging time intervals that significantly exceed the nominal sampling period.
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

import csv
import json
import os
import sys
from pathlib import Path
from collections import defaultdict
import statistics
import datetime

def parse_numeric(value):
    if value is None:
        return None
    value = str(value).strip()
    if value == '' or value.lower() in ('na', 'n/a', 'None', ''):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

def find_data_file():
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / 'data').exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent
    data_file = root_dir / 'data' / 'lab-data' / 'raw_data.csv'
    if not data_file.exists():
        data_file = root_dir / 'data' / 'lab-data' / 'raw_data.txt'
    return data_file

def main():
    data_file = find_data_file()
    if not data_file.exists():
        print(f'Error: Data file not found at {data_file}')
        sys.exit(1)

    mote_epochs = defaultdict(list)
    dropped_rows = 0
    total_rows = 0
    skipped_motels = set()

    try:
        with open(data_file, 'r', newline='') as f:
            reader = csv.DictReader(f)
            if reader.fieldnames:
                reader.fieldnames = [fn.lower().strip() for fn in reader.fieldnames]
            for row in reader:
                total_rows += 1
                row = {k.lower(): v for k, v in row.items()}
                if 'moteid' not in row or 'epoch' not in row:
                    dropped_rows += 1
                    continue
                mote_id_str = row.get('moteid', '').strip()
                epoch_val = parse_numeric(row.get('epoch'))
                date_val = row.get('date', '').strip()
                time_val = row.get('time', '').strip()
                if not mote_id_str or epoch_val is None:
                    dropped_rows += 1
                    continue
                try:
                    mote_id_int = int(float(mote_id_str))
                except (ValueError, TypeError):
                    dropped_rows += 1
                    continue
                if mote_id_int in skipped_motels:
                    continue
                mote_epochs[mote_id_int].append({
                    'epoch': epoch_val,
                    'date': date_val,
                    'time': time_val
                })
    except Exception as e:
        print(f'Error reading data file: {e}')
        sys.exit(1)

    print(f'Loaded {total_rows} rows, {len(mote_epochs)} motes, {dropped_rows} dropped')

    results = []
    overall_gaps = []
    anomaly_threshold_multiplier = 2.0

    for mote_id in sorted(mote_epochs.keys()):
        readings = mote_epochs[mote_id]
        readings.sort(key=lambda x: x['epoch'])
        if len(readings) < 2:
            continue

        gaps = []
        for i in range(1, len(readings)):
            gap = readings[i]['epoch'] - readings[i-1]['epoch']
            if gap > 0:
                gaps.append(gap)

        if not gaps:
            continue

        median_gap = statistics.median(gaps)
        mean_gap = statistics.mean(gaps)
        overall_gaps.extend(gaps)

        anomalies = []
        for i in range(1, len(readings)):
            gap = readings[i]['epoch'] - readings[i-1]['epoch']
            if gap > 0 and median_gap > 0 and gap > anomaly_threshold_multiplier * median_gap:
                anomalies.append({
                    'from_epoch': readings[i-1]['epoch'],
                    'to_epoch': readings[i]['epoch'],
                    'gap_size': gap,
                    'ratio_to_median': round(gap / median_gap, 2),
                    'date': readings[i]['date'],
                    'time': readings[i]['time']
                })

        if anomalies:
            results.append({
                'mote_id': mote_id,
                'total_readings': len(readings),
                'nominal_sampling_period': round(median_gap, 2),
                'mean_gap': round(mean_gap, 2),
                'anomaly_count': len(anomalies),
                'max_gap': max(gaps),
                'anomalies': anomalies[:10]
            })

    overall_stats = {}
    if overall_gaps:
        overall_stats = {
            'total_motes_analyzed': len(results),
            'overall_median_gap': round(statistics.median(overall_gaps), 2),
            'overall_mean_gap': round(statistics.mean(overall_gaps), 2),
            'mot_with_anomalies': len(results),
            'total_anomalies_detected': sum(r['anomaly_count'] for r in results)
        }

    output = {
        'task_name': 'Sensor Synchronization Gap Detection',
        'description': 'Analyze epoch sequences per mote to detect missing or delayed readings by flagging time intervals that significantly exceed the nominal sampling period.',
        'result_summary': results,
        'overall_statistics': overall_stats,
        'result_generated_at': datetime.datetime.now().isoformat(),
        'dropped_rows': dropped_rows,
        'total_rows_processed': total_rows
    }

    output_dir = Path('/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_qwen_qwen3.7-flash_google_gemini-3.1-flash-lite_run1')
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / 'sensor_synchronization_gap_detection_result.json'

    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2, default=str)

    print(f'Results saved to {output_file}')
    print(f'Motes with anomalies: {len(results)}')
    print(f'Total anomalies detected: {sum(r["anomaly_count"] for r in results)}')

if __name__ == '__main__':
    main()