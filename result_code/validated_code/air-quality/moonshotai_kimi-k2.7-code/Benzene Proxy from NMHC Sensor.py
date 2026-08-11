import json
import sys
import math
"""
Task: Benzene Proxy from NMHC Sensor
Description: Estimate C6H6(GT) benzene concentration from PT08.S2(NMHC) using a simple linear regression over a sliding window of valid observations. This provides a low-cost proxy when a dedicated benzene sensor channel is unavailable.
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

import csv, json, math, sys
from pathlib import Path
from collections import deque
from datetime import datetime

TASK_NAME = 'Benzene Proxy from NMHC Sensor'
TASK_SLUG = 'benzene_proxy_from_nmhc_sensor'
TARGET = 'c6h6(gt)'
SENSOR = 'pt08.s2(nmhc)'
WINDOW = 168
MISSING = {'', 'na', 'n/a', 'None', '-200'}


def find_root():
    curr = Path(__file__).resolve().parent
    root = curr
    while root.name and not (root / 'data').exists():
        parent = root.parent
        if parent == root:
            break
        root = parent
    return root


def to_float(value, col_name, log, log_limit):
    if value is None:
        return None
    s = str(value).strip()
    if s.lower() in MISSING:
        return None
    try:
        f = float(s)
    except Exception:
        if log['count'] < log_limit:
            print(f'Invalid numeric value in {col_name}: {value!r}', file=sys.stderr)
            log['count'] += 1
        return None
    if f <= -200:
        return None
    return f


def main():
    strict = '--strict' in sys.argv
    root = find_root()
    if not (root / 'data').exists():
        print('Project root with data directory not found.', file=sys.stderr)
        sys.exit(1)

    data_file = root / 'data' / 'air-quality' / 'raw_data.csv'
    if not data_file.exists():
        data_file = root / 'data' / 'air-quality' / 'raw_data.txt'
    if not data_file.exists():
        print(f'Input file not found: {data_file}', file=sys.stderr)
        sys.exit(1)

    out_dir = Path('/home/dcc/LEI-Models-Comparision/output/air-quality/air-quality_moonshotai_kimi-k2.7-code_google_gemini-3.1-flash-lite_run1')
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f'{TASK_SLUG}_result.json'

    window = deque()
    sum_x = sum_y = sum_xx = sum_xy = 0.0
    total_rows = 0
    dropped = 0
    predictions = 0
    sum_sq_err = 0.0
    latest = {}
    invalid_log = {'count': 0}
    log_limit = 5

    with open(data_file, newline='') as f:
        reader = csv.DictReader(f)
        fieldnames = [n.lower() for n in reader.fieldnames if n]
        if TARGET not in fieldnames or SENSOR not in fieldnames:
            print(f'Required columns missing: {TARGET}, {SENSOR}', file=sys.stderr)
            sys.exit(1)

        for raw in reader:
            total_rows += 1
            row = {k.lower(): v for k, v in raw.items() if k}
            x = to_float(row.get(SENSOR), SENSOR, invalid_log, log_limit)
            y = to_float(row.get(TARGET), TARGET, invalid_log, log_limit)

            if x is None or y is None:
                dropped += 1
                if strict:
                    print(f'Strict mode: missing/invalid value at row {total_rows}', file=sys.stderr)
                    sys.exit(1)
                continue

            n = len(window)
            if n >= 2:
                denom = n * sum_xx - sum_x * sum_x
                if abs(denom) < 1e-12:
                    slope = 0.0
                    intercept = sum_y / n
                else:
                    slope = (n * sum_xy - sum_x * sum_y) / denom
                    intercept = (sum_y - slope * sum_x) / n
                y_hat = slope * x + intercept
                err = y - y_hat
                predictions += 1
                sum_sq_err += err * err
                latest = {
                    'date': row.get('date'),
                    'time': row.get('time'),
                    'sensor_nmhc': x,
                    'benzene_gt': y,
                    'benzene_predicted': round(y_hat, 4),
                    'residual': round(err, 4),
                    'slope': round(slope, 6),
                    'intercept': round(intercept, 6),
                }

            if len(window) == WINDOW:
                ox, oy = window.popleft()
                sum_x -= ox
                sum_y -= oy
                sum_xx -= ox * ox
                sum_xy -= ox * oy
            window.append((x, y))
            sum_x += x
            sum_y += y
            sum_xx += x * x
            sum_xy += x * y

    n = len(window)
    final_slope = final_intercept = None
    if n >= 2:
        denom = n * sum_xx - sum_x * sum_x
        if abs(denom) < 1e-12:
            final_slope = 0.0
            final_intercept = sum_y / n
        else:
            final_slope = (n * sum_xy - sum_x * sum_y) / denom
            final_intercept = (sum_y - final_slope * sum_x) / n

    rmse = math.sqrt(sum_sq_err / predictions) if predictions > 0 else None

    summary = {
        'task': TASK_NAME,
        'input_file': str(data_file),
        'total_rows': total_rows,
        'valid_pairs': total_rows - dropped,
        'dropped_rows': dropped,
        'window_size': WINDOW,
        'final_window_count': n,
        'predictions_made': predictions,
        'rmse_predictions': round(rmse, 4) if rmse is not None else None,
        'final_slope': round(final_slope, 6) if final_slope is not None else None,
        'final_intercept': round(final_intercept, 6) if final_intercept is not None else None,
        'latest_prediction': latest,
    }

    result = {
        'task_name': TASK_NAME,
        'description': 'Estimate C6H6(GT) benzene concentration from PT08.S2(NMHC) using a simple linear regression over a sliding window of valid observations.',
        'result_summary': [summary],
        'result_generated_at': datetime.utcnow().isoformat() + 'Z',
    }

    with open(out_file, 'w') as f:
        json.dump(result, f, indent=2)

    print(f'Saved result to {out_file}')
    if rmse is not None:
        print(f'Rows: {total_rows}, valid pairs: {total_rows - dropped}, predictions: {predictions}, RMSE: {rmse:.4f}')
    else:
        print(f'Rows: {total_rows}, valid pairs: {total_rows - dropped}, predictions: {predictions}')


if __name__ == '__main__':
    main()