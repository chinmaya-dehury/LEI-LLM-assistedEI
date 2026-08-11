"""
Task: Voltage-Temperature Correlation Monitor
Description: Compute a rolling correlation between voltage and temperature for each mote to detect unexpected battery behavior or calibration issues.
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
import sys
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path

MISSING = {'', 'na', 'n/a', 'None', 'none'}
REQUIRED = {'moteid', 'temperature', 'voltage'}
DEFAULT_WINDOW = 50


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


def to_float(value, col, row_num):
    if value is None:
        return None
    v = value.strip().lower()
    if v in MISSING:
        return None
    try:
        return float(v)
    except ValueError:
        print(f'Row {row_num}: invalid {col} value {value!r}; skipped', file=sys.stderr)
        return None


def to_int(value, col, row_num):
    if value is None:
        return None
    v = value.strip().lower()
    if v in MISSING:
        return None
    try:
        return int(float(v))
    except ValueError:
        print(f'Row {row_num}: invalid {col} value {value!r}; skipped', file=sys.stderr)
        return None


class MoteState:
    __slots__ = ('window', 'xs', 'ys', 'sx', 'sy', 'sxx', 'syy', 'sxy',
                 'n', 'total_added', 'dropped', 'latest_r', 'sum_r',
                 'count_r', 'min_r', 'max_r')

    def __init__(self, window):
        self.window = window
        self.xs = deque(maxlen=window)
        self.ys = deque(maxlen=window)
        self.sx = 0.0
        self.sy = 0.0
        self.sxx = 0.0
        self.syy = 0.0
        self.sxy = 0.0
        self.n = 0
        self.total_added = 0
        self.dropped = 0
        self.latest_r = None
        self.sum_r = 0.0
        self.count_r = 0
        self.min_r = None
        self.max_r = None

    def add(self, x, y):
        self.xs.append(x)
        self.ys.append(y)
        self.sx += x
        self.sy += y
        self.sxx += x * x
        self.syy += y * y
        self.sxy += x * y
        self.n += 1
        self.total_added += 1
        if self.n > self.window:
            ox = self.xs.popleft()
            oy = self.ys.popleft()
            self.sx -= ox
            self.sy -= oy
            self.sxx -= ox * ox
            self.syy -= oy * oy
            self.sxy -= ox * oy
            self.n = self.window
        if self.n == self.window:
            num = self.n * self.sxy - self.sx * self.sy
            denom_x = self.n * self.sxx - self.sx * self.sx
            denom_y = self.n * self.syy - self.sy * self.sy
            denom = denom_x * denom_y
            if denom <= 0:
                r = None
            else:
                r = num / math.sqrt(denom)
                r = max(-1.0, min(1.0, r))
            self.latest_r = r
            if r is not None:
                self.sum_r += r
                self.count_r += 1
                if self.min_r is None or r < self.min_r:
                    self.min_r = r
                if self.max_r is None or r > self.max_r:
                    self.max_r = r


def main():
    parser = argparse.ArgumentParser(description='Rolling voltage-temperature correlation per mote')
    parser.add_argument('--strict', action='store_true', help='Abort if any required field is missing or invalid')
    parser.add_argument('--window', type=int, default=DEFAULT_WINDOW, help='Rolling window size')
    args = parser.parse_args()
    window = args.window
    if window < 2:
        print('Window must be at least 2', file=sys.stderr)
        sys.exit(1)

    data_file = find_data_file()
    if data_file is None:
        print('Input data file not found under data/lab-data/', file=sys.stderr)
        sys.exit(1)
    print(f'Reading {data_file}')

    output_dir = Path('/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_moonshotai_kimi-k2.7-code_google_gemini-3.1-flash-lite_run1')
    output_dir.mkdir(parents=True, exist_ok=True)
    task_slug = 'voltage_temperature_correlation_monitor'
    out_path = output_dir / f'{task_slug}_result.json'

    def make_state():
        return MoteState(window)

    motes = defaultdict(make_state)
    total_rows = 0
    global_dropped = 0

    with open(data_file, 'r', newline='') as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            print('Empty input file', file=sys.stderr)
            sys.exit(1)
        fields = {fn.lower() for fn in reader.fieldnames}
        missing_cols = REQUIRED - fields
        if missing_cols:
            print(f'Missing required columns: {sorted(missing_cols)}', file=sys.stderr)
            sys.exit(1)

        for row_num, raw_row in enumerate(reader, start=2):
            total_rows += 1
            row = {k.lower(): v for k, v in raw_row.items()}
            moteid = to_int(row.get('moteid'), 'moteid', row_num)
            temp = to_float(row.get('temperature'), 'temperature', row_num)
            voltage = to_float(row.get('voltage'), 'voltage', row_num)

            if moteid is None or temp is None or voltage is None:
                global_dropped += 1
                if moteid is not None:
                    motes[moteid].dropped += 1
                continue

            motes[moteid].add(temp, voltage)

    if args.strict and global_dropped:
        print(f'Strict mode: {global_dropped} rows had missing/invalid required fields. Aborting.', file=sys.stderr)
        sys.exit(1)

    summary = [{
        'total_rows': total_rows,
        'global_dropped': global_dropped,
        'motes_observed': len(motes),
        'window_size': window
    }]

    for moteid in sorted(motes.keys()):
        st = motes[moteid]
        mean_r = st.sum_r / st.count_r if st.count_r else None
        summary.append({
            'moteid': moteid,
            'valid_pairs': st.total_added,
            'dropped_rows': st.dropped,
            'windows_computed': st.count_r,
            'latest_correlation': st.latest_r,
            'mean_correlation': mean_r,
            'min_correlation': st.min_r,
            'max_correlation': st.max_r
        })

    result = {
        'task_name': 'Voltage-Temperature Correlation Monitor',
        'description': 'Rolling Pearson correlation between voltage and temperature per mote to detect battery or calibration anomalies.',
        'result_summary': summary,
        'result_generated_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    }

    with open(out_path, 'w') as f:
        json.dump(result, f, indent=2)

    print(f'Processed {total_rows} rows, dropped {global_dropped}. Results saved to {out_path}')


if __name__ == '__main__':
    main()