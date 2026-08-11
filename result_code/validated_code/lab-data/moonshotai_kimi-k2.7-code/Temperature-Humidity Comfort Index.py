import json
import sys
import math
import csv
"""
Task: Temperature-Humidity Comfort Index
Description: Compute a lightweight comfort index from concurrent temperature and humidity readings for each mote, classifying conditions as comfortable, dry, humid, or hot for localized environmental awareness.
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

import os, sys, csv, json, math
from pathlib import Path
from datetime import datetime

TASK_NAME = 'Temperature-Humidity Comfort Index'
OUTPUT_DIR = Path('/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_moonshotai_kimi-k2.7-code_anthropic_claude-3-haiku_run1')

def find_data_file():
    curr = Path(__file__).resolve().parent
    root = curr
    while root.name and not (root / 'data').exists():
        parent = root.parent
        if parent == root:
            break
        root = parent
    for name in ['raw_data.csv', 'raw_data.txt']:
        p = root / 'data' / 'lab-data' / name
        if p.exists():
            return p
    return None

MISSING = {'', 'NA', 'N/A', 'None', 'None'}

def to_float(val, col):
    if val is None:
        return None
    s = str(val).strip()
    if s in MISSING:
        return None
    try:
        return float(s)
    except ValueError:
        print('Warning: invalid numeric value in column', repr(col), ':', repr(s), file=sys.stderr)
        return None

def discomfort_index(t, rh):
    return t - 0.55 * (1.0 - 0.01 * rh) * (t - 14.5)

def classify(di):
    if di < 21:
        return 'comfortable'
    if di < 24:
        return 'slightly_uncomfortable'
    if di < 27:
        return 'uncomfortable'
    return 'very_uncomfortable'

def main():
    strict = '--strict' in sys.argv
    data_file = find_data_file()
    if not data_file:
        print('Error: raw_data.csv/txt not found under data/lab-data', file=sys.stderr)
        sys.exit(1)
    required = {'temperature', 'humidity', 'moteid'}
    per_mote = {}
    total = 0
    dropped = 0
    with open(data_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            row = {k.lower(): v for k, v in row.items()}
            if not required.issubset(row.keys()):
                if strict:
                    dropped += 1
                    continue
                print('Warning: missing columns', required - row.keys(), 'in row', total, file=sys.stderr)
                dropped += 1
                continue
            mote = row.get('moteid', '').strip()
            t = to_float(row.get('temperature'), 'temperature')
            rh = to_float(row.get('humidity'), 'humidity')
            if mote == '' or t is None or rh is None:
                dropped += 1
                continue
            di = discomfort_index(t, rh)
            cat = classify(di)
            rec = per_mote.setdefault(mote, {'readings': 0, 'di_sum': 0.0, 'di_min': math.inf, 'di_max': -math.inf, 'categories': {}})
            rec['readings'] += 1
            rec['di_sum'] += di
            rec['di_min'] = min(rec['di_min'], di)
            rec['di_max'] = max(rec['di_max'], di)
            rec['categories'][cat] = rec['categories'].get(cat, 0) + 1
    summary = []
    for mote in sorted(per_mote.keys(), key=lambda x: int(x) if x.isdigit() else x):
        rec = per_mote[mote]
        n = rec['readings']
        avg_di = rec['di_sum'] / n if n else math.nan
        summary.append({
            'moteid': mote,
            'readings': n,
            'avg_discomfort_index': round(avg_di, 3),
            'min_discomfort_index': round(rec['di_min'], 3) if math.isfinite(rec['di_min']) else None,
            'max_discomfort_index': round(rec['di_max'], 3) if math.isfinite(rec['di_max']) else None,
            'dominant_condition': max(rec['categories'], key=rec['categories'].get) if rec['categories'] else None,
            'category_counts': rec['categories']
        })
    result = {
        'task_name': TASK_NAME,
        'description': 'Per-mote temperature-humidity discomfort index and comfort classification.',
        'result_summary': summary,
        'result_generated_at': datetime.now().isoformat()
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / (TASK_NAME.replace(' ', '_').replace('-', '_') + '_result.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
    print('Processed', total, 'rows, dropped', dropped, '. Wrote', len(summary), 'mote summaries to', out_path)

if __name__ == '__main__':
    main()