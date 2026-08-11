"""
Task: Per-Mote Temperature Rolling Average and Trend
Description: Compute a sliding-window average of temperature readings for each mote over the most recent epochs and flag rising or falling trends that exceed a configurable threshold, supporting lightweight local trend monitoring.
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
import os
import sys
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path

TASK_NAME = 'Per-Mote Temperature Rolling Average and Trend'
OUTPUT_DIR = Path('/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_moonshotai_kimi-k2.7-code_anthropic_claude-3-haiku_run1')

def find_data_file():
    curr_dir = Path(__file__).resolve().parent
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

def is_missing(v):
    if v is None:
        return True
    s = str(v).strip()
    return s == '' or s.lower() in ('na', 'n/a', 'None', 'none')

def to_float(v, col):
    if is_missing(v):
        return None
    try:
        return float(v)
    except Exception:
        print(f'Warning: invalid numeric value in column {col!r}: {v!r}; treating as missing', file=sys.stderr)
        return None

def to_int(v, col):
    if is_missing(v):
        return None
    try:
        return int(float(v))
    except Exception:
        print(f'Warning: invalid integer value in column {col!r}: {v!r}; treating as missing', file=sys.stderr)
        return None

def main():
    parser = argparse.ArgumentParser(description='Per-mote temperature rolling average and trend')
    parser.add_argument('--window', type=int, default=10, help='Rolling window size (epochs)')
    parser.add_argument('--threshold', type=float, default=0.5, help='Trend threshold in degrees Celsius')
    parser.add_argument('--strict', action='store_true', help='Fail if any required rows are missing or invalid')
    args = parser.parse_args()

    data_file = find_data_file()
    if data_file is None:
        print('Error: could not locate data/lab-data/raw_data.csv or .txt', file=sys.stderr)
        sys.exit(1)

    window = args.window
    threshold = args.threshold

    state = defaultdict(lambda: {
        'window': deque(maxlen=window),
        'sum': 0.0,
        'prev_avg': None,
        'latest_epoch': None,
        'latest_temp': None,
        'latest_date': None,
        'latest_time': None,
        'trend_direction': 'stable',
        'trend_magnitude': 0.0,
    })

    total_rows = 0
    dropped_rows = 0
    valid_rows = 0

    with open(data_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            row = {k.lower(): v for k, v in row.items()}
            mote = to_int(row.get('moteid'), 'moteid')
            epoch = to_int(row.get('epoch'), 'epoch')
            temp = to_float(row.get('temperature'), 'temperature')
            if mote is None or epoch is None or temp is None:
                dropped_rows += 1
                continue
            if temp < 0 or temp > 50:
                dropped_rows += 1
                print(f'Warning: temperature {temp} out of range for mote {mote} epoch {epoch}; skipping', file=sys.stderr)
                continue

            valid_rows += 1
            st = state[mote]
            if len(st['window']) == window:
                st['sum'] -= st['window'][0]
            st['window'].append(temp)
            st['sum'] += temp
            current_avg = st['sum'] / len(st['window'])

            if st['prev_avg'] is not None:
                diff = current_avg - st['prev_avg']
                if diff > threshold:
                    st['trend_direction'] = 'rising'
                    st['trend_magnitude'] = round(diff, 4)
                elif diff < -threshold:
                    st['trend_direction'] = 'falling'
                    st['trend_magnitude'] = round(abs(diff), 4)
                else:
                    st['trend_direction'] = 'stable'
                    st['trend_magnitude'] = round(abs(diff), 4)
            st['prev_avg'] = current_avg

            if st['latest_epoch'] is None or epoch > st['latest_epoch']:
                st['latest_epoch'] = epoch
                st['latest_temp'] = round(temp, 4)
                st['latest_date'] = row.get('date')
                st['latest_time'] = row.get('time')

    if args.strict and dropped_rows > 0:
        print(f'Error: strict mode enabled but {dropped_rows} rows were dropped', file=sys.stderr)
        sys.exit(1)

    if not state:
        print('No valid sensor data found.', file=sys.stderr)
        sys.exit(1)

    summary = []
    for mote in sorted(state.keys()):
        st = state[mote]
        n = len(st['window'])
        avg = round(st['sum'] / n, 4) if n else None
        summary.append({
            'moteid': mote,
            'latest_epoch': st['latest_epoch'],
            'latest_date': st['latest_date'],
            'latest_time': st['latest_time'],
            'latest_temperature': st['latest_temp'],
            'rolling_window_size': n,
            'rolling_average_temperature': avg,
            'trend_direction': st['trend_direction'],
            'trend_magnitude_celsius': st['trend_magnitude'],
        })

    result = {
        'task_name': TASK_NAME,
        'description': 'Sliding-window average of temperature per mote over recent epochs with rising/falling trend flags.',
        'result_summary': summary,
        'result_generated_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        'metadata': {
            'input_file': str(data_file),
            'total_rows': total_rows,
            'valid_rows': valid_rows,
            'dropped_rows': dropped_rows,
            'window_size': window,
            'trend_threshold_celsius': threshold,
        }
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f'{TASK_NAME}_result.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)

    print(f'Processed {valid_rows}/{total_rows} rows; dropped {dropped_rows}.')
    print(f'Results saved to {out_path}')
    rising = sum(1 for s in summary if s['trend_direction'] == 'rising')
    falling = sum(1 for s in summary if s['trend_direction'] == 'falling')
    print(f'Motes trending: rising={rising}, falling={falling}, stable={len(summary)-rising-falling}')

if __name__ == '__main__':
    main()