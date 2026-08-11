"""
Task: Battery Voltage Health Monitor
Description: Track each mote's battery voltage over time, identify readings below a healthy threshold, and compute a simple voltage-temperature correlation indicator to support energy-health diagnostics.
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
import argparse
import csv
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

TASK_NAME = 'Battery Voltage Health Monitor'
DESCRIPTION = "Track each mote's battery voltage over time, identify readings below a healthy threshold, and compute a simple voltage-temperature correlation indicator to support energy-health diagnostics."
OUTPUT_DIR = Path('/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_moonshotai_kimi-k2.7-code_anthropic_claude-3-haiku_run1')
HEALTHY_THRESHOLD = 2.3

MISSING_TOKENS = {'', 'na', 'n/a', 'None', 'none'}


def is_missing(value):
    if value is None:
        return True
    return str(value).strip().lower() in MISSING_TOKENS


def to_float(value, context):
    if is_missing(value):
        return None
    try:
        return float(value)
    except (ValueError, TypeError) as e:
        print(f'Warning: invalid numeric value in {context}: {value!r} ({e})', file=sys.stderr)
        return None


def to_int(value, context):
    if is_missing(value):
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError) as e:
        print(f'Warning: invalid integer in {context}: {value!r} ({e})', file=sys.stderr)
        return None


def resolve_data_file():
    try:
        curr_dir = Path(__file__).resolve().parent
    except NameError:
        curr_dir = Path.cwd()
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


def pearson_r(n, sum_x, sum_y, sum_x2, sum_y2, sum_xy):
    if n < 2:
        return None
    num = n * sum_xy - sum_x * sum_y
    den_x = n * sum_x2 - sum_x * sum_x
    den_y = n * sum_y2 - sum_y * sum_y
    denom = den_x * den_y
    if denom <= 0:
        return None
    return num / math.sqrt(denom)


def main():
    parser = argparse.ArgumentParser(description=TASK_NAME)
    parser.add_argument('--strict', action='store_true', help='Require valid moteid, voltage and temperature for every row')
    args = parser.parse_args()

    data_file = resolve_data_file()
    if data_file is None:
        print('Error: raw_data.csv or raw_data.txt not found under data/lab-data/', file=sys.stderr)
        sys.exit(1)

    motes = {}
    total_rows = 0
    dropped_rows = 0

    with open(data_file, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            print('Error: input file is empty', file=sys.stderr)
            sys.exit(1)
        fieldnames = [fn.lower() for fn in reader.fieldnames]
        required = {'moteid', 'voltage', 'temperature'}
        missing_cols = required - set(fieldnames)
        if missing_cols:
            print(f'Error: missing required columns: {sorted(missing_cols)}', file=sys.stderr)
            sys.exit(1)

        for row in reader:
            total_rows += 1
            row = {k.lower(): v for k, v in row.items()}
            mote_id = to_int(row.get('moteid'), 'moteid')
            voltage = to_float(row.get('voltage'), 'voltage')
            temperature = to_float(row.get('temperature'), 'temperature')

            if mote_id is None or voltage is None:
                dropped_rows += 1
                continue
            if args.strict and temperature is None:
                dropped_rows += 1
                continue

            if mote_id not in motes:
                motes[mote_id] = {
                    'count': 0,
                    'sum_v': 0.0,
                    'sum_v2': 0.0,
                    'min_v': float('inf'),
                    'max_v': float('-inf'),
                    'low_count': 0,
                    'count_corr': 0,
                    'sum_t': 0.0,
                    'sum_t2': 0.0,
                    'sum_vt': 0.0,
                }
            m = motes[mote_id]
            m['count'] += 1
            m['sum_v'] += voltage
            m['sum_v2'] += voltage * voltage
            if voltage < m['min_v']:
                m['min_v'] = voltage
            if voltage > m['max_v']:
                m['max_v'] = voltage
            if voltage < HEALTHY_THRESHOLD:
                m['low_count'] += 1
            if temperature is not None:
                m['count_corr'] += 1
                m['sum_t'] += temperature
                m['sum_t2'] += temperature * temperature
                m['sum_vt'] += voltage * temperature

    if not motes:
        print('Error: no valid data rows found', file=sys.stderr)
        sys.exit(1)

    summary = []
    overall_count = 0
    overall_low = 0
    for mote_id in sorted(motes.keys()):
        m = motes[mote_id]
        count = m['count']
        mean_v = m['sum_v'] / count if count else None
        min_v = m['min_v'] if count else None
        max_v = m['max_v'] if count else None
        low_pct = (m['low_count'] / count * 100.0) if count else 0.0
        corr = pearson_r(m['count_corr'], m['sum_v'], m['sum_t'], m['sum_v2'], m['sum_t2'], m['sum_vt'])
        summary.append({
            'moteid': mote_id,
            'reading_count': count,
            'mean_voltage': round(mean_v, 5) if mean_v is not None else None,
            'min_voltage': round(min_v, 5) if min_v is not None else None,
            'max_voltage': round(max_v, 5) if max_v is not None else None,
            'low_voltage_count': m['low_count'],
            'low_voltage_percent': round(low_pct, 3),
            'voltage_temp_correlation': round(corr, 5) if corr is not None else None,
        })
        overall_count += count
        overall_low += m['low_count']

    overall_pct = (overall_low / overall_count * 100.0) if overall_count else 0.0
    summary.append({
        'moteid': 'overall',
        'reading_count': overall_count,
        'low_voltage_count': overall_low,
        'low_voltage_percent': round(overall_pct, 3),
    })

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result = {
        'task_name': TASK_NAME,
        'description': DESCRIPTION,
        'result_summary': summary,
        'result_generated_at': datetime.now(timezone.utc).isoformat(),
    }
    out_path = OUTPUT_DIR / f'{TASK_NAME}_result.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)

    print(f'{TASK_NAME}: processed {total_rows} rows ({dropped_rows} dropped), {len(motes)} motes. Result saved to {out_path}')


if __name__ == '__main__':
    main()