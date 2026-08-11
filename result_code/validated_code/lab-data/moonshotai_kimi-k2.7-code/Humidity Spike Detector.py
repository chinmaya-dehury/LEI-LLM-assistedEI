"""
Task: Humidity Spike Detector
Description: Flag sudden humidity changes or readings outside a per-mote expected range to identify environmental disturbances or sensor anomalies.
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
import math
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

MISSING_TOKENS = {'', 'na', 'n/a', 'None', 'none'}
Z_THRESHOLD = 3.0
RANGE_MIN = 0.0
RANGE_MAX = 100.0
ANOMALY_LIMIT = 100


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
    candidates = [
        root_dir / 'data' / 'lab-data' / 'raw_data.csv',
        root_dir / 'data' / 'lab-data' / 'raw_data.txt',
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def is_missing(value):
    if value is None:
        return True
    return str(value).strip().lower() in MISSING_TOKENS


def safe_float(value, field_name, row_index):
    if is_missing(value):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        print(f'Warning: invalid numeric value for {field_name} at row {row_index}: {value!r}', file=sys.stderr)
        return None


def safe_int(value, field_name, row_index):
    if is_missing(value):
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        print(f'Warning: invalid integer value for {field_name} at row {row_index}: {value!r}', file=sys.stderr)
        return None


def compute_stats(data_file, strict):
    stats = defaultdict(lambda: {'count': 0, 'mean': 0.0, 'm2': 0.0})
    dropped = 0
    row_index = 0
    with open(data_file, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for raw_row in reader:
            row_index += 1
            row = {k.lower(): v for k, v in raw_row.items()}
            mote_id = safe_int(row.get('moteid'), 'moteid', row_index)
            humidity = safe_float(row.get('humidity'), 'humidity', row_index)
            if mote_id is None or humidity is None:
                dropped += 1
                if strict:
                    continue
                if mote_id is None:
                    continue
            if humidity is None:
                continue
            s = stats[mote_id]
            s['count'] += 1
            delta = humidity - s['mean']
            s['mean'] += delta / s['count']
            delta2 = humidity - s['mean']
            s['m2'] += delta * delta2
    return stats, dropped, row_index


def detect_spikes(data_file, stats, strict):
    anomalies = []
    per_mote = defaultdict(lambda: {
        'total': 0,
        'spikes': 0,
        'out_of_range': 0,
        'sudden_changes': 0,
        'min_humidity': math.inf,
        'max_humidity': -math.inf,
    })
    previous = {}
    dropped = 0
    row_index = 0
    with open(data_file, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for raw_row in reader:
            row_index += 1
            row = {k.lower(): v for k, v in raw_row.items()}
            mote_id = safe_int(row.get('moteid'), 'moteid', row_index)
            humidity = safe_float(row.get('humidity'), 'humidity', row_index)
            timestamp = f"{row.get('date', '')} {row.get('time', '')}".strip()
            if mote_id is None or humidity is None:
                dropped += 1
                if strict:
                    continue
                if mote_id is None:
                    continue
            if humidity is None:
                continue
            s = stats[mote_id]
            count = s['count']
            mean = s['mean']
            std = math.sqrt(s['m2'] / count) if count > 1 else 0.0
            threshold = max(Z_THRESHOLD * std, 5.0)
            z_score = (humidity - mean) / std if std > 0 else 0.0
            spike = False
            reasons = []
            if humidity < RANGE_MIN or humidity > RANGE_MAX:
                spike = True
                reasons.append('out_of_range')
            if std > 0 and abs(z_score) > Z_THRESHOLD:
                spike = True
                reasons.append('statistical_outlier')
            prev = previous.get(mote_id)
            if prev is not None and abs(humidity - prev) > threshold:
                spike = True
                reasons.append('sudden_change')
            pm = per_mote[mote_id]
            pm['total'] += 1
            pm['min_humidity'] = min(pm['min_humidity'], humidity)
            pm['max_humidity'] = max(pm['max_humidity'], humidity)
            if spike:
                pm['spikes'] += 1
                if 'out_of_range' in reasons:
                    pm['out_of_range'] += 1
                if 'sudden_change' in reasons:
                    pm['sudden_changes'] += 1
                if len(anomalies) < ANOMALY_LIMIT:
                    anomalies.append({
                        'moteid': mote_id,
                        'timestamp': timestamp,
                        'humidity': humidity,
                        'mote_mean': round(mean, 4),
                        'mote_std': round(std, 4),
                        'z_score': round(z_score, 4),
                        'reasons': reasons,
                    })
            previous[mote_id] = humidity
    return per_mote, anomalies, dropped


def main():
    parser = argparse.ArgumentParser(description='Detect humidity spikes per mote.')
    parser.add_argument('--strict', action='store_true', help='Skip rows with missing moteid or humidity.')
    args = parser.parse_args()

    root_dir = find_project_root()
    data_file = resolve_input_file(root_dir)
    if data_file is None:
        print('Error: input file not found at data/lab-data/raw_data.csv or .txt', file=sys.stderr)
        sys.exit(1)

    print(f'Reading {data_file} ...')
    stats, dropped_read, total_rows = compute_stats(data_file, args.strict)
    per_mote, anomalies, dropped_detect = detect_spikes(data_file, stats, args.strict)

    summary = []
    for mote_id in sorted(per_mote.keys()):
        pm = per_mote[mote_id]
        s = stats[mote_id]
        summary.append({
            'moteid': mote_id,
            'total_readings': pm['total'],
            'spike_count': pm['spikes'],
            'out_of_range_count': pm['out_of_range'],
            'sudden_change_count': pm['sudden_changes'],
            'mean_humidity': round(s['mean'], 4),
            'std_humidity': round(math.sqrt(s['m2'] / s['count']) if s['count'] > 1 else 0.0, 4),
            'min_humidity': round(pm['min_humidity'], 4) if pm['min_humidity'] != math.inf else None,
            'max_humidity': round(pm['max_humidity'], 4) if pm['max_humidity'] != -math.inf else None,
        })

    result = {
        'task_name': 'Humidity Spike Detector',
        'description': 'Flag sudden humidity changes or readings outside a per-mote expected range to identify environmental disturbances or sensor anomalies.',
        'result_summary': {
            'total_rows_scanned': total_rows,
            'motes_analyzed': len(stats),
            'rows_dropped': max(dropped_read, dropped_detect),
            'anomaly_sample': anomalies,
            'per_mote_summary': summary,
        },
        'result_generated_at': datetime.now(timezone.utc).isoformat(),
    }

    output_dir = Path('/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_moonshotai_kimi-k2.7-code_google_gemini-3.1-flash-lite_run2')
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / 'humidity_spike_detector_result.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)

    print(f'Analyzed {len(stats)} motes, {total_rows} rows, dropped {max(dropped_read, dropped_detect)} rows.')
    print(f'Found {sum(pm["spikes"] for pm in per_mote.values())} humidity spikes.')
    print(f'Result saved to {output_file}')


if __name__ == '__main__':
    main()