"""
Task: Frost Risk Flag
Description: Monitor the frost risk index and temperature to issue a warning when conditions indicate a possible frost event that could damage crops.
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

#!/usr/bin/env python3
import os
import sys
import csv
import json
import math
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path('/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_moonshotai_kimi-k2.7-code_google_gemini-3.1-flash-lite_run2')
TASK_NAME = 'Frost Risk Flag'
MISSING = {'', 'NA', 'N/A', 'None', 'None'}


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


def to_float(value, col):
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        if value in MISSING:
            return None
    try:
        return float(value)
    except Exception:
        print(f'Warning: invalid numeric value in column {col!r}: {value!r}', file=sys.stderr)
        return None


def main():
    strict = '--strict' in sys.argv
    data_file = find_data_file()
    if not data_file:
        print('Error: raw_data.csv/txt not found under data/agri-data', file=sys.stderr)
        sys.exit(1)

    rows = []
    dropped = 0
    with open(data_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=2):
            row = {k.lower().strip(): v for k, v in row.items()}
            temp = to_float(row.get('temperature'), 'temperature')
            frost = to_float(row.get('frost_risk'), 'frost_risk')
            if temp is None or frost is None:
                dropped += 1
                continue
            rows.append({'temperature': temp, 'frost_risk': frost, 'index': i})

    total = len(rows) + dropped
    if strict and dropped:
        print(f'Strict mode: dropped {dropped} rows due to missing/invalid data', file=sys.stderr)
        sys.exit(2)

    frost_threshold = 0.3
    temp_threshold = 2.0
    warnings = []
    for r in rows:
        if r['frost_risk'] >= frost_threshold or r['temperature'] <= temp_threshold:
            warnings.append({'row': r['index'], 'temperature': r['temperature'], 'frost_risk': r['frost_risk']})

    summary = {
        'total_rows': total,
        'valid_rows': len(rows),
        'dropped_rows': dropped,
        'frost_warnings': len(warnings),
        'thresholds': {'frost_risk': frost_threshold, 'temperature_c': temp_threshold},
        'warning_examples': warnings[:10]
    }

    result = {
        'task_name': TASK_NAME,
        'description': 'Flag rows where frost risk index or temperature indicates a possible frost event.',
        'result_summary': [summary],
        'result_generated_at': datetime.utcnow().isoformat() + 'Z'
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f'{TASK_NAME.replace(" ", "_").lower()}_result.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)

    print(f'{TASK_NAME}: {len(warnings)} warnings out of {len(rows)} valid rows. Saved to {out_path}')


if __name__ == '__main__':
    main()