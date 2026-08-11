"""
Task: Diurnal Baseline Profiler
Description: Maintain running hourly-of-day averages for CO(GT) and NO2(GT), and compare the current reading to its corresponding hour-of-day baseline to detect atypical pollution levels.
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
'''Diurnal Baseline Profiler for air quality sensor data.

Computes hourly-of-day baselines for CO(GT) and NO2(GT) from historical
readings and flags current readings that deviate significantly from their
hour-of-day baseline.
'''
import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

MISSING_SENTINELS = {'', 'na', 'n/a', 'None', 'none', '-200'}
OUTPUT_DIR = Path('/home/dcc/LEI-Models-Comparision/output/air-quality/air-quality_moonshotai_kimi-k2.7-code_nvidia_nemotron-3-ultra-550b-a55b_run2')
TASK_NAME = 'Diurnal Baseline Profiler'
TASK_DESCRIPTION = (
    'Maintain running hourly-of-day averages for CO(GT) and NO2(GT), '
    'and compare the current reading to its corresponding hour-of-day '
    'baseline to detect atypical pollution levels.'
)


def is_missing(value):
    if value is None:
        return True
    return str(value).strip().lower() in MISSING_SENTINELS


def safe_float(value, column_name):
    if is_missing(value):
        return None
    try:
        return float(value)
    except (ValueError, TypeError) as exc:
        print(
            f'Warning: invalid numeric value for {column_name}: {value!r} ({exc})',
            file=sys.stderr,
        )
        return None


def resolve_data_file():
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / 'data').exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent
    for fname in ('raw_data.csv', 'raw_data.txt'):
        candidate = root_dir / 'data' / 'air-quality' / fname
        if candidate.exists():
            return candidate
    return None


def parse_hour(time_str):
    if not time_str:
        return None
    parts = time_str.strip().split(':')
    if not parts:
        return None
    try:
        return int(parts[0])
    except (ValueError, IndexError):
        return None


def is_atypical(value, baseline, multiplier):
    if value is None or baseline is None:
        return False
    if baseline == 0:
        return value > 0
    return value > multiplier * baseline


def main():
    parser = argparse.ArgumentParser(description='Diurnal baseline profiler for CO and NO2.')
    parser.add_argument('--strict', action='store_true', help='Skip rows missing required fields entirely.')
    args = parser.parse_args()

    data_file = resolve_data_file()
    if data_file is None:
        print('Error: could not locate data/air-quality/raw_data.csv or raw_data.txt', file=sys.stderr)
        sys.exit(1)

    required_cols = ['date', 'time', 'co(gt)', 'no2(gt)']
    co_key = 'co(gt)'
    no2_key = 'no2(gt)'

    hourly = {
        h: {'co_sum': 0.0, 'co_count': 0, 'no2_sum': 0.0, 'no2_count': 0}
        for h in range(24)
    }
    total_rows = 0
    dropped_rows = 0

    # First pass: accumulate hourly sums and counts.
    with open(data_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            row = {k.lower(): v for k, v in row.items()}

            missing_cols = [c for c in required_cols if c not in row]
            if missing_cols:
                dropped_rows += 1
                print(
                    f'Warning: row {total_rows} missing columns {missing_cols}',
                    file=sys.stderr,
                )
                continue

            hour = parse_hour(row.get('time'))
            if hour is None:
                dropped_rows += 1
                print(
                    f'Warning: row {total_rows} has unparseable time {row.get("time")!r}',
                    file=sys.stderr,
                )
                continue

            co = safe_float(row.get(co_key), co_key)
            no2 = safe_float(row.get(no2_key), no2_key)

            if co is None and no2 is None:
                dropped_rows += 1
                continue

            if co is not None:
                hourly[hour]['co_sum'] += co
                hourly[hour]['co_count'] += 1
            if no2 is not None:
                hourly[hour]['no2_sum'] += no2
                hourly[hour]['no2_count'] += 1

    # Compute baselines.
    baselines = {}
    for h in range(24):
        stats = hourly[h]
        co_base = stats['co_sum'] / stats['co_count'] if stats['co_count'] else None
        no2_base = stats['no2_sum'] / stats['no2_count'] if stats['no2_count'] else None
        baselines[h] = {'co': co_base, 'no2': no2_base}

    # Second pass: compare each reading to its baseline.
    threshold_multiplier = 1.5
    atypical_co = 0
    atypical_no2 = 0
    hourly_atypical = {h: {'co': 0, 'no2': 0} for h in range(24)}
    sample_atypical = []

    with open(data_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            row = {k.lower(): v for k, v in row.items()}
            if 'time' not in row or co_key not in row or no2_key not in row:
                continue

            hour = parse_hour(row.get('time'))
            if hour is None:
                continue

            co = safe_float(row.get(co_key), co_key)
            no2 = safe_float(row.get(no2_key), no2_key)
            base_co = baselines[hour]['co']
            base_no2 = baselines[hour]['no2']

            if is_atypical(co, base_co, threshold_multiplier):
                atypical_co += 1
                hourly_atypical[hour]['co'] += 1
                if len(sample_atypical) < 10:
                    sample_atypical.append({
                        'row': idx,
                        'date': row.get('date'),
                        'time': row.get('time'),
                        'hour': hour,
                        'pollutant': 'CO(GT)',
                        'value': co,
                        'baseline': base_co,
                        'deviation_pct': round(((co - base_co) / base_co) * 100, 2) if base_co else None,
                    })

            if is_atypical(no2, base_no2, threshold_multiplier):
                atypical_no2 += 1
                hourly_atypical[hour]['no2'] += 1
                if len(sample_atypical) < 10:
                    sample_atypical.append({
                        'row': idx,
                        'date': row.get('date'),
                        'time': row.get('time'),
                        'hour': hour,
                        'pollutant': 'NO2(GT)',
                        'value': no2,
                        'baseline': base_no2,
                        'deviation_pct': round(((no2 - base_no2) / base_no2) * 100, 2) if base_no2 else None,
                    })

    # Build per-hour baseline profiles.
    baseline_profiles = []
    for h in range(24):
        base_co = baselines[h]['co']
        base_no2 = baselines[h]['no2']
        baseline_profiles.append({
            'hour': h,
            'co_baseline': round(base_co, 4) if base_co is not None else None,
            'co_reading_count': hourly[h]['co_count'],
            'co_atypical_count': hourly_atypical[h]['co'],
            'no2_baseline': round(base_no2, 4) if base_no2 is not None else None,
            'no2_reading_count': hourly[h]['no2_count'],
            'no2_atypical_count': hourly_atypical[h]['no2'],
        })

    valid_co = sum(hourly[h]['co_count'] for h in range(24))
    valid_no2 = sum(hourly[h]['no2_count'] for h in range(24))

    result = {
        'task_name': TASK_NAME,
        'description': TASK_DESCRIPTION,
        'result_summary': [
            {
                'summary': {
                    'total_rows_read': total_rows,
                    'rows_dropped': dropped_rows,
                    'valid_co_readings': valid_co,
                    'valid_no2_readings': valid_no2,
                    'threshold_description': (
                        f'Atypical if value > {threshold_multiplier} * hourly baseline '
                        '(or > 0 when baseline is 0)'
                    ),
                    'total_atypical_co_readings': atypical_co,
                    'total_atypical_no2_readings': atypical_no2,
                }
            },
            {'baseline_profiles': baseline_profiles},
            {'sample_atypical_readings': sample_atypical},
        ],
        'result_generated_at': datetime.now(timezone.utc).isoformat(),
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_file = OUTPUT_DIR / 'diurnal_baseline_profiler_result.json'
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)

    print(f'Result written to {out_file}')


if __name__ == '__main__':
    main()