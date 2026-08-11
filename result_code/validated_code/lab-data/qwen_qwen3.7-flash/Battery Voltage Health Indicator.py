"""
Task: Battery Voltage Health Indicator
Description: Monitor battery voltage levels per mote and flag nodes where voltage drops below a safe operational threshold or exhibits a rapid decline rate indicative of power degradation.
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

def resolve_input_path():
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
        print('ERROR: No input data file found under data/lab-data/', file=sys.stderr)
        sys.exit(1)
    return data_file

def safe_float(value):
    if value is None:
        return None
    v = str(value).strip()
    if v in ('', 'NA', 'N/A', 'None', 'None'):
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None

def main():
    DATA_THRESHOLD = 2.5
    DECLINE_RATE_THRESHOLD = -0.001
    OUTPUT_DIR = Path('/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_qwen_qwen3.7-flash_anthropic_claude-3-haiku_run2')
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    data_file = resolve_input_path()
    print(f'Reading data from: {data_file}')

    mote_data = {}
    total_rows = 0
    skipped_rows = 0

    try:
        with open(data_file, 'r', newline='', encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f)
            for row in reader:
                total_rows += 1
                normalized = {k.lower(): v for k, v in row.items()}
                mote_id = normalized.get('moteid', '').strip()
                if not mote_id:
                    skipped_rows += 1
                    continue
                voltage = safe_float(normalized.get('voltage'))
                epoch = safe_float(normalized.get('epoch'))
                date_val = normalized.get('date', '').strip()
                time_val = normalized.get('time', '').strip()
                if voltage is None:
                    skipped_rows += 1
                    continue
                if mote_id not in mote_data:
                    mote_data[mote_id] = []
                ts_str = f'{date_val} {time_val}' if date_val and time_val else None
                mote_data[mote_id].append({
                    'voltage': voltage,
                    'epoch': epoch,
                    'timestamp': ts_str
                })
    except Exception as e:
        print(f'ERROR reading file: {e}', file=sys.stderr)
        sys.exit(1)

    print(f'Total rows processed: {total_rows}, Skipped: {skipped_rows}, Motes found: {len(mote_data)}')

    results = []
    flagged_motes = []

    for mote_id, readings in sorted(mote_data.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0):
        voltages = [r['voltage'] for r in readings]
        epochs = [r['epoch'] for r in readings if r['epoch'] is not None]
        timestamps = [(r['timestamp'], r['voltage']) for r in readings if r['timestamp']]

        min_v = min(voltages)
        max_v = max(voltages)
        avg_v = sum(voltages) / len(voltages)
        count = len(voltages)

        decline_rate = 0.0
        if len(epochs) >= 2:
            sorted_epochs = sorted(epochs)
            first_e = sorted_epochs[0]
            last_e = sorted_epochs[-1]
            idx_first = next(i for i, r in enumerate(readings) if r['epoch'] == first_e)
            idx_last = next(i for i, r in enumerate(readings) if r['epoch'] == last_e)
            first_v = readings[idx_first]['voltage']
            last_v = readings[idx_last]['voltage']
            epoch_diff = last_e - first_e
            if epoch_diff > 0:
                decline_rate = (last_v - first_v) / epoch_diff

        is_flagged = False
        flags = []
        if min_v < DATA_THRESHOLD:
            is_flagged = True
            flags.append(f'LOW_VOLTAGE(min={min_v:.3f}V<{DATA_THRESHOLD}V)')
        if decline_rate < DECLINE_RATE_THRESHOLD:
            is_flagged = True
            flags.append(f'RAPID_DECLINE(rate={decline_rate:.6f}V/epoch)')

        entry = {
            'mote_id': mote_id,
            'reading_count': count,
            'min_voltage': round(min_v, 4),
            'max_voltage': round(max_v, 4),
            'avg_voltage': round(avg_v, 4),
            'voltage_decline_rate_per_epoch': round(decline_rate, 6),
            'is_flagged': is_flagged,
            'flags': flags
        }
        results.append(entry)
        if is_flagged:
            flagged_motes.append(entry)

    output_path = OUTPUT_DIR / 'Battery_Voltage_Health_Indicator_result.json'
    output_data = {
        'task_name': 'Battery Voltage Health Indicator',
        'description': 'Monitor battery voltage levels per mote and flag nodes where voltage drops below a safe operational threshold or exhibits a rapid decline rate indicative of power degradation.',
        'result_summary': [
            f'Total motes analyzed: {len(results)}',
            f'Motes flagged: {len(flagged_motes)}',
            f'Safe voltage threshold: {DATA_THRESHOLD}V',
            f'Decline rate threshold: {DECLINE_RATE_THRESHOLD} V/epoch',
            f'Total rows processed: {total_rows}',
            f'Rows skipped (missing voltage): {skipped_rows}'
        ],
        'mote_details': results,
        'flagged_motes': flagged_motes,
        'result_generated_at': datetime.utcnow().isoformat() + 'Z'
    }

    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f'Result saved to: {output_path}')
    print(f'Motes flagged: {len(flagged_motes)} out of {len(results)}')
    for fm in flagged_motes[:10]:
        print(f"  Mote {fm['mote_id']}: min={fm['min_voltage']}V, avg={fm['avg_voltage']}V, flags={fm['flags']}")

if __name__ == '__main__':
    main()