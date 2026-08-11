import json
import sys
import math
import csv
"""
Task: Short_Window_Cross_Sensitivity_Index
Description: Calculate the Pearson correlation between two targeted sensor responses, such as PT08.S1(CO) and PT08.S3(NOx), over a small rolling window to detect potential cross-sensitivity.
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

import os, sys, csv, math, json
from pathlib import Path
from datetime import datetime

TASK_NAME = 'Short_Window_Cross_Sensitivity_Index'
OUT_DIR = Path('/home/dcc/LEI-Models-Comparision/output/air-quality/air-quality_moonshotai_kimi-k2.7-code_anthropic_claude-3-haiku_run1')
WINDOW_SIZE = 24

MISSING = {'', 'NA', 'N/A', 'na', 'n/a', 'None', 'NULL', '-200', '-200.0'}

def find_data_file():
    curr = Path(__file__).resolve().parent
    root = curr
    while root.name and not (root / 'data').exists():
        parent = root.parent
        if parent == root:
            break
        root = parent
    for name in ['raw_data.csv', 'raw_data.txt']:
        p = root / 'data' / 'air-quality' / name
        if p.exists():
            return p
    return None

def to_float(v):
    if v is None:
        return None
    s = str(v).strip()
    if s in MISSING:
        return None
    try:
        f = float(s)
    except ValueError:
        return None
    if f == -200.0:
        return None
    return f

def pearson(xs, ys):
    n = len(xs)
    if n < 2:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    num = 0.0
    dx2 = 0.0
    dy2 = 0.0
    for x, y in zip(xs, ys):
        dx = x - mx
        dy = y - my
        num += dx * dy
        dx2 += dx * dx
        dy2 += dy * dy
    denom = math.sqrt(dx2 * dy2)
    if denom == 0:
        return None
    return num / denom

def main():
    data_file = find_data_file()
    if not data_file:
        print('Data file not found in data/air-quality/', file=sys.stderr)
        sys.exit(1)

    col_x = 'pt08.s1(co)'
    col_y = 'pt08.s3(nox)'
    xs_full = []
    ys_full = []
    dropped = 0

    with open(data_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            row = {k.lower().strip(): v for k, v in row.items()}
            if col_x not in row or col_y not in row:
                dropped += 1
                continue
            x = to_float(row.get(col_x))
            y = to_float(row.get(col_y))
            if x is None or y is None:
                dropped += 1
                continue
            xs_full.append(x)
            ys_full.append(y)

    if len(xs_full) < WINDOW_SIZE:
        print('Not enough valid data for window size', file=sys.stderr)
        sys.exit(1)

    windows = []
    for i in range(len(xs_full) - WINDOW_SIZE + 1):
        wx = xs_full[i:i + WINDOW_SIZE]
        wy = ys_full[i:i + WINDOW_SIZE]
        r = pearson(wx, wy)
        windows.append({'window_start': i, 'window_end': i + WINDOW_SIZE - 1, 'correlation': r, 'valid_pairs': WINDOW_SIZE})

    valid_corr = [w['correlation'] for w in windows if w['correlation'] is not None]
    summary = {
        'total_windows': len(windows),
        'window_size': WINDOW_SIZE,
        'valid_windows': len(valid_corr),
        'mean_correlation': round(sum(valid_corr) / len(valid_corr), 4) if valid_corr else None,
        'min_correlation': round(min(valid_corr), 4) if valid_corr else None,
        'max_correlation': round(max(valid_corr), 4) if valid_corr else None,
        'sample_windows': windows[:5] + windows[-5:] if len(windows) >= 10 else windows,
        'dropped_rows': dropped
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f'{TASK_NAME}_result.json'
    result = {
        'task_name': TASK_NAME,
        'description': 'Rolling-window Pearson correlation between PT08.S1(CO) and PT08.S3(NOx) sensor responses to detect cross-sensitivity.',
        'result_summary': [summary],
        'result_generated_at': datetime.utcnow().isoformat() + 'Z'
    }
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
    print(f'Result saved to {out_path}')

if __name__ == '__main__':
    main()