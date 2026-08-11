"""
Task: O3 Sensor Baseline Characterizer
Description: Compute rolling mean, standard deviation, and min/max of PT08.S5(O3) resistance over daily windows. Detect sustained deviations from the established baseline that may indicate environmental changes or sensor drift.
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

import os
import sys
import csv
import json
import math
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict

MISSING_STRINGS = {'', 'na', 'n/a', 'None', 'none', '-200'}

def is_missing(v):
    if v is None:
        return True
    s = str(v).strip().lower()
    return s in MISSING_STRINGS

def safe_float(v, col):
    if is_missing(v):
        return None
    try:
        f = float(v)
        if f <= -199.0:
            return None
        return f
    except Exception as e:
        print(f'Warning: cannot parse {col} value {v!r}: {e}', file=sys.stderr)
        return None

def resolve_data_file():
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / 'data').exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent
    for name in ('raw_data.csv', 'raw_data.txt'):
        candidate = root_dir / 'data' / 'air-quality' / name
        if candidate.exists():
            return candidate
    return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--strict', action='store_true', help='Require valid O3 reading on every row')
    args = parser.parse_args()

    data_file = resolve_data_file()
    if not data_file:
        print('Error: raw_data.csv/txt not found under data/air-quality/', file=sys.stderr)
        sys.exit(1)

    o3_col = 'pt08.s5(o3)'
    date_col = 'date'
    rows_total = 0
    rows_dropped = 0
    daily_values = defaultdict(list)

    try:
        with open(data_file, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                print('Error: empty file', file=sys.stderr)
                sys.exit(1)
            fieldnames = [fn.lower() for fn in reader.fieldnames]
            if o3_col not in fieldnames:
                print(f'Error: required column {o3_col} not found', file=sys.stderr)
                sys.exit(1)
            if date_col not in fieldnames:
                print(f'Error: required column {date_col} not found', file=sys.stderr)
                sys.exit(1)

            for raw_row in reader:
                rows_total += 1
                row = {k.lower(): v for k, v in raw_row.items()}
                date_val = row.get(date_col)
                o3_val = safe_float(row.get(o3_col), o3_col)
                if args.strict and o3_val is None:
                    rows_dropped += 1
                    continue
                if o3_val is None:
                    rows_dropped += 1
                    continue
                if not date_val or str(date_val).strip() == '':
                    rows_dropped += 1
                    continue
                daily_values[str(date_val).strip()].append(o3_val)
    except Exception as e:
        print(f'Error reading data: {e}', file=sys.stderr)
        sys.exit(1)

    if not daily_values:
        print('Error: no valid O3 readings found', file=sys.stderr)
        sys.exit(1)

    daily_stats = []
    for date in sorted(daily_values.keys(), key=lambda d: datetime.strptime(d, '%d-%m-%Y')):
        vals = daily_values[date]
        n = len(vals)
        mean = sum(vals) / n
        variance = sum((x - mean) ** 2 for x in vals) / n
        std = math.sqrt(variance)
        daily_stats.append({
            'date': date,
            'count': n,
            'mean': round(mean, 4),
            'std': round(std, 4),
            'min': round(min(vals), 4),
            'max': round(max(vals), 4)
        })

    daily_means = [d['mean'] for d in daily_stats]
    baseline_mean = sum(daily_means) / len(daily_means)
    baseline_var = sum((m - baseline_mean) ** 2 for m in daily_means) / len(daily_means)
    baseline_std = math.sqrt(baseline_var)
    baseline = {
        'daily_mean_avg': round(baseline_mean, 4),
        'daily_mean_std': round(baseline_std, 4),
        'min_daily_mean': round(min(daily_means), 4),
        'max_daily_mean': round(max(daily_means), 4)
    }

    window = 7
    rolling = []
    for i in range(len(daily_stats)):
        start = max(0, i - window + 1)
        window_means = daily_means[start:i+1]
        wmean = sum(window_means) / len(window_means)
        wvar = sum((m - wmean) ** 2 for m in window_means) / len(window_means)
        wstd = math.sqrt(wvar)
        rolling.append({
            'date': daily_stats[i]['date'],
            'window_days': len(window_means),
            'rolling_mean': round(wmean, 4),
            'rolling_std': round(wstd, 4)
        })

    threshold = 2.0 * baseline_std
    anomalies = []
    for d in daily_stats:
        dev = abs(d['mean'] - baseline_mean)
        if dev > threshold:
            anomalies.append({
                'date': d['date'],
                'daily_mean': d['mean'],
                'deviation': round(dev, 4),
                'direction': 'high' if d['mean'] > baseline_mean else 'low'
            })

    summary = {
        'input_file': str(data_file),
        'rows_total': rows_total,
        'rows_dropped_missing': rows_dropped,
        'days_analyzed': len(daily_stats),
        'baseline': baseline,
        'daily_statistics_sample': daily_stats[:5],
        'rolling_statistics_sample': rolling[:5],
        'anomalies_detected': len(anomalies),
        'anomaly_sample': anomalies[:10]
    }

    result = {
        'task_name': 'O3 Sensor Baseline Characterizer',
        'description': 'Compute rolling mean, standard deviation, and min/max of PT08.S5(O3) resistance over daily windows. Detect sustained deviations from the established baseline that may indicate environmental changes or sensor drift.',
        'result_summary': [summary],
        'result_generated_at': datetime.utcnow().isoformat() + 'Z'
    }

    out_dir = Path('/home/dcc/LEI-Models-Comparision/output/air-quality/air-quality_moonshotai_kimi-k2.7-code_google_gemini-3.1-flash-lite_run1')
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / 'O3_Sensor_Baseline_Characterizer_result.json'
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
    print(f'Result saved to {out_file}')

if __name__ == '__main__':
    main()