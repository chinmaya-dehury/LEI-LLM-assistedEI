"""
Task: NOx_Sensor_Drift_Monitor
Description: Compute a rolling 7-day mean of the difference between PT08.S3(NOx) sensor response and NOx(GT) ground truth to detect long-term sensor drift.
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
import csv
import json
import math
from pathlib import Path
from datetime import datetime
from collections import defaultdict

TASK_NAME = 'NOx_Sensor_Drift_Monitor'
DESCRIPTION = 'Compute a rolling 7-day mean of the difference between PT08.S3(NOx) sensor response and NOx(GT) ground truth to detect long-term sensor drift.'

def find_project_root():
    curr = Path(__file__).resolve().parent
    while curr.name and not (curr / 'data').exists():
        parent = curr.parent
        if parent == curr:
            break
        curr = parent
    return curr

def is_missing(v):
    if v is None:
        return True
    s = str(v).strip()
    return s == '' or s.lower() in {'na', 'n/a', 'None', 'none'} or s == '-200'

def to_float(v, col):
    if is_missing(v):
        return None
    try:
        return float(v)
    except Exception:
        print(f'Warning: invalid numeric value in {col}: {v!r}', flush=True)
        return None

def parse_date(s):
    try:
        return datetime.strptime(s.strip(), '%d-%m-%Y').date()
    except Exception:
        return None

def main():
    root = find_project_root()
    data_dir = root / 'data' / 'air-quality'
    data_file = data_dir / 'raw_data.csv'
    if not data_file.exists():
        data_file = data_dir / 'raw_data.txt'
    if not data_file.exists():
        print(f'Input file not found in {data_dir}', flush=True)
        return

    daily_diffs = defaultdict(list)
    dropped = 0
    total = 0
    sensor_col = 'pt08.s3(nox)'
    gt_col = 'nox(gt)'

    with open(data_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            row = {k.lower().strip(): v for k, v in row.items()}
            d = parse_date(row.get('date', ''))
            s_val = to_float(row.get(sensor_col), sensor_col)
            g_val = to_float(row.get(gt_col), gt_col)
            if d is None or s_val is None or g_val is None:
                dropped += 1
                continue
            daily_diffs[d].append(s_val - g_val)

    print(f'Processed {total} rows, dropped {dropped} invalid rows.', flush=True)

    if not daily_diffs:
        print('No valid daily data available.', flush=True)
        return

    daily_means = {}
    for d, diffs in daily_diffs.items():
        daily_means[d] = sum(diffs) / len(diffs)

    sorted_dates = sorted(daily_means.keys())
    result_summary = []
    window = []
    for d in sorted_dates:
        window.append(daily_means[d])
        if len(window) > 7:
            window.pop(0)
        rolling_mean = sum(window) / len(window)
        result_summary.append({
            'date': d.strftime('%d-%m-%Y'),
            'daily_mean_diff': round(daily_means[d], 4),
            'rolling_7day_mean_diff': round(rolling_mean, 4)
        })

    overall_mean = sum(daily_means.values()) / len(daily_means)
    stats = {
        'total_days': len(daily_means),
        'overall_mean_diff': round(overall_mean, 4),
        'first_date': sorted_dates[0].strftime('%d-%m-%Y'),
        'last_date': sorted_dates[-1].strftime('%d-%m-%Y')
    }

    out_dir = Path('/home/dcc/LEI-Models-Comparision/output/air-quality/air-quality_moonshotai_kimi-k2.7-code_anthropic_claude-3-haiku_run2')
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f'{TASK_NAME}_result.json'

    output = {
        'task_name': TASK_NAME,
        'description': DESCRIPTION,
        'result_summary': result_summary,
        'stats': stats,
        'result_generated_at': datetime.utcnow().isoformat() + 'Z'
    }

    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)
    print(f'Saved results to {out_file}', flush=True)

if __name__ == '__main__':
    main()