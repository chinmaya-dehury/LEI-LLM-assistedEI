import json
import sys
import csv
"""
Task: Soil Fertility Index Snapshot
Description: Calculate and report the current Soil Fertility Index (SFI) based on organic matter and NPK levels, classifying soil fertility as low, medium, or high.
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

DATA_FILE_PATH = os.path.join(_root_dir, "data", "agri-data", "raw_data.csv")
if not os.path.exists(DATA_FILE_PATH):
    DATA_FILE_PATH = os.path.join(_root_dir, "data", "agri-data", "raw_data.txt")

METADATA_FILE_PATH = os.path.join(_root_dir, "data", "agri-data", "metadata.json")
OUTPUT_DIR = os.path.join(_root_dir, "output", "agri-data")
os.makedirs(OUTPUT_DIR, exist_ok=True)

import os, sys, csv, json, math, argparse
from pathlib import Path
from datetime import datetime

TASK_NAME = 'soil_fertility_index_snapshot'
DESCRIPTION = 'Calculate and report the current Soil Fertility Index (SFI) based on organic matter and NPK levels, classifying soil fertility as low, medium, or high.'

def find_data_file():
    curr = Path(__file__).resolve().parent
    root = curr
    while root.name and not (root / 'data').exists():
        parent = root.parent
        if parent == root:
            break
        root = parent
    for name in ('raw_data.csv', 'raw_data.txt'):
        p = root / 'data' / 'agri-data' / name
        if p.exists():
            return p
    return None

def is_missing(v):
    if v is None:
        return True
    s = str(v).strip()
    return s == '' or s.upper() in ('NA', 'N/A', 'NULL', 'NONE')

def to_float(v, col):
    if is_missing(v):
        return None
    try:
        return float(v)
    except Exception:
        print(f'Warning: invalid numeric value in column {col}: {v!r}', file=sys.stderr)
        return None

def classify_sfi(sfi):
    if sfi < 0.4:
        return 'low'
    elif sfi < 0.7:
        return 'medium'
    else:
        return 'high'

def main():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument('--strict', action='store_true', help='Fail if any required value is missing/invalid')
    args = parser.parse_args()

    data_file = find_data_file()
    if not data_file:
        print('Error: raw_data.csv/txt not found under data/agri-data/', file=sys.stderr)
        sys.exit(1)

    required = ('n', 'p', 'k', 'organic_matter')
    records = []
    dropped = 0
    total = 0

    with open(data_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            row = {k.lower(): v for k, v in row.items()}
            vals = {}
            missing = False
            for col in required:
                val = to_float(row.get(col), col)
                if val is None:
                    missing = True
                    break
                vals[col] = val
            if missing:
                dropped += 1
                if args.strict:
                    print(f'Error: missing/invalid required value in row {total}', file=sys.stderr)
                    sys.exit(1)
                continue

            sfi = (vals['n']/200.0 + vals['p']/200.0 + vals['k']/200.0 + vals['organic_matter']/100.0) / 4.0
            sfi = round(sfi, 4)
            records.append({
                'row': total,
                'N': vals['n'],
                'P': vals['p'],
                'K': vals['k'],
                'Organic_Matter': vals['organic_matter'],
                'SFI': sfi,
                'fertility_class': classify_sfi(sfi)
            })

    counts = {'low': 0, 'medium': 0, 'high': 0}
    for r in records:
        counts[r['fertility_class']] += 1

    summary = {
        'total_rows': total,
        'valid_rows': len(records),
        'dropped_rows': dropped,
        'class_distribution': counts,
        'sample_records': records[:5]
    }

    result = {
        'task_name': TASK_NAME,
        'description': DESCRIPTION,
        'result_summary': [summary],
        'result_generated_at': datetime.utcnow().isoformat() + 'Z'
    }

    out_dir = Path('/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_moonshotai_kimi-k2.7-code_google_gemini-3.1-flash-lite_run2')
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f'{TASK_NAME}_result.json'
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)

    print(f'Saved {len(records)} records to {out_file}')
    print(f'Class distribution: {counts}')

if __name__ == '__main__':
    main()