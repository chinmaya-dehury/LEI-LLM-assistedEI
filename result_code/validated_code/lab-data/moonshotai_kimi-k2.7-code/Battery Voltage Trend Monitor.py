"""
Task: Battery Voltage Trend Monitor
Description: Track per-mote battery voltage over recent readings and alert when voltage drops below a healthy threshold or shows a declining trend.
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
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path

TASK_NAME = 'Battery Voltage Trend Monitor'
DESCRIPTION = 'Track per-mote battery voltage over recent readings and alert when voltage drops below a healthy threshold or shows a declining trend.'
RESULT_DIR = Path('/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_moonshotai_kimi-k2.7-code_google_gemini-3.1-flash-lite_run2')
WINDOW_SIZE = 100
HEALTHY_THRESHOLD = 2.3
DECLINE_DELTA = 0.02
MISSING = {'', 'na', 'n/a', 'None', 'none', '.'}

def is_missing(value):
    if value is None:
        return True
    return str(value).strip().lower() in MISSING

def safe_float(row, column):
    value = row.get(column)
    if is_missing(value):
        return None
    try:
        return float(value)
    except Exception:
        raise ValueError(f'invalid numeric value in column {column!r}: {value!r}')

def find_data_file():
    try:
        current = Path(__file__).resolve().parent
    except NameError:
        current = Path.cwd()
    root = current
    while root.name and not (root / 'data').exists():
        parent = root.parent
        if parent == root:
            break
        root = parent
    for name in ('raw_data.csv', 'raw_data.txt'):
        candidate = root / 'data' / 'lab-data' / name
        if candidate.exists():
            return candidate
    return None

def main():
    parser = argparse.ArgumentParser(description=TASK_NAME)
    parser.add_argument('--strict', action='store_true', help='Require complete moteid and voltage rows')
    args = parser.parse_args()

    data_file = find_data_file()
    if not data_file:
        print('ERROR: raw_data.csv or raw_data.txt not found under data/lab-data/', file=sys.stderr)
        sys.exit(1)

    motes = defaultdict(lambda: deque(maxlen=WINDOW_SIZE))
    total_rows = 0
    dropped_rows = 0
    invalid_voltage = 0

    with open(data_file, 'r', newline='', encoding='utf-8') as handle:
        reader = csv.DictReader(handle)
        for line_no, raw_row in enumerate(reader, start=2):
            total_rows += 1
            row = {k.lower(): v for k, v in raw_row.items()}
            if 'moteid' not in row or 'voltage' not in row:
                if args.strict:
                    dropped_rows += 1
                    continue
                if 'moteid' not in row:
                    dropped_rows += 1
                    continue
            mote_id = row.get('moteid', '').strip()
            if is_missing(mote_id):
                dropped_rows += 1
                continue
            try:
                voltage = safe_float(row, 'voltage')
            except ValueError as error:
                print(f'WARNING row {line_no}: {error}', file=sys.stderr)
                invalid_voltage += 1
                if args.strict:
                    dropped_rows += 1
                continue
            if voltage is None:
                invalid_voltage += 1
                if args.strict:
                    dropped_rows += 1
                continue
            epoch_value = row.get('epoch')
            try:
                epoch = int(epoch_value) if not is_missing(epoch_value) else line_no
            except Exception:
                epoch = line_no
            motes[mote_id].append((epoch, voltage))

    alerts = []
    healthy_count = 0
    for mote_id, readings in sorted(motes.items(), key=lambda item: int(item[0]) if str(item[0]).isdigit() else item[0]):
        ordered = sorted(readings, key=lambda pair: pair[0])
        voltages = [v for _, v in ordered]
        count = len(voltages)
        mean_voltage = sum(voltages) / count
        latest = voltages[-1]
        minimum = min(voltages)
        maximum = max(voltages)
        low_alert = latest < HEALTHY_THRESHOLD or mean_voltage < HEALTHY_THRESHOLD
        decline_alert = False
        slope = None
        if count >= 10:
            half = count // 2
            first_mean = sum(voltages[:half]) / half
            second_mean = sum(voltages[half:]) / (count - half)
            slope = second_mean - first_mean
            decline_alert = slope < -DECLINE_DELTA
        status = 'alert' if (low_alert or decline_alert) else 'healthy'
        if status == 'healthy':
            healthy_count += 1
        alerts.append({
            'mote_id': mote_id,
            'readings_count': count,
            'voltage_mean': round(mean_voltage, 5),
            'voltage_latest': round(latest, 5),
            'voltage_min': round(minimum, 5),
            'voltage_max': round(maximum, 5),
            'trend_slope': round(slope, 6) if slope is not None else None,
            'low_voltage_alert': low_alert,
            'declining_trend_alert': decline_alert,
            'status': status
        })

    summary = {
        'total_rows_read': total_rows,
        'dropped_or_invalid_rows': dropped_rows + invalid_voltage,
        'motes_observed': len(motes),
        'healthy_motes': healthy_count,
        'alerted_motes': len(motes) - healthy_count,
        'voltage_threshold_volts': HEALTHY_THRESHOLD,
        'decline_threshold_volts': DECLINE_DELTA,
        'recent_window_size': WINDOW_SIZE
    }

    result = {
        'task_name': TASK_NAME,
        'description': DESCRIPTION,
        'result_summary': [summary, {'per_mote_voltage_status': alerts}],
        'result_generated_at': datetime.now(timezone.utc).isoformat()
    }

    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = RESULT_DIR / f'{TASK_NAME.lower().replace(" ", "_")}_result.json'
    with open(output_file, 'w', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2)
    print(f'{TASK_NAME}: processed {total_rows} rows, {len(motes)} motes, {summary["alerted_motes"]} alerts. Result saved to {output_file}')

if __name__ == '__main__':
    main()