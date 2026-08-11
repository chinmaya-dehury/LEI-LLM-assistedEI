"""
Task: Battery Voltage Health Monitoring
Description: Track battery voltage trends per mote and trigger alerts when voltage falls below a safety threshold or shows a steep decline independent of temperature fluctuations.
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
from datetime import datetime

def safe_float(val):
    if val is None:
        return None
    val = str(val).strip()
    if val == '' or val.upper() in ('NA', 'N/A', 'NULL', 'NONE'):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None

def resolve_data_path():
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
    if not data_file.exists():
        print('ERROR: No raw_data.csv or raw_data.txt found under data/lab-data/', file=sys.stderr)
        sys.exit(1)
    return data_file

def main():
    data_file = resolve_data_path()
    VOLTAGE_THRESHOLD = 2.0
    STEEP_DROP_VOLTAGE = 0.1
    TEMP_CORRELATION_FACTOR = 0.05

    motes = {}
    dropped_rows = 0
    total_rows = 0

    try:
        with open(data_file, 'r', newline='', encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f)
            for row in reader:
                total_rows += 1
                row = {k.lower(): v for k, v in row.items()}
                mote_id = row.get('moteid', '').strip()
                if not mote_id:
                    dropped_rows += 1
                    continue
                voltage = safe_float(row.get('voltage'))
                temperature = safe_float(row.get('temperature'))
                epoch = safe_float(row.get('epoch'))
                date_str = row.get('date', '').strip()
                time_str = row.get('time', '').strip()
                if voltage is None:
                    dropped_rows += 1
                    continue
                key = int(mote_id)
                if key not in motes:
                    motes[key] = []
                motes[key].append({
                    'voltage': voltage,
                    'temperature': temperature,
                    'epoch': epoch,
                    'datetime_str': f'{date_str} {time_str}' if date_str else ''
                })
    except Exception as e:
        print(f'ERROR reading data: {e}', file=sys.stderr)
        sys.exit(1)

    alerts = []
    mote_summaries = {}

    for mote_id, readings in sorted(motes.items()):
        readings.sort(key=lambda r: (r['epoch'] if r['epoch'] is not None else 0))
        voltages = [r['voltage'] for r in readings]
        temps = [r['temperature'] for r in readings]
        min_v = min(voltages)
        max_v = max(voltages)
        avg_v = sum(voltages) / len(voltages)
        first_v = voltages[0]
        last_v = voltages[-1]
        total_drop = first_v - last_v
        has_below_threshold = min_v < VOLTAGE_THRESHOLD
        alerts_for_mote = []
        for i in range(1, len(readings)):
            dv = voltages[i-1] - voltages[i]
            dt = (temps[i-1] - temps[i]) if (temps[i-1] is not None and temps[i] is not None) else 0
            if dv > STEEP_DROP_VOLTAGE:
                if abs(dt) * TEMP_CORRELATION_FACTOR < dv:
                    ts = readings[i]['datetime_str']
                    alerts_for_mote.append({
                        'type': 'steep_decline_uncorrelated',
                        'epoch': readings[i]['epoch'],
                        'timestamp': ts,
                        'voltage_before': round(voltages[i-1], 4),
                        'voltage_after': round(voltages[i], 4),
                        'drop': round(dv, 4),
                        'temp_change': round(dt, 4)
                    })
        if has_below_threshold:
            alerts_for_mote.append({
                'type': 'below_threshold',
                'min_voltage': round(min_v, 4),
                'threshold': VOLTAGE_THRESHOLD
            })
        if alerts_for_mote:
            alerts.append({
                'mote_id': mote_id,
                'readings_count': len(readings),
                'min_voltage': round(min_v, 4),
                'max_voltage': round(max_v, 4),
                'avg_voltage': round(avg_v, 4),
                'total_drop': round(total_drop, 4),
                'alerts': alerts_for_mote
            })
        mote_summaries[mote_id] = {
            'count': len(readings),
            'min_voltage': round(min_v, 4),
            'max_voltage': round(max_v, 4),
            'avg_voltage': round(avg_v, 4),
            'total_drop': round(total_drop, 4)
        }

    result = {
        'task_name': 'Battery Voltage Health Monitoring',
        'description': 'Track battery voltage trends per mote and trigger alerts when voltage falls below a safety threshold or shows a steep decline independent of temperature fluctuations.',
        'result_summary': [
            f'Total rows processed: {total_rows}',
            f'Dropped rows (missing voltage): {dropped_rows}',
            f'Motes analyzed: {len(motes)}',
            f'Motes with alerts: {len(alerts)}',
            f'Safety voltage threshold: {VOLTAGE_THRESHOLD}V',
            f'Steep decline threshold: {STEEP_DROP_VOLTAGE}V'
        ],
        'mote_health': mote_summaries,
        'alerts': alerts,
        'result_generated_at': datetime.utcnow().isoformat() + 'Z'
    }

    output_dir = Path('/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_qwen_qwen3.7-flash_google_gemini-3.1-flash-lite_run1')
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / 'Battery Voltage Health Monitoring_result.json'
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    print(f'Result saved to {output_file}')
    print(f'Motes with alerts: {len(alerts)} out of {len(motes)}')

if __name__ == '__main__':
    main()